"""
Gateway-level caching middleware

Caches responses for frequently accessed endpoints like:
- Personas list
- Models list
- Static configuration data
"""
import hashlib
import json
import time
from typing import Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers

from app.shared.redis_client import redis_client
from app.shared.logging import logger


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Response caching middleware for gateway
    
    Features:
    - Selective endpoint caching
    - User-specific cache keys
    - Configurable TTLs
    - Cache invalidation support
    """
    
    # Endpoints to cache with TTL in seconds
    CACHEABLE_ENDPOINTS = {
        "/api/v1/chat/personas": 300,       # 5 minutes
        "/api/v1/models": 600,              # 10 minutes
        "/api/v1/chat/models": 600,         # 10 minutes
        "/api/v1/auth/validate": 60,        # 1 minute
        "/health": 10,                      # 10 seconds
        "/api/v1/chat/status": 30,          # 30 seconds
    }
    
    def __init__(self, app):
        super().__init__(app)
        self.redis = redis_client
        self.cache_prefix = "gateway:cache:"
    
    def _should_cache(self, path: str, method: str) -> Optional[int]:
        """Check if endpoint should be cached and return TTL"""
        if method != "GET":
            return None
            
        for endpoint, ttl in self.CACHEABLE_ENDPOINTS.items():
            if path.startswith(endpoint):
                return ttl
        return None
    
    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key based on request properties"""
        # Include user identity in cache key
        auth_header = request.headers.get("authorization", "")
        api_key = request.headers.get("x-api-key", "")
        
        # Create unique key components
        components = [
            self.cache_prefix,
            request.url.path,
            str(dict(request.query_params)),
            auth_header[:20] if auth_header else "",  # First 20 chars
            api_key[:20] if api_key else "",          # First 20 chars
        ]
        
        # Hash for consistent length
        key_string = ":".join(components)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        return f"{self.cache_prefix}{request.url.path}:{key_hash}"
    
    async def dispatch(self, request: Request, call_next):
        """Process request with caching logic"""
        
        # Check if endpoint should be cached
        ttl = self._should_cache(request.url.path, request.method)
        if not ttl:
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._get_cache_key(request)
        
        # Try to get from cache
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                # Parse cached response
                cached_response = json.loads(cached_data)
                
                # Create response with cached data
                response = Response(
                    content=cached_response["body"],
                    status_code=cached_response["status_code"],
                    headers=cached_response["headers"],
                    media_type=cached_response.get("media_type", "application/json")
                )
                
                # Add cache hit header
                response.headers["X-Cache"] = "HIT"
                response.headers["X-Cache-TTL"] = str(ttl)
                
                logger.debug(f"Cache HIT for {request.url.path}")
                return response
                
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            # Continue without cache on error
        
        # Cache miss - process request
        response = await call_next(request)
        
        # Only cache successful responses
        if response.status_code == 200:
            try:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                # Cache the response
                cache_data = {
                    "body": body.decode("utf-8"),
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type,
                    "cached_at": time.time()
                }
                
                await self.redis.setex(
                    cache_key,
                    ttl,
                    json.dumps(cache_data)
                )
                
                # Create new response with body
                response = Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
                # Add cache miss header
                response.headers["X-Cache"] = "MISS"
                response.headers["X-Cache-TTL"] = str(ttl)
                
                logger.debug(f"Cached response for {request.url.path} (TTL: {ttl}s)")
                
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
                # Return original response on cache error
        
        return response
    
    @classmethod
    async def invalidate_cache(cls, pattern: str):
        """Invalidate cache entries matching pattern"""
        try:
            redis = redis_client
            cache_pattern = f"{cls.cache_prefix}{pattern}*"
            
            # Find all matching keys
            keys = []
            async for key in redis.scan_iter(match=cache_pattern):
                keys.append(key)
            
            # Delete all matching keys
            if keys:
                await redis.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries matching {pattern}")
                
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")


# Helper function for manual cache invalidation
async def invalidate_gateway_cache(endpoint: str):
    """Invalidate gateway cache for specific endpoint"""
    await CacheMiddleware.invalidate_cache(endpoint)