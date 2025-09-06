# API Key Configuration Guide

## Overview
This guide provides specific instructions for configuring API keys across Gaia microservices as part of the unified authentication system (mTLS + JWT + API keys). 

**Current Status**: mTLS + JWT authentication infrastructure complete (Phases 1-3), with API keys providing backward compatibility and Redis caching for 97% performance improvement.

## Key Concepts

### Service-Specific Environment Variables
Each service may use different environment variable prefixes:
- **Gateway**: Uses `API_KEY` directly
- **Web Service**: Uses `WEB_API_KEY` (with `WEB_` prefix)
- **Auth Service**: Uses `API_KEY` directly
- **Other Services**: Check their `config.py` for specific prefixes

### Pydantic Configuration Patterns

#### ✅ Current Unified Authentication Pattern
```python
from pydantic import Field
from app.shared.security import get_current_auth_unified

class WebSettings(BaseSettings):
    api_key: str = Field(default="default-key", env="WEB_API_KEY")

# Usage in endpoints
@app.post("/endpoint")
async def endpoint(auth_result: dict = Depends(get_current_auth_unified)):
    # Handles both API keys and JWT tokens automatically
    user_id = auth_result["user_id"]
```

#### 🔄 Legacy Pattern (Pre-Unified Auth)
```python
# Old approach - now replaced by unified authentication
class WebSettings(BaseSettings):
    api_key: str = "default-key"
    
    class Config:
        env_prefix = "WEB_"  # Replaced by explicit Field(env=...)
```

## Step-by-Step Configuration

### 1. Local Development (.env file)
```bash
# Core API Key - used by most services
API_KEY=your-actual-api-key-here

# Web Service specific
WEB_API_KEY=your-actual-api-key-here
WEB_GATEWAY_URL=http://gateway:8000
WEB_SESSION_SECRET=your-session-secret

# Other service-specific variables...
```

### 2. Fly.io Deployment
```bash
# Set secrets for each service
fly secrets set -a gaia-gateway-dev API_KEY="your-actual-api-key"
fly secrets set -a gaia-auth-dev API_KEY="your-actual-api-key"
fly secrets set -a gaia-web-dev WEB_API_KEY="your-actual-api-key"
```

### 3. Verification
```bash
# Verify all services have matching API key digests
./scripts/verify-api-keys.sh

# Or manually check each service
fly secrets list -a gaia-gateway-dev | grep API_KEY
fly secrets list -a gaia-web-dev | grep WEB_API_KEY
fly secrets list -a gaia-auth-dev | grep API_KEY
```

## Debugging API Key Issues

### 1. Check Service Logs
```bash
# Look for API key in startup logs
fly logs -a gaia-web-dev | grep "API Key:"

# Should see something like:
# 2025-07-18 05:57:29 - web - INFO - API Key: FJUeDkZRy0...
```

### 2. Test Authentication Flow
```bash
# Test registration through web service
./scripts/test.sh --url https://gaia-web-dev.fly.dev auth-register test@example.com password

# Test direct auth service
curl -X POST https://gaia-auth-dev.fly.dev/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'
```

### 3. Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid API key" | API key mismatch between services | Verify all services have same key |
| "Registration failed: Invalid API key" | Web service not sending API key | Check WEB_API_KEY is set |
| "Service unavailable" | Service can't reach other services | Check service URLs and health |

## Service Configuration Examples

### Web Service (config.py)
```python
from pydantic_settings import BaseSettings
from pydantic import Field

class WebSettings(BaseSettings):
    # Explicit env variable mapping
    api_key: str = Field(default="dev-key", env="WEB_API_KEY")
    gateway_url: str = Field(default="http://gateway:8000", env="WEB_GATEWAY_URL")
    
    # Service identification
    service_name: str = "web"
    
    class Config:
        env_file = ".env"
```

### Gateway Client Configuration
```python
class GaiaAPIClient:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=settings.gateway_url,
            timeout=30.0
        )
    
    async def register(self, email: str, password: str):
        # Include API key in headers
        response = await self.client.post(
            "/api/v1/auth/register",
            headers={"X-API-Key": settings.api_key},
            json={"email": email, "password": password}
        )
```

## Automated Verification Script

Create `scripts/verify-api-keys.sh`:
```bash
#!/bin/bash
set -e

echo "Verifying API key configuration across services..."

# Expected services and their API key env vars
declare -A SERVICES=(
    ["gaia-gateway-dev"]="API_KEY"
    ["gaia-auth-dev"]="API_KEY" 
    ["gaia-web-dev"]="WEB_API_KEY"
    ["gaia-asset-dev"]="API_KEY"
    ["gaia-chat-dev"]="API_KEY"
)

# Get the digest from the first service
FIRST_DIGEST=""
ALL_MATCH=true

for SERVICE in "${!SERVICES[@]}"; do
    ENV_VAR="${SERVICES[$SERVICE]}"
    
    # Get the digest for this service
    DIGEST=$(fly secrets list -a "$SERVICE" 2>/dev/null | grep "$ENV_VAR" | awk '{print $2}')
    
    if [ -z "$DIGEST" ]; then
        echo "❌ $SERVICE: $ENV_VAR not found!"
        ALL_MATCH=false
    elif [ -z "$FIRST_DIGEST" ]; then
        FIRST_DIGEST="$DIGEST"
        echo "✅ $SERVICE: $ENV_VAR = $DIGEST"
    elif [ "$DIGEST" != "$FIRST_DIGEST" ]; then
        echo "❌ $SERVICE: $ENV_VAR = $DIGEST (MISMATCH!)"
        ALL_MATCH=false
    else
        echo "✅ $SERVICE: $ENV_VAR = $DIGEST"
    fi
done

if $ALL_MATCH; then
    echo "✅ All services have matching API keys!"
else
    echo "❌ API key mismatch detected!"
    exit 1
fi
```

## Best Practices

1. **Always use explicit Field configuration** for critical environment variables
2. **Log configuration values** (first few chars only) during startup
3. **Test configuration loading** before deploying
4. **Use consistent naming** but be aware of service-specific prefixes
5. **Document any non-standard configuration** in service README
6. **Create verification scripts** for multi-service configurations

## Quick Reference

### Set API Key for All Services
```bash
# Local development
echo "API_KEY=your-key" >> .env
echo "WEB_API_KEY=your-key" >> .env

# Fly.io deployment
API_KEY="your-actual-api-key"
fly secrets set -a gaia-gateway-dev API_KEY="$API_KEY"
fly secrets set -a gaia-auth-dev API_KEY="$API_KEY"
fly secrets set -a gaia-web-dev WEB_API_KEY="$API_KEY"
fly secrets set -a gaia-asset-dev API_KEY="$API_KEY"
fly secrets set -a gaia-chat-dev API_KEY="$API_KEY"
```

### Debug Checklist
- [ ] Check service logs for API key value
- [ ] Verify Fly.io secrets are set
- [ ] Test service health endpoints
- [ ] Check request headers in logs
- [ ] Verify Pydantic Field configuration
- [ ] Test with curl to isolate issues