# Authentication Strategy for Multi-Environment Deployments

## The Problem

Currently, we have authentication fragmentation:
- Local development uses API keys in local PostgreSQL
- Remote deployments have separate PostgreSQL databases
- API keys don't sync between environments
- This causes authentication failures when moving between environments

## Recommended Solution: Supabase-First Authentication

### Phase 1: Immediate Fix (Current State)
- Local: Continue using API keys in PostgreSQL
- Remote: Must create API keys per environment (manual process)

### Phase 2: Unified Authentication (Recommended)
Move ALL authentication to Supabase for consistency across environments.

#### Implementation Plan

1. **Supabase User Management**
   ```typescript
   // All users stored in Supabase
   - Email/password authentication
   - OAuth providers (Google, GitHub)
   - Magic links
   ```

2. **API Key Storage in Supabase**
   ```sql
   -- Create api_keys table in Supabase
   CREATE TABLE api_keys (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     user_id UUID REFERENCES auth.users(id),
     key_hash VARCHAR(64) UNIQUE NOT NULL,
     name VARCHAR(255),
     permissions JSONB DEFAULT '{}',
     is_active BOOLEAN DEFAULT true,
     created_at TIMESTAMP DEFAULT NOW()
   );
   ```

3. **Unified Authentication Flow**
   ```python
   async def get_current_auth():
       # 1. Check for JWT token (Supabase)
       if jwt_token:
           return validate_supabase_jwt(token)
       
       # 2. Check for API key
       if api_key:
           # Query Supabase instead of local PostgreSQL
           return validate_api_key_supabase(api_key)
   ```

### Benefits

1. **Single Source of Truth**: All auth data in Supabase
2. **Environment Parity**: Same users/keys work everywhere  
3. **Simplified Deployment**: No per-environment user setup
4. **Better Security**: Centralized auth management
5. **Easier Testing**: One set of test credentials

### Migration Path

#### Step 1: Update Auth Service
```python
# app/services/auth/main.py
async def validate_api_key(key: str):
    # Check Supabase first
    supabase_result = await check_api_key_supabase(key)
    if supabase_result:
        return supabase_result
    
    # Fall back to local PostgreSQL (for backward compatibility)
    return await check_api_key_postgres(key)
```

#### Step 2: Migrate Existing Keys
```python
# scripts/migrate_api_keys_to_supabase.py
async def migrate_api_keys():
    # 1. Read all API keys from local PostgreSQL
    local_keys = await get_all_api_keys_postgres()
    
    # 2. Insert into Supabase
    for key in local_keys:
        await supabase.table('api_keys').insert(key)
```

#### Step 3: Update Configuration
```python
# app/shared/config.py
class Settings:
    # Use Supabase for all auth operations
    AUTH_BACKEND = os.getenv("AUTH_BACKEND", "supabase")  # or "postgres"
    
    # Supabase is already configured
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
```

### Alternative: Service Accounts

For service-to-service authentication, use service accounts:

```python
# Each environment gets a service account
SERVICE_ACCOUNTS = {
    "dev": {
        "gateway": "dev-gateway-key-xxx",
        "auth": "dev-auth-key-xxx"
    },
    "staging": {
        "gateway": "staging-gateway-key-xxx",
        "auth": "staging-auth-key-xxx"
    }
}
```

Store these in environment variables or secrets management.

## Quick Wins (Immediate Implementation)

### 1. Environment-Specific Test Users
```bash
# Create standard test users in each environment
./scripts/create_test_users.sh --env dev
./scripts/create_test_users.sh --env staging
./scripts/create_test_users.sh --env production
```

### 2. Service Account Authentication
```python
# For inter-service calls, use service accounts
if request.headers.get("X-Service-Auth") == SERVICE_KEY:
    return {"auth_type": "service", "service": service_name}
```

### 3. JWT-First Testing
```bash
# Update test scripts to prefer JWT auth
./scripts/test.sh --auth jwt --env dev
```

## Implementation Timeline

1. **Week 1**: Create Supabase API keys table
2. **Week 2**: Update auth service to check Supabase
3. **Week 3**: Migrate existing keys
4. **Week 4**: Remove PostgreSQL auth dependency

## Environment Variables

```bash
# .env.dev
AUTH_BACKEND=supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=xxxxx  # Service key for API key queries

# .env.local (during transition)
AUTH_BACKEND=postgres  # Keep using local PostgreSQL
```

## Testing Strategy

```bash
# Test both auth methods
pytest tests/auth/test_jwt.py
pytest tests/auth/test_api_keys.py
pytest tests/auth/test_unified_auth.py
```

## Security Considerations

1. **API Key Hashing**: Always store hashed keys
2. **Permission Scoping**: Use JSONB permissions field
3. **Rate Limiting**: Apply per-key rate limits
4. **Audit Logging**: Track all auth attempts
5. **Key Rotation**: Support key expiration/rotation

## Rollback Plan

If issues arise, we can quickly rollback:
```python
# Feature flag for auth backend
if FEATURE_FLAGS.get("use_supabase_auth", False):
    auth_result = await supabase_auth(key)
else:
    auth_result = await postgres_auth(key)
```

## Related Documents

- [Remote Auth Setup](remote-auth-setup.md)
- [Authentication Guide](authentication-guide.md)
- [Phase 3 Migration Plan](mtls-jwt-migration-plan.md)