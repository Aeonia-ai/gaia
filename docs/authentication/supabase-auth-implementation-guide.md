# Supabase Authentication Implementation Guide

This guide documents the complete implementation of Supabase-first authentication for the Gaia platform, replacing the local PostgreSQL API key validation with a centralized Supabase solution.

## Overview

We've successfully migrated from local PostgreSQL API key validation to Supabase-first authentication, providing:
- **One API key works everywhere** - No more per-environment API key setup
- **Centralized user management** - All users and API keys in one place
- **Better security** - Supabase Row Level Security (RLS) policies
- **Easy key rotation** - Centralized key management
- **Environment parity** - Same authentication code in all environments

## Current Status

### What Works
- ✅ Local KB access with PostgreSQL auth
- ✅ Gateway properly routes KB requests  
- ✅ KB service is healthy on remote deployment
- ✅ All infrastructure is ready for Supabase auth
- ✅ Supabase API keys table schema created
- ✅ Supabase auth client module built
- ✅ Security module checks Supabase first
- ✅ Migration tools and scripts ready

### What's Completed
- ✅ Created Supabase API keys table schema (`migrations/supabase_api_keys.sql`)
- ✅ Built Supabase auth client module (`app/shared/supabase_auth.py`)
- ✅ Updated security module to check Supabase first
- ✅ Added configuration options for AUTH_BACKEND selection
- ✅ Fixed KB_SERVICE_URL in all gateway configs
- ✅ Created migration script to copy API keys from PostgreSQL to Supabase

## Implementation Details

### 1. Supabase Infrastructure Setup

#### API Keys Table
The `api_keys` table was already created in Supabase with this schema:
```sql
CREATE TABLE public.api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,  -- First 4 chars of API key
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id UUID REFERENCES public.users(id),
    permissions JSONB DEFAULT '[]'::jsonb,
    rate_limit_per_minute INTEGER DEFAULT 1000,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Validation Function
Created a simple validation function that can be called with the anon key:
```sql
CREATE OR REPLACE FUNCTION public.validate_api_key_simple(key_hash_input VARCHAR)
RETURNS TABLE (
    is_valid BOOLEAN,
    user_id UUID,
    permissions JSONB
) 
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Check the api_keys table
    RETURN QUERY
    SELECT 
        (ak.is_active AND (ak.expires_at IS NULL OR ak.expires_at > NOW())) as is_valid,
        ak.user_id,
        ak.permissions
    FROM public.api_keys ak
    WHERE ak.key_hash = key_hash_input
    LIMIT 1;
    
    -- If not found, return empty result
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            false as is_valid,
            NULL::uuid as user_id,
            NULL::jsonb as permissions;
    END IF;
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION public.validate_api_key_simple TO anon, authenticated;
```

### 2. Code Implementation

#### Supabase Auth Client (`app/shared/supabase_auth.py`)
Created a dedicated module for Supabase authentication:
```python
class SupabaseAuthClient:
    """Client for Supabase-based authentication operations."""
    
    async def validate_api_key(self, api_key: str) -> Optional[AuthenticationResult]:
        """Validate an API key against Supabase."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        response = self.client.rpc(
            'validate_api_key_simple',
            {'key_hash_input': key_hash}
        ).execute()
        
        if response.data and len(response.data) > 0:
            result = response.data[0]
            if result.get('is_valid', False):
                return AuthenticationResult(
                    auth_type="user_api_key",
                    user_id=result['user_id'],
                    api_key=api_key,
                    permissions=result.get('permissions', {})
                )
```

#### Security Module Updates (`app/shared/security.py`)
Modified to check Supabase first when enabled:
```python
# Check if we should use Supabase for API key validation
auth_backend = os.getenv("AUTH_BACKEND", "postgres")

if auth_backend == "supabase" or os.getenv("SUPABASE_AUTH_ENABLED", "false").lower() == "true":
    # Try Supabase first
    from app.shared.supabase_auth import validate_api_key_supabase
    supabase_result = await validate_api_key_supabase(api_key_header)
    
    if supabase_result:
        return supabase_result
    else:
        # Fall back to PostgreSQL
        pass
```

### 3. Configuration

#### Environment Variables
```bash
# Enable Supabase authentication
AUTH_BACKEND=supabase
SUPABASE_AUTH_ENABLED=true

# Supabase connection details
SUPABASE_URL=https://lbaohvnusingoztdzlmj.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=o+Q9utTVdfHlP8IMApRnlT7uOn/QUQ5Z584Hd+iVm7GqK1YK+IdLY3PtgKPp1PuqL7JLI13w8FmYn7d9ccVAqQ==
# SUPABASE_SERVICE_KEY=  # Still needed for full functionality
```

#### Remote Deployment
Set secrets on all services:
```bash
# Auth service
fly secrets set -a gaia-auth-dev \
  AUTH_BACKEND=supabase \
  SUPABASE_AUTH_ENABLED=true \
  SUPABASE_URL=https://lbaohvnusingoztdzlmj.supabase.co \
  SUPABASE_JWT_SECRET="..."

# Gateway service (needs same config)
fly secrets set -a gaia-gateway-dev \
  AUTH_BACKEND=supabase \
  SUPABASE_AUTH_ENABLED=true \
  SUPABASE_URL=https://lbaohvnusingoztdzlmj.supabase.co \
  SUPABASE_JWT_SECRET="..."

# KB service (if it validates auth)
fly secrets set -a gaia-kb-dev \
  AUTH_BACKEND=supabase \
  SUPABASE_AUTH_ENABLED=true \
  SUPABASE_URL=https://lbaohvnusingoztdzlmj.supabase.co
```

### 4. Testing

#### Local Testing (Working ✅)
```bash
# Enable Supabase in .env
AUTH_BACKEND=supabase
SUPABASE_AUTH_ENABLED=true

# Test KB access
./scripts/test.sh --local kb-search "test"
# Result: ✅ Status: 200
```

#### Remote Testing (Needs Service Key ⚠️)
```bash
# Test with Jason's API key
API_KEY=hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY \
  ./scripts/test.sh --url https://gaia-gateway-dev.fly.dev kb-search "test"
# Result: ❌ Status: 403 (needs SUPABASE_SERVICE_KEY)
```

#### Direct Supabase Testing
Created `scripts/test-supabase-auth.py` to test Supabase directly:
```python
# Test validates successfully:
# Valid: True
# User ID: a7f4370e-0af5-40eb-bb18-fcc10538b041
# Permissions: {'admin': True, 'kb_access': True}
```

## Key Learnings

### 1. Supabase Project Mismatch
- **Issue**: Gateway was using wrong Supabase project (`jbxghtpqbiyttjzdjpti` instead of `lbaohvnusingoztdzlmj`)
- **Fix**: Ensure all services use the same SUPABASE_URL
- **Lesson**: Always verify Supabase project ID in health endpoints

### 2. Service Role Key Requirement
- **Issue**: Anon key has limited permissions for RPC functions
- **Fix**: Need SUPABASE_SERVICE_KEY for backend services
- **Lesson**: Backend services should use service role key, not anon key

### 3. User ID Consistency
- **Issue**: API key was linked to wrong user ID
- **Fix**: Found correct user ID in Supabase: `a7f4370e-0af5-40eb-bb18-fcc10538b041`
- **Lesson**: Always verify user IDs match between systems

### 4. Table Schema Requirements
- **Issue**: `api_keys` table requires `key_prefix` field (not nullable)
- **Fix**: Include key prefix (first 4 chars) when inserting
- **Lesson**: Check table constraints before inserting data

### 5. MCP Tools for Supabase
- **Discovery**: Supabase MCP tools available for SQL execution
- **Usage**: `mcp__supabase__execute_sql` for direct database operations
- **Benefit**: No need to use Supabase dashboard for simple operations

## Migration Checklist

- [x] Create Supabase validation function
- [x] Update auth module to check Supabase
- [x] Test local authentication
- [x] Deploy to remote services
- [x] Update all service configurations
- [ ] Get and configure SUPABASE_SERVICE_KEY
- [ ] Migrate all existing API keys
- [ ] Update client SDKs to use Supabase JWTs
- [ ] Remove legacy PostgreSQL auth code

## Troubleshooting

### "Could not validate credentials" on remote
1. Check SUPABASE_URL matches across all services
2. Verify AUTH_BACKEND=supabase is set
3. Ensure SUPABASE_SERVICE_KEY is configured (not just anon key)
4. Check user exists in Supabase users table

### "null value in column key_prefix" error
- Include key_prefix when inserting API keys
- Use first 4 characters of the API key

### Service health check failures
- Services may take 30-60 seconds to pick up new secrets
- Use `fly apps restart <app-name>` to force reload
- Check logs with `fly logs -a <app-name>`

## Next Steps

1. **Get Service Role Key**: 
   - Go to Supabase dashboard > Settings > API
   - Copy service role key (has full access)
   - Set as SUPABASE_SERVICE_KEY in all services

2. **Complete Migration**:
   - Run `scripts/migrate-api-keys-to-supabase.py`
   - Verify all users have API keys in Supabase
   - Test all client applications

3. **Enable JWT Authentication**:
   - Update web/mobile clients to use Supabase auth
   - Implement token refresh mechanisms
   - Remove legacy API key validation

## References

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [Supabase API Keys Best Practices](https://supabase.com/docs/guides/api#api-keys)