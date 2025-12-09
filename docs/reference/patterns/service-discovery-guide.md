# Service Discovery Guide

**Created**: January 2025  
**Status**: Implemented and operational  
**Scope**: Comprehensive guide covering pattern, implementation, and future roadmap

## Overview

Service discovery enables automatic discovery of microservice endpoints and their available routes in the Gaia platform. This eliminates hardcoded routes in the gateway and allows services to evolve independently.

## Problem Statement

Previously, adding new endpoints required:
1. Creating the endpoint in a service
2. Manually adding a hardcoded route in the gateway
3. Deploying both services
4. Often forgetting steps, leading to 404 errors

## Solution Architecture

### Core Components

#### 1. Service Registry (`app/shared/service_discovery.py`)
- Central registry for service information
- Maintains list of healthy services and their routes
- Periodic health checks with automatic updates (every 30 seconds)

#### 2. Enhanced Health Endpoints
- Services expose routes via `/health?include_routes=true`
- Automatically extracts routes from FastAPI app
- Filters out internal routes (health, docs, etc.)

#### 3. Dynamic Gateway Routing
- Gateway discovers services on startup
- Creates routes dynamically based on discovery
- Falls back gracefully when services are unavailable

## Current Implementation

### Service-Side Setup

Each service uses the enhanced health endpoint:

```python
from app.shared.service_discovery import create_service_health_endpoint

# In service main.py
app = FastAPI(title="My Service", version="1.0")

# Replace standard health endpoint with enhanced version
create_service_health_endpoint(app, "my-service", "1.0")
```

This automatically creates a health endpoint that:
- Returns standard health information
- Optionally includes all available routes when `?include_routes=true`
- Filters out internal routes

### Gateway Integration

The gateway discovers services on startup:

```python
from app.shared.service_discovery import service_registry, discover_services_from_config

@app.on_event("startup")
async def startup_event():
    # Start service registry
    await service_registry.start()
    
    # Discover all configured services
    await discover_services_from_config()
    
    # Log discovered routes
    for service_name, service_info in service_registry.get_healthy_services().items():
        logger.info(f"Discovered {service_name} with {len(service_info.routes)} routes")
```

### Dynamic Route Checking

New endpoints check if routes exist before forwarding:

```python
@app.post("/chat/intelligent")
async def intelligent_chat(request: Request, auth: dict = Depends(get_current_auth)):
    # Check if chat service has this route
    chat_routes = service_registry.get_service_routes("chat")
    
    for route in chat_routes:
        if route.path == "/chat/intelligent" and "POST" in route.methods:
            # Route exists - forward the request
            return await forward_request_to_service(
                service_name="chat",
                path="/chat/intelligent",
                method="POST",
                json_data=body,
                headers=headers
            )
    
    # Route not found
    raise HTTPException(status_code=404, detail="Endpoint not available")
```

### Services Updated

All services now use enhanced health endpoints:
- **Chat Service**: `app/services/chat/main.py`
- **Auth Service**: `app/services/auth/main.py`
- **KB Service**: `app/services/kb/main.py`
- **Asset Service**: `app/services/asset/main.py`

### New Gateway Features

- Service discovery on startup
- Dynamic route checking
- New endpoints demonstrating discovery:
  - `/chat/intelligent`
  - `/chat/fast`
  - `/chat/mcp-agent`
  - `/chat/intelligent/metrics`

## Testing

Run the test script to verify service discovery:

```bash
./scripts/test-service-discovery.sh
```

This tests:
- Enhanced health endpoints with route discovery
- Gateway's view of discovered services
- Dynamic routing for new endpoints
- Automatic 404s for non-existent routes

## Benefits Realized

1. **No More Hardcoded Routes** - Services register automatically
2. **Independent Deployment** - Services can evolve without gateway changes
3. **Better Debugging** - Clear visibility into available endpoints
4. **Automatic Updates** - New endpoints available immediately
5. **Service Independence** - No coordination needed with gateway team
6. **Better Error Handling** - Clear 404 messages when routes don't exist
7. **Graceful Degradation** - System continues when services are down

## Future Roadmap: Service Registry Pattern

### Enhanced ServiceConfig Model

We plan to extend the service registry with richer configuration:

```python
class ServiceConfig(BaseModel):
    name: str                    # Service identifier
    port: int                    # Default port for local development
    description: str             # Human-readable description
    has_v1_api: bool = True     # Supports /api/v1/* routes
    has_v0_2_api: bool = False  # Supports /api/v0.2/* routes
    requires_auth: bool = True   # Requires authentication
    health_endpoint: str = "/health"
    endpoints: List[str] = []    # List of service endpoints
    depends_on: List[str] = []  # Service dependencies
    version: str = "1.0"
    features: Dict[str, bool] = {}  # Feature flags
    rate_limits: Dict[str, str] = {}  # Rate limiting config
```

### Central Registry

Replace scattered configurations with a single source of truth:

```python
SERVICE_REGISTRY: Dict[str, ServiceConfig] = {
    "auth": ServiceConfig(...),
    "asset": ServiceConfig(...),
    "chat": ServiceConfig(...),
    "kb": ServiceConfig(...),
}
```

### Advanced Features Planned

1. **Service Versioning** - Support multiple versions of the same service
2. **Feature Flags** - Enable/disable service features dynamically
3. **Dependency Management** - Track and validate service dependencies
4. **Rate Limiting** - Configure per-service rate limits
5. **Service Metrics** - Track usage from the registry
6. **Auto-route Generation** - Generate all routes from registry
7. **WebSocket Support** - Discover WebSocket endpoints
8. **gRPC Integration** - Protocol-agnostic discovery
9. **Service Mesh Integration** - Work with Istio/Linkerd

## Migration Guide

### To Current Implementation (Enhanced Health)

1. **Update Service Health Endpoint**
   ```python
   # Replace this:
   @app.get("/health")
   async def health_check():
       return {"status": "healthy", ...}
   
   # With this:
   create_service_health_endpoint(app, "service-name", "version")
   ```

2. **Update Gateway Startup**
   - Import service discovery modules
   - Start service registry on startup
   - Run service discovery

3. **Convert Hardcoded Routes** (Optional)
   - Can keep existing hardcoded routes
   - Gradually migrate to dynamic discovery
   - Use discovery for new endpoints

### To Future Registry Pattern

**Phase 1**: Create Registry ✅ DONE
- Define ServiceConfig model
- Create SERVICE_REGISTRY with existing services
- Add helper functions

**Phase 2**: Update Gateway (TODO)
- Import and use SERVICE_REGISTRY
- Generate SERVICE_URLS dynamically
- Add generic route forwarders

**Phase 3**: Auto-route Generation (TODO)
- Implement dynamic route creation
- Remove manual route definitions
- Add route customization hooks

**Phase 4**: Advanced Features (FUTURE)
- Service versioning
- Feature flags
- Dependency management
- Metrics and monitoring

## Troubleshooting

### Service Not Discovered
1. Check service has enhanced health endpoint
2. Verify service URL in configuration
3. Check service is healthy
4. Look for discovery errors in gateway logs

### Routes Not Found
1. Ensure route is registered in FastAPI app
2. Check route isn't filtered (health, docs)
3. Verify include_routes=true works
4. Check service discovery ran successfully

### Performance Issues
1. Adjust health check interval if needed
2. Cache discovery results appropriately
3. Use async operations for discovery

## Best Practices

### 1. Keep Endpoints Consistent
Use RESTful patterns:
- GET `/items` - List
- POST `/items` - Create
- GET `/items/{id}` - Get one
- PUT `/items/{id}` - Update
- DELETE `/items/{id}` - Delete

### 2. Document Endpoints
Include descriptions in the endpoint list when using future registry pattern

### 3. Version Carefully
Separate endpoint lists for different API versions

### 4. Handle Dependencies
Always check if dependent services are available before using them

## Related Documentation

- [Service Initialization Pattern](service-initialization-pattern.md) - Correct initialization order
- [Service Creation Automation](service-creation-automation.md) - Automated service creation
- [Deferred Initialization Pattern](deferred-initialization-pattern.md) - Fast startup patterns

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document describes a service discovery architecture that is **partially implemented but not fully integrated**, leading to significant discrepancies between the documentation and the current operational behavior.

-   **✅ Core Components & Service-Side Setup:**
    *   **Claim:** A `ServiceRegistry` and `create_service_health_endpoint` function exist to allow services to expose their routes.
    *   **Code Reference:** `app/shared/service_discovery.py`.
    *   **Verification:** This is **VERIFIED**. The core components for service-side discovery are implemented as described.

-   **✅ Services Updated:**
    *   **Claim:** The `chat`, `auth`, `kb`, and `asset` services have been updated to use the enhanced health endpoints.
    *   **Code References:** `app/services/chat/main.py`, `app/services/auth/main.py`, `app/services/kb/main.py`, `app/services/asset/main.py`.
    *   **Verification:** This is **VERIFIED**. Each service's `main.py` file correctly calls `create_service_health_endpoint`.

-   **❌ Gateway Integration:**
    *   **Claim:** The gateway discovers services on startup using `discover_services_from_config` and dynamically checks for routes using `service_registry.get_service_routes`.
    *   **Code Reference:** `app/gateway/main.py`.
    *   **Verification:** This is **INCORRECT**. The gateway's `startup_event` does **not** call `discover_services_from_config` or use the `service_registry` for routing. It continues to use a hardcoded `SERVICE_URLS` dictionary populated from environment settings. The service discovery mechanism is not currently used by the gateway.

-   **❌ New Gateway Features:**
    *   **Claim:** The document lists several new endpoints in the gateway that demonstrate service discovery, such as `/chat/intelligent` and `/chat/fast`.
    *   **Verification:** This is **INCORRECT**. As verified in other documents, these endpoints do not exist in the gateway. The functionality has been consolidated into the `/chat/unified` endpoint, which is routed via the hardcoded `SERVICE_URLS`.

**Overall Conclusion:** The service-side part of the service discovery system is implemented, but the client-side (the gateway) does not use it. This means the primary benefit of the system—eliminating hardcoded routes in the gateway—has not been realized. The document is **outdated and misleading** regarding the gateway's actual behavior.