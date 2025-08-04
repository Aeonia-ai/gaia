# Microservice Quick Reference

**Last Updated**: January 2025

## 🚀 Create New Service (2 minutes)

```bash
# Create service with all boilerplate
./scripts/create-new-service.sh <name> <port>

# Example: Create analytics service on port 8005
./scripts/create-new-service.sh analytics 8005
```

## 📝 Manual Steps Required

### 1. Add to Service Registry
```python
# app/shared/service_registry.py
"analytics": ServiceConfig(
    name="analytics",
    port=8005,
    description="Analytics service",
    endpoints=["/metrics", "/reports"]
)
```

### 2. Update Gateway
```python
# app/gateway/main.py
SERVICE_URLS = {
    # ... existing ...
    "analytics": settings.ANALYTICS_SERVICE_URL,
}

# Add routes as needed
```

### 3. Deploy
```bash
fly apps create gaia-analytics-dev
fly deploy --config fly.analytics.dev.toml
fly secrets set DATABASE_URL="..." -a gaia-analytics-dev
```

## 📁 Files Created Automatically

| File | Purpose |
|------|---------|
| `app/services/<name>/main.py` | Service implementation |
| `Dockerfile.<name>` | Container definition |
| `fly.<name>.*.toml` | Deployment configs |
| `docker compose.yml` | Local development (updated) |
| `.env.example` | Environment vars (updated) |
| `app/shared/config.py` | Service URL config (updated) |

## 🔧 Common Service Patterns

### Basic Endpoint
```python
@app.get("/metrics")
async def get_metrics(auth: dict = Depends(get_current_auth_legacy)):
    return {"metrics": [...]}
```

### Gateway Forward
```python
return await forward_request_to_service(
    service_name="analytics",
    path="/metrics",
    method="GET",
    headers=dict(request.headers)
)
```

### Service-to-Service Call
```python
async with httpx.AsyncClient() as client:
    response = await client.get(
        f"{settings.GATEWAY_URL}/api/v1/other-service/data",
        headers={"X-API-Key": settings.API_KEY}
    )
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port conflict | Check `docker compose.yml` for used ports |
| Gateway 503 | Verify SERVICE_URL in gateway secrets |
| Auth errors | Ensure API_KEY set in service secrets |
| Service won't start | Check logs: `docker compose logs <name>-service` |

## 🛠️ Useful Commands

```bash
# Local testing
docker compose build <name>-service
docker compose up <name>-service

# Check service health
curl http://localhost:<port>/health

# View logs
docker compose logs -f <name>-service

# Deploy status
fly status -a gaia-<name>-dev

# Update gateway service URL
fly secrets set <NAME>_SERVICE_URL="https://..." -a gaia-gateway-dev
```

## 🏗️ Service Checklist

- [ ] Run `create-new-service.sh`
- [ ] Add to service registry
- [ ] Update gateway SERVICE_URLS
- [ ] Add gateway routes
- [ ] Implement service logic
- [ ] Test locally
- [ ] Create Fly.io app
- [ ] Deploy service
- [ ] Set service secrets
- [ ] Update gateway with service URL
- [ ] Test through gateway

## 📚 Full Documentation

- [Service Creation Automation Guide](service-creation-automation.md)
- [Service Registry Pattern](service-registry-pattern.md)
- [Adding New Microservice](adding-new-microservice.md)

## 🔮 Coming Soon

- Automatic gateway route generation
- Service discovery via NATS
- CLI tool for service management
- Service templates for common patterns