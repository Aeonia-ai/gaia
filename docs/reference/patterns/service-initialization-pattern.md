# Service Initialization Pattern


**Created**: January 2025  
**Updated**: January 2025 (with industry best practices)
**Purpose**: Establish consistent patterns for service initialization across all Gaia microservices

## The Problem

Service discovery failed because services were inconsistently initializing their health endpoints:
- Some services called `create_service_health_endpoint()` BEFORE adding routes
- Routes added via `include_router()` weren't discoverable
- No consistent pattern was established
- We didn't follow industry best practices for initialization order

## Industry Best Practices (2025)

Based on research, the recommended initialization order is:

1. **Basic health endpoint first** - For orchestrator probes (K8s, Docker)
2. **Middleware second** - Applied to all routes consistently  
3. **Application routes third** - Business logic endpoints
4. **Enhanced health/discovery last** - After all routes are registered

## The Correct Pattern for Gaia

```python
# app/services/{service_name}/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.shared.service_discovery import create_service_health_endpoint

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan management for startup/shutdown"""
    # Startup: Initialize connections, register with discovery
    logger.info(f"Starting {SERVICE_NAME} service...")
    # Initialize database, NATS, etc.
    yield
    # Shutdown: Cleanup connections, deregister
    logger.info(f"Shutting down {SERVICE_NAME} service...")

# 1. Create FastAPI app with lifespan
app = FastAPI(
    title="Service Name",
    version="0.2",
    lifespan=lifespan
)

# 2. Basic health endpoint FIRST (for orchestrators)
@app.get("/health")
async def basic_health():
    """Basic health check for K8s/Docker probes"""
    return {"status": "healthy", "service": "service-name"}

# 3. Add middleware (applies to all routes)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, ...)

# 4. Define business routes OR include routers
@app.get("/direct-route")
async def direct_route():
    pass

# Include external routers
app.include_router(some_router, prefix="/prefix")

# 5. LAST: Create enhanced health endpoint with route discovery
# This MUST be called AFTER all routes are registered
# This overwrites the basic /health with an enhanced version
create_service_health_endpoint(app, "service-name", "version")
```

## TL;DR - One Paragraph Summary

The correct initialization order for FastAPI microservices is: (1) create the FastAPI app with lifespan events, (2) define a basic `/health` endpoint immediately for orchestrator probes, (3) add all middleware to ensure consistent processing across routes, (4) register all business logic routes and routers, and finally (5) create the enhanced health endpoint with route discovery capability. This order ensures health checks are always available (even during partial startup), middleware applies to all routes consistently, and the service discovery system can see all registered routes. The key mistake we made was calling `create_service_health_endpoint()` before `include_router()`, which meant the discovery system couldn't see any routes - this is why the chat service showed 0 routes despite having many defined.

## Why This Order Matters

1. **Basic Health First**: Orchestrators (K8s/Docker) can always probe service health
2. **Middleware Second**: Ensures all routes benefit from compression, CORS, auth, etc.
3. **Routes Third**: All business logic routes must be registered before discovery
4. **Enhanced Health Last**: Can now discover all registered routes for service mesh

## Common Mistakes

❌ **Wrong**: Creating health endpoint before routes
```python
create_service_health_endpoint(app, "chat", "0.2")  # Too early!
app.include_router(chat_router)  # Routes won't be discovered
```

✅ **Correct**: Creating health endpoint after routes
```python
app.include_router(chat_router)  # Register routes first
create_service_health_endpoint(app, "chat", "0.2")  # Now discover them
```

## Verification

Test service discovery:
```bash
# Should return all routes
curl "https://service-url/health?include_routes=true" | jq '.routes'
```

## Service Checklist

- [ ] Auth Service - ✅ Correct (defines routes directly)
- [ ] Asset Service - ✅ Correct (health endpoint after router)
- [ ] KB Service - ✅ Correct (defines routes directly)
- [ ] Chat Service - ❌ Fixed (moved health endpoint to end)
- [ ] Web Service - N/A (doesn't use service discovery)

## Future Improvements

1. **Automated Testing**: Add tests to verify route discovery works
2. **Linting Rule**: Create a linter to enforce initialization order
3. **Service Template**: Update `create-new-service.sh` to use correct pattern