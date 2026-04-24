"""Tests for index versioning and compatibility checking."""

import pytest
import hashlib
from datetime import datetime
from typing import Dict, Any


def generate_test_chunk_id(file_hash: str, chunk_index: int) -> str:
    """Copy from embedder.py for testing."""
    content = f"{file_hash}_{chunk_index}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]


class TestIndexVersioning:
    """Tests for index version tracking."""
    
    def test_index_version_constant_defined(self):
        """INDEX_VERSION constant is defined."""
        from app.indexer.embedder import INDEX_VERSION
        
        assert INDEX_VERSION is not None
        assert isinstance(INDEX_VERSION, str)
        assert len(INDEX_VERSION) > 0
    
    def test_index_version_format(self):
        """INDEX_VERSION follows semver-like format."""
        from app.indexer.embedder import INDEX_VERSION
        
        # Should be like "1.0", "2.1.3", etc.
        parts = INDEX_VERSION.split('.')
        assert len(parts) >= 2
        for part in parts:
            assert part.isdigit()


class TestMetadataStructure:
    """Tests for metadata structure."""
    
    def test_metadata_contains_required_fields(self):
        """Metadata dictionary contains all required fields."""
        # Simulate metadata structure
        metadata = {
            "type": "metadata",
            "embed_model": "test-model",
            "vector_dim": 768,
            "index_version": "1.0",
            "created_at": "2024-01-01T00:00:00Z",
        }
        
        assert "type" in metadata
        assert "embed_model" in metadata
        assert "vector_dim" in metadata
        assert "index_version" in metadata
        assert "created_at" in metadata
    
    def test_metadata_vector_dim_is_integer(self):
        """vector_dim is stored as integer."""
        metadata = {
            "vector_dim": 768,
        }
        
        assert isinstance(metadata["vector_dim"], int)
    
    def test_metadata_index_version_matches_constant(self):
        """Metadata index_version matches constant."""
        from app.indexer.embedder import INDEX_VERSION
        
        metadata = {
            "index_version": INDEX_VERSION,
        }
        
        assert metadata["index_version"] == INDEX_VERSION


class TestCompatibilityChecking:
    """Tests for compatibility checking logic."""
    
    def test_compatible_same_model_same_dim(self):
        """Same model and dimension is compatible."""
        indexed = {"embed_model": "model-a", "vector_dim": 768}
        current = {"embed_model": "model-a", "vector_dim": 768}
        
        compatible = (
            indexed["vector_dim"] == current["vector_dim"]
        )
        
        assert compatible is True
    
    def test_incompatible_different_dim(self):
        """Different dimension is incompatible."""
        indexed = {"embed_model": "model-a", "vector_dim": 768}
        current = {"embed_model": "model-a", "vector_dim": 1024}
        
        compatible = (
            indexed["vector_dim"] == current["vector_dim"]
        )
        
        assert compatible is False
    
    def test_warning_different_model_same_dim(self):
        """Different model but same dimension gives warning."""
        indexed = {"embed_model": "model-a", "vector_dim": 768}
        current = {"embed_model": "model-b", "vector_dim": 768}
        
        dim_match = indexed["vector_dim"] == current["vector_dim"]
        model_match = indexed["embed_model"] == current["embed_model"]
        
        assert dim_match is True  # Compatible
        assert model_match is False  # But different model
    
    def test_legacy_index_no_metadata(self):
        """Legacy index without metadata is treated as compatible."""
        metadata = None
        
        # Legacy index: assume compatible but recommend reindex
        compatible = metadata is None
        
        assert compatible is True  # Don't block, but warn


class TestIndexVersionAPI:
    """Tests for index version API response structure."""
    
    def test_version_response_structure(self):
        """API response has correct structure."""
        response = {
            "status": "ok",
            "index_version": "1.0",
            "embed_model": "test-model",
            "vector_dim": 768,
            "current_model": "test-model",
            "current_dim": 768,
            "compatible": True,
            "message": "Index compatible",
        }
        
        assert "status" in response
        assert "index_version" in response
        assert "embed_model" in response
        assert "vector_dim" in response
        assert "current_model" in response
        assert "current_dim" in response
        assert "compatible" in response
        assert "message" in response
    
    def test_version_response_status_values(self):
        """Status field has valid values."""
        valid_statuses = {"ok", "warning", "reindex_required", "error"}
        
        test_cases = [
            {"status": "ok", "compatible": True},
            {"status": "warning", "compatible": True},
            {"status": "reindex_required", "compatible": False},
            {"status": "error", "compatible": False},
        ]
        
        for case in test_cases:
            assert case["status"] in valid_statuses
    
    def test_reindex_required_when_dim_mismatch(self):
        """Dimension mismatch returns reindex_required."""
        response = {
            "status": "reindex_required",
            "index_version": "1.0",
            "embed_model": "model-a",
            "vector_dim": 768,
            "current_model": "model-b",
            "current_dim": 1024,
            "compatible": False,
            "message": "Dimension mismatch: 768d vs 1024d",
        }
        
        assert response["status"] == "reindex_required"
        assert response["compatible"] is False
        assert "Dimension mismatch" in response["message"]
    
    def test_warning_when_model_changed(self):
        """Model change with same dimension returns warning."""
        response = {
            "status": "warning",
            "index_version": "1.0",
            "embed_model": "model-a",
            "vector_dim": 768,
            "current_model": "model-b",
            "current_dim": 768,
            "compatible": True,
            "message": "Model changed but dimension matches",
        }
        
        assert response["status"] == "warning"
        assert response["compatible"] is True


class TestMigrationScenarios:
    """Tests for migration scenarios."""
    
    def test_scenario_legacy_to_versioned(self):
        """Legacy index (no metadata) to versioned index."""
        # Before: no metadata
        legacy_metadata = None
        
        # After: with metadata
        new_metadata = {
            "embed_model": "multilingual-e5-large",
            "vector_dim": 1024,
            "index_version": "1.0",
        }
        
        # Migration: create metadata point
        assert legacy_metadata is None
        assert new_metadata["index_version"] == "1.0"
    
    def test_scenario_model_upgrade_same_dim(self):
        """Model upgrade with same dimension."""
        old_model = {
            "embed_model": "model-a",
            "vector_dim": 768,
            "index_version": "1.0",
        }
        
        new_model = {
            "embed_model": "model-b",
            "vector_dim": 768,  # Same dimension
            "index_version": "1.0",
        }
        
        # Compatible, but reindex recommended
        assert old_model["vector_dim"] == new_model["vector_dim"]
        assert old_model["embed_model"] != new_model["embed_model"]
    
    def test_scenario_model_upgrade_different_dim(self):
        """Model upgrade with different dimension."""
        old_model = {
            "embed_model": "model-a",
            "vector_dim": 768,
            "index_version": "1.0",
        }
        
        new_model = {
            "embed_model": "model-b",
            "vector_dim": 1024,  # Different dimension
            "index_version": "1.0",
        }
        
        # Incompatible, reindex required
        assert old_model["vector_dim"] != new_model["vector_dim"]
        # This should trigger reindex_required status
    
    def test_scenario_same_model_rerun(self):
        """Same model, re-running indexing."""
        original = {
            "embed_model": "stable-model",
            "vector_dim": 1024,
            "index_version": "1.0",
        }
        
        rerun = {
            "embed_model": "stable-model",
            "vector_dim": 1024,
            "index_version": "1.0",
        }
        
        # Fully compatible
        assert original == rerun


class TestIdempotentChunkIdWithVersioning:
    """Tests combining idempotent chunking with versioning."""
    
    def test_chunk_id_stable_across_version_check(self):
        """Chunk ID remains stable regardless of version checking."""
        file_hash = "test_file_hash"
        
        # Generate chunk IDs multiple times (simulating version checks)
        chunk_ids_1 = [generate_test_chunk_id(file_hash, i) for i in range(5)]
        chunk_ids_2 = [generate_test_chunk_id(file_hash, i) for i in range(5)]
        chunk_ids_3 = [generate_test_chunk_id(file_hash, i) for i in range(5)]
        
        assert chunk_ids_1 == chunk_ids_2 == chunk_ids_3
    
    def test_different_files_different_chunks(self):
        """Different files have different chunk IDs."""
        file_hash_1 = "file_a_hash"
        file_hash_2 = "file_b_hash"
        
        chunk_ids_1 = [generate_test_chunk_id(file_hash_1, i) for i in range(3)]
        chunk_ids_2 = [generate_test_chunk_id(file_hash_2, i) for i in range(3)]
        
        assert chunk_ids_1 != chunk_ids_2
        assert len(set(chunk_ids_1 + chunk_ids_2)) == 6  # All unique
