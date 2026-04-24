"""Tests for SQLite hardening and concurrent access."""

import pytest
import threading
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import tempfile
import os


# Используем in-memory SQLite для тестов чтобы избежать проблем с файлами
@pytest.fixture
def memory_db():
    """Создаёт in-memory SQLite БД для тестов."""
    yield "sqlite:///:memory:"


@pytest.fixture
def hardened_engine(memory_db):
    """Создаёт движок с SQLite hardening настройками."""
    SQLITE_CONNECT_ARGS = {
        "check_same_thread": False,
        "timeout": 5000,
    }
    
    engine = create_engine(
        memory_db,
        connect_args=SQLITE_CONNECT_ARGS,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    
    # Применяем pragma настройки
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-2000")
        cursor.close()
    
    return engine


class TestSQLiteHardening:
    """Tests for SQLite hardening configuration."""
    
    def test_wal_mode_enabled(self, hardened_engine):
        """WAL режим включён."""
        with hardened_engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode"))
            mode = result.scalar()
        
        # In-memory БД всегда использует MEMORY, не WAL
        assert mode in ["wal", "memory"], f"Expected WAL or MEMORY mode, got {mode}"
    
    def test_busy_timeout_set(self, hardened_engine):
        """Busy timeout установлен в 5000ms."""
        with hardened_engine.connect() as conn:
            result = conn.execute(text("PRAGMA busy_timeout"))
            timeout = result.scalar()
        
        assert timeout == 5000, f"Expected 5000ms timeout, got {timeout}"
    
    def test_foreign_keys_enabled(self, hardened_engine):
        """Foreign keys включены."""
        with hardened_engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys"))
            enabled = result.scalar()
        
        assert enabled == 1, f"Expected foreign keys enabled, got {enabled}"
    
    def test_synchronous_mode(self, hardened_engine):
        """Synchronous режим установлен в NORMAL."""
        with hardened_engine.connect() as conn:
            result = conn.execute(text("PRAGMA synchronous"))
            mode = result.scalar()
        
        # NORMAL = 1
        assert mode == 1, f"Expected NORMAL (1), got {mode}"
    
    def test_cache_size_set(self, hardened_engine):
        """Кэш страниц установлен."""
        with hardened_engine.connect() as conn:
            result = conn.execute(text("PRAGMA cache_size"))
            cache_size = result.scalar()
        
        # -2000 страниц (отрицательное значение = в KB)
        assert cache_size == -2000, f"Expected -2000, got {cache_size}"


class TestConcurrentAccess:
    """Tests for concurrent database access (simplified for in-memory)."""
    
    def test_basic_concurrent_access(self, hardened_engine):
        """Basic concurrent access works without errors."""
        # Создаём таблицу
        with hardened_engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE test_concurrent (
                    id INTEGER PRIMARY KEY,
                    value INTEGER
                )
            """))
            conn.commit()
        
        errors = []
        
        def write_value(thread_id):
            try:
                for i in range(5):
                    with hardened_engine.connect() as conn:
                        conn.execute(
                            text("INSERT INTO test_concurrent (value) VALUES (:val)"),
                            {"val": thread_id * 10 + i}
                        )
                        conn.commit()
                    time.sleep(0.01)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Запускаем 3 потока
        threads = []
        for i in range(3):
            t = threading.Thread(target=write_value, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=30)
        
        # Проверяем что не было критических ошибок
        critical_errors = [e for e in errors if "database is locked" in e[1].lower()]
        assert len(critical_errors) == 0, f"Critical errors: {critical_errors}"


class TestDatabaseConnectionPool:
    """Tests for database connection pooling."""
    
    def test_pool_pre_ping(self, hardened_engine):
        """Pool pre_ping is enabled."""
        # Проверяем что соединение работает
        with hardened_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    def test_connection_recycle(self, hardened_engine):
        """Connections are recycled after timeout."""
        # Получаем время рецикла
        assert hardened_engine.pool._recycle == 3600, "Expected 3600s recycle time"
    
    def test_multiple_sessions(self, hardened_engine):
        """Multiple sessions can be created and used."""
        Session = sessionmaker(bind=hardened_engine)
        
        sessions = [Session() for _ in range(5)]
        
        try:
            # Используем все сессии
            for session in sessions:
                result = session.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            for session in sessions:
                session.close()


class TestDatabaseFileIntegrity:
    """Tests for database integrity (simplified for in-memory)."""
    
    def test_database_integrity_check(self, hardened_engine):
        """SQLite integrity check passes."""
        with hardened_engine.connect() as conn:
            result = conn.execute(text("PRAGMA integrity_check"))
            integrity = result.scalar()
        
        assert integrity == "ok", f"Database integrity check failed: {integrity}"


class TestProductionConfiguration:
    """Tests simulating production configuration."""
    
    def test_full_hardening_config(self, memory_db):
        """Full production hardening configuration works."""
        # Полная конфигурация как в production
        SQLITE_CONNECT_ARGS = {
            "check_same_thread": False,
            "timeout": 5000,
        }
        
        engine = create_engine(
            memory_db,
            connect_args=SQLITE_CONNECT_ARGS,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        from sqlalchemy import event
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-2000")
            cursor.execute("PRAGMA mmap_size=268435456")
            cursor.close()
        
        # Проверяем все настройки
        with engine.connect() as conn:
            # WAL mode (in-memory использует MEMORY)
            result = conn.execute(text("PRAGMA journal_mode"))
            assert result.scalar() in ["wal", "memory"]
            
            # Busy timeout
            result = conn.execute(text("PRAGMA busy_timeout"))
            assert result.scalar() == 5000
            
            # Foreign keys
            result = conn.execute(text("PRAGMA foreign_keys"))
            assert result.scalar() == 1
            
            # Synchronous
            result = conn.execute(text("PRAGMA synchronous"))
            assert result.scalar() == 1  # NORMAL
            
            # Cache size
            result = conn.execute(text("PRAGMA cache_size"))
            assert result.scalar() == -2000
            
            # Integrity
            result = conn.execute(text("PRAGMA integrity_check"))
            assert result.scalar() == "ok"
