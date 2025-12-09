# ADR-003: API Key to JWT Exchange Pattern

## Status
Proposed

## Context

We have discovered systematic authentication issues in our microservices architecture where API keys and JWTs are handled inconsistently, leading to:

1. **User ID Mismatches**: Different services extract user IDs from different fields (`key`, `sub`, `user_id`), causing conversation persistence failures
2. **Authentication Interference**: API key authentication interferes with JWT authentication due to shared state/caching
3. **Code Complexity**: Every service has complex fallback logic checking multiple auth fields
4. **404 Errors**: Conversations created with one auth method cannot be retrieved with another

### Current Problem Example
```python
# Current pattern repeated across services:
user_id = auth_principal.get("sub") or auth_principal.get("user_id") or auth_principal.get("key")

# But inconsistently implemented - some places missing fields:
user_id = auth_principal.get("sub") or auth_principal.get("key", "unknown")  # Missing user_id!
```

This has resulted in 20+ failing integration tests related to conversation persistence.

## Decision

Implement an **API Key to JWT Exchange Pattern** where:

1. API keys are only validated at the edge (gateway/auth service)
2. API keys are immediately exchanged for short-lived JWTs
3. All internal services only handle JWTs with standardized claims
4. User ID is consistently extracted from the `sub` claim

### Implementation Plan

1. **Create `/auth/api-key-login` endpoint** that:
   - Validates the API key
   - Generates a JWT with proper claims (`sub`, `exp`, `iat`, `aud`)
   - Returns the JWT for the client to use

2. **Update Gateway** to automatically exchange API keys for JWTs:
   - Detect `X-API-Key` header
   - Call auth service to exchange for JWT
   - Forward requests with `Authorization: Bearer <jwt>` internally

3. **Simplify all services** to only use:
   ```python
   user_id = jwt_claims["sub"]  # Consistent everywhere
   ```

## Consequences

### Positive

1. **Eliminates user ID mismatches** - Single source of truth (`sub` claim)
2. **Fixes conversation persistence** - Consistent user IDs across all operations
3. **Simplifies codebase** - Remove complex multi-field checking logic
4. **Follows industry best practices** - Recommended pattern for microservices
5. **Better security** - API keys never leave the edge, short-lived tokens internally
6. **Improved performance** - No need to validate API keys in every service

### Negative

1. **Additional hop** - API key requests need JWT exchange first
2. **Migration effort** - Need to update clients to handle JWT responses
3. **Token management** - Clients need to handle JWT expiration/refresh

### Neutral

1. **Backward compatibility** - Can be implemented gradually
2. **Existing JWT infrastructure** - We already have JWT generation/validation

## Implementation Details

### Phase 1: Add Exchange Endpoint
```python
@app.post("/auth/api-key-login")
async def exchange_api_key_for_jwt(api_key: str = Header(alias="X-API-Key")):
    # Validate API key
    user = await validate_api_key(api_key)
    if not user:
        raise HTTPException(401, "Invalid API key")
    
    # Generate JWT
    claims = {
        "sub": user.id,
        "email": user.email,
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "iat": datetime.utcnow(),
        "aud": "gaia-platform"
    }
    
    jwt_token = create_jwt(claims)
    
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "expires_in": 900  # 15 minutes
    }
```

### Phase 2: Gateway Auto-Exchange
```python
# In gateway middleware
if "X-API-Key" in request.headers and "Authorization" not in request.headers:
    # Exchange API key for JWT
    jwt_response = await auth_service.exchange_api_key(request.headers["X-API-Key"])
    # Replace auth header
    request.headers["Authorization"] = f"Bearer {jwt_response['access_token']}"
```

### Phase 3: Service Simplification
Remove all instances of multi-field auth checking and use standard JWT validation.

## References

- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Microservices Authentication Patterns](https://microservices.io/patterns/security/access-token.html)
- Industry recommendation: "Terminate API keys at the API gateway... exchange them for short-lived JWTs"

## Related

- ADR-001: Microservices Architecture
- ADR-002: Authentication Strategy
- Issue #123: Conversation persistence failures
- PR #456: Initial auth field mismatch fix