# Phase 3: Client Migration to Supabase JWTs

## Overview
Phase 3 focuses on enabling Supabase JWT authentication for web and mobile clients while maintaining backward compatibility with API keys.

## Current State
- Web service already uses Supabase for login/register
- Web service stores JWT tokens in session after login
- BUT: Web service still uses API keys for gateway requests
- Gateway only accepts API keys (uses `get_current_auth_legacy`)

## Implementation Steps

### 1. Update Gateway Authentication
Create a new authentication function that accepts both:
- API Keys (X-API-Key header) - for backward compatibility
- Supabase JWTs (Authorization: Bearer header) - for web/mobile clients

### 2. Modify Web Service Gateway Client
Update the gateway client to use JWT tokens when available:
- Check if JWT token exists in session
- If yes: Use Authorization: Bearer header
- If no: Fall back to X-API-Key

### 3. Test Both Authentication Methods
- Ensure API key authentication still works
- Test Supabase JWT authentication
- Verify smooth transition between auth methods

### 4. Update Mobile Clients (Future)
- Unity XR, Mobile AR, Unreal clients
- Add JWT token refresh logic
- Maintain API key fallback during transition

## Key Files to Modify
1. `/app/gateway/main.py` - Add dual authentication support
2. `/app/services/web/utils/gateway_client.py` - Use JWT when available
3. `/app/shared/security.py` - Create unified auth function

## Success Criteria
- [ ] Gateway accepts both API keys and Supabase JWTs
- [ ] Web UI uses JWTs for authenticated requests
- [ ] API key authentication remains functional
- [ ] No breaking changes for existing clients