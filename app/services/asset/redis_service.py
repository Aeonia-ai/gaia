import json
import asyncio
from typing import Optional, Any, Dict, List
try:
    import redis.asyncio as redis
except ImportError:
    import aioredis as redis  # Fallback for older installations
from app.shared.config import settings
from app.shared.logging import get_logger

logger = get_logger(__name__)


class RedisService:
    def __init__(self):
        self.settings = settings
        self._redis_client: Optional[redis.Redis] = None

    async def get_client(self) -> redis.Redis:
        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(
                    self.settings.REDIS_URL,
                    password=self.settings.REDIS_PASSWORD,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                await self._redis_client.ping()
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        
        return self._redis_client

    async def close(self):
        if self._redis_client:
            await self._redis_client.aclose()
            self._redis_client = None

    async def set_cache(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None
    ) -> bool:
        try:
            client = await self.get_client()
            ttl = ttl_seconds or self.settings.DEFAULT_CACHE_TTL_SECONDS
            
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = await client.setex(key, ttl, value)
            logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")
            return result
        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {e}")
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        try:
            client = await self.get_client()
            value = await client.get(key)
            
            if value is None:
                return None
            
            # Try to parse as JSON, fallback to string
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.error(f"Failed to get cache for key {key}: {e}")
            return None

    async def delete_cache(self, key: str) -> bool:
        try:
            client = await self.get_client()
            result = await client.delete(key)
            logger.debug(f"Cache deleted for key: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {e}")
            return False

    async def get_cache_pattern(self, pattern: str) -> Dict[str, Any]:
        try:
            client = await self.get_client()
            keys = await client.keys(pattern)
            
            if not keys:
                return {}
            
            # Get all values at once
            values = await client.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value
            
            return result
        except Exception as e:
            logger.error(f"Failed to get cache pattern {pattern}: {e}")
            return {}

    async def increment_counter(self, key: str, amount: int = 1) -> int:
        try:
            client = await self.get_client()
            result = await client.incrby(key, amount)
            logger.debug(f"Counter incremented for key: {key}, new value: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to increment counter for key {key}: {e}")
            return 0

    async def set_hash(self, key: str, mapping: Dict[str, Any], ttl_seconds: Optional[int] = None):
        try:
            client = await self.get_client()
            
            # Convert values to strings, handling JSON serialization
            string_mapping = {}
            for k, v in mapping.items():
                if isinstance(v, (dict, list)):
                    string_mapping[k] = json.dumps(v)
                else:
                    string_mapping[k] = str(v)
            
            await client.hset(key, mapping=string_mapping)
            
            if ttl_seconds:
                await client.expire(key, ttl_seconds)
            
            logger.debug(f"Hash set for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to set hash for key {key}: {e}")
            return False

    async def get_hash(self, key: str) -> Dict[str, Any]:
        try:
            client = await self.get_client()
            result = await client.hgetall(key)
            
            # Try to parse JSON values back
            parsed_result = {}
            for k, v in result.items():
                try:
                    parsed_result[k] = json.loads(v)
                except json.JSONDecodeError:
                    parsed_result[k] = v
            
            return parsed_result
        except Exception as e:
            logger.error(f"Failed to get hash for key {key}: {e}")
            return {}

    # Asset-specific caching methods

    async def cache_asset_search(
        self, 
        search_query: str, 
        category: str, 
        results: List[Dict[str, Any]], 
        ttl_seconds: Optional[int] = None
    ) -> bool:
        cache_key = f"asset_search:{category}:{hash(search_query)}"
        return await self.set_cache(cache_key, results, ttl_seconds)

    async def get_cached_asset_search(
        self, 
        search_query: str, 
        category: str
    ) -> Optional[List[Dict[str, Any]]]:
        cache_key = f"asset_search:{category}:{hash(search_query)}"
        return await self.get_cache(cache_key)

    async def cache_external_asset(
        self, 
        source_name: str, 
        asset_id: str, 
        asset_data: Dict[str, Any], 
        ttl_seconds: Optional[int] = None
    ) -> bool:
        cache_key = f"external_asset:{source_name}:{asset_id}"
        return await self.set_cache(cache_key, asset_data, ttl_seconds)

    async def get_cached_external_asset(
        self, 
        source_name: str, 
        asset_id: str
    ) -> Optional[Dict[str, Any]]:
        cache_key = f"external_asset:{source_name}:{asset_id}"
        return await self.get_cache(cache_key)

    async def track_generation_cost(
        self, 
        session_id: str, 
        cost: float
    ) -> float:
        daily_key = f"generation_cost:daily:{session_id}"
        total_key = f"generation_cost:total:{session_id}"
        
        try:
            client = await self.get_client()
            # Add to daily total (expires at midnight)
            daily_cost = await client.incrbyfloat(daily_key, cost)
            await client.expire(daily_key, 86400)  # 24 hours
            
            # Add to total
            total_cost = await client.incrbyfloat(total_key, cost)
            
            logger.info(f"Generation cost tracked - Session: {session_id}, Cost: ${cost:.4f}, Daily: ${daily_cost:.4f}, Total: ${total_cost:.4f}")
            return daily_cost
        except Exception as e:
            logger.error(f"Failed to track generation cost: {e}")
            return 0.0

    async def get_generation_cost_stats(self, session_id: str) -> Dict[str, float]:
        daily_key = f"generation_cost:daily:{session_id}"
        total_key = f"generation_cost:total:{session_id}"
        
        try:
            client = await self.get_client()
            daily_cost = await client.get(daily_key) or "0"
            total_cost = await client.get(total_key) or "0"
            
            return {
                "daily_cost": float(daily_cost),
                "total_cost": float(total_cost),
                "remaining_budget": max(0, self.settings.MAX_GENERATION_COST_PER_ASSET - float(daily_cost))
            }
        except Exception as e:
            logger.error(f"Failed to get generation cost stats: {e}")
            return {"daily_cost": 0.0, "total_cost": 0.0, "remaining_budget": self.settings.MAX_GENERATION_COST_PER_ASSET}


# Global Redis service instance
redis_service = RedisService()