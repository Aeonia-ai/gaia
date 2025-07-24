# ADR-002: Microservice Creation Automation

**Date**: January 2025  
**Status**: Implemented  
**Decision**: Automate microservice creation with scripts and service registry

## Context

Adding a new microservice to Gaia Platform required 7+ manual steps:
1. Create service directory structure
2. Write boilerplate FastAPI code
3. Create Dockerfile
4. Update docker-compose.yml
5. Create Fly.io deployment configs
6. Update gateway routes
7. Configure environment variables

This friction discouraged proper service decomposition and led to errors.

## Decision

Implement automation tools:
1. `create-new-service.sh` script for service scaffolding
2. Service registry pattern for centralized configuration
3. Future: Automatic gateway route generation

## Rationale

1. **Reduce Friction**: Make it easy to create properly bounded services
2. **Consistency**: Ensure all services follow the same patterns
3. **Prevent Errors**: Automation reduces manual configuration mistakes
4. **Knowledge Capture**: Scripts encode best practices

## Consequences

### Positive
- Service creation time reduced from hours to minutes
- Consistent service structure across the platform
- Easier onboarding for new developers
- Encourages proper microservice boundaries

### Negative
- Additional tooling to maintain
- Scripts must be updated when patterns change
- Some manual steps still required (will be addressed)

### Neutral
- Service registry becomes critical infrastructure
- Gateway configuration still partially manual

## Implementation

### Service Creation Script
```bash
./scripts/create-new-service.sh analytics 8005
# Creates: directory, main.py, Dockerfile, docker-compose entry, Fly configs
```

### Service Registry
```python
SERVICE_REGISTRY = {
    "analytics": ServiceConfig(
        name="analytics",
        port=8005,
        description="Analytics and metrics service",
        endpoints=["/metrics", "/reports"]
    )
}
```

### Future: Automatic Routes
```python
# Gateway will auto-generate routes from registry
for service, config in SERVICE_REGISTRY.items():
    generate_routes(service, config)
```

## Alternatives Considered

1. **Code Generation Framework**: Too heavy, adds dependencies
2. **Template Repository**: Harder to maintain consistency
3. **Manual Documentation**: Doesn't reduce friction enough

## Lessons Learned

Developer experience improvements have multiplicative effects. Reducing service creation friction from 7 steps to 2-3 steps dramatically increases the likelihood that developers will properly decompose services.

## References

- [Adding New Microservice Guide](../adding-new-microservice.md)
- [Service Registry Implementation](../../app/shared/service_registry.py)