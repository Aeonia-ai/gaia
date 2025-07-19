# API Contracts Documentation

This document defines the API contracts for Gaia Platform services, clearly specifying which endpoints require authentication and which are public.

## Public Endpoints (No Authentication Required)

These endpoints MUST remain publicly accessible without any authentication headers:

### Gateway Service

| Endpoint | Method | Purpose | Notes |
|----------|--------|---------|-------|
| `/` | GET | Root endpoint | Returns API version info |
| `/health` | GET | Health check | Used for monitoring |
| `/api/v1/auth/register` | POST | User registration | Creates new user account |
| `/api/v1/auth/login` | POST | User login | Returns JWT token |
| `/api/v1/auth/resend-verification` | POST | Resend email verification | For unverified accounts |
| `/api/v1/auth/confirm` | POST | Confirm email | Validates email token |

### Web Service

| Endpoint | Method | Purpose | Notes |
|----------|--------|---------|-------|
| `/` | GET | Landing page | Public homepage |
| `/login` | GET | Login page | Shows login form |
| `/register` | GET | Registration page | Shows signup form |
| `/auth/login` | POST | Process login | Calls gateway login |
| `/auth/register` | POST | Process registration | Calls gateway register |
| `/auth/signup` | POST | Registration alias | Same as /auth/register |
| `/auth/confirm` | GET | Email confirmation | Handles Supabase redirect |
| `/auth/resend-verification` | POST | Resend verification | HTMX endpoint |
| `/health` | GET | Health check | Service monitoring |
| `/static/*` | GET | Static assets | CSS, JS, images |

### Auth Service

| Endpoint | Method | Purpose | Notes |
|----------|--------|---------|-------|
| `/health` | GET | Health check | Service monitoring |
| `/auth/register` | POST | User registration | Direct registration |
| `/auth/login` | POST | User login | Direct authentication |

## Protected Endpoints (Authentication Required)

All other endpoints require either:
- JWT Bearer token in `Authorization` header
- API key in `X-API-Key` header

### Common Protected Patterns

- `/api/v1/chat/*` - All chat endpoints
- `/api/v1/conversations/*` - Conversation management
- `/api/v1/assets/*` - Asset generation
- `/api/v1/models/*` - Model listing
- `/api/v0.2/chat/*` - v0.2 chat endpoints
- `/chat` - Web UI chat interface
- `/settings` - User settings

## Inter-Service Communication

Services communicate using internal URLs with authentication:

### When to Include Authentication

1. **Service-to-Service Calls**: Include API key when one service calls another's protected endpoint
2. **User Request Forwarding**: Forward user's JWT when proxying user requests
3. **Internal Validation**: Use `/internal/validate` endpoints with service API keys

### When NOT to Include Authentication

1. **Public Endpoint Forwarding**: When forwarding to public endpoints (login, register)
2. **Health Checks**: Inter-service health monitoring
3. **Status Endpoints**: Service discovery and status checks

## Contract Testing

To ensure these contracts are maintained:

```python
# Example contract test
async def test_public_endpoints_require_no_auth():
    """Ensure public endpoints work without authentication"""
    public_endpoints = [
        ("/api/v1/auth/register", "POST"),
        ("/api/v1/auth/login", "POST"),
        ("/health", "GET"),
    ]
    
    for endpoint, method in public_endpoints:
        response = await client.request(
            method=method,
            url=endpoint,
            # No auth headers
        )
        # Should not return 401 or 403
        assert response.status_code not in [401, 403]
```

## Breaking Changes Policy

1. **Never Add Auth Requirements** to public endpoints without:
   - Major version bump
   - Migration period with warnings
   - Client notification

2. **Test Before Deploy**:
   - Run contract tests locally
   - Test on staging environment
   - Monitor error rates after deployment

3. **Document Changes**:
   - Update this document
   - Add to CHANGELOG
   - Notify in release notes

## Common Mistakes to Avoid

1. **Adding API Key to Gateway Client for Public Endpoints**
   ```python
   # ❌ WRONG - Don't add auth to public endpoints
   async def register(self, email, password):
       return await self.client.post(
           "/api/v1/auth/register",
           headers={"X-API-Key": self.api_key},  # Don't do this!
           json={"email": email, "password": password}
       )
   
   # ✅ CORRECT - Public endpoints need no auth
   async def register(self, email, password):
       return await self.client.post(
           "/api/v1/auth/register",
           json={"email": email, "password": password}
       )
   ```

2. **Checking Auth in Middleware for Public Routes**
   ```python
   # ❌ WRONG - Don't check auth on public routes
   @app.post("/api/v1/auth/register")
   async def register(auth=Depends(require_auth)):  # Don't do this!
       ...
   
   # ✅ CORRECT - Public endpoints have no auth dependency
   @app.post("/api/v1/auth/register")
   async def register(request: Request):
       ...
   ```

## Monitoring and Alerts

Set up monitoring for:

1. **401/403 Error Rates** on public endpoints (should be 0%)
2. **Registration Success Rate** (detect auth issues quickly)
3. **Login Success Rate** (catch authentication problems)

## References

- [HTMX + FastHTML Debugging Guide](htmx-fasthtml-debugging-guide.md)
- [Web UI Development Status](web-ui-development-status.md)
- [Troubleshooting Guide](troubleshooting-flyio-dns.md)