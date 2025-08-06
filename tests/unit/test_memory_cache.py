"""
Unit tests for the memory cache service.
Tests in-memory caching for personas and tools.
"""
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from app.services import memory_cache
from app.services.memory_cache import (
    get_cached_persona_memory,
    get_cached_tools_memory,
    invalidate_persona_cache,
    invalidate_tools_cache,
    get_cache_status,
    PERSONA_CACHE_TTL_SECONDS,
    TOOLS_CACHE_TTL_SECONDS
)


class TestMemoryCache:
    """Test the memory cache service"""
    
    @pytest.fixture(autouse=True)
    def clear_caches(self):
        """Clear all caches before each test"""
        memory_cache.persona_memory_cache.clear()
        memory_cache.persona_cache_ttl.clear()
        memory_cache.tools_memory_cache.clear()
        memory_cache.tools_cache_ttl.clear()
        yield
        # Clear again after test
        memory_cache.persona_memory_cache.clear()
        memory_cache.persona_cache_ttl.clear()
        memory_cache.tools_memory_cache.clear()
        memory_cache.tools_cache_ttl.clear()
    
    @pytest.mark.asyncio
    @patch('app.services.memory_cache.PromptManager.get_system_prompt')
    async def test_get_cached_persona_memory_cache_miss(self, mock_get_prompt):
        """Test persona fetch on cache miss"""
        # Setup mock
        mock_get_prompt.return_value = "You are a helpful assistant."
        
        # First call - cache miss
        result = await get_cached_persona_memory("persona1", "user1")
        
        # Verify result
        assert result["name"] == "Assistant"
        assert result["system_prompt"] == "You are a helpful assistant."
        assert result["persona_id"] == "persona1"
        assert result["user_id"] == "user1"
        
        # Verify cache was populated
        cache_key = "user1:persona1"
        assert cache_key in memory_cache.persona_memory_cache
        assert cache_key in memory_cache.persona_cache_ttl
        assert memory_cache.persona_cache_ttl[cache_key] > time.time()
        
        # Verify prompt manager was called
        mock_get_prompt.assert_called_once_with(user_id="user1")
    
    @pytest.mark.asyncio
    @patch('app.services.memory_cache.PromptManager.get_system_prompt')
    async def test_get_cached_persona_memory_cache_hit(self, mock_get_prompt):
        """Test persona fetch on cache hit"""
        # Pre-populate cache
        cache_key = "user1:persona1"
        cached_persona = {
            "name": "Cached Assistant",
            "system_prompt": "Cached prompt",
            "persona_id": "persona1",
            "user_id": "user1"
        }
        memory_cache.persona_memory_cache[cache_key] = cached_persona
        memory_cache.persona_cache_ttl[cache_key] = time.time() + 100
        
        # Call should return cached data
        result = await get_cached_persona_memory("persona1", "user1")
        
        # Verify cached data returned
        assert result == cached_persona
        
        # Verify prompt manager was NOT called
        mock_get_prompt.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.services.memory_cache.PromptManager.get_system_prompt')
    async def test_get_cached_persona_memory_ttl_expired(self, mock_get_prompt):
        """Test persona fetch when TTL has expired"""
        # Pre-populate cache with expired TTL
        cache_key = "user1:persona1"
        old_persona = {
            "name": "Old Assistant",
            "system_prompt": "Old prompt",
            "persona_id": "persona1",
            "user_id": "user1"
        }
        memory_cache.persona_memory_cache[cache_key] = old_persona
        memory_cache.persona_cache_ttl[cache_key] = time.time() - 1  # Expired
        
        # Setup mock for new fetch
        mock_get_prompt.return_value = "Fresh prompt"
        
        # Call should fetch fresh data
        result = await get_cached_persona_memory("persona1", "user1")
        
        # Verify fresh data returned
        assert result["system_prompt"] == "Fresh prompt"
        assert result != old_persona
        
        # Verify prompt manager was called
        mock_get_prompt.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.memory_cache.PromptManager.get_system_prompt')
    @patch('app.services.memory_cache.logger')
    async def test_get_cached_persona_memory_error_fallback(self, mock_logger, mock_get_prompt):
        """Test persona fetch falls back on error"""
        # Setup mock to raise exception
        mock_get_prompt.side_effect = Exception("Database error")
        
        # Call should return fallback
        result = await get_cached_persona_memory("persona1", "user1")
        
        # Verify fallback data
        assert result["name"] == "Assistant"
        assert result["system_prompt"] == "You are a helpful AI assistant."
        assert result["persona_id"] == "persona1"
        assert result["user_id"] == "user1"
        
        # Verify error was logged
        mock_logger.warning.assert_called()
        
        # Verify fallback was cached with shorter TTL
        cache_key = "user1:persona1"
        assert cache_key in memory_cache.persona_memory_cache
        ttl_remaining = memory_cache.persona_cache_ttl[cache_key] - time.time()
        assert ttl_remaining < 60  # Shorter TTL for fallback
    
    @pytest.mark.asyncio
    @patch('app.services.memory_cache.ToolProvider.get_tools_for_activity')
    async def test_get_cached_tools_memory_cache_miss(self, mock_get_tools):
        """Test tools fetch on cache miss"""
        # Setup mock
        mock_tools = [{"name": "tool1"}, {"name": "tool2"}]
        mock_get_tools.return_value = mock_tools
        
        # First call - cache miss
        result = await get_cached_tools_memory("coding")
        
        # Verify result
        assert result == mock_tools
        
        # Verify cache was populated
        assert "coding" in memory_cache.tools_memory_cache
        assert "coding" in memory_cache.tools_cache_ttl
        assert memory_cache.tools_cache_ttl["coding"] > time.time()
        
        # Verify tool provider was called
        mock_get_tools.assert_called_once_with("coding")
    
    @pytest.mark.asyncio
    @patch('app.services.memory_cache.ToolProvider.get_tools_for_activity')
    async def test_get_cached_tools_memory_cache_hit(self, mock_get_tools):
        """Test tools fetch on cache hit"""
        # Pre-populate cache
        cached_tools = [{"name": "cached_tool"}]
        memory_cache.tools_memory_cache["coding"] = cached_tools
        memory_cache.tools_cache_ttl["coding"] = time.time() + 100
        
        # Call should return cached data
        result = await get_cached_tools_memory("coding")
        
        # Verify cached data returned
        assert result == cached_tools
        
        # Verify tool provider was NOT called
        mock_get_tools.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.services.memory_cache.ToolProvider.get_tools_for_activity')
    async def test_get_cached_tools_memory_error_fallback(self, mock_get_tools):
        """Test tools fetch returns empty list on error"""
        # Setup mock to raise exception
        mock_get_tools.side_effect = Exception("MCP error")
        
        # Call should return empty list
        result = await get_cached_tools_memory("coding")
        
        # Verify empty list returned
        assert result == []
        
        # Verify error was cached with shorter TTL
        assert "coding" in memory_cache.tools_memory_cache
        ttl_remaining = memory_cache.tools_cache_ttl["coding"] - time.time()
        assert ttl_remaining < 60
    
    def test_invalidate_persona_cache_specific(self):
        """Test invalidating specific persona cache"""
        # Pre-populate cache
        memory_cache.persona_memory_cache["user1:persona1"] = {"data": "test1"}
        memory_cache.persona_memory_cache["user1:persona2"] = {"data": "test2"}
        memory_cache.persona_memory_cache["user2:persona1"] = {"data": "test3"}
        memory_cache.persona_cache_ttl["user1:persona1"] = time.time() + 100
        memory_cache.persona_cache_ttl["user1:persona2"] = time.time() + 100
        memory_cache.persona_cache_ttl["user2:persona1"] = time.time() + 100
        
        # Invalidate specific persona
        invalidate_persona_cache(user_id="user1", persona_id="persona1")
        
        # Verify only specific entry was removed
        assert "user1:persona1" not in memory_cache.persona_memory_cache
        assert "user1:persona1" not in memory_cache.persona_cache_ttl
        assert "user1:persona2" in memory_cache.persona_memory_cache
        assert "user2:persona1" in memory_cache.persona_memory_cache
    
    def test_invalidate_persona_cache_user(self):
        """Test invalidating all personas for a user"""
        # Pre-populate cache
        memory_cache.persona_memory_cache["user1:persona1"] = {"data": "test1"}
        memory_cache.persona_memory_cache["user1:persona2"] = {"data": "test2"}
        memory_cache.persona_memory_cache["user2:persona1"] = {"data": "test3"}
        memory_cache.persona_cache_ttl["user1:persona1"] = time.time() + 100
        memory_cache.persona_cache_ttl["user1:persona2"] = time.time() + 100
        memory_cache.persona_cache_ttl["user2:persona1"] = time.time() + 100
        
        # Invalidate all personas for user1
        invalidate_persona_cache(user_id="user1")
        
        # Verify all user1 entries removed
        assert "user1:persona1" not in memory_cache.persona_memory_cache
        assert "user1:persona2" not in memory_cache.persona_memory_cache
        assert "user2:persona1" in memory_cache.persona_memory_cache
    
    def test_invalidate_persona_cache_all(self):
        """Test invalidating entire persona cache"""
        # Pre-populate cache
        memory_cache.persona_memory_cache["user1:persona1"] = {"data": "test1"}
        memory_cache.persona_memory_cache["user2:persona1"] = {"data": "test2"}
        memory_cache.persona_cache_ttl["user1:persona1"] = time.time() + 100
        memory_cache.persona_cache_ttl["user2:persona1"] = time.time() + 100
        
        # Invalidate entire cache
        invalidate_persona_cache()
        
        # Verify all entries removed
        assert len(memory_cache.persona_memory_cache) == 0
        assert len(memory_cache.persona_cache_ttl) == 0
    
    def test_invalidate_tools_cache_specific(self):
        """Test invalidating specific tools cache"""
        # Pre-populate cache
        memory_cache.tools_memory_cache["coding"] = [{"tool": "1"}]
        memory_cache.tools_memory_cache["writing"] = [{"tool": "2"}]
        memory_cache.tools_cache_ttl["coding"] = time.time() + 100
        memory_cache.tools_cache_ttl["writing"] = time.time() + 100
        
        # Invalidate specific activity
        invalidate_tools_cache(activity="coding")
        
        # Verify only specific entry was removed
        assert "coding" not in memory_cache.tools_memory_cache
        assert "coding" not in memory_cache.tools_cache_ttl
        assert "writing" in memory_cache.tools_memory_cache
    
    def test_invalidate_tools_cache_all(self):
        """Test invalidating entire tools cache"""
        # Pre-populate cache
        memory_cache.tools_memory_cache["coding"] = [{"tool": "1"}]
        memory_cache.tools_memory_cache["writing"] = [{"tool": "2"}]
        memory_cache.tools_cache_ttl["coding"] = time.time() + 100
        memory_cache.tools_cache_ttl["writing"] = time.time() + 100
        
        # Invalidate entire cache
        invalidate_tools_cache()
        
        # Verify all entries removed
        assert len(memory_cache.tools_memory_cache) == 0
        assert len(memory_cache.tools_cache_ttl) == 0
    
    def test_get_cache_status(self):
        """Test getting cache status"""
        # Pre-populate caches
        memory_cache.persona_memory_cache["user1:persona1"] = {"data": "test1"}
        memory_cache.persona_memory_cache["user2:persona1"] = {"data": "test2"}
        memory_cache.tools_memory_cache["coding"] = [{"tool": "1"}]
        memory_cache.tools_memory_cache["writing"] = [{"tool": "2"}]
        memory_cache.tools_memory_cache["gaming"] = [{"tool": "3"}]
        
        # Get status
        status = get_cache_status()
        
        # Verify status
        assert status["persona_cache_entries"] == 2
        assert status["tools_cache_entries"] == 3
        assert set(status["persona_cache_keys"]) == {"user1:persona1", "user2:persona1"}
        assert set(status["tools_cache_keys"]) == {"coding", "writing", "gaming"}
    
    @pytest.mark.asyncio
    @patch('app.services.memory_cache.logger')
    async def test_logging(self, mock_logger):
        """Test that appropriate logging occurs"""
        # Test cache hit logging
        memory_cache.persona_memory_cache["user1:persona1"] = {"data": "test"}
        memory_cache.persona_cache_ttl["user1:persona1"] = time.time() + 100
        
        await get_cached_persona_memory("persona1", "user1")
        mock_logger.debug.assert_called_with("Memory cache hit for persona persona1 (0ms)")
        
        # Test invalidation logging
        invalidate_persona_cache(user_id="user1", persona_id="persona1")
        mock_logger.info.assert_called_with("Invalidated persona cache for user1:persona1")
    
    @pytest.mark.asyncio
    async def test_ttl_values(self):
        """Test that TTL values are set correctly"""
        # Test persona TTL
        with patch('app.services.memory_cache.PromptManager.get_system_prompt') as mock:
            mock.return_value = "test"
            await get_cached_persona_memory("p1", "u1")
            
            ttl = memory_cache.persona_cache_ttl["u1:p1"]
            expected_ttl = time.time() + PERSONA_CACHE_TTL_SECONDS
            assert abs(ttl - expected_ttl) < 1  # Within 1 second
        
        # Test tools TTL
        with patch('app.services.memory_cache.ToolProvider.get_tools_for_activity') as mock:
            mock.return_value = []
            await get_cached_tools_memory("test")
            
            ttl = memory_cache.tools_cache_ttl["test"]
            expected_ttl = time.time() + TOOLS_CACHE_TTL_SECONDS
            assert abs(ttl - expected_ttl) < 1  # Within 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])