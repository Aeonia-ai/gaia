# API Key Authentication Troubleshooting Guide

## Overview
This guide documents the resolution of API key authentication issues between microservices in the Gaia platform, specifically the web service → gateway → auth service communication flow.

## Issue Summary
**Problem**: Registration through the web interface was failing with "Invalid API key" errors despite all services having the same API key configured.

**Root Causes**:
1. Web service wasn't reading the `WEB_API_KEY` environment variable correctly
2. Gateway client was sending extra fields that auth service didn't expect
3. Configuration mismatch between Pydantic settings and environment variables

## Debugging Steps

### 1. Verify API Keys Match Across Services
```bash
# Check API key digests for all services
fly secrets list -a gaia-gateway-dev
fly secrets list -a gaia-web-dev  
fly secrets list -a gaia-auth-dev

# All should show the same digest for API_KEY/WEB_API_KEY
# Example: bbc3b14a24aa6f42
```

### 2. Check Service Health
```bash
# Test each service individually
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev health
./scripts/test.sh --url https://gaia-web-dev.fly.dev health
curl -H "X-API-Key: YOUR_API_KEY" https://gaia-auth-dev.fly.dev/health
```

### 3. Verify Environment Variable Loading
Check service logs to see what API key is being loaded:
```bash
fly logs -a gaia-web-dev
# Look for: "API Key: FJUeDkZRy0..." (first 10 chars)
```

## Solutions Applied

### 1. Fix Pydantic Settings Configuration
**File**: `/app/services/web/config.py`

**Problem**: Default Pydantic env_prefix wasn't working with explicit env names
```python
# ❌ Didn't work - used default value
class WebSettings(BaseSettings):
    api_key: str = "your-api-key-here"
    
    class Config:
        env_prefix = "WEB_"
```

**Solution**: Use Field with explicit env parameter
```python
# ✅ Works correctly
from pydantic import Field

class WebSettings(BaseSettings):
    api_key: str = Field(default="your-api-key-here", env="WEB_API_KEY")
```

### 2. Fix Gateway Client Request Payload
**File**: `/app/services/web/utils/gateway_client.py`

**Problem**: Sending extra fields auth service doesn't accept
```python
# ❌ Auth service UserRegistrationRequest only accepts email/password
json={
    "email": email,
    "password": password,
    "username": username or email.split("@")[0]  # This field causes validation error
}
```

**Solution**: Only send required fields
```python
# ✅ Matches auth service model
json={
    "email": email,
    "password": password
}
```

### 3. Set Environment Variables on Fly.io
```bash
# Set the API key for web service
fly secrets set -a gaia-web-dev WEB_API_KEY="YOUR_API_KEY_HERE"

# Verify it was set
fly secrets list -a gaia-web-dev
# Should show WEB_API_KEY with same digest as other services
```

## Lessons Learned

### 1. Environment Variable Naming
- Be consistent with env var prefixes across services
- When using Pydantic with custom env names, use Field(env="VAR_NAME")
- Test env var loading in startup logs

### 2. API Contract Validation
- Ensure request/response models match between services
- Don't send extra fields that downstream services don't expect
- Use Pydantic models to enforce contracts

### 3. Debugging Multi-Service Issues
- Test each service in isolation first
- Check service logs for actual values being used
- Verify environment variables are set correctly on deployment platform

### 4. Service Communication Flow
```
Web UI → Web Service → Gateway → Auth Service
         ↓              ↓         ↓
    Uses WEB_API_KEY  Uses API_KEY  Uses API_KEY
```

## Prevention Strategies

1. **Automated Testing**: Add integration tests that verify service-to-service communication
2. **Configuration Validation**: Add startup checks that verify critical config values
3. **Consistent Naming**: Use consistent environment variable naming across services
4. **Contract Testing**: Use shared Pydantic models or OpenAPI specs to ensure API compatibility

## Quick Reference

### Check API Key Configuration
```bash
# Development
echo $WEB_API_KEY  # Local env var

# Production (Fly.io)
fly secrets list -a gaia-web-dev | grep API_KEY
```

### Test Registration Flow
```bash
# Via web service (full flow)
./scripts/test.sh --url https://gaia-web-dev.fly.dev auth-register test@example.com password

# Direct to auth service (bypass gateway)
curl -X POST https://gaia-auth-dev.fly.dev/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'
```

## Related Documentation
- [Web Service Configuration](../web-service-config.md)
- [Microservices Architecture](../microservices-architecture.md)
- [Fly.io Deployment Guide](../flyio-deployment-config.md)