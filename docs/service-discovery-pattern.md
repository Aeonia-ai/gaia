# Service Discovery Pattern

## Overview

The service discovery pattern solves the microservices communication challenge by enabling automatic discovery of service endpoints and their available routes. This eliminates the need for hardcoded routes in the gateway and allows services to evolve independently.

## Problem Statement

Previously, adding new endpoints required:
1. Creating the endpoint in a service
2. Manually adding a hardcoded route in the gateway
3. Deploying both services
4. Often forgetting steps, leading to 404 errors

## Solution Architecture

### Components

1. **Service Registry** (`app/shared/service_discovery.py`)
   - Central registry for service information
   - Maintains list of healthy services and their routes
   - Periodic health checks with automatic updates

2. **Enhanced Health Endpoints**
   - Services expose their routes via `/health?include_routes=true`
   - Automatically extracts routes from FastAPI app
   - Provides metadata about each route

3. **Dynamic Gateway Routing**
   - Gateway discovers services on startup
   - Creates routes dynamically based on discovery
   - Falls back gracefully when services are unavailable

### Implementation

#### 1. Service-Side Implementation

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
- Filters out internal routes (health, docs, etc.)

#### 2. Gateway-Side Implementation

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

#### 3. Dynamic Route Creation

New endpoints can check if routes exist before forwarding:

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

## Benefits

1. **No More Hardcoded Routes**
   - Services register their routes automatically
   - Gateway discovers routes dynamically
   - Changes propagate without code changes

2. **Service Independence**
   - Services can add/remove endpoints freely
   - No coordination needed with gateway team
   - Deploy services independently

3. **Better Error Handling**
   - Clear 404 messages when routes don't exist
   - Health checks show which services are available
   - Graceful degradation when services are down

4. **Improved Developer Experience**
   - Add endpoint once, available everywhere
   - No manual gateway configuration
   - Self-documenting system

## Testing

Use the test script to verify service discovery:

```bash
./scripts/test-service-discovery.sh
```

This tests:
- Enhanced health endpoints with route discovery
- Gateway's view of discovered services
- Dynamic routing for new endpoints
- Automatic 404s for non-existent routes

## Migration Guide

To migrate existing services:

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

## Advanced Features

### Periodic Health Checks

The service registry runs health checks every 30 seconds:
- Updates service status
- Removes unhealthy services
- Discovers new routes automatically

### Route Metadata

Routes include metadata:
- HTTP methods supported
- Description (from FastAPI)
- Tags for grouping
- Authentication requirements

### Multi-Cloud Support

Service discovery works with:
- Local Docker Compose
- Fly.io deployments
- AWS/GCP/Azure
- Any URL-addressable service

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

## Future Enhancements

1. **WebSocket Support**
   - Discover WebSocket endpoints
   - Dynamic WebSocket routing

2. **gRPC Integration**
   - Discover gRPC services
   - Protocol-agnostic discovery

3. **Service Mesh Integration**
   - Work with Istio/Linkerd
   - Leverage existing service mesh

4. **Configuration Management**
   - Store discovery in database
   - UI for service management
   - Manual override capabilities