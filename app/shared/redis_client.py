"""
Redis client utility for caching and session management.
Provides consistent Redis connection management across all services.
"""
import json
import logging
from typing import Any, Optional, Union
from redis import Redis
from redis.exceptions import RedisError, ConnectionError
from app.shared.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client wrapper with connection pooling and error handling."""
    
    def __init__(self):
        self._client: Optional[Redis] = None
        self._connected = False
    
    @property
    def client(self) -> Redis:
        """Get Redis client, initializing if needed."""
        if self._client is None:
            self._connect()
        return self._client
    
    def _connect(self):
        """Initialize Redis connection."""
        try:
            # Parse URL and override password if provided separately
            redis_kwargs = {
                "decode_responses": True,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True,
                "health_check_interval": 30
            }
            
            # If password is provided separately, use it
            if settings.REDIS_PASSWORD:
                redis_kwargs["password"] = settings.REDIS_PASSWORD
            
            self._client = Redis.from_url(
                settings.REDIS_URL,
                **redis_kwargs
            )
            # Test connection
            self._client.ping()
            self._connected = True
            logger.info("Redis connection established")
        except (ConnectionError, RedisError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            raise
    
    def is_connected(self) -> bool:
        """Check if Redis is connected and healthy."""
        try:
            # Try to initialize if not already done
            if self._client is None:
                self._connect()
            self._client.ping()
            return True
        except (ConnectionError, RedisError):
            self._connected = False
            return False
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        try:
            return self.client.get(key)
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis GET failed for key {key}: {e}")
            return None
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value pair with optional expiration."""
        try:
            return self.client.set(key, value, ex=ex)
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis SET failed for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key."""
        try:
            return bool(self.client.delete(key))
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis DELETE failed for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(self.client.exists(key))
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis EXISTS failed for key {key}: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter."""
        try:
            return self.client.incr(key, amount)
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis INCR failed for key {key}: {e}")
            return None
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        try:
            return self.client.expire(key, seconds)
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis EXPIRE failed for key {key}: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value by key."""
        value = self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode JSON for key {key}: {e}")
            return None
    
    def set_json(self, key: str, value: dict, ex: Optional[int] = None) -> bool:
        """Set JSON value with optional expiration."""
        try:
            json_str = json.dumps(value)
            return self.set(key, json_str, ex=ex)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to encode JSON for key {key}: {e}")
            return False
    
    def get_or_set(self, key: str, default_func, ex: Optional[int] = None) -> Any:
        """Get value or set default if not exists."""
        value = self.get(key)
        if value is not None:
            return value
        
        # Generate default value
        default_value = default_func()
        if isinstance(default_value, (dict, list)):
            self.set_json(key, default_value, ex=ex)
        else:
            self.set(key, str(default_value), ex=ex)
        
        return default_value
    
    async def ping(self) -> bool:
        """Async ping to test Redis connection."""
        try:
            if self._client:
                self._client.ping()
                return True
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis ping failed: {e}")
        return False
    
    def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis pattern flush failed for {pattern}: {e}")
            return 0
    
    async def scan_iter(self, match: str = None, count: int = 100):
        """Async generator for scanning Redis keys matching pattern."""
        if not self.is_connected():
            return
        
        try:
            # Use sync scan_iter but yield results asynchronously
            for key in self.client.scan_iter(match=match, count=count):
                yield key
        except (ConnectionError, RedisError) as e:
            logger.error(f"Redis scan error: {e}")
    
    async def delete(self, *keys):
        """Delete one or more keys."""
        if not keys or not self.is_connected():
            return 0
        
        try:
            return self.client.delete(*keys)
        except (ConnectionError, RedisError) as e:
            logger.error(f"Redis delete error: {e}")
            return 0

# Global Redis client instance
redis_client = RedisClient()

# Cache decorators and utilities
class CacheManager:
    """Higher-level cache management utilities."""
    
    @staticmethod
    def cache_key(*parts: str) -> str:
        """Generate consistent cache key."""
        return ":".join(str(part) for part in parts if part)
    
    @staticmethod
    def auth_cache_key(token_hash: str) -> str:
        """Generate auth cache key."""
        return CacheManager.cache_key("auth", "jwt", token_hash)
    
    @staticmethod
    def api_key_cache_key(key_hash: str) -> str:
        """Generate API key cache key."""
        return CacheManager.cache_key("auth", "api_key", key_hash)
    
    @staticmethod
    def user_session_key(user_id: str) -> str:
        """Generate user session cache key."""
        return CacheManager.cache_key("user", "session", user_id)
    
    @staticmethod
    def persona_cache_key(persona_id: str) -> str:
        """Generate persona cache key."""
        return CacheManager.cache_key("persona", persona_id)
    
    @staticmethod
    def rate_limit_key(identifier: str, window: str) -> str:
        """Generate rate limit cache key."""
        return CacheManager.cache_key("rate_limit", identifier, window)
    
    @staticmethod
    def service_health_key(service_name: str) -> str:
        """Generate service health cache key."""
        return CacheManager.cache_key("service", "health", service_name)
    
    @staticmethod
    def personas_list_key(active_only: bool = True, created_by: Optional[str] = None) -> str:
        """Generate personas list cache key."""
        if created_by:
            return CacheManager.cache_key("personas", "list", "active" if active_only else "all", created_by)
        return CacheManager.cache_key("personas", "list", "active" if active_only else "all")
    
    @staticmethod
    def user_persona_preference_key(user_id: str) -> str:
        """Generate user persona preference cache key."""
        return CacheManager.cache_key("user", "persona", "preference", user_id)

# Aliases for convenience
cache = redis_client
cache_key = CacheManager.cache_key