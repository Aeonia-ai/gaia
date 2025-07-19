# Authentication Guide

## Overview
Gaia Platform supports multiple authentication methods to accommodate different client types and migration paths:

1. **API Keys** - Traditional authentication for existing clients
2. **Supabase JWTs** - Modern authentication for web/mobile apps
3. **Service JWTs** - Internal service-to-service authentication

## Authentication Methods

### 1. API Key Authentication (Legacy)
Traditional method using user-associated API keys stored in the database.

**Usage:**
```bash
curl -H "X-API-Key: your-api-key" https://api.gaia.com/endpoint
```

**Where it works:**
- All endpoints (backward compatibility)
- Unity XR, Mobile AR, Unreal clients
- Local development and testing

### 2. Supabase JWT Authentication (Recommended)
Modern authentication using JWT tokens issued by Supabase after email/password login.

**Usage:**
```bash
curl -H "Authorization: Bearer your-jwt-token" https://api.gaia.com/endpoint
```

**Where it works:**
- All v0.2 streaming endpoints
- Web UI (automatic after login)
- Mobile apps (after implementing Supabase SDK)

**Benefits:**
- Automatic expiry and refresh
- User metadata in token
- No database lookup needed
- Industry standard

### 3. Service-to-Service JWT Authentication
For internal microservice communication using mTLS certificates and short-lived JWTs.

**Usage:**
```python
from app.shared.mtls_client import create_auth_client

async with create_auth_client("gateway") as client:
    response = await client.get("/internal/endpoint")
```

## Migration Path

### Current State (July 2025)
- ✅ API keys fully supported
- ✅ Supabase JWTs supported in gateway
- ✅ Web UI uses JWTs after login
- ✅ Dual authentication enabled

### For Web UI Users
1. Login via `/login` page → Supabase authentication
2. Receive JWT token → stored in session
3. All requests automatically use JWT
4. Seamless experience, no code changes

### For API Clients
1. **Option A**: Continue using API keys (no changes needed)
2. **Option B**: Implement Supabase SDK
   - Add login flow
   - Store JWT tokens
   - Include in Authorization header
   - Implement token refresh

### Example: Migrating from API Key to JWT

**Before (API Key):**
```python
headers = {"X-API-Key": "your-api-key"}
response = requests.post(url, headers=headers, json=data)
```

**After (JWT):**
```python
# After Supabase login
headers = {"Authorization": f"Bearer {jwt_token}"}
response = requests.post(url, headers=headers, json=data)
```

## Gateway Authentication Flow

The gateway uses `get_current_auth_unified()` which:

1. First checks for JWT token (Authorization: Bearer)
2. Validates JWT with Supabase
3. If no JWT or validation fails, checks for API key
4. Validates API key against database
5. Returns unified auth result

This ensures zero breaking changes during migration.

## Configuration

### Environment Variables
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret

# API Key (for backward compatibility)
API_KEY=your-default-api-key
```

### Web Service Configuration
The web service automatically handles JWT tokens:
- Stores in session after login
- Includes in gateway requests
- Falls back to API key when needed

## Security Considerations

### JWT Tokens
- Expire after 1 hour (configurable)
- Should be refreshed before expiry
- Never store in localStorage (use secure cookies)
- Validate on every request

### API Keys
- Still secure for server-to-server
- Should be rotated periodically
- Never expose in client-side code
- Use environment variables

### mTLS Certificates
- For service-to-service only
- Rotate annually
- Store securely in production
- Never commit to repository

## Troubleshooting

### "Not authenticated" Error
1. Check Authorization header format: `Bearer <token>`
2. Verify JWT hasn't expired
3. Try with API key to isolate issue
4. Check Supabase configuration

### JWT Validation Failures
1. Verify SUPABASE_JWT_SECRET is correct
2. Check token expiry time
3. Ensure Supabase project is active
4. Validate token format

### API Key Not Working
1. Check X-API-Key header spelling
2. Verify key exists in database
3. Check key hasn't expired
4. Ensure user is active

## Future Plans

### Phase 4 (Planned)
- Remove API key validation logic
- Require JWT for all endpoints
- Update all client SDKs
- Deprecation notices

### Token Refresh (In Progress)
- Automatic refresh before expiry
- Refresh token rotation
- Grace period for expired tokens