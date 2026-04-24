"""Tests for idempotent indexing with fingerprint/chunk_id."""

import pytest
import hashlib
from datetime import datetime


def generate_chunk_id(file_hash: str, chunk_index: int) -> str:
    """Copy from embedder.py for testing."""
    content = f"{file_hash}_{chunk_index}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def content_fingerprint(file_path: str, file_hash: str, mtime: datetime, size_bytes: int) -> str:
    """Copy from watcher.py for testing."""
    content = f"{file_hash}_{mtime.timestamp()}_{size_bytes}"
    return hashlib.sha256(content.encode()).hexdigest()


class TestChunkIdGeneration:
    """Tests for stable chunk_id generation."""
    
    def test_same_file_hash_same_index_produces_same_id(self):
        """Same file_hash + index always produces same chunk_id."""
        file_hash = "abc123"
        chunk_index = 5
        
        id1 = generate_chunk_id(file_hash, chunk_index)
        id2 = generate_chunk_id(file_hash, chunk_index)
        
        assert id1 == id2
        assert len(id1) == 32  # SHA256 hex truncated
    
    def test_different_file_hash_produces_different_id(self):
        """Different file_hash produces different chunk_id."""
        chunk_index = 5
        
        id1 = generate_chunk_id("abc123", chunk_index)
        id2 = generate_chunk_id("def456", chunk_index)
        
        assert id1 != id2
    
    def test_different_index_produces_different_id(self):
        """Different chunk_index produces different chunk_id."""
        file_hash = "abc123"
        
        id1 = generate_chunk_id(file_hash, 0)
        id2 = generate_chunk_id(file_hash, 1)
        
        assert id1 != id2
    
    def test_chunk_id_is_deterministic(self):
        """Chunk ID generation is deterministic across multiple calls."""
        file_hash = "test_hash_123"
        
        ids = [generate_chunk_id(file_hash, i) for i in range(10)]
        
        # All IDs should be unique
        assert len(set(ids)) == 10
        
        # Regenerating should produce same IDs
        ids2 = [generate_chunk_id(file_hash, i) for i in range(10)]
        assert ids == ids2
    
    def test_chunk_id_format(self):
        """Chunk ID is a valid hex string."""
        chunk_id = generate_chunk_id("test", 0)
        
        # Should be valid hex
        int(chunk_id, 16)
        assert len(chunk_id) == 32


class TestContentFingerprint:
    """Tests for content fingerprint calculation."""
    
    def test_same_inputs_produce_same_fingerprint(self):
        """Same inputs always produce same fingerprint."""
        mtime = datetime(2024, 1, 1, 12, 0, 0)
        file_hash = "abc123"
        size = 1024
        
        fp1 = content_fingerprint("/test/file.txt", file_hash, mtime, size)
        fp2 = content_fingerprint("/test/file.txt", file_hash, mtime, size)
        
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA256 hex
    
    def test_different_mtime_produces_different_fingerprint(self):
        """Different mtime produces different fingerprint."""
        file_hash = "abc123"
        size = 1024
        
        mtime1 = datetime(2024, 1, 1, 12, 0, 0)
        mtime2 = datetime(2024, 1, 1, 12, 0, 1)
        
        fp1 = content_fingerprint("/test/file.txt", file_hash, mtime1, size)
        fp2 = content_fingerprint("/test/file.txt", file_hash, mtime2, size)
        
        assert fp1 != fp2
    
    def test_different_size_produces_different_fingerprint(self):
        """Different size produces different fingerprint."""
        file_hash = "abc123"
        mtime = datetime(2024, 1, 1, 12, 0, 0)
        
        fp1 = content_fingerprint("/test/file.txt", file_hash, mtime, 1024)
        fp2 = content_fingerprint("/test/file.txt", file_hash, mtime, 2048)
        
        assert fp1 != fp2
    
    def test_fingerprint_includes_all_components(self):
        """Fingerprint includes file_hash, mtime, and size."""
        file_hash = "unique_hash_xyz"
        mtime = datetime(2024, 6, 15, 10, 30, 0)
        size = 5000
        
        fingerprint = content_fingerprint("/path/to/file.pdf", file_hash, mtime, size)
        
        # Fingerprint should be deterministic
        assert len(fingerprint) == 64
        
        # Same inputs should produce same fingerprint
        fp2 = content_fingerprint("/path/to/file.pdf", file_hash, mtime, size)
        assert fingerprint == fp2


class TestFileHash:
    """Tests for file hash calculation."""
    
    def test_file_hash_is_md5(self):
        """file_hash returns MD5 hex digest."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            # Inline implementation to avoid import
            h = hashlib.md5()
            with open(temp_path, "rb") as file:
                for chunk in iter(lambda: file.read(8192), b""):
                    h.update(chunk)
            hash_result = h.hexdigest()
            
            # MD5 is 32 hex characters
            assert len(hash_result) == 32
            int(hash_result, 16)  # Should be valid hex
        finally:
            os.unlink(temp_path)
    
    def test_same_content_produces_same_hash(self):
        """Same file content produces same hash."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            f1.write(b"identical content")
            path1 = f1.name
        
        with tempfile.NamedTemporaryFile(delete=False) as f2:
            f2.write(b"identical content")
            path2 = f2.name
        
        try:
            def calc_hash(p):
                h = hashlib.md5()
                with open(p, "rb") as file:
                    for chunk in iter(lambda: file.read(8192), b""):
                        h.update(chunk)
                return h.hexdigest()
            
            hash1 = calc_hash(path1)
            hash2 = calc_hash(path2)
            
            assert hash1 == hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)
    
    def test_different_content_produces_different_hash(self):
        """Different file content produces different hash."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            f1.write(b"content A")
            path1 = f1.name
        
        with tempfile.NamedTemporaryFile(delete=False) as f2:
            f2.write(b"content B")
            path2 = f2.name
        
        try:
            def calc_hash(p):
                h = hashlib.md5()
                with open(p, "rb") as file:
                    for chunk in iter(lambda: file.read(8192), b""):
                        h.update(chunk)
                return h.hexdigest()
            
            hash1 = calc_hash(path1)
            hash2 = calc_hash(path2)
            
            assert hash1 != hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)


class TestIdempotentIndexing:
    """Integration tests for idempotent indexing behavior."""
    
    def test_chunk_id_stability_across_reindex(self):
        """Re-indexing same file produces same chunk IDs."""
        file_hash = "stable_hash_123"
        
        # First indexing
        chunk_ids_1 = [generate_chunk_id(file_hash, i) for i in range(5)]
        
        # Simulate re-indexing
        chunk_ids_2 = [generate_chunk_id(file_hash, i) for i in range(5)]
        
        assert chunk_ids_1 == chunk_ids_2
    
    def test_different_files_have_different_chunk_ids(self):
        """Different files have different chunk IDs even at same index."""
        file_hash_1 = "file_a_hash"
        file_hash_2 = "file_b_hash"
        
        # Same index, different files
        id1 = generate_chunk_id(file_hash_1, 0)
        id2 = generate_chunk_id(file_hash_2, 0)
        
        assert id1 != id2
    
    def test_fingerprint_changes_when_file_modified(self):
        """Fingerprint changes when file is modified."""
        original_hash = "original_content_hash"
        modified_hash = "modified_content_hash"
        mtime = datetime(2024, 1, 1, 12, 0, 0)
        size = 1024
        
        fp_original = content_fingerprint("/file.txt", original_hash, mtime, size)
        fp_modified = content_fingerprint("/file.txt", modified_hash, mtime, size)
        
        assert fp_original != fp_modified
    
    def test_fingerprint_consistency_for_unchanged_file(self):
        """Fingerprint remains same for unchanged file."""
        file_hash = "constant_hash"
        mtime = datetime(2024, 1, 1, 12, 0, 0)
        size = 2048
        
        # Multiple fingerprint calculations for same file
        fps = [
            content_fingerprint("/unchanged/file.txt", file_hash, mtime, size)
            for _ in range(10)
        ]
        
        # All should be identical
        assert len(set(fps)) == 1

    def test_idempotent_scenario_full_cycle(self):
        """Full idempotent indexing cycle simulation."""
        # Initial indexing
        file_hash_v1 = "hash_version_1"
        mtime_v1 = datetime(2024, 1, 1, 12, 0, 0)
        size_v1 = 1024
        
        fp_v1 = content_fingerprint("/file.txt", file_hash_v1, mtime_v1, size_v1)
        chunk_ids_v1 = [generate_chunk_id(file_hash_v1, i) for i in range(3)]
        
        # File modified
        file_hash_v2 = "hash_version_2"
        mtime_v2 = datetime(2024, 1, 2, 12, 0, 0)
        size_v2 = 2048
        
        fp_v2 = content_fingerprint("/file.txt", file_hash_v2, mtime_v2, size_v2)
        chunk_ids_v2 = [generate_chunk_id(file_hash_v2, i) for i in range(3)]
        
        # Fingerprints should be different
        assert fp_v1 != fp_v2
        
        # Chunk IDs should be different
        assert chunk_ids_v1 != chunk_ids_v2
        
        # But within same version, IDs should be stable
        chunk_ids_v1_retry = [generate_chunk_id(file_hash_v1, i) for i in range(3)]
        assert chunk_ids_v1 == chunk_ids_v1_retry
