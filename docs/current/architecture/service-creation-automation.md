# Service Creation Automation Guide

**Created**: January 2025  
**Purpose**: Streamline the process of adding new microservices to Gaia Platform

## Overview

We've automated much of the boilerplate required when adding new microservices. This guide explains the new tools and patterns that reduce service creation from ~7 manual steps to 2-3 automated steps.

## Quick Start

```bash
# Create a new service called "analytics" on port 8005
./scripts/create-new-service.sh analytics 8005

# Follow the printed instructions to complete setup
```

## Architecture Components

### 1. Service Creation Script

**Location**: `scripts/create-new-service.sh`

This script automates the creation of:
- Service directory structure (`app/services/<name>/`)
- FastAPI service boilerplate (`main.py`)
- Dockerfile for the service
- Docker Compose service entry
- Fly.io deployment configs (dev, staging, prod)
- Environment variable updates

**Usage**:
```bash
./scripts/create-new-service.sh <service-name> [port]
# Port defaults to 8000 if not specified
```

**What it creates**:
```
app/services/analytics/
├── __init__.py
└── main.py              # FastAPI app with health endpoint

Dockerfile.analytics     # Production-ready Dockerfile
fly.analytics.dev.toml   # Fly.io deployment configs
fly.analytics.staging.toml
fly.analytics.production.toml
```

### 2. Service Registry Pattern

**Location**: `app/shared/service_registry.py`

A centralized registry that defines all microservices and their configurations:

```python
from app.shared.service_registry import ServiceConfig, SERVICE_REGISTRY

# Example service configuration
"analytics": ServiceConfig(
    name="analytics",
    port=8005,
    description="Analytics and metrics service",
    has_v1_api=True,
    has_v0_2_api=True,
    requires_auth=True,
    endpoints=[
        "/metrics",
        "/reports/generate",
        "/reports/{report_id}"
    ]
)
```

**Benefits**:
- Single source of truth for service configurations
- Auto-generation of gateway routes (future)
- Service discovery patterns
- Standardized endpoint definitions

### 3. Gateway Route Simplification

**Location**: `scripts/simplify-gateway-routes.py`

Demonstrates how gateway routes can be automated using the service registry:

```python
# Instead of manually defining routes for each service...
@app.get("/api/v1/analytics/metrics")
async def get_metrics(...):
    return await forward_request_to_service(...)

# We can auto-generate from registry
for service_name, config in SERVICE_REGISTRY.items():
    create_service_routes(app, service_name, config)
```

## Step-by-Step: Adding a New Service

### Step 1: Run the Creation Script

```bash
./scripts/create-new-service.sh notification 8006
```

Output:
```
Creating new microservice: notification
External port: 8006
Internal port: 9006

✅ Service 'notification' created successfully!

Next steps:
1. Update gateway/main.py...
2. Test locally...
3. Deploy to Fly.io...
```

### Step 2: Add to Service Registry

Edit `app/shared/service_registry.py`:

```python
SERVICE_REGISTRY = {
    # ... existing services ...
    
    "notification": ServiceConfig(
        name="notification",
        port=8006,
        description="Notification and messaging service",
        has_v1_api=True,
        has_v0_2_api=False,
        endpoints=[
            "/notifications",
            "/notifications/send",
            "/notifications/{id}",
            "/subscriptions"
        ]
    ),
}
```

### Step 3: Update Gateway Routes

Add to `app/gateway/main.py`:

```python
# In SERVICE_URLS dictionary
SERVICE_URLS = {
    # ... existing services ...
    "notification": settings.NOTIFICATION_SERVICE_URL,
}

# Add route handlers
@app.post("/api/v1/notifications/send")
async def send_notification(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    body = await request.json()
    body["_auth"] = auth
    
    return await forward_request_to_service(
        service_name="notification",
        path="/notifications/send",
        method="POST",
        json_data=body,
        headers=dict(request.headers)
    )
```

### Step 4: Implement Service Logic

Edit `app/services/notification/main.py`:

```python
from typing import List, Dict
from pydantic import BaseModel

class NotificationRequest(BaseModel):
    user_id: str
    message: str
    type: str = "info"  # info, warning, error
    channels: List[str] = ["in-app"]  # in-app, email, sms

@app.post("/notifications/send")
async def send_notification(
    notification: NotificationRequest,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Send a notification to a user"""
    # TODO: Implement actual notification logic
    return {
        "id": f"notif_{datetime.utcnow().timestamp()}",
        "status": "queued",
        "user_id": notification.user_id,
        "message": notification.message,
        "channels": notification.channels
    }
```

### Step 5: Test Locally

```bash
# Build the service
docker compose build notification-service

# Run it
docker compose up notification-service

# Test health endpoint
curl http://localhost:9006/health

# Test through gateway (in another terminal)
docker compose up gateway

curl -X POST http://localhost:8666/api/v1/notifications/send \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "123",
    "message": "Test notification",
    "channels": ["in-app", "email"]
  }'
```

### Step 6: Deploy to Fly.io

```bash
# Create the app
fly apps create gaia-notification-dev

# Deploy
fly deploy --config fly.notification.dev.toml

# Set secrets
fly secrets set -a gaia-notification-dev \
  DATABASE_URL="$DATABASE_URL" \
  REDIS_URL="$REDIS_URL" \
  API_KEY="$API_KEY" \
  SUPABASE_URL="$SUPABASE_URL" \
  SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY"

# Update gateway with service URL
fly secrets set -a gaia-gateway-dev \
  NOTIFICATION_SERVICE_URL="https://gaia-notification-dev.fly.dev"

# Restart gateway
fly apps restart gaia-gateway-dev
```

## File Structure After Creation

```
gaia/
├── app/
│   ├── services/
│   │   └── notification/
│   │       ├── __init__.py
│   │       └── main.py
│   └── shared/
│       ├── service_registry.py  # Updated with new service
│       └── config.py            # Auto-updated with NOTIFICATION_SERVICE_URL
├── Dockerfile.notification       # Created by script
├── fly.notification.*.toml      # Deployment configs
├── docker-compose.yml          # Updated with notification-service
└── .env.example                # Updated with NOTIFICATION_SERVICE_URL
```

## Advanced Patterns

### Generic Route Forwarding

For services with many endpoints, use pattern matching:

```python
# In gateway/main.py
@app.api_route("/api/v1/notification/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def notification_proxy(
    path: str,
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Forward all notification routes to notification service"""
    return await forward_to_service(
        service_name="notification",
        path=f"/{path}",
        request=request,
        auth_required=True
    )
```

### Service-to-Service Communication

Services can call each other using the shared configuration:

```python
# In notification service
from app.shared.config import settings
import httpx

async def send_email_notification(user_id: str, message: str):
    """Send email via communication service"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.GATEWAY_URL}/api/v1/email/send",
            headers={"X-API-Key": settings.API_KEY},
            json={
                "user_id": user_id,
                "subject": "Notification",
                "body": message
            }
        )
        return response.json()
```

### Health Check Aggregation

The gateway automatically checks all services:

```python
# This is already implemented in gateway/main.py
@app.get("/health")
async def health_check():
    service_health = {}
    for service_name, service_url in SERVICE_URLS.items():
        try:
            response = await client.get(f"{service_url}/health")
            service_health[service_name] = {"status": "healthy"}
        except:
            service_health[service_name] = {"status": "unhealthy"}
    return {"services": service_health}
```

## Best Practices

### 1. Service Independence
Each service should be independently deployable and testable. Avoid tight coupling.

### 2. Consistent Patterns
Follow the patterns established by existing services:
- Health endpoints at `/health`
- Authentication via `get_current_auth_legacy`
- Structured logging with `app.shared.logging`
- Error handling that returns proper HTTP status codes

### 3. Environment Parity
Ensure services work the same locally and remotely:
- Use environment variables for configuration
- Test with the same auth patterns
- Use the shared database schema

### 4. Documentation
Document your service endpoints in:
- The service's main.py docstrings
- The service registry endpoints list
- API documentation (if applicable)

## Future Improvements

### Fully Automated Gateway Routes
We're working on making gateway routes completely automatic:

```python
# Future: No manual gateway updates needed
# Services auto-register their routes
SERVICE_AUTO_DISCOVERY = True

# Gateway discovers and proxies all registered services
for service in discover_services():
    register_service_routes(service)
```

### Service Mesh Integration
Future plans include:
- Automatic mTLS between services
- Service discovery via NATS
- Circuit breakers and retries
- Distributed tracing

### CLI Tool
A future CLI tool could provide:
```bash
gaia service create notification --port 8006
gaia service list
gaia service deploy notification --env dev
gaia service logs notification --env dev
```

## Troubleshooting

### Service Won't Start
1. Check port conflicts in docker-compose.yml
2. Verify DATABASE_URL is accessible
3. Check logs: `docker compose logs notification-service`

### Gateway Can't Find Service
1. Verify SERVICE_URL is set in gateway environment
2. Check service is running: `fly status -a gaia-notification-dev`
3. Test service directly: `curl https://gaia-notification-dev.fly.dev/health`

### Authentication Errors
1. Ensure API_KEY is set in service secrets
2. Verify using `get_current_auth_legacy` in endpoints
3. Check auth service is healthy

## Conclusion

The new automation tools significantly reduce the boilerplate required for adding microservices. While some manual steps remain (updating gateway routes), the process is much simpler and less error-prone than before. Future improvements will eliminate even more manual steps.