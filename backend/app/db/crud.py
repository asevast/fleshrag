from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.db.models import IndexedFile, AppSetting, Conversation, Message, TokenLog
from typing import Optional, List, Dict, Any


def get_file_by_path(db: Session, path: str):
    return db.query(IndexedFile).filter(IndexedFile.path == path).first()


def create_or_update_file(db: Session, path: str, filename: str, file_hash: str, file_type: str, mtime, chunk_count: int = 0, status: str = "pending", error_message: str = None):
    file = get_file_by_path(db, path)
    if file:
        file.file_hash = file_hash
        file.mtime = mtime
        file.chunk_count = chunk_count
        file.status = status
        file.error_message = error_message
    else:
        file = IndexedFile(
            path=path,
            filename=filename,
            file_hash=file_hash,
            file_type=file_type,
            mtime=mtime,
            chunk_count=chunk_count,
            status=status,
            error_message=error_message,
        )
        db.add(file)
    db.commit()
    db.refresh(file)
    return file


def get_indexed_files(db: Session, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None):
    query = db.query(IndexedFile)
    
    if filters:
        if filters.get("file_types"):
            query = query.filter(IndexedFile.file_type.in_(filters["file_types"]))
        if filters.get("date_after"):
            date_after = datetime.fromisoformat(filters["date_after"].replace("Z", "+00:00"))
            query = query.filter(IndexedFile.mtime >= date_after)
        if filters.get("date_before"):
            date_before = datetime.fromisoformat(filters["date_before"].replace("Z", "+00:00"))
            query = query.filter(IndexedFile.mtime <= date_before)
        if filters.get("status"):
            query = query.filter(IndexedFile.status == filters["status"])
        if filters.get("path_contains"):
            query = query.filter(IndexedFile.path.contains(filters["path_contains"]))
    
    return query.offset(skip).limit(limit).all()


def get_index_stats(db: Session) -> dict:
    counts = db.query(
        IndexedFile.status,
        func.count(IndexedFile.id)
    ).group_by(IndexedFile.status).all()
    total = db.query(func.count(IndexedFile.id)).scalar()
    stats = {status: count for status, count in counts}
    stats["total"] = total or 0
    stats.setdefault("indexed", 0)
    stats.setdefault("pending", 0)
    stats.setdefault("error", 0)
    stats.setdefault("empty", 0)
    return stats


def get_available_file_types(db: Session) -> List[str]:
    result = db.query(IndexedFile.file_type).distinct().all()
    return [rt[0] for rt in result if rt[0]]


# Settings CRUD
def get_setting(db: Session, key: str, default: str = None) -> Optional[str]:
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str):
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if setting:
        setting.value = value
        setting.updated_at = datetime.utcnow()
    else:
        setting = AppSetting(key=key, value=value)
        db.add(setting)
    db.commit()
    return setting


def get_all_settings(db: Session) -> Dict[str, str]:
    settings = db.query(AppSetting).all()
    return {s.key: s.value for s in settings}


def log_token_usage(
    db: Session,
    *,
    provider: str,
    model: str,
    op_type: str,
    input_tok: int = 0,
    output_tok: int = 0,
    cost_usd: float = 0.0,
    session_id: Optional[str] = None,
) -> TokenLog:
    entry = TokenLog(
        provider=provider,
        model=model,
        op_type=op_type,
        input_tok=input_tok,
        output_tok=output_tok,
        cost_usd=cost_usd,
        session_id=session_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# Conversation CRUD
def create_conversation(db: Session, title: Optional[str] = None) -> Conversation:
    conv = Conversation(title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversation(db: Session, conv_id: int) -> Optional[Conversation]:
    return db.query(Conversation).options(joinedload(Conversation.messages)).filter(Conversation.id == conv_id).first()


def get_conversations(db: Session, limit: int = 20) -> List[Conversation]:
    return db.query(Conversation).order_by(Conversation.updated_at.desc()).limit(limit).all()


def delete_conversation(db: Session, conv_id: int):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if conv:
        db.delete(conv)
        db.commit()
        return True
    return False


def add_message(db: Session, conv_id: int, role: str, content: str, sources: Optional[List[Dict]] = None) -> Message:
    import json as json_module
    sources_json = json_module.dumps(sources) if sources else None
    msg = Message(conversation_id=conv_id, role=role, content=content, sources=sources_json)
    db.add(msg)
    
    # Обновляем updated_at у conversation
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if conv:
        conv.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(msg)
    return msg


def get_messages(db: Session, conv_id: int) -> List[Message]:
    return db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at.asc()).all()
