"""
KB Cache Implementation

Provides Redis-based caching for KB operations to improve performance
and reduce filesystem access in production.
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.shared.redis_client import redis_client

logger = logging.getLogger(__name__)

class KBCache:
    """
    Redis-based cache for KB operations.
    
    Caches:
    - Search results
    - File contents
    - Context metadata
    - Navigation trees
    - Synthesis results
    """
    
    def __init__(self, ttl: int = 3600, enabled: bool = True):
        self.ttl = ttl  # Default 1 hour
        # Temporarily disable cache to debug search issues
        self.enabled = False  # was: enabled and redis_client.is_connected()
        self.prefix = "kb:cache:"
        
        if not self.enabled:
            logger.warning("KB cache disabled - Redis not available")
    
    def _make_key(self, category: str, identifier: str) -> str:
        """Generate cache key"""
        return f"{self.prefix}{category}:{identifier}"
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query strings"""
        return hashlib.md5(query.encode()).hexdigest()
    
    async def get_search_results(self, query: str, contexts: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Get cached search results"""
        if not self.enabled:
            return None
            
        try:
            # Include contexts in cache key
            cache_id = f"{query}:{','.join(contexts or [])}"
            key = self._make_key("search", self._hash_query(cache_id))
            
            data = redis_client.get(key)
            if data:
                logger.debug(f"Cache hit for search: {query}")
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    async def set_search_results(self, query: str, results: Dict[str, Any], contexts: Optional[List[str]] = None):
        """Cache search results"""
        if not self.enabled:
            return
            
        try:
            cache_id = f"{query}:{','.join(contexts or [])}"
            key = self._make_key("search", self._hash_query(cache_id))
            
            # Add cache metadata
            results["_cached_at"] = datetime.now().isoformat()
            
            redis_client.set(
                key, 
                json.dumps(results),
                ex=self.ttl
            )
            logger.debug(f"Cached search results for: {query}")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def get_file_content(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached file content with metadata"""
        if not self.enabled:
            return None
            
        try:
            key = self._make_key("file", file_path.replace("/", "_"))
            data = redis_client.get(key)
            
            if data:
                logger.debug(f"Cache hit for file: {file_path}")
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    async def set_file_content(self, file_path: str, content: str, metadata: Optional[Dict] = None):
        """Cache file content with metadata"""
        if not self.enabled:
            return
            
        try:
            key = self._make_key("file", file_path.replace("/", "_"))
            
            cache_data = {
                "content": content,
                "metadata": metadata or {},
                "_cached_at": datetime.now().isoformat()
            }
            
            redis_client.set(
                key,
                json.dumps(cache_data),
                ex=self.ttl
            )
            logger.debug(f"Cached file content: {file_path}")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def get_context(self, context_name: str) -> Optional[Dict[str, Any]]:
        """Get cached context data"""
        if not self.enabled:
            return None
            
        try:
            key = self._make_key("context", context_name)
            data = redis_client.get(key)
            
            if data:
                logger.debug(f"Cache hit for context: {context_name}")
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    async def set_context(self, context_name: str, context_data: Dict[str, Any]):
        """Cache context data"""
        if not self.enabled:
            return
            
        try:
            key = self._make_key("context", context_name)
            
            # Add cache metadata
            context_data["_cached_at"] = datetime.now().isoformat()
            
            redis_client.set(
                key,
                json.dumps(context_data),
                ex=self.ttl * 2  # Contexts are more stable, cache longer
            )
            logger.debug(f"Cached context: {context_name}")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def get_navigation(self, start_path: str, max_depth: int) -> Optional[Dict[str, Any]]:
        """Get cached navigation tree"""
        if not self.enabled:
            return None
            
        try:
            cache_id = f"{start_path}:depth{max_depth}"
            key = self._make_key("nav", self._hash_query(cache_id))
            data = redis_client.get(key)
            
            if data:
                logger.debug(f"Cache hit for navigation: {start_path}")
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    async def set_navigation(self, start_path: str, max_depth: int, nav_data: Dict[str, Any]):
        """Cache navigation tree"""
        if not self.enabled:
            return
            
        try:
            cache_id = f"{start_path}:depth{max_depth}"
            key = self._make_key("nav", self._hash_query(cache_id))
            
            # Add cache metadata
            nav_data["_cached_at"] = datetime.now().isoformat()
            
            redis_client.set(
                key,
                json.dumps(nav_data),
                ex=self.ttl * 4  # Navigation is very stable, cache longer
            )
            logger.debug(f"Cached navigation: {start_path}")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        if not self.enabled:
            return
            
        try:
            full_pattern = f"{self.prefix}{pattern}"
            
            # Get all matching keys
            keys = []
            async for key in redis_client.scan_iter(match=full_pattern):
                keys.append(key)
            
            # Delete in batch
            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries matching: {pattern}")
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
    
    async def invalidate_all(self):
        """Clear all KB cache entries"""
        await self.invalidate_pattern("*")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled:
            return {"enabled": False}
            
        try:
            # Count keys by category
            stats = {
                "enabled": True,
                "ttl": self.ttl,
                "categories": {}
            }
            
            for category in ["search", "file", "context", "nav"]:
                pattern = f"{self.prefix}{category}:*"
                count = 0
                async for _ in redis_client.scan_iter(match=pattern):
                    count += 1
                stats["categories"][category] = count
            
            stats["total_entries"] = sum(stats["categories"].values())
            
            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"enabled": True, "error": str(e)}

# Global cache instance
kb_cache = KBCache()