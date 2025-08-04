# Adding a New Microservice to Gaia Platform

**Updated**: January 2025

## Quick Start

Adding a new microservice is now simplified with our automated tooling:

```bash
# Create a new service (e.g., "analytics" on port 8005)
./scripts/create-new-service.sh analytics 8005

# The script creates everything needed and provides next steps
```

## What Gets Created Automatically

The `create-new-service.sh` script creates:

1. **Service directory structure**
   - `app/services/<service-name>/`
   - `__init__.py`
   - `main.py` with FastAPI boilerplate

2. **Dockerfile**
   - `Dockerfile.<service-name>`
   - Optimized for Python microservices

3. **Docker Compose entry**
   - Service definition added to `docker compose.yml`
   - Proper networking and dependencies

4. **Fly.io deployment configs**
   - `fly.<service-name>.dev.toml`
   - `fly.<service-name>.staging.toml`
   - `fly.<service-name>.production.toml`

5. **Configuration updates**
   - `.env.example` - adds SERVICE_URL variable
   - `app/shared/config.py` - adds service URL configuration

## Manual Steps Still Required

### 1. Update Service Registry

Add your service to `app/shared/service_registry.py`:

```python
SERVICE_REGISTRY = {
    # ... existing services ...
    
    "analytics": ServiceConfig(
        name="analytics",
        port=8005,
        description="Analytics and metrics service",
        has_v1_api=True,
        has_v0_2_api=True,
        endpoints=[
            "/metrics",
            "/metrics/export",
            "/reports/generate",
            "/reports/{report_id}"
        ]
    ),
}
```

### 2. Update Gateway Routes

Add to `app/gateway/main.py`:

```python
# In SERVICE_URLS dictionary
SERVICE_URLS = {
    "auth": settings.AUTH_SERVICE_URL,
    "asset": settings.ASSET_SERVICE_URL,
    "chat": settings.CHAT_SERVICE_URL,
    "kb": settings.KB_SERVICE_URL,
    "analytics": settings.ANALYTICS_SERVICE_URL,  # Add this
}
```

Then add your route handlers. For simple forwarding:

```python
# Analytics endpoints - forward to analytics service
@app.get("/api/v1/analytics/metrics", tags=["Analytics"])
async def get_metrics(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get analytics metrics"""
    return await forward_request_to_service(
        service_name="analytics",
        path="/metrics",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )
```

### 3. Deploy to Fly.io

```bash
# Create the app
fly apps create gaia-analytics-dev

# Deploy
fly deploy --config fly.analytics.dev.toml

# Set required secrets
fly secrets set -a gaia-analytics-dev \
  DATABASE_URL="..." \
  REDIS_URL="..." \
  API_KEY="..." \
  SUPABASE_URL="..." \
  SUPABASE_ANON_KEY="..."

# Update gateway with new service URL
fly secrets set -a gaia-gateway-dev \
  ANALYTICS_SERVICE_URL="https://gaia-analytics-dev.fly.dev"
```

## Future: Fully Automated Gateway Routes

We're working on making gateway routes fully automatic using the service registry. Once implemented, you'll just need to:

1. Run `create-new-service.sh`
2. Add to service registry
3. Deploy - routes will be automatic!

See `scripts/simplify-gateway-routes.py` for the proposed approach.

## Service Development Tips

### 1. Start Simple
Begin with just a health endpoint and one basic route. You can add complexity later.

### 2. Use Shared Utilities
Leverage the shared modules:
- `app.shared.security` - Authentication
- `app.shared.logging` - Structured logging
- `app.shared.database` - Database connections
- `app.shared.nats_client` - Service messaging

### 3. Follow Patterns
Look at existing services (auth, chat, kb) for patterns:
- Lifespan management
- Error handling
- Response formats
- Testing approaches

### 4. Test Locally First
```bash
# Build and run your service
docker compose build analytics-service
docker compose up analytics-service

# Test the health endpoint
curl http://localhost:9005/health

# Test through gateway
curl -H "X-API-Key: YOUR_KEY" http://localhost:8666/api/v1/analytics/metrics
```

## Common Issues

### Port Conflicts
Make sure your chosen port isn't already in use. Check:
- `docker compose.yml` for local ports
- `app/shared/config.py` for service URLs

### Gateway 503 Errors
If gateway returns 503 for your service:
1. Check service is running: `fly status -a gaia-<service>-dev`
2. Verify SERVICE_URL is set correctly in gateway
3. Check service health endpoint directly

### Authentication Issues
If getting 401/403 errors:
1. Ensure you're passing auth headers
2. Check service is using `get_current_auth_legacy`
3. Verify API_KEY is set in service secrets

## Example: Complete Analytics Service

Here's what a minimal analytics service might look like:

```python
# app/services/analytics/main.py
from fastapi import FastAPI, Depends
from app.shared.security import get_current_auth_legacy
from datetime import datetime, timedelta
from typing import Dict, List

# ... (boilerplate from template) ...

@app.get("/metrics")
async def get_metrics(
    days: int = 7,
    auth: dict = Depends(get_current_auth_legacy)
) -> Dict:
    """Get platform metrics for the last N days"""
    return {
        "period": f"last_{days}_days",
        "metrics": {
            "total_requests": 15234,
            "unique_users": 342,
            "api_calls_by_service": {
                "chat": 8923,
                "assets": 4234,
                "kb": 2077
            }
        },
        "generated_at": datetime.utcnow().isoformat()
    }

@app.post("/reports/generate")
async def generate_report(
    report_type: str,
    auth: dict = Depends(get_current_auth_legacy)
) -> Dict:
    """Generate an analytics report"""
    report_id = f"report_{datetime.utcnow().timestamp()}"
    
    # In real implementation, queue report generation
    return {
        "report_id": report_id,
        "status": "queued",
        "type": report_type,
        "estimated_time": "2-3 minutes"
    }
```

## Conclusion

While adding a microservice still requires some manual steps, the automated tooling significantly reduces the boilerplate. The future goal is to make this even simpler with automatic gateway route generation from the service registry.