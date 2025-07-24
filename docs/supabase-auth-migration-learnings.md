# Supabase Authentication Migration Learnings

**Date**: January 2025  
**Context**: Migration from PostgreSQL-only authentication to Supabase-first authentication

## Overview

This document captures key learnings from migrating the Gaia platform's authentication system from PostgreSQL to Supabase. The migration maintained 100% backward compatibility while enabling modern authentication patterns.

## Key Architectural Decisions

### 1. No Fallback Pattern
**Decision**: When `AUTH_BACKEND=supabase`, use Supabase exclusively - no PostgreSQL fallback.

**Why This Matters**:
- Cleaner separation of concerns
- Predictable behavior in different environments
- Easier debugging - only one auth path to trace
- Prevents split-brain scenarios where keys exist in different systems

**Implementation**:
```python
if auth_backend == "supabase":
    # Use Supabase exclusively when configured
    supabase_result = await validate_api_key_supabase(api_key_header)
    if not supabase_result:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    # No PostgreSQL fallback!
```

### 2. Data Model Compatibility

**Challenge**: Supabase returns `permissions` as a dict, but `AuthenticationResult` expects `scopes` as a list.

**Solution**: Convert at the boundary:
```python
# Convert permissions dict to scopes list for compatibility
permissions = result.get('permissions', {})
scopes = []
if isinstance(permissions, dict):
    if permissions.get('admin'):
        scopes.append('admin')
    if permissions.get('kb_access'):
        scopes.append('kb:read')
        scopes.append('kb:write')

return AuthenticationResult(
    auth_type="user_api_key",
    user_id=result['user_id'],
    api_key=api_key,
    scopes=scopes
)
```

## Deployment Strategies

### 1. Local Docker Builds for Fly.io

**Problem**: Remote builds were timing out or failing intermittently.

**Solution**: Use local Docker builds with explicit Docker host:
```bash
DOCKER_HOST=unix:///Users/jasbahr/.docker/run/docker.sock \
  fly deploy --config fly.service.dev.toml --local-only --strategy immediate
```

**Benefits**:
- Faster deployment (uses local Docker cache)
- More reliable (no network timeouts)
- Better debugging (can inspect images locally)

### 2. Feature Branch Deployment

**Strategy**: Deploy all services from the same feature branch to ensure consistency.

**Process**:
1. Update all services locally on feature branch
2. Deploy each service with local builds
3. Test end-to-end before merging

**Key Learning**: Service version mismatch is a common source of authentication issues.

## Testing Infrastructure

### 1. Environment-Aware Test Scripts

**Issue**: Test scripts only supported `staging` and `prod`, not `dev`.

**Fix**: Add environment cases to test scripts:
```bash
case $ENVIRONMENT in
    "dev")
        BASE_URL="https://gaia-gateway-dev.fly.dev"
        API_KEY="${DEV_API_KEY:-$API_KEY}"
        ;;
    # ... other environments
esac
```

### 2. Comprehensive Test Coverage

**What to Test**:
- Health endpoints (all services)
- Authentication flow (API key validation)
- Service-to-service communication
- Feature-specific endpoints (KB, chat, etc.)

**Test Command**:
```bash
API_KEY=your-key ./scripts/test-comprehensive.sh dev
```

## Migration Process

### 1. Supabase Setup

**Tables Created**:
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT,
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ
);
```

### 2. Data Migration

**Process**:
1. Export existing API keys from PostgreSQL
2. Import into Supabase with matching structure
3. Verify key hashes match
4. Test authentication before switching

### 3. Service Configuration

**Environment Variables**:
```bash
# Enable Supabase authentication
AUTH_BACKEND=supabase
SUPABASE_AUTH_ENABLED=true

# Supabase credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

## Common Pitfalls and Solutions

### 1. Service URL Configuration

**Pitfall**: Services can't communicate after deployment.

**Solution**: Use public URLs for service-to-service communication on Fly.io:
```bash
# ❌ Unreliable
AUTH_SERVICE_URL=http://gaia-auth-dev.internal:8000

# ✅ Reliable
AUTH_SERVICE_URL=https://gaia-auth-dev.fly.dev
```

### 2. Secret Synchronization

**Pitfall**: Forgetting to set Supabase secrets on deployed services.

**Solution**: Always set all required secrets:
```bash
fly secrets set -a gaia-service-dev \
  AUTH_BACKEND=supabase \
  SUPABASE_URL="$SUPABASE_URL" \
  SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY" \
  SUPABASE_SERVICE_ROLE_KEY="$SUPABASE_SERVICE_ROLE_KEY"
```

### 3. Authentication Testing

**Pitfall**: Testing with wrong API keys or in wrong environment.

**Solution**: Always verify:
1. Which environment you're testing
2. That the API key exists in that environment's Supabase
3. That services are using the correct auth backend

## Performance Considerations

### 1. Supabase Latency

**Observation**: Supabase adds ~100-200ms latency compared to local PostgreSQL.

**Mitigation**:
- Redis caching for validated tokens
- Connection pooling
- Regional deployment (use Supabase region close to services)

### 2. Service Health Checks

**Pattern**: Health checks now verify Supabase connectivity:
```json
{
  "supabase": {
    "status": "healthy",
    "service": "supabase",
    "url": "https://project.supabase.co",
    "responsive": true
  }
}
```

## Future Improvements

### 1. Phase 3 - JWT Migration
- Migrate web/mobile clients to Supabase JWTs
- Implement token refresh mechanisms
- Add JWT validation to gateway

### 2. Phase 4 - Cleanup
- Remove legacy PostgreSQL API key validation
- Update all client SDKs
- Perform security audit

## Key Takeaways

1. **Listen to architectural intent** - "No fallback" was the right call
2. **Test infrastructure must match deployment environments**
3. **Local Docker builds are more reliable for Fly.io**
4. **Feature branch deployments prevent version mismatches**
5. **Comprehensive testing catches integration issues early**
6. **Document environment-specific configurations clearly**

## Related Documentation

- [Supabase Auth Implementation Guide](supabase-auth-implementation-guide.md)
- [Authentication Guide](authentication-guide.md)
- [API Key Configuration Guide](api-key-configuration-guide.md)
- [Deployment Best Practices](deployment-best-practices.md)