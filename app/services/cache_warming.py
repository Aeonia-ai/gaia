"""
Cache warming and keep-alive service to eliminate cold start penalties
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import time

from app.services.memory_cache import get_cached_persona_memory, get_cached_tools_memory

logger = logging.getLogger(__name__)

class CacheWarmingService:
    """Service to keep caches warm and connections active"""
    
    def __init__(self):
        self.warming_active = False
        self.last_activity: Dict[str, datetime] = {}
        self.keep_alive_tasks: Dict[str, asyncio.Task] = {}
        
    async def start_warming_service(self):
        """Start the cache warming background service"""
        if self.warming_active:
            return
            
        self.warming_active = True
        logger.info("Starting cache warming service")
        
        # Start background tasks
        asyncio.create_task(self._periodic_cache_warming())
        asyncio.create_task(self._connection_keep_alive())
        
    async def _periodic_cache_warming(self):
        """Periodically warm common caches"""
        while self.warming_active:
            try:
                # Warm common persona/tools combinations
                await self._warm_common_caches()
                
                # Wait 5 minutes between warming cycles
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Cache warming error: {e}")
                await asyncio.sleep(60)  # Shorter retry on error
    
    async def _warm_common_caches(self):
        """Warm the most commonly used caches"""
        common_combinations = [
            ("anonymous", "default", "generic"),
            ("anonymous", "default", "knowledge_base"),
            ("test_user", "default", "generic"),
        ]
        
        for user_id, persona_id, activity in common_combinations:
            try:
                # Warm persona cache
                start_time = time.time()
                await get_cached_persona_memory(persona_id, user_id)
                persona_time = (time.time() - start_time) * 1000
                
                # Warm tools cache  
                start_time = time.time()
                await get_cached_tools_memory(activity)
                tools_time = (time.time() - start_time) * 1000
                
                logger.debug(f"Warmed {user_id}:{persona_id}:{activity} - persona: {persona_time:.1f}ms, tools: {tools_time:.1f}ms")
                
            except Exception as e:
                logger.warning(f"Failed to warm cache for {user_id}:{persona_id}:{activity}: {e}")
    
    async def _connection_keep_alive(self):
        """Keep connections warm (simplified for Gaia)"""
        while self.warming_active:
            try:
                # For Gaia, we'll just sleep and let the multi-provider system handle connection warming
                # Keep alive every 2 minutes
                await asyncio.sleep(120)
                logger.debug("Connection keep-alive cycle completed")
                
            except Exception as e:
                logger.warning(f"Keep-alive cycle failed: {e}")
                await asyncio.sleep(60)
    
    async def register_user_activity(self, user_id: str):
        """Register user activity to prioritize their caches"""
        self.last_activity[user_id] = datetime.utcnow()
        
        # Start personalized keep-alive if this is an active user
        if user_id not in self.keep_alive_tasks:
            task = asyncio.create_task(self._user_specific_warming(user_id))
            self.keep_alive_tasks[user_id] = task
    
    async def _user_specific_warming(self, user_id: str):
        """Keep specific user's caches warm based on their activity"""
        try:
            while self.warming_active:
                # Check if user has been active recently
                last_active = self.last_activity.get(user_id)
                if not last_active or datetime.utcnow() - last_active > timedelta(minutes=30):
                    # User inactive, stop warming their specific caches
                    break
                
                # Warm their specific persona/tools
                try:
                    await get_cached_persona_memory("default", user_id)
                    await get_cached_tools_memory("generic")
                    logger.debug(f"Warmed caches for active user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to warm caches for user {user_id}: {e}")
                
                # Wait 5 minutes between user-specific warming
                await asyncio.sleep(300)
                
        except Exception as e:
            logger.error(f"User-specific warming error for {user_id}: {e}")
        finally:
            # Clean up task reference
            self.keep_alive_tasks.pop(user_id, None)
    
    def stop_warming_service(self):
        """Stop the cache warming service"""
        self.warming_active = False
        
        # Cancel all user-specific tasks
        for task in self.keep_alive_tasks.values():
            task.cancel()
        self.keep_alive_tasks.clear()
        
        logger.info("Cache warming service stopped")

# Global warming service instance
cache_warming_service = CacheWarmingService()