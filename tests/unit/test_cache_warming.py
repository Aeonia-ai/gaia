"""
Unit tests for the cache warming service.
Tests background cache warming and connection keep-alive functionality.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, call
from app.services.cache_warming import CacheWarmingService, cache_warming_service


class TestCacheWarmingService:
    """Test the cache warming service"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh CacheWarmingService instance"""
        return CacheWarmingService()
    
    def test_init_default_values(self, service):
        """Test CacheWarmingService initializes with correct defaults"""
        assert service.warming_active is False
        assert service.last_activity == {}
        assert service.keep_alive_tasks == {}
    
    @pytest.mark.asyncio
    async def test_start_warming_service(self, service):
        """Test starting the warming service"""
        with patch('asyncio.create_task') as mock_create_task:
            await service.start_warming_service()
            
            # Verify service is marked as active
            assert service.warming_active is True
            
            # Verify background tasks were created
            assert mock_create_task.call_count == 2
            calls = mock_create_task.call_args_list
            
            # Should create periodic warming and keep-alive tasks
            assert any('_periodic_cache_warming' in str(call) for call in calls)
            assert any('_connection_keep_alive' in str(call) for call in calls)
    
    @pytest.mark.asyncio
    async def test_start_warming_service_idempotent(self, service):
        """Test starting service multiple times is safe"""
        service.warming_active = True
        
        with patch('asyncio.create_task') as mock_create_task:
            await service.start_warming_service()
            
            # Should not create new tasks if already active
            mock_create_task.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.services.cache_warming.get_cached_persona_memory')
    @patch('app.services.cache_warming.get_cached_tools_memory')
    async def test_warm_common_caches(self, mock_tools, mock_persona, service):
        """Test warming common cache combinations"""
        # Setup mocks
        mock_persona.return_value = {"test": "persona"}
        mock_tools.return_value = [{"test": "tool"}]
        
        await service._warm_common_caches()
        
        # Verify all common combinations were warmed
        expected_persona_calls = [
            call("default", "anonymous"),
            call("default", "anonymous"),
            call("default", "test_user")
        ]
        mock_persona.assert_has_calls(expected_persona_calls)
        
        expected_tools_calls = [
            call("generic"),
            call("knowledge_base"),
            call("generic")
        ]
        mock_tools.assert_has_calls(expected_tools_calls)
    
    @pytest.mark.asyncio
    @patch('app.services.cache_warming.get_cached_persona_memory')
    @patch('app.services.cache_warming.logger')
    async def test_warm_common_caches_handles_errors(self, mock_logger, mock_persona, service):
        """Test cache warming continues on individual errors"""
        # Make first call fail, others succeed
        mock_persona.side_effect = [Exception("DB error"), {"test": "persona"}, {"test": "persona"}]
        
        await service._warm_common_caches()
        
        # Should log warning for failed cache
        mock_logger.warning.assert_called()
        
        # Should still attempt other caches
        assert mock_persona.call_count == 3
    
    @pytest.mark.asyncio
    @patch('app.services.cache_warming.get_cached_persona_memory')
    @patch('app.services.cache_warming.get_cached_tools_memory')
    @patch('asyncio.sleep')
    async def test_periodic_cache_warming_loop(self, mock_sleep, mock_tools, mock_persona, service):
        """Test periodic cache warming loop behavior"""
        service.warming_active = True
        
        # Setup to run loop twice then stop
        call_count = 0
        def sleep_side_effect(duration):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                service.warming_active = False
            return asyncio.sleep(0)  # Don't actually sleep
        
        mock_sleep.side_effect = sleep_side_effect
        
        await service._periodic_cache_warming()
        
        # Should warm caches twice (2 iterations)
        assert mock_persona.call_count >= 6  # 3 combinations * 2 iterations
        
        # Should sleep 300 seconds between warming
        mock_sleep.assert_any_call(300)
    
    @pytest.mark.asyncio
    @patch('app.services.cache_warming.logger')
    @patch('asyncio.sleep')
    async def test_periodic_cache_warming_error_handling(self, mock_sleep, mock_logger, service):
        """Test periodic warming handles errors gracefully"""
        service.warming_active = True
        
        # Mock the warming method to raise an error
        with patch.object(service, '_warm_common_caches', side_effect=Exception("Test error")):
            # Run one iteration
            mock_sleep.side_effect = [asyncio.sleep(0), Exception("Stop loop")]
            
            try:
                await service._periodic_cache_warming()
            except:
                pass
            
            # Should log error
            mock_logger.error.assert_called()
            
            # Should use shorter retry delay on error (60s instead of 300s)
            mock_sleep.assert_any_call(60)
    
    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    async def test_connection_keep_alive(self, mock_sleep, service):
        """Test connection keep-alive behavior"""
        service.warming_active = True
        
        # Run two iterations then stop
        call_count = 0
        def sleep_side_effect(duration):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                service.warming_active = False
            return asyncio.sleep(0)
        
        mock_sleep.side_effect = sleep_side_effect
        
        await service._connection_keep_alive()
        
        # Should sleep 120 seconds between keep-alive
        mock_sleep.assert_any_call(120)
    
    @pytest.mark.asyncio
    async def test_register_user_activity(self, service):
        """Test registering user activity"""
        with patch('asyncio.create_task') as mock_create_task:
            # Register activity
            await service.register_user_activity("user123")
            
            # Should record activity time
            assert "user123" in service.last_activity
            assert isinstance(service.last_activity["user123"], datetime)
            
            # Should create user-specific warming task
            mock_create_task.assert_called_once()
            
            # Task should be tracked
            assert "user123" in service.keep_alive_tasks
    
    @pytest.mark.asyncio
    async def test_register_user_activity_existing_user(self, service):
        """Test registering activity for user with existing task"""
        # Pre-create a task
        mock_task = Mock()
        service.keep_alive_tasks["user123"] = mock_task
        
        with patch('asyncio.create_task') as mock_create_task:
            await service.register_user_activity("user123")
            
            # Should update activity time
            assert "user123" in service.last_activity
            
            # Should NOT create new task
            mock_create_task.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.services.cache_warming.get_cached_persona_memory')
    @patch('app.services.cache_warming.get_cached_tools_memory')
    @patch('asyncio.sleep')
    async def test_user_specific_warming_active_user(self, mock_sleep, mock_tools, mock_persona, service):
        """Test user-specific warming for active user"""
        service.warming_active = True
        service.last_activity["user123"] = datetime.utcnow()
        
        # Run one iteration then stop
        mock_sleep.side_effect = [asyncio.sleep(0), Exception("Stop loop")]
        
        try:
            await service._user_specific_warming("user123")
        except:
            pass
        
        # Should warm user's caches
        mock_persona.assert_called_with("default", "user123")
        mock_tools.assert_called_with("generic")
        
        # Should clean up task reference
        assert "user123" not in service.keep_alive_tasks
    
    @pytest.mark.asyncio
    @patch('app.services.cache_warming.get_cached_persona_memory')
    @patch('asyncio.sleep')
    async def test_user_specific_warming_inactive_user(self, mock_sleep, mock_persona, service):
        """Test user-specific warming stops for inactive user"""
        service.warming_active = True
        # Set last activity to 31 minutes ago (over 30 minute threshold)
        service.last_activity["user123"] = datetime.utcnow() - timedelta(minutes=31)
        
        await service._user_specific_warming("user123")
        
        # Should not warm caches for inactive user
        mock_persona.assert_not_called()
        
        # Should clean up task reference
        assert "user123" not in service.keep_alive_tasks
    
    @pytest.mark.asyncio
    @patch('app.services.cache_warming.get_cached_persona_memory')
    @patch('app.services.cache_warming.logger')
    async def test_user_specific_warming_error_handling(self, mock_logger, mock_persona, service):
        """Test user-specific warming handles errors gracefully"""
        service.warming_active = True
        service.last_activity["user123"] = datetime.utcnow()
        
        # Mock cache warming to fail
        mock_persona.side_effect = Exception("Cache error")
        
        # Run one iteration
        with patch('asyncio.sleep', side_effect=[asyncio.sleep(0), Exception("Stop")]):
            try:
                await service._user_specific_warming("user123")
            except:
                pass
        
        # Should log warning
        mock_logger.warning.assert_called()
        
        # Should clean up task reference
        assert "user123" not in service.keep_alive_tasks
    
    def test_stop_warming_service(self, service):
        """Test stopping the warming service"""
        # Setup service as active with tasks
        service.warming_active = True
        
        mock_task1 = Mock()
        mock_task2 = Mock()
        service.keep_alive_tasks = {
            "user1": mock_task1,
            "user2": mock_task2
        }
        
        # Stop service
        service.stop_warming_service()
        
        # Should mark as inactive
        assert service.warming_active is False
        
        # Should cancel all tasks
        mock_task1.cancel.assert_called_once()
        mock_task2.cancel.assert_called_once()
        
        # Should clear task dict
        assert len(service.keep_alive_tasks) == 0
    
    @pytest.mark.asyncio
    @patch('app.services.cache_warming.logger')
    async def test_logging(self, mock_logger, service):
        """Test appropriate logging throughout service"""
        # Test start logging
        await service.start_warming_service()
        mock_logger.info.assert_called_with("Starting cache warming service")
        
        # Test stop logging
        service.stop_warming_service()
        mock_logger.info.assert_called_with("Cache warming service stopped")
    
    def test_global_instance(self):
        """Test global cache warming service instance exists"""
        assert cache_warming_service is not None
        assert isinstance(cache_warming_service, CacheWarmingService)
    
    @pytest.mark.asyncio
    async def test_timing_measurements(self, service):
        """Test that cache warming measures timing correctly"""
        with patch('app.services.cache_warming.get_cached_persona_memory') as mock_persona:
            with patch('app.services.cache_warming.get_cached_tools_memory') as mock_tools:
                with patch('app.services.cache_warming.time.time') as mock_time:
                    # Mock time progression
                    mock_time.side_effect = [
                        1000.0,  # Start persona
                        1000.1,  # End persona (100ms)
                        1000.1,  # Start tools
                        1000.15  # End tools (50ms)
                    ]
                    
                    mock_persona.return_value = {}
                    mock_tools.return_value = []
                    
                    with patch('app.services.cache_warming.logger') as mock_logger:
                        # Warm one combination
                        service.warming_active = True
                        await service._warm_common_caches()
                        
                        # Should log timing for each combination
                        debug_calls = [call for call in mock_logger.debug.call_args_list 
                                     if 'persona: 100.0ms, tools: 50.0ms' in str(call)]
                        assert len(debug_calls) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])