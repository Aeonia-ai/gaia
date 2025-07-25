# Service Registry Pattern

**Created**: January 2025  
**Purpose**: Centralize microservice configuration and enable auto-discovery

## Overview

The Service Registry pattern provides a single source of truth for all microservices in the Gaia platform. It enables automatic route generation, service discovery, and consistent configuration across the platform.

## Core Concepts

### ServiceConfig Model

Located in `app/shared/service_registry.py`:

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
```

### Central Registry

```python
SERVICE_REGISTRY: Dict[str, ServiceConfig] = {
    "auth": ServiceConfig(...),
    "asset": ServiceConfig(...),
    "chat": ServiceConfig(...),
    "kb": ServiceConfig(...),
}
```

## Usage Patterns

### 1. Service URL Generation

Instead of hardcoding service URLs:

```python
# OLD: Hardcoded in gateway/main.py
SERVICE_URLS = {
    "auth": "http://auth-service:8000",
    "chat": "http://chat-service:8000",
}

# NEW: Generated from registry
SERVICE_URLS = {
    service_name: getattr(settings, f"{service_name.upper()}_SERVICE_URL")
    for service_name in SERVICE_REGISTRY.keys()
}
```

### 2. Automatic Route Registration

Generate gateway routes from the registry:

```python
# Generate routes for all services
for service_name, config in SERVICE_REGISTRY.items():
    if config.has_v1_api:
        create_v1_routes(app, service_name, config)
    if config.has_v0_2_api:
        create_v0_2_routes(app, service_name, config)
```

### 3. Service Discovery

Find services by capability:

```python
def get_services_with_v0_2_api() -> List[str]:
    """Get all services that support v0.2 API"""
    return [
        name for name, config in SERVICE_REGISTRY.items()
        if config.has_v0_2_api
    ]

def get_authenticated_services() -> List[str]:
    """Get all services requiring authentication"""
    return [
        name for name, config in SERVICE_REGISTRY.items()
        if config.requires_auth
    ]
```

### 4. Health Check Aggregation

Dynamically check health of all registered services:

```python
async def check_all_services_health():
    """Check health of all registered services"""
    health_status = {}
    
    for service_name, config in SERVICE_REGISTRY.items():
        service_url = SERVICE_URLS.get(service_name)
        if service_url:
            try:
                response = await http_client.get(
                    f"{service_url}{config.health_endpoint}"
                )
                health_status[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                health_status[service_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
    
    return health_status
```

## Implementation Examples

### Adding a New Service

1. **Define in Registry**:
```python
# In app/shared/service_registry.py
SERVICE_REGISTRY["analytics"] = ServiceConfig(
    name="analytics",
    port=8005,
    description="Analytics and reporting service",
    has_v1_api=True,
    has_v0_2_api=True,
    endpoints=[
        "/metrics",
        "/metrics/export",
        "/reports/generate",
        "/reports/{report_id}",
        "/dashboards",
        "/dashboards/{dashboard_id}"
    ]
)
```

2. **Auto-generate Documentation**:
```python
def generate_service_docs():
    """Generate markdown documentation for all services"""
    docs = ["# Gaia Platform Services\n"]
    
    for service_name, config in SERVICE_REGISTRY.items():
        docs.append(f"## {service_name.title()} Service")
        docs.append(f"\n{config.description}\n")
        docs.append(f"- Port: {config.port}")
        docs.append(f"- API Versions: ", end="")
        versions = []
        if config.has_v1_api:
            versions.append("v1")
        if config.has_v0_2_api:
            versions.append("v0.2")
        docs.append(", ".join(versions))
        docs.append(f"- Requires Auth: {config.requires_auth}")
        docs.append("\n### Endpoints:")
        for endpoint in config.endpoints:
            docs.append(f"- {endpoint}")
        docs.append("")
    
    return "\n".join(docs)
```

### Dynamic Route Generation

Create a generic route forwarder:

```python
def create_generic_service_routes(app: FastAPI, service_name: str, config: ServiceConfig):
    """Create all routes for a service based on its config"""
    
    # Health endpoint (no auth)
    @app.get(f"/api/v1/{service_name}/health", tags=[service_name.title()])
    async def service_health(request: Request):
        return await forward_request_to_service(
            service_name=service_name,
            path="/health",
            method="GET",
            headers=dict(request.headers)
        )
    
    # Create routes for each endpoint
    for endpoint in config.endpoints:
        # Parse endpoint to determine method and create route
        if "{" in endpoint:  # Has path parameters
            # Handle path parameters
            route_path = f"/api/v1/{service_name}{endpoint}"
            
            @app.api_route(route_path, methods=["GET", "POST", "PUT", "DELETE"])
            async def service_endpoint(request: Request, **kwargs):
                return await forward_to_service_with_auth(
                    service_name=service_name,
                    path=endpoint.format(**kwargs),
                    request=request,
                    requires_auth=config.requires_auth
                )
        else:
            # Simple endpoint
            create_simple_endpoint(app, service_name, endpoint, config)
```

### Service Dependency Management

Track and validate service dependencies:

```python
# Extended ServiceConfig with dependencies
class ServiceConfig(BaseModel):
    # ... existing fields ...
    depends_on: List[str] = []  # Services this service depends on
    
# Validate dependencies on startup
def validate_service_dependencies():
    """Ensure all service dependencies are satisfied"""
    for service_name, config in SERVICE_REGISTRY.items():
        for dependency in config.depends_on:
            if dependency not in SERVICE_REGISTRY:
                raise ValueError(
                    f"Service '{service_name}' depends on '{dependency}' "
                    f"which is not registered"
                )
            
            # Check if dependency is healthy
            dep_url = SERVICE_URLS.get(dependency)
            if not dep_url:
                logger.warning(
                    f"Service '{service_name}' dependency '{dependency}' "
                    f"has no URL configured"
                )
```

## Advanced Features

### 1. Service Versioning

Support multiple versions of the same service:

```python
class ServiceConfig(BaseModel):
    # ... existing fields ...
    version: str = "1.0"
    deprecated: bool = False
    sunset_date: Optional[datetime] = None

# Registry with versions
SERVICE_REGISTRY = {
    "chat": ServiceConfig(name="chat", version="1.0", ...),
    "chat-v2": ServiceConfig(name="chat", version="2.0", ...),
}
```

### 2. Feature Flags

Enable/disable service features dynamically:

```python
class ServiceConfig(BaseModel):
    # ... existing fields ...
    features: Dict[str, bool] = {}
    
# Example usage
"analytics": ServiceConfig(
    name="analytics",
    features={
        "real_time_metrics": True,
        "export_csv": True,
        "ml_predictions": False  # Coming soon
    }
)
```

### 3. Rate Limiting Configuration

Define rate limits per service:

```python
class ServiceConfig(BaseModel):
    # ... existing fields ...
    rate_limits: Dict[str, str] = {
        "default": "60/minute",
        "authenticated": "600/minute",
        "premium": "6000/minute"
    }
```

### 4. Service Metrics

Track service usage from the registry:

```python
class ServiceMetrics:
    def __init__(self):
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.response_times = defaultdict(list)
    
    async def track_request(self, service_name: str, endpoint: str, 
                          response_time: float, status_code: int):
        key = f"{service_name}:{endpoint}"
        self.request_counts[key] += 1
        self.response_times[key].append(response_time)
        
        if status_code >= 400:
            self.error_counts[key] += 1

# Global metrics tracker
service_metrics = ServiceMetrics()
```

## Integration with Gateway

### Current Implementation

The gateway currently uses a static SERVICE_URLS dictionary:

```python
# In gateway/main.py
SERVICE_URLS = {
    "auth": settings.AUTH_SERVICE_URL,
    "asset": settings.ASSET_SERVICE_URL,
    "chat": settings.CHAT_SERVICE_URL,
    "kb": settings.KB_SERVICE_URL,
}
```

### Future Dynamic Implementation

Replace with dynamic generation:

```python
# In gateway/main.py
from app.shared.service_registry import SERVICE_REGISTRY, get_service_url

# Dynamic service URL loading
SERVICE_URLS = {}
for service_name in SERVICE_REGISTRY.keys():
    url_attr = f"{service_name.upper()}_SERVICE_URL"
    if hasattr(settings, url_attr):
        SERVICE_URLS[service_name] = getattr(settings, url_attr)
    else:
        logger.warning(f"No URL configured for service: {service_name}")

# Or even simpler with a helper
SERVICE_URLS = build_service_urls_from_registry()
```

## Benefits

### 1. Single Source of Truth
All service configuration in one place, reducing inconsistencies.

### 2. Reduced Boilerplate
Less manual route definition in the gateway.

### 3. Better Documentation
Auto-generate service documentation from the registry.

### 4. Easier Testing
Mock services based on their registry configuration.

### 5. Service Discovery
Find services by capability, version, or feature.

### 6. Consistent Patterns
Enforce consistent endpoint naming and structure.

## Migration Path

### Phase 1: Create Registry (DONE)
- ✅ Define ServiceConfig model
- ✅ Create SERVICE_REGISTRY with existing services
- ✅ Add helper functions

### Phase 2: Update Gateway (TODO)
- Import and use SERVICE_REGISTRY
- Generate SERVICE_URLS dynamically
- Add generic route forwarders

### Phase 3: Auto-route Generation (TODO)
- Implement dynamic route creation
- Remove manual route definitions
- Add route customization hooks

### Phase 4: Advanced Features (FUTURE)
- Service versioning
- Feature flags
- Dependency management
- Metrics and monitoring

## Best Practices

### 1. Keep Endpoints Consistent
Use RESTful patterns:
- GET `/items` - List
- POST `/items` - Create
- GET `/items/{id}` - Get one
- PUT `/items/{id}` - Update
- DELETE `/items/{id}` - Delete

### 2. Document Endpoints
Include descriptions in the endpoint list:
```python
endpoints=[
    "/metrics",  # GET: Retrieve current metrics
    "/metrics/export",  # POST: Export metrics for date range
    "/reports/generate",  # POST: Generate new report
    "/reports/{report_id}",  # GET: Retrieve report
]
```

### 3. Version Carefully
When adding v0.2 support:
```python
has_v0_2_api=True,
endpoints_v0_2=[  # Separate endpoint list for v0.2
    "/streaming/metrics",
    "/batch/process"
]
```

### 4. Handle Dependencies
Always check if dependent services are available:
```python
if "analytics" in SERVICE_URLS:
    # Enable analytics features
else:
    logger.warning("Analytics service not available")
```

## Conclusion

The Service Registry pattern provides a foundation for more automated and maintainable microservice management. While not fully implemented yet, it shows the path toward reducing manual configuration and enabling dynamic service discovery and routing.