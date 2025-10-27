"""
Unit tests for pgvector-based semantic search implementation.

Tests verify:
- Embedding generation with sentence-transformers
- PostgreSQL storage with pgvector
- Incremental indexing based on file mtime
- Semantic search with cosine similarity
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List
import tempfile
import os

# Will be available after implementation
from app.services.kb.kb_semantic_search import SemanticIndexer


@pytest.fixture
async def test_indexer(tmp_path):
    """Create a test indexer with temporary KB path."""
    # Create test KB structure
    kb_path = tmp_path / "kb"
    kb_path.mkdir()

    # Create test markdown files
    (kb_path / "doc1.md").write_text("# AI Game Design\n\nArtificial intelligence in games.")
    (kb_path / "doc2.md").write_text("# Unity Development\n\nGame engine programming.")
    (kb_path / "doc3.md").write_text("# AR Waypoints\n\nLocation-based gameplay.")

    # Mock settings
    class MockSettings:
        KB_PATH = str(kb_path)
        KB_SEMANTIC_SEARCH_ENABLED = True
        KB_SEMANTIC_CACHE_TTL = 3600
        KB_MULTI_USER_ENABLED = False

    # Create indexer with mocked settings
    import app.shared.config as config_module
    original_settings = config_module.settings
    config_module.settings = MockSettings()

    indexer = SemanticIndexer()

    yield indexer

    # Cleanup
    config_module.settings = original_settings
    await indexer.shutdown()


@pytest.fixture
async def db_connection():
    """Get database connection for testing."""
    from app.shared.database import get_database
    db = get_database()

    # Clean up test data before each test
    async with db.acquire() as conn:
        await conn.execute("DELETE FROM kb_semantic_chunk_ids")
        await conn.execute("DELETE FROM kb_semantic_index_metadata")

    yield db

    # Clean up after test
    async with db.acquire() as conn:
        await conn.execute("DELETE FROM kb_semantic_chunk_ids")
        await conn.execute("DELETE FROM kb_semantic_index_metadata")


class TestPgvectorIndexing:
    """Test pgvector indexing functionality."""

    @pytest.mark.asyncio
    async def test_embedding_model_loading(self, test_indexer):
        """Test that embedding model loads successfully."""
        model = test_indexer._get_embedding_model()

        assert model is not None
        # Verify model can generate embeddings
        test_text = "This is a test sentence"
        embedding = model.encode(test_text)

        # all-MiniLM-L6-v2 produces 384-dimensional vectors
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_index_creates_embeddings(self, test_indexer, db_connection, tmp_path):
        """Test that indexing creates embeddings in PostgreSQL."""
        # Set up test KB path
        test_indexer.kb_path = tmp_path / "kb"

        # Index the namespace
        await test_indexer._index_namespace("root", test_indexer.kb_path)

        # Verify embeddings were created in database
        async with db_connection.acquire() as conn:
            # Check metadata table
            metadata_count = await conn.fetchval(
                "SELECT COUNT(*) FROM kb_semantic_index_metadata WHERE namespace = $1",
                "root"
            )
            assert metadata_count == 3, "Should have indexed 3 files"

            # Check chunk embeddings
            chunk_count = await conn.fetchval(
                "SELECT COUNT(*) FROM kb_semantic_chunk_ids WHERE embedding IS NOT NULL"
            )
            assert chunk_count > 0, "Should have created chunk embeddings"

            # Verify embedding dimensions
            sample_embedding = await conn.fetchval(
                "SELECT embedding FROM kb_semantic_chunk_ids LIMIT 1"
            )
            assert sample_embedding is not None
            # pgvector stores as string representation, check it's valid
            assert "384" in str(type(sample_embedding)) or len(sample_embedding) == 384

    @pytest.mark.asyncio
    async def test_metadata_tracking(self, test_indexer, db_connection, tmp_path):
        """Test that file metadata is tracked correctly."""
        test_indexer.kb_path = tmp_path / "kb"

        # Index files
        await test_indexer._index_namespace("root", test_indexer.kb_path)

        # Verify metadata was stored
        async with db_connection.acquire() as conn:
            metadata = await conn.fetch(
                """
                SELECT relative_path, mtime, num_chunks, namespace
                FROM kb_semantic_index_metadata
                WHERE namespace = $1
                ORDER BY relative_path
                """,
                "root"
            )

            assert len(metadata) == 3

            # Check each file has metadata
            paths = {row['relative_path'] for row in metadata}
            assert 'doc1.md' in paths
            assert 'doc2.md' in paths
            assert 'doc3.md' in paths

            # Verify mtime is reasonable (recent)
            for row in metadata:
                assert row['mtime'] > 0
                assert row['num_chunks'] > 0
                assert row['namespace'] == 'root'

    @pytest.mark.asyncio
    async def test_incremental_indexing_unchanged_files(self, test_indexer, db_connection, tmp_path):
        """Test that unchanged files are not reindexed."""
        test_indexer.kb_path = tmp_path / "kb"

        # First index
        await test_indexer._index_namespace("root", test_indexer.kb_path)

        # Get initial chunk count
        async with db_connection.acquire() as conn:
            initial_count = await conn.fetchval(
                "SELECT COUNT(*) FROM kb_semantic_chunk_ids"
            )

        # Reindex without changing files
        await test_indexer._index_namespace("root", test_indexer.kb_path)

        # Verify count is the same (no duplicates)
        async with db_connection.acquire() as conn:
            final_count = await conn.fetchval(
                "SELECT COUNT(*) FROM kb_semantic_chunk_ids"
            )

        assert final_count == initial_count, "Unchanged files should not create duplicate chunks"

    @pytest.mark.asyncio
    async def test_incremental_indexing_changed_file(self, test_indexer, db_connection, tmp_path):
        """Test that changed files are reindexed."""
        test_indexer.kb_path = tmp_path / "kb"

        # First index
        await test_indexer._index_namespace("root", test_indexer.kb_path)

        # Wait to ensure mtime difference
        await asyncio.sleep(0.1)

        # Modify one file
        doc1 = test_indexer.kb_path / "doc1.md"
        doc1.write_text("# AI Game Design\n\nArtificial intelligence in games.\n\nNew content added!")

        # Reindex
        await test_indexer._index_namespace("root", test_indexer.kb_path)

        # Verify the changed file was reindexed
        async with db_connection.acquire() as conn:
            # Check that doc1.md has updated mtime
            metadata = await conn.fetchrow(
                "SELECT mtime, num_chunks FROM kb_semantic_index_metadata WHERE relative_path = $1",
                "doc1.md"
            )

            assert metadata is not None
            # Should have more chunks now
            assert metadata['num_chunks'] >= 2, "Modified file should have been reindexed"


class TestPgvectorSemanticSearch:
    """Test semantic search with pgvector."""

    @pytest.mark.asyncio
    async def test_semantic_search_returns_results(self, test_indexer, db_connection, tmp_path):
        """Test that semantic search returns relevant results."""
        test_indexer.kb_path = tmp_path / "kb"

        # Index files
        await test_indexer._index_namespace("root", test_indexer.kb_path)

        # Search for AI-related content
        results = await test_indexer.search_semantic(
            query="artificial intelligence in video games",
            namespace="root",
            limit=5
        )

        assert results['success'] is True
        assert len(results['results']) > 0
        assert results['total_results'] > 0

        # Most relevant result should be doc1.md (AI Game Design)
        top_result = results['results'][0]
        assert 'doc1.md' in top_result['relative_path']
        assert top_result['relevance_score'] > 0.5, "Top result should have high similarity"

    @pytest.mark.asyncio
    async def test_semantic_search_ranking(self, test_indexer, db_connection, tmp_path):
        """Test that results are ranked by relevance."""
        test_indexer.kb_path = tmp_path / "kb"

        # Index files
        await test_indexer._index_namespace("root", test_indexer.kb_path)

        # Search for Unity-related content
        results = await test_indexer.search_semantic(
            query="Unity game engine development",
            namespace="root",
            limit=5
        )

        assert results['success'] is True

        # Results should be ordered by relevance_score (descending)
        scores = [r['relevance_score'] for r in results['results']]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by relevance"

        # Top result should be doc2.md (Unity Development)
        top_result = results['results'][0]
        assert 'doc2.md' in top_result['relative_path']

    @pytest.mark.asyncio
    async def test_semantic_search_limit(self, test_indexer, db_connection, tmp_path):
        """Test that limit parameter works correctly."""
        test_indexer.kb_path = tmp_path / "kb"

        # Create more test files
        for i in range(10):
            (test_indexer.kb_path / f"extra{i}.md").write_text(f"# Document {i}\n\nExtra content.")

        # Index all files
        await test_indexer._index_namespace("root", test_indexer.kb_path)

        # Search with limit
        results = await test_indexer.search_semantic(
            query="document content",
            namespace="root",
            limit=3
        )

        assert results['success'] is True
        assert len(results['results']) <= 3, "Should respect limit parameter"

    @pytest.mark.asyncio
    async def test_semantic_search_namespace_isolation(self, test_indexer, db_connection, tmp_path):
        """Test that namespaces are isolated."""
        # Create two namespaces
        root_path = tmp_path / "kb"
        user_path = tmp_path / "kb" / "users" / "test@example.com"
        user_path.mkdir(parents=True)

        # Different content in each namespace
        (root_path / "root_doc.md").write_text("# Root Content\n\nRoot namespace document.")
        (user_path / "user_doc.md").write_text("# User Content\n\nUser namespace document.")

        test_indexer.kb_path = root_path

        # Index both namespaces
        await test_indexer._index_namespace("root", root_path)
        await test_indexer._index_namespace("users/test@example.com", user_path)

        # Search root namespace
        root_results = await test_indexer.search_semantic(
            query="content document",
            namespace="root",
            limit=5
        )

        # Search user namespace
        user_results = await test_indexer.search_semantic(
            query="content document",
            namespace="users/test@example.com",
            limit=5
        )

        # Verify isolation
        root_paths = {r['relative_path'] for r in root_results['results']}
        user_paths = {r['relative_path'] for r in user_results['results']}

        assert 'root_doc.md' in root_paths
        assert 'root_doc.md' not in user_paths
        assert 'user_doc.md' in user_paths
        assert 'user_doc.md' not in root_paths


class TestPgvectorIndexStatus:
    """Test indexing status queries."""

    @pytest.mark.asyncio
    async def test_status_before_indexing(self, test_indexer, db_connection):
        """Test status when no index exists."""
        status = await test_indexer.get_indexing_status("root")

        assert status['indexed'] is False
        assert status['status'] in ['not_indexed', 'indexing']

    @pytest.mark.asyncio
    async def test_status_after_indexing(self, test_indexer, db_connection, tmp_path):
        """Test status after successful indexing."""
        test_indexer.kb_path = tmp_path / "kb"

        # Index files
        await test_indexer._index_namespace("root", test_indexer.kb_path)

        # Check status
        status = await test_indexer.get_indexing_status("root")

        assert status['indexed'] is True
        assert status['status'] == 'ready'
        assert status['indexed_chunks'] > 0
        assert status['total_files'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
