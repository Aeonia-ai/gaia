# Gaia Platform Optimization Guide

This document outlines performance optimization opportunities for the Gaia Platform, prioritized by implementation effort and impact.

## Overview

The Gaia Platform demonstrates solid microservices architecture but has several low-cost optimization opportunities that could provide significant performance improvements with minimal risk. This guide focuses on proven optimization patterns that maintain API compatibility while delivering substantial performance gains.

## Quick Wins (High ROI, Low Effort)

### 1. Database Indexing ⚡ **PRIORITY 1**

**Problem**: Missing database indexes causing slow persona queries
**Effort**: 30 minutes
**Impact**: 30-50% faster database queries

**Implementation**:
```sql
-- Connect to your PostgreSQL database and run:
CREATE INDEX CONCURRENTLY idx_personas_active ON personas(is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_personas_created_by ON personas(created_by);
CREATE INDEX CONCURRENTLY idx_personas_active_created_at ON personas(is_active, created_at) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_user_persona_preferences_user ON user_persona_preferences(user_id);

-- Verify indexes were created:
\d+ personas
\d+ user_persona_preferences
```

**Validation**:
```bash
# Test persona list performance before/after
time curl -H "X-API-Key: YOUR_KEY" http://localhost:8666/api/v1/chat/personas
```

### 2. Response Compression ⚡ **PRIORITY 2**

**Problem**: Large JSON responses without compression
**Effort**: 15 minutes
**Impact**: 30-50% smaller response sizes

**Implementation**:
Add to `app/gateway/main.py` and all service main files:
```python
from fastapi.middleware.gzip import GZipMiddleware

# Add after FastAPI app creation, before CORS middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Validation**:
```bash
# Check response headers include compression
curl -H "Accept-Encoding: gzip" -H "X-API-Key: YOUR_KEY" -v http://localhost:8666/api/v1/chat/personas
# Should see: Content-Encoding: gzip
```

### 3. Database Connection Pool Enhancement ⚡ **PRIORITY 3**

**Problem**: Conservative connection pool settings limiting concurrency
**Effort**: 10 minutes  
**Impact**: Better handling of concurrent requests

**Implementation**:
Update `app/shared/database.py`:
```python
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "20")),      # Increased from 5
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "30")), # Increased from 10
    pool_timeout=30,
    pool_reset_on_return='commit'  # Add for better connection hygiene
)
```

Update `.env.example`:
```bash
# Enhanced database configuration
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
```

### 4. Cache TTL Optimization ⚡ **PRIORITY 4**

**Problem**: Conservative cache TTLs causing unnecessary database hits
**Effort**: 30 minutes
**Impact**: 50-70% reduction in database queries for repeated requests

**Implementation**:
Update `app/shared/redis_client.py`:
```python
class CacheManager:
    # Optimized TTL values based on data volatility
    CACHE_TTLS = {
        "persona_individual": 3600,      # 1 hour (unchanged)
        "persona_list_active": 1800,     # 30 min (was 5 min)
        "persona_list_all": 900,         # 15 min (was 5 min)  
        "user_preference": 3600,         # 1 hour (was 10 min)
        "auth_jwt": 1800,               # 30 min (was 15 min)
        "auth_api_key": 1200,           # 20 min (was 10 min)
        "service_health": 60             # 1 min (unchanged)
    }
```

Update persona service cache calls:
```python
# In persona_service_postgres.py, update TTL values:
redis_client.set_json(cache_key, cache_data, ex=1800)  # personas list: 30 min
redis_client.set(pref_cache_key, persona_id, ex=3600)  # user preference: 1 hour
```

**Total Quick Wins**: ~1.5 hours for 40-60% overall performance improvement

## Medium Effort Optimizations (4-8 hours each)

### 5. Container Multi-stage Builds

**Problem**: Large container images with unnecessary dependencies
**Impact**: 40-60% smaller images, 30-50% faster startup times

**Implementation**:
Create optimized `Dockerfile.gateway`:
```dockerfile
# Multi-stage build for gateway service
FROM node:18-alpine AS node-builder
RUN npm install -g @modelcontextprotocol/server-filesystem

FROM python:3.11-alpine AS python-builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

FROM python:3.11-alpine
# Copy only what we need
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-builder /usr/local/bin/mcp-server-filesystem /usr/local/bin/
COPY --from=python-builder /app/wheels /wheels

# Install Python dependencies
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Copy application code
WORKDIR /app
COPY ./app /app/app
COPY ./docs /app/docs

# Set environment and expose port
ENV PYTHONPATH=/app
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6. API Pagination

**Problem**: Large list responses without pagination
**Impact**: Faster response times, better user experience

**Implementation**:
Update `PostgresPersonaService.list_personas()`:
```python
async def list_personas(
    self, 
    active_only: bool = True, 
    created_by: str = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[Persona], int]:
    """List personas with pagination"""
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Get total count
    count_query = "SELECT COUNT(*) FROM personas WHERE 1=1"
    if active_only:
        count_query += " AND is_active = true"
    if created_by:
        count_query += " AND created_by = :created_by"
    
    count_result = db.execute(text(count_query), params)
    total_count = count_result.scalar()
    
    # Get paginated results
    query += f" LIMIT {page_size} OFFSET {offset}"
    # ... rest of existing implementation
    
    return personas, total_count
```

Update gateway endpoints to support pagination:
```python
@app.get("/api/v1/chat/personas")
async def list_personas(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True)
):
    personas, total = await persona_service.list_personas(
        active_only=active_only,
        page=page,
        page_size=page_size
    )
    
    return {
        "personas": personas,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": math.ceil(total / page_size)
        }
    }
```

### 7. HTTP Client Connection Pooling

**Problem**: HTTP clients created per request in gateway
**Impact**: 15-25% reduction in processing overhead

**Implementation**:
Create `app/shared/http_client.py`:
```python
import httpx
from typing import Optional

class HTTPClientManager:
    _client: Optional[httpx.AsyncClient] = None
    
    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(
                    max_connections=100, 
                    max_keepalive_connections=20
                ),
                transport=httpx.AsyncHTTPTransport(retries=2)
            )
        return cls._client
    
    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.aclose()
            cls._client = None
```

Update gateway service calls to use pooled client:
```python
# Replace httpx.AsyncClient() usage with:
client = await HTTPClientManager.get_client()
response = await client.get(f"{service_url}/endpoint")
```

### 8. Request Deduplication Middleware

**Problem**: Identical requests processed multiple times
**Impact**: 20-30% reduction in processing for duplicate requests

**Implementation**:
```python
import hashlib
from fastapi import Request
from datetime import datetime, timedelta

# Add to gateway main.py
@app.middleware("http")
async def request_deduplication(request: Request, call_next):
    # Only deduplicate GET requests
    if request.method != "GET":
        return await call_next(request)
    
    # Create request signature
    url_path = str(request.url.path)
    query_params = str(request.url.query)
    auth_header = request.headers.get("authorization", "")
    api_key = request.headers.get("x-api-key", "")
    
    request_signature = f"{url_path}:{query_params}:{auth_header}:{api_key}"
    request_hash = hashlib.sha256(request_signature.encode()).hexdigest()[:16]
    
    # Check cache for recent identical request
    cache_key = f"request_dedup:{request_hash}"
    if redis_client.is_connected():
        cached_response = redis_client.get_json(cache_key)
        if cached_response:
            return JSONResponse(content=cached_response["content"])
    
    # Process request
    response = await call_next(request)
    
    # Cache successful responses for 30 seconds
    if response.status_code == 200 and redis_client.is_connected():
        response_body = await response.body()
        redis_client.set_json(
            cache_key, 
            {"content": response_body.decode()}, 
            ex=30
        )
    
    return response
```

## Advanced Optimizations

### 9. Background Job Processing

**Problem**: Cache invalidation and health checks block request processing
**Implementation**: Use NATS for async cache invalidation

```python
# Add to shared utilities
async def invalidate_cache_async(pattern: str):
    """Asynchronous cache invalidation using NATS"""
    await nats_client.publish("gaia.cache.invalidate", {
        "pattern": pattern,
        "timestamp": datetime.now().isoformat()
    })

# Background worker to process cache invalidation
async def cache_invalidation_worker():
    async def cache_handler(msg):
        data = json.loads(msg.data.decode())
        redis_client.flush_pattern(data["pattern"])
    
    await nats_client.subscribe("gaia.cache.invalidate", cb=cache_handler)
```

### 10. Memory Optimization

**Problem**: Inefficient memory usage in containers
**Implementation**: Add memory optimization to Dockerfiles

```dockerfile
# Add to all Dockerfile files
ENV PYTHONMALLOC=malloc
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_TOP_PAD_=131072
ENV MALLOC_MMAP_MAX_=65536

# Also add memory limits to docker compose.yml
deploy:
  resources:
    limits:
      memory: 512M
    reservations:
      memory: 256M
```

## Performance Monitoring

### 11. Response Time Monitoring

```python
import time
from fastapi import Request

@app.middleware("http")
async def performance_monitoring(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Log slow requests
    if duration > 1.0:
        logger.warning(f"Slow request: {request.method} {request.url.path} took {duration:.2f}s")
    
    # Add performance header
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    
    return response
```

### 12. Cache Hit Rate Monitoring

```python
class CacheMetrics:
    def __init__(self):
        self.hits = 0
        self.misses = 0
    
    def record_hit(self):
        self.hits += 1
    
    def record_miss(self):
        self.misses += 1
    
    def get_hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

# Add to redis_client.py
cache_metrics = CacheMetrics()
```

## Implementation Timeline

### Phase 1: Quick Wins (Week 1)
- [ ] Database indexing (30 min)
- [ ] Response compression (15 min)  
- [ ] Connection pool enhancement (10 min)
- [ ] Cache TTL optimization (30 min)

**Expected Improvement**: 40-60% performance boost

### Phase 2: Medium Effort (Week 2)
- [ ] Container multi-stage builds (4 hours)
- [ ] HTTP client pooling (2 hours)
- [ ] API pagination (4 hours)

**Expected Improvement**: Additional 20-30% improvement

### Phase 3: Advanced (Week 3)
- [ ] Request deduplication (4 hours)
- [ ] Background job processing (6 hours)
- [ ] Performance monitoring (2 hours)

**Expected Improvement**: Additional 15-25% improvement

### Phase 4: Fine-tuning (Week 4)
- [ ] Memory optimization (2 hours)
- [ ] Cache metrics and monitoring (3 hours)
- [ ] Performance testing and validation (3 hours)

## Validation and Testing

### Performance Testing Commands

```bash
# Database query performance
time curl -H "X-API-Key: YOUR_KEY" http://localhost:8666/api/v1/chat/personas

# Response compression validation
curl -H "Accept-Encoding: gzip" -H "X-API-Key: YOUR_KEY" -v http://localhost:8666/api/v1/chat/personas

# Cache hit rate testing
for i in {1..10}; do
  time curl -H "X-API-Key: YOUR_KEY" http://localhost:8666/api/v1/chat/personas
done

# Memory usage monitoring
docker stats --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}"

# Redis cache inspection
docker exec gaia-redis-1 redis-cli -a redis_password INFO memory
docker exec gaia-redis-1 redis-cli -a redis_password KEYS "*" | wc -l
```

### Expected Performance Metrics

| Optimization | Metric | Before | After | Improvement |
|-------------|--------|--------|-------|-------------|
| Database Indexes | Persona query time | 200ms | 100ms | 50% |
| Response Compression | Response size | 50KB | 25KB | 50% |
| Connection Pooling | Concurrent requests | 10/sec | 25/sec | 150% |
| Cache TTL | Database queries | 100/min | 30/min | 70% |
| Container Optimization | Image size | 500MB | 200MB | 60% |
| HTTP Client Pooling | Service calls | 50ms | 30ms | 40% |

## Risk Assessment

**Low Risk Optimizations** (Safe to implement immediately):
- Database indexing
- Response compression  
- Connection pool settings
- Cache TTL adjustments

**Medium Risk Optimizations** (Test thoroughly):
- Container multi-stage builds
- Request deduplication
- Background job processing

**Best Practices**:
1. Implement one optimization at a time
2. Test each change in development environment
3. Monitor performance metrics before/after
4. Have rollback plan for each change
5. Document all configuration changes

## Related Documentation

- [Redis Integration Guide](./redis-integration.md) - Comprehensive caching documentation
- [CLAUDE.md](../CLAUDE.md) - Main development guide
- [Docker Configuration](../docker compose.yml) - Container setup
- [Fly.io Configuration](../fly.dev.toml) - Production deployment

---

**Next Steps**: Start with Phase 1 quick wins for immediate 40-60% performance improvement with minimal risk and effort.