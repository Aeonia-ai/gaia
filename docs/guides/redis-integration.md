# Redis Integration Guide



This document covers the comprehensive Redis caching system implemented in the Gaia platform for performance optimization and scalability.

## Overview

Redis is integrated across the Gaia microservices architecture to provide:
- **Authentication caching** (JWT tokens, API keys)
- **Persona data caching** (individual personas, lists, user preferences)
- **Rate limiting** (distributed, persistent across deployments)
- **Service health caching** (reduce monitoring overhead)

## Architecture

```
Internet → Gateway Service
             ↓
┌─────────────────────────────────┐
│ Redis Cache Layer               │
│ - Auth tokens (15min TTL)       │
│ - API keys (10min TTL)          │
│ - Personas (1hr TTL)            │
│ - Rate limits (persistent)      │
└─────────────────────────────────┘
             ↓
┌──────────┬──────────┬──────────┐
│Auth      │Chat      │Asset     │
│Service   │Service   │Service   │
└──────────┴──────────┴──────────┘
             ↓
┌─────────────────────────────────┐
│ PostgreSQL + NATS               │
└─────────────────────────────────┘
```

## Performance Improvements

### Local Development Results
- **Persona queries**: 1.955s → 0.060s (**97% improvement**)
- **Authentication**: 0.589s → 0.054s (**91% improvement**)
- **Consistent sub-100ms** response times on cache hits

### Production (Fly.io) Results
- **Auth caching**: 50ms → 23ms (**54% improvement** over multiple requests)
- **Memory efficient**: 1.16MB Redis usage
- **Cost effective**: $0.20 per 100K commands on Fly.io

## Implementation Details

### 1. Authentication Caching

**JWT Token Validation**
```python
# Cache key: auth:jwt:{token_hash}
# TTL: 15 minutes
# Reduces cryptographic operations on every request
```

**API Key Validation**
```python
# Cache key: auth:api_key:{key_hash}
# TTL: 10 minutes  
# Avoids database lookups for API key validation
```

### 2. Persona Caching

**Individual Personas**
```python
# Cache key: persona:{persona_id}
# TTL: 1 hour
# Caches full persona data including system prompts
```

**Personas List**
```python
# Cache key: personas:list:active|all[:created_by]
# TTL: 5 minutes
# Caches filtered persona lists
```

**User Preferences**
```python
# Cache key: user:persona:preference:{user_id}
# TTL: 10 minutes
# Caches user's selected persona
```

### 3. Rate Limiting

**Distributed Rate Limits**
```python
# Cache key: rate_limit:{identifier}:{window}
# Persistent across service restarts
# User/API key/IP based limits
```

### 4. Cache Invalidation

**Smart Invalidation Strategy**
- **Create**: Clears personas list cache
- **Update**: Clears specific persona + list caches  
- **Delete**: Clears specific persona + list caches
- **User preference change**: Clears user preference cache

## Local Development Setup

### 1. Docker Compose Configuration

Redis service is included in `docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  networks:
    - gaia_net
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-redis_password}
```

### 2. Environment Variables

Add to `.env`:
```bash
# Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=redis_password

# Cache Settings
AUTH_CACHE_TTL=900         # JWT cache TTL (15 minutes)
API_KEY_CACHE_TTL=600      # API key cache TTL (10 minutes)
SERVICE_HEALTH_CACHE_TTL=60 # Service health cache TTL (1 minute)
```

### 3. Starting Services

```bash
# Start all services including Redis
docker compose up

# Start just infrastructure
docker compose up db nats redis

# Check Redis health
curl http://localhost:8666/health | jq '.redis'
```

## Production Deployment (Fly.io)

### 1. Create Redis Instance

```bash
# Create Upstash Redis on Fly.io
flyctl redis create gaia-redis-dev --org aeonia-dev --region sjc --enable-eviction --no-replicas
```

### 2. Configure Application

**Update `fly.dev.toml`:**
```toml
[env]
  # Redis (Upstash Redis on Fly.io)
  REDIS_URL = "redis://fly-gaia-redis-dev.upstash.io:6379"
```

**Set Redis password as secret:**
```bash
flyctl secrets set REDIS_PASSWORD="your_redis_password" --app gaia-gateway-dev
```

### 3. Deploy with Redis

```bash
flyctl deploy --config fly.dev.toml --app gaia-gateway-dev
```

### 4. Verify Deployment

```bash
# Check Redis status
curl https://gaia-gateway-dev.fly.dev/health | jq '.redis'

# Test performance
curl -s https://gaia-gateway-dev.fly.dev/api/v1/chat/personas \
  -H "X-API-Key: YOUR_API_KEY"
```

## Monitoring and Maintenance

### Health Monitoring

Redis health is included in the gateway `/health` endpoint:

```json
{
  "redis": {
    "status": "healthy",
    "connected": true
  }
}
```

### Cache Metrics

**Local Development:**
```bash
# Check Redis memory usage
docker exec gaia-redis-1 redis-cli -a redis_password INFO memory

# List cache keys
docker exec gaia-redis-1 redis-cli -a redis_password KEYS "*"

# Check specific cache
docker exec gaia-redis-1 redis-cli -a redis_password GET "persona:123"
```

**Production (Fly.io):**
```bash
# Connect to Redis
flyctl redis connect gaia-redis-dev --org aeonia-dev

# Check metrics via health endpoint
curl https://gaia-gateway-dev.fly.dev/health
```

### Cache Management

**Clear specific cache patterns:**
```python
from app.shared.redis_client import redis_client

# Clear all persona caches
redis_client.flush_pattern("persona:*")

# Clear personas list caches
redis_client.flush_pattern("personas:list:*")

# Clear user preferences
redis_client.flush_pattern("user:persona:*")
```

## Graceful Fallback

The Redis integration includes graceful fallback when Redis is unavailable:

**Fallback Behavior:**
- ✅ Services continue operating normally
- ✅ Database queries executed directly
- ✅ Authentication still works (no caching)
- ✅ Health endpoint shows Redis as "unhealthy" but system remains functional

**Example Health Response (Redis down):**
```json
{
  "status": "degraded",
  "redis": {
    "status": "unhealthy", 
    "connected": false
  },
  "services": {
    "auth": {"status": "healthy"},
    "chat": {"status": "healthy"},
    "asset": {"status": "healthy"}
  }
}
```

## Configuration Options

### Cache TTL Settings

Configure cache durations in environment variables:

```bash
# Authentication caching
AUTH_CACHE_TTL=900          # 15 minutes
API_KEY_CACHE_TTL=600       # 10 minutes

# Persona caching  
PERSONA_CACHE_TTL=3600      # 1 hour
PERSONA_LIST_CACHE_TTL=300  # 5 minutes
USER_PREF_CACHE_TTL=600     # 10 minutes

# Service health caching
SERVICE_HEALTH_CACHE_TTL=60 # 1 minute
```

### Redis Connection Settings

```bash
# Connection configuration
REDIS_URL=redis://hostname:6379
REDIS_PASSWORD=your_password

# Connection pooling (handled automatically by redis_client.py)
REDIS_SOCKET_TIMEOUT=5
REDIS_CONNECT_TIMEOUT=5
REDIS_HEALTH_CHECK_INTERVAL=30
```

## Troubleshooting

### Common Issues

**1. Redis Connection Failed**
```bash
# Check Redis service status
docker ps | grep redis
curl http://localhost:8666/health | jq '.redis'

# Check Redis logs
docker logs gaia-redis-1
```

**2. Authentication Not Cached**
```bash
# Verify Redis keys are being created
docker exec gaia-redis-1 redis-cli -a redis_password KEYS "auth:*"

# Check authentication logs
docker logs gaia-gateway-1 | grep -i "cache"
```

**3. Performance Not Improved**
```bash
# Clear cache and test cold vs warm
docker exec gaia-redis-1 redis-cli -a redis_password FLUSHALL

# Time first request (cold)
time curl -H "X-API-Key: KEY" http://localhost:8666/api/v1/chat/personas

# Time second request (cached)  
time curl -H "X-API-Key: KEY" http://localhost:8666/api/v1/chat/personas
```

### Debug Commands

**Check cache contents:**
```bash
# List all keys
redis-cli KEYS "*"

# Get specific cache value
redis-cli GET "persona:123"

# Check TTL
redis-cli TTL "auth:jwt:abc123"

# Monitor commands in real-time
redis-cli MONITOR
```

**Performance testing:**
```bash
# Test authentication caching
for i in {1..5}; do
  time curl -H "X-API-Key: KEY" http://localhost:8666/api/v1/chat/personas
done

# Test persona caching
time curl http://localhost:8666/api/v1/chat/personas | jq '.total'
```

## Cost Optimization

### Fly.io Redis Pricing

- **Pay-as-you-go**: $0.20 per 100K commands
- **Fixed pricing**: Available for high-volume applications
- **Eviction enabled**: Automatically manages memory usage

### Cache Strategy Recommendations

**High-frequency data** (shorter TTL):
- Personas list: 5 minutes
- Service health: 1 minute

**Medium-frequency data** (medium TTL):
- API key validation: 10 minutes
- User preferences: 10 minutes

**Low-frequency data** (longer TTL):
- JWT tokens: 15 minutes  
- Individual personas: 1 hour

## Security Considerations

### Password Management

**Local Development:**
- Password in `.env` file (not committed)
- Docker secrets for container access

**Production:**
- Fly.io secrets for password storage
- TLS encryption for Redis connections
- Network isolation within Fly.io private network

### Cache Security

- **No sensitive data** stored in plaintext
- **Token hashes** used as cache keys (not full tokens)
- **TTL expiration** ensures data freshness
- **Cache invalidation** on user actions (logout, password change)

## Future Enhancements

### Planned Features
- Redis Cluster support for horizontal scaling
- Cache warming strategies for critical data
- Advanced cache analytics and monitoring
- Redis Streams for event sourcing integration
- Multi-region Redis replication

### Monitoring Improvements
- Cache hit/miss ratio tracking
- Performance metrics dashboard
- Automated cache tuning recommendations
- Cost optimization alerts

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Main development guide
- [Docker Configuration](../docker-compose.yml) - Container setup
- [Fly.io Configuration](../fly.dev.toml) - Production deployment