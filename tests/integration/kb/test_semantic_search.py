"""
Integration tests for KB Semantic Search functionality.

Tests the AI-powered semantic search capabilities including:
- Natural language queries
- Namespace isolation
- Caching behavior
- Reindexing triggers
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import shutil

from app.services.kb.kb_semantic_search import SemanticIndexer
from app.services.kb.kb_semantic_endpoints import (
    kb_search_semantic_endpoint,
    kb_reindex_semantic_endpoint,
    kb_semantic_stats_endpoint
)
from app.models.chat import ChatRequest


@pytest.fixture
async def temp_kb_path():
    """Create a temporary KB directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="kb_test_")
    
    # Create test structure
    users_dir = Path(temp_dir) / "users"
    users_dir.mkdir(parents=True)
    
    # Create test user namespace with sample files
    user_dir = users_dir / "test@example.com"
    user_dir.mkdir()
    
    # Add test content
    (user_dir / "authentication.md").write_text("""
# Authentication Guide

This document explains how users log in to the system.

## Login Process
1. User enters email and password
2. System validates credentials
3. JWT token is generated
4. Session is established

## Security Features
- Password hashing with bcrypt
- JWT tokens for session management
- Multi-factor authentication support
""")
    
    (user_dir / "api-reference.md").write_text("""
# API Reference

## Endpoints

### POST /auth/login
Authenticate a user and receive a session token.

### GET /api/user/profile
Retrieve the current user's profile information.

### POST /api/chat
Send a message to the AI chat service.
""")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
async def semantic_indexer(temp_kb_path):
    """Create a semantic indexer with test configuration."""
    with patch('app.services.kb.kb_semantic_search.settings') as mock_settings:
        mock_settings.KB_PATH = temp_kb_path
        mock_settings.KB_SEMANTIC_SEARCH_ENABLED = True
        mock_settings.KB_MULTI_USER_ENABLED = True
        
        indexer = SemanticIndexer()
        indexer.enabled = True  # Force enable for testing
        
        yield indexer
        
        # Cleanup
        await indexer.shutdown()


@pytest.fixture
async def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    mock_client.setex = AsyncMock()
    mock_client.scan = AsyncMock(return_value=(0, []))
    mock_client.delete = AsyncMock()
    return mock_client


class TestSemanticIndexer:
    """Test the SemanticIndexer class."""
    
    @pytest.mark.asyncio
    async def test_namespace_detection(self, semantic_indexer, temp_kb_path):
        """Test that namespaces are correctly identified."""
        # Queue active namespaces
        await semantic_indexer._queue_active_namespaces()
        
        # Should have queued the test user namespace
        assert semantic_indexer.indexing_queue.qsize() > 0
        
        # Get the queued task
        task = await semantic_indexer.indexing_queue.get()
        assert task["action"] == "index"
        assert "users/test@example.com" in task["namespace"]
    
    @pytest.mark.asyncio
    @patch('app.services.kb.kb_semantic_search.aifs_search')
    async def test_semantic_search_with_mock(
        self,
        mock_aifs_search,
        semantic_indexer,
        mock_redis_client
    ):
        """Test semantic search with mocked aifs."""
        # Mock aifs search results
        mock_aifs_search.return_value = [
            {
                "path": "/users/test@example.com/authentication.md",
                "content": "This document explains how users log in...",
                "score": 0.95
            }
        ]
        
        # Mock Redis
        with patch('app.services.kb.kb_semantic_search.redis_client', mock_redis_client):
            # Perform search
            result = await semantic_indexer.search_semantic(
                query="how do users log in?",
                user_id="test@example.com",
                limit=10
            )
        
        assert result["success"] is True
        assert len(result["results"]) > 0
        assert "authentication.md" in result["results"][0]["relative_path"]
        assert result["results"][0]["relevance_score"] == 0.95
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, semantic_indexer):
        """Test cache key generation for queries."""
        key1 = semantic_indexer._get_cache_key("users/test", "query one")
        key2 = semantic_indexer._get_cache_key("users/test", "query two")
        key3 = semantic_indexer._get_cache_key("users/other", "query one")
        
        # Same namespace and query should generate same key
        key4 = semantic_indexer._get_cache_key("users/test", "query one")
        assert key1 == key4
        
        # Different queries should generate different keys
        assert key1 != key2
        
        # Different namespaces should generate different keys
        assert key1 != key3
    
    @pytest.mark.asyncio
    async def test_reindex_namespace(self, semantic_indexer, temp_kb_path):
        """Test namespace reindexing."""
        # Create a fake _.aifs file
        namespace_path = Path(temp_kb_path) / "users" / "test@example.com"
        aifs_file = namespace_path / "_.aifs"
        aifs_file.touch()
        
        # Trigger reindex
        result = await semantic_indexer.reindex_namespace("users/test@example.com")
        
        assert result["success"] is True
        assert "users/test@example.com" in result["message"]
        
        # Check that old index was deleted
        assert not aifs_file.exists()
        
        # Check that reindex was queued
        assert semantic_indexer.indexing_queue.qsize() > 0
    
    @pytest.mark.asyncio
    async def test_reindex_changed_files(self, semantic_indexer, temp_kb_path):
        """Test reindexing after file changes."""
        changed_files = [
            f"{temp_kb_path}/users/test@example.com/new_doc.md",
            f"{temp_kb_path}/users/test@example.com/updated_doc.md",
            f"{temp_kb_path}/teams/engineering/team_doc.md"
        ]
        
        await semantic_indexer.reindex_changed_files(changed_files)
        
        # Should have queued reindexing for affected namespaces
        queued_namespaces = []
        while not semantic_indexer.indexing_queue.empty():
            task = await semantic_indexer.indexing_queue.get()
            queued_namespaces.append(task["namespace"])
        
        assert "users/test@example.com" in queued_namespaces
        # Note: teams/engineering would only be queued if the directory exists


class TestSemanticEndpoints:
    """Test the FastAPI endpoints for semantic search."""
    
    @pytest.mark.asyncio
    @patch('app.services.kb.kb_semantic_endpoints.semantic_indexer')
    async def test_search_endpoint(self, mock_indexer):
        """Test the semantic search endpoint."""
        # Mock the indexer's search method
        mock_indexer.search_semantic = AsyncMock(return_value={
            "success": True,
            "results": [
                {
                    "relative_path": "docs/auth.md",
                    "content_excerpt": "Login process...",
                    "relevance_score": 0.9,
                    "namespace": "users/test@example.com"
                }
            ],
            "total_results": 1,
            "status": "ready"
        })
        
        # Create request
        request = ChatRequest(message="how to authenticate?")
        auth_principal = {"email": "test@example.com"}
        
        # Call endpoint
        result = await kb_search_semantic_endpoint(request, auth_principal)
        
        assert result["status"] == "success"
        assert "Semantic Search Results" in result["response"]
        assert result["metadata"]["search_type"] == "semantic"
        assert result["metadata"]["total_results"] == 1
    
    @pytest.mark.asyncio
    @patch('app.services.kb.kb_semantic_endpoints.semantic_indexer')
    async def test_search_endpoint_indexing_status(self, mock_indexer):
        """Test search endpoint when indexing is in progress."""
        # Mock indexing status
        mock_indexer.search_semantic = AsyncMock(return_value={
            "success": True,
            "results": [],
            "total_results": 0,
            "status": "indexing",
            "message": "Namespace is being indexed, please try again in a few moments"
        })
        
        request = ChatRequest(message="test query")
        auth_principal = {"email": "test@example.com"}
        
        result = await kb_search_semantic_endpoint(request, auth_principal)
        
        assert "indexing" in result["response"].lower()
        assert result["metadata"]["indexing_status"] == "indexing"
    
    @pytest.mark.asyncio
    @patch('app.services.kb.kb_semantic_endpoints.semantic_indexer')
    async def test_reindex_endpoint(self, mock_indexer):
        """Test the reindex endpoint."""
        # Mock reindex method
        mock_indexer.reindex_namespace = AsyncMock(return_value={
            "success": True,
            "message": "Reindexing queued for namespace: users/test@example.com",
            "namespace": "users/test@example.com"
        })
        
        auth_principal = {"email": "test@example.com"}
        
        result = await kb_reindex_semantic_endpoint(auth_principal)
        
        assert result["status"] == "success"
        assert "users/test@example.com" in result["namespace"]
    
    @pytest.mark.asyncio
    @patch('app.services.kb.kb_semantic_endpoints.semantic_indexer')
    async def test_reindex_endpoint_admin(self, mock_indexer):
        """Test admin reindexing other namespaces."""
        # Mock reindex method
        mock_indexer.reindex_namespace = AsyncMock(return_value={
            "success": True,
            "message": "Reindexing queued",
            "namespace": "teams/engineering"
        })
        
        auth_principal = {"email": "admin@example.com", "is_admin": True}
        
        result = await kb_reindex_semantic_endpoint(
            auth_principal,
            namespace="teams/engineering"
        )
        
        assert result["status"] == "success"
        mock_indexer.reindex_namespace.assert_called_with("teams/engineering")
    
    @pytest.mark.asyncio
    @patch('app.services.kb.kb_semantic_endpoints.semantic_indexer')
    async def test_stats_endpoint(self, mock_indexer):
        """Test the statistics endpoint."""
        # Mock indexer properties
        mock_indexer.enabled = True
        mock_indexer.indexing_queue = AsyncMock()
        mock_indexer.indexing_queue.qsize = MagicMock(return_value=3)
        mock_indexer.cache_ttl = 3600
        mock_indexer.kb_path = Path("/kb")
        
        auth_principal = {"email": "test@example.com"}
        
        with patch('app.services.kb.kb_semantic_endpoints.settings') as mock_settings:
            mock_settings.KB_MULTI_USER_ENABLED = True
            
            result = await kb_semantic_stats_endpoint(auth_principal)
        
        assert result["status"] == "success"
        assert result["enabled"] is True
        assert result["statistics"]["indexing_queue_size"] == 3
        assert result["statistics"]["cache_ttl_seconds"] == 3600


class TestSemanticSearchIntegration:
    """Integration tests with real file system operations."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not Path("/kb").exists(),
        reason="Requires KB directory to exist"
    )
    async def test_real_indexing(self):
        """Test with actual file system (optional, skipped if /kb doesn't exist)."""
        indexer = SemanticIndexer()
        
        # This test would actually create indexes
        # Only run in environments where /kb exists
        await indexer.initialize_indexes()
        
        # Wait a bit for background indexing to start
        await asyncio.sleep(2)
        
        # Shutdown cleanly
        await indexer.shutdown()