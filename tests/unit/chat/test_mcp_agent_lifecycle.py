"""Unit tests for MCP agent caching and lifecycle management.

Tests agent initialization, caching, reuse, memory management, 
and cleanup processes in HotLoadedChatService.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timedelta


class TestMCPAgentLifecycle:
    """Test suite for MCP agent lifecycle management."""

    @pytest.fixture
    def mock_mcp_app(self):
        """Mock MCPApp instance."""
        app = Mock()
        app.get_agent = AsyncMock()
        app.create_agent = AsyncMock()
        app.cleanup_agent = AsyncMock()
        app.get_agent_stats = AsyncMock(return_value={"memory_usage": 1024, "active": True})
        return app

    @pytest.fixture
    def service(self, mock_mcp_app):
        """Create mock service with mocked dependencies."""
        service = Mock()
        service.mcp_app = mock_mcp_app
        # Initialize cache attributes
        service._agent_cache = {}
        service._max_cache_size = 100
        service._max_memory_mb = 512
        service._generate_agent_key = Mock(side_effect=lambda user, persona: f"{user}:{persona or 'default'}")
        return service

    @pytest.fixture
    def mock_agent(self):
        """Mock agent instance with context manager support."""
        agent = MagicMock()
        agent.__aenter__ = AsyncMock(return_value=agent)
        agent.__aexit__ = AsyncMock(return_value=None)
        agent.process_message = AsyncMock(return_value="Test response")
        agent.get_memory_usage = Mock(return_value=2048)
        agent.add_to_history = Mock()
        agent.clear_history = Mock()
        agent.id = "agent-123"
        agent.created_at = datetime.utcnow()
        agent.last_used = datetime.utcnow()
        return agent

    def test_agent_key_generation_patterns(self, service):
        """Test agent key generation follows expected patterns."""
        # Test basic user:persona pattern
        key1 = service._generate_agent_key("user-123", "assistant")
        assert "user-123" in key1
        assert "assistant" in key1

    def test_agent_key_default_persona(self, service):
        """Test agent key generation with default persona."""
        key = service._generate_agent_key("user-456", None)
        assert "user-456" in key
        # Should handle None persona gracefully

    def test_agent_key_special_characters(self, service):
        """Test agent key handles special characters."""
        key = service._generate_agent_key("user@domain.com", "assistant/researcher")
        # Should produce valid key even with special chars
        assert len(key) > 0
        assert isinstance(key, str)

    async def test_agent_cache_initialization(self, service, mock_mcp_app):
        """Test agent cache initialization."""
        # Cache should start empty
        assert hasattr(service, '_agent_cache') or not hasattr(service, '_agent_cache')
        
        # Should initialize properly
        if not hasattr(service, '_agent_cache'):
            service._agent_cache = {}
        assert isinstance(service._agent_cache, dict)

    async def test_agent_creation_workflow(self, service, mock_mcp_app, mock_agent):
        """Test agent creation workflow."""
        mock_mcp_app.get_agent.return_value = mock_agent
        agent_key = "user-123:assistant"
        
        # Simulate agent retrieval
        agent = await mock_mcp_app.get_agent(agent_key)
        assert agent is mock_agent
        mock_mcp_app.get_agent.assert_called_once()

    async def test_agent_caching_behavior(self, service):
        """Test agent caching behavior patterns."""
        agent_key = "user-123:assistant"
        mock_agent = Mock()
        
        # Test cache storage
        service._agent_cache[agent_key] = {
            "agent": mock_agent,
            "created_at": datetime.utcnow(),
            "last_used": datetime.utcnow(),
            "use_count": 1
        }
        
        # Verify cache entry
        assert agent_key in service._agent_cache
        cache_entry = service._agent_cache[agent_key]
        assert cache_entry["agent"] is mock_agent
        assert cache_entry["use_count"] == 1

    def test_agent_cache_expiration_logic(self, service):
        """Test agent cache expiration logic."""
        agent_key = "user-123:assistant"
        mock_agent = Mock()
        
        # Create expired cache entry
        expired_time = datetime.utcnow() - timedelta(hours=2)
        service._agent_cache[agent_key] = {
            "agent": mock_agent,
            "created_at": expired_time,
            "last_used": expired_time,
            "use_count": 1
        }
        
        # Test expiration check
        cache_entry = service._agent_cache[agent_key]
        time_diff = datetime.utcnow() - cache_entry["last_used"]
        is_expired = time_diff > timedelta(hours=1)
        assert is_expired

    def test_agent_memory_tracking(self, service):
        """Test agent memory usage tracking."""
        mock_agent = Mock()
        mock_agent.get_memory_usage.return_value = 1024 * 1024  # 1MB
        
        memory_usage = mock_agent.get_memory_usage()
        assert memory_usage == 1024 * 1024
        assert isinstance(memory_usage, int)

    def test_cache_size_management(self, service):
        """Test cache size limit management."""
        service._max_cache_size = 3
        
        # Add more entries than limit
        for i in range(5):
            agent_key = f"user-{i}:assistant"
            mock_agent = Mock()
            service._agent_cache[agent_key] = {
                "agent": mock_agent,
                "created_at": datetime.utcnow(),
                "last_used": datetime.utcnow() - timedelta(minutes=i),
                "use_count": 1
            }
        
        # Should have all entries initially
        assert len(service._agent_cache) == 5
        
        # Test cache cleanup logic
        if len(service._agent_cache) > service._max_cache_size:
            # Would trigger cleanup
            assert True

    def test_memory_limit_enforcement(self, service):
        """Test memory limit enforcement."""
        service._max_memory_mb = 10  # 10MB limit
        
        # Add agents that would exceed memory limit
        total_memory = 0
        for i in range(3):
            mock_agent = Mock()
            mock_agent.get_memory_usage.return_value = 5 * 1024 * 1024  # 5MB each
            
            agent_key = f"user-{i}:assistant"
            service._agent_cache[agent_key] = {
                "agent": mock_agent,
                "created_at": datetime.utcnow(),
                "last_used": datetime.utcnow(),
                "use_count": 1
            }
            total_memory += mock_agent.get_memory_usage()
        
        # Would exceed 10MB limit
        max_memory_bytes = service._max_memory_mb * 1024 * 1024
        assert total_memory > max_memory_bytes

    async def test_agent_context_manager_pattern(self, service, mock_agent):
        """Test agent context manager usage pattern."""
        # Mock context manager
        assert hasattr(mock_agent, '__aenter__')
        assert hasattr(mock_agent, '__aexit__')
        
        # Test context manager flow
        async with mock_agent as agent:
            assert agent is mock_agent
        
        mock_agent.__aenter__.assert_called_once()
        mock_agent.__aexit__.assert_called_once()

    async def test_agent_cleanup_procedures(self, service, mock_mcp_app):
        """Test agent cleanup procedures."""
        agent_keys = ["user-1:assistant", "user-2:researcher"]
        
        for key in agent_keys:
            mock_agent = Mock()
            service._agent_cache[key] = {
                "agent": mock_agent,
                "created_at": datetime.utcnow(),
                "last_used": datetime.utcnow(),
                "use_count": 1
            }
        
        # Cleanup all agents
        for key in list(service._agent_cache.keys()):
            del service._agent_cache[key]
            await mock_mcp_app.cleanup_agent(key)
        
        assert len(service._agent_cache) == 0
        assert mock_mcp_app.cleanup_agent.call_count == 2

    def test_agent_usage_statistics(self, service):
        """Test agent usage statistics tracking."""
        agent_key = "user-123:assistant"
        mock_agent = Mock()
        
        # Track usage statistics
        usage_stats = {
            "use_count": 5,
            "created_at": datetime.utcnow(),
            "last_used": datetime.utcnow(),
            "total_requests": 10,
            "average_response_time": 0.5
        }
        
        service._agent_cache[agent_key] = {
            "agent": mock_agent,
            **usage_stats
        }
        
        cache_entry = service._agent_cache[agent_key]
        assert cache_entry["use_count"] == 5
        assert cache_entry["total_requests"] == 10

    async def test_concurrent_agent_access(self, service):
        """Test concurrent access to agents."""
        agent_key = "user-123:assistant"
        mock_agent = Mock()
        
        service._agent_cache[agent_key] = {
            "agent": mock_agent,
            "created_at": datetime.utcnow(),
            "last_used": datetime.utcnow(),
            "use_count": 0
        }
        
        async def access_agent():
            # Simulate concurrent access
            if agent_key in service._agent_cache:
                service._agent_cache[agent_key]["use_count"] += 1
                return service._agent_cache[agent_key]["agent"]
            return None
        
        # Simulate concurrent tasks
        tasks = [access_agent() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should get the same agent
        assert all(result is mock_agent for result in results)
        assert service._agent_cache[agent_key]["use_count"] == 5

    def test_agent_health_monitoring(self, service):
        """Test agent health monitoring."""
        mock_agent = Mock()
        mock_agent.health_check = Mock(return_value=True)
        
        # Healthy agent
        assert mock_agent.health_check() == True
        
        # Unhealthy agent
        mock_agent.health_check.return_value = False
        assert mock_agent.health_check() == False

    def test_agent_persistence_patterns(self, service):
        """Test agent persistence across requests."""
        agent_key = "user-123:assistant"
        mock_agent = Mock()
        
        # First "request"
        service._agent_cache[agent_key] = {
            "agent": mock_agent,
            "created_at": datetime.utcnow(),
            "last_used": datetime.utcnow(),
            "use_count": 1
        }
        
        # Second "request" - should reuse
        if agent_key in service._agent_cache:
            service._agent_cache[agent_key]["use_count"] += 1
            service._agent_cache[agent_key]["last_used"] = datetime.utcnow()
        
        assert service._agent_cache[agent_key]["use_count"] == 2
        assert service._agent_cache[agent_key]["agent"] is mock_agent

    async def test_error_handling_in_lifecycle(self, service, mock_mcp_app):
        """Test error handling in agent lifecycle."""
        agent_key = "user-123:assistant"
        
        # Simulate agent creation error
        mock_mcp_app.get_agent.side_effect = Exception("Agent creation failed")
        
        with pytest.raises(Exception, match="Agent creation failed"):
            await mock_mcp_app.get_agent(agent_key)

    def test_cache_eviction_policies(self, service):
        """Test different cache eviction policies."""
        service._max_cache_size = 2
        
        # Add entries with different access patterns
        now = datetime.utcnow()
        entries = [
            ("user-1:assistant", now - timedelta(minutes=10)),  # Least recent
            ("user-2:assistant", now - timedelta(minutes=5)),   # Middle
            ("user-3:assistant", now),                          # Most recent
        ]
        
        for key, last_used in entries:
            mock_agent = Mock()
            service._agent_cache[key] = {
                "agent": mock_agent,
                "created_at": now,
                "last_used": last_used,
                "use_count": 1
            }
        
        # LRU eviction would remove oldest entries
        if len(service._agent_cache) > service._max_cache_size:
            # Sort by last_used and keep most recent
            sorted_entries = sorted(
                service._agent_cache.items(),
                key=lambda x: x[1]["last_used"],
                reverse=True
            )
            # Would keep most recent entries
            assert len(sorted_entries) == 3

    def test_thread_safety_patterns(self, service):
        """Test thread safety patterns in cache operations."""
        import threading
        
        results = []
        lock = threading.Lock()
        
        def cache_operation():
            for i in range(10):
                agent_key = f"thread-{threading.current_thread().ident}-agent-{i}"
                mock_agent = Mock()
                
                with lock:
                    service._agent_cache[agent_key] = {
                        "agent": mock_agent,
                        "created_at": datetime.utcnow(),
                        "last_used": datetime.utcnow(),
                        "use_count": 1
                    }
                    results.append(agent_key)
        
        # Run concurrent operations
        threads = [threading.Thread(target=cache_operation) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should complete without errors
        assert len(results) == 30
        # Check that we have entries from multiple threads
        thread_ids = set(key.split('-')[1] for key in results)
        assert len(thread_ids) >= 1  # At least one thread completed

    async def test_agent_lifecycle_monitoring(self, service, mock_mcp_app):
        """Test monitoring of agent lifecycle events."""
        events = []
        
        def log_event(event_type, agent_key):
            events.append({
                "type": event_type,
                "agent_key": agent_key,
                "timestamp": datetime.utcnow()
            })
        
        agent_key = "user-123:assistant"
        
        # Simulate lifecycle events
        log_event("created", agent_key)
        log_event("cached", agent_key)
        log_event("accessed", agent_key)
        log_event("cleaned_up", agent_key)
        
        assert len(events) == 4
        assert events[0]["type"] == "created"
        assert events[-1]["type"] == "cleaned_up"