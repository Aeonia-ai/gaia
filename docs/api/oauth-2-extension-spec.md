# OAuth 2.0 Extension Specification

**Created**: July 2025  
**Purpose**: Extend GAIA's authentication system with full OAuth 2.0 flows for third-party integrations and enterprise use cases  
**Version**: 1.0  
**Status**: Planning  

## Overview

GAIA currently implements a robust authentication system using the **Resource Owner Password Credentials Grant** (OAuth 2.0 Section 4.3) via Supabase. This specification defines extensions to support the complete OAuth 2.0 framework, enabling third-party applications, enterprise SSO integration, and a developer ecosystem.

The extension maintains **100% backward compatibility** with existing API key and JWT authentication while adding:
- Authorization Code Flow for secure third-party app integration
- Client Credentials Flow for server-to-server API access  
- Scoped permissions for granular access control
- Client registration and management for developer ecosystem
- Enterprise SSO integration patterns

This positions GAIA as a platform-ready AI service that enterprises and developers can integrate with confidence.

## Core Design Principle

**"Secure by Default, Extensible by Design"**

GAIA's OAuth 2.0 extension follows the principle of **progressive enhancement**:
1. **Existing users see no changes** - Current API keys and password login continue working
2. **New capabilities unlock gradually** - Developers can adopt OAuth flows as needed
3. **Security increases incrementally** - More secure flows become available without breaking existing integrations
4. **Enterprise readiness scales naturally** - SSO and compliance features layer on top

The extension leverages GAIA's existing **dual authentication architecture** (API keys + JWT) as the foundation for OAuth 2.0 compliance.

## Implementation

### 1. Client Registration System

#### Client Application Model
```python
from sqlalchemy import Column, String, DateTime, Boolean, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import enum

class ClientType(enum.Enum):
    CONFIDENTIAL = "confidential"  # Server-side apps with client_secret
    PUBLIC = "public"              # Mobile/SPA apps without client_secret
    SERVICE = "service"            # Server-to-server communication

class OAuthClient(Base):
    __tablename__ = "oauth_clients"
    
    client_id = Column(String(64), primary_key=True)
    client_secret_hash = Column(String(64), nullable=True)  # SHA256 hash
    client_name = Column(String(255), nullable=False)
    client_type = Column(Enum(ClientType), nullable=False)
    
    # OAuth 2.0 Configuration
    redirect_uris = Column(ARRAY(String), nullable=False)
    allowed_scopes = Column(ARRAY(String), nullable=False) 
    grant_types = Column(ARRAY(String), nullable=False)
    
    # Enterprise Features
    organization_id = Column(UUID, nullable=True)
    rate_limit_tier = Column(String(50), default="standard")
    webhook_url = Column(String(500), nullable=True)
    
    # Audit Trail
    created_by = Column(UUID, nullable=False)
    created_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
```

#### Client Registration Endpoint
```python
@app.post("/api/v1/oauth/clients", tags=["OAuth 2.0"])
async def register_client(
    request: ClientRegistrationRequest,
    current_user = Depends(get_current_user)
):
    client_id = generate_client_id()
    client_secret = None
    
    if request.client_type == ClientType.CONFIDENTIAL:
        client_secret = generate_client_secret()
        secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()
    
    client = OAuthClient(
        client_id=client_id,
        client_secret_hash=secret_hash,
        client_name=request.client_name,
        client_type=request.client_type,
        redirect_uris=request.redirect_uris,
        allowed_scopes=request.scopes or ["chat:read"],
        grant_types=request.grant_types or ["authorization_code"],
        created_by=current_user.id
    )
    
    db.add(client)
    await db.commit()
    
    response = {
        "client_id": client_id,
        "client_name": request.client_name,
        "client_type": request.client_type.value,
        "redirect_uris": request.redirect_uris,
        "allowed_scopes": client.allowed_scopes
    }
    
    if client_secret:
        response["client_secret"] = client_secret
        
    return response
```

### 2. Authorization Code Flow

#### Authorization Endpoint
```python
@app.get("/oauth/authorize", tags=["OAuth 2.0"])
async def authorize(
    client_id: str,
    redirect_uri: str,
    scope: str = "chat:read",
    state: str = None,
    code_challenge: str = None,  # PKCE support
    code_challenge_method: str = None,
    current_user = Depends(get_current_user_optional)
):
    # Validate client and redirect URI
    client = await get_oauth_client(client_id)
    if not client or redirect_uri not in client.redirect_uris:
        raise HTTPException(400, "Invalid client or redirect URI")
    
    # Validate requested scopes
    requested_scopes = scope.split()
    if not all(s in client.allowed_scopes for s in requested_scopes):
        raise HTTPException(400, "Invalid scope requested")
    
    # If user not logged in, redirect to login
    if not current_user:
        login_url = f"/login?continue={urllib.parse.quote(request.url)}"
        return RedirectResponse(login_url, status_code=303)
    
    # Show consent page
    return await render_consent_page(
        client=client,
        scopes=requested_scopes,
        redirect_uri=redirect_uri,
        state=state,
        code_challenge=code_challenge
    )

@app.post("/oauth/authorize", tags=["OAuth 2.0"])
async def authorize_consent(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str = None,
    action: str = Form(...),  # "approve" or "deny"
    code_challenge: str = None,
    current_user = Depends(get_current_user)
):
    if action != "approve":
        error_url = f"{redirect_uri}?error=access_denied"
        if state:
            error_url += f"&state={state}"
        return RedirectResponse(error_url)
    
    # Generate authorization code
    auth_code = generate_authorization_code()
    
    # Store authorization code with metadata
    await store_authorization_code(
        code=auth_code,
        client_id=client_id,
        user_id=current_user.id,
        redirect_uri=redirect_uri,
        scopes=scope.split(),
        code_challenge=code_challenge,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    
    # Redirect back to client
    callback_url = f"{redirect_uri}?code={auth_code}"
    if state:
        callback_url += f"&state={state}"
        
    return RedirectResponse(callback_url)
```

#### Token Exchange Endpoint
```python
@app.post("/oauth/token", tags=["OAuth 2.0"])
async def token_exchange(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(None),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    code_verifier: str = Form(None),  # PKCE
    scope: str = Form(None)
):
    if grant_type == "authorization_code":
        return await handle_authorization_code_grant(
            client_id, client_secret, code, redirect_uri, code_verifier
        )
    elif grant_type == "client_credentials":
        return await handle_client_credentials_grant(
            client_id, client_secret, scope
        )
    elif grant_type == "refresh_token":
        return await handle_refresh_token_grant(request)
    else:
        raise HTTPException(400, "Unsupported grant type")

async def handle_authorization_code_grant(
    client_id: str, client_secret: str, code: str, 
    redirect_uri: str, code_verifier: str
):
    # Validate client credentials
    client = await validate_oauth_client(client_id, client_secret)
    
    # Retrieve and validate authorization code
    auth_code_data = await get_authorization_code(code)
    if not auth_code_data or auth_code_data.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invalid or expired authorization code")
    
    # Validate PKCE if used
    if auth_code_data.code_challenge:
        if not verify_pkce_challenge(code_verifier, auth_code_data.code_challenge):
            raise HTTPException(400, "Invalid code verifier")
    
    # Generate tokens
    access_token = generate_jwt_token(
        user_id=auth_code_data.user_id,
        client_id=client_id,
        scopes=auth_code_data.scopes,
        expires_in=3600
    )
    
    refresh_token = generate_refresh_token(
        user_id=auth_code_data.user_id,
        client_id=client_id,
        scopes=auth_code_data.scopes
    )
    
    # Clean up authorization code
    await delete_authorization_code(code)
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": refresh_token,
        "scope": " ".join(auth_code_data.scopes)
    }
```

### 3. Scoped Permission System

#### Scope Definitions
```python
GAIA_OAUTH_SCOPES = {
    # Chat & LLM Access
    "chat:read": {
        "description": "Read chat conversations and history",
        "endpoints": ["GET /api/v1/chat/status", "GET /api/v1/chat/conversations"],
        "level": "read"
    },
    "chat:write": {
        "description": "Send chat messages and create conversations", 
        "endpoints": ["POST /api/v1/chat", "POST /api/v1/chat/completions"],
        "level": "write"
    },
    "chat:stream": {
        "description": "Access streaming chat responses",
        "endpoints": ["POST /api/v0.2/chat/stream"],
        "level": "write"
    },
    
    # Knowledge Base Access
    "kb:read": {
        "description": "Search and read knowledge base content",
        "endpoints": ["POST /api/v0.2/kb/search", "POST /api/v0.2/kb/read"],
        "level": "read"
    },
    "kb:write": {
        "description": "Create and modify knowledge base content",
        "endpoints": ["POST /api/v0.2/kb/write", "DELETE /api/v0.2/kb/delete"],
        "level": "write"
    },
    "kb:admin": {
        "description": "Full knowledge base administration",
        "endpoints": ["POST /api/v0.2/kb/sync", "GET /api/v0.2/kb/git/status"],
        "level": "admin"
    },
    
    # Asset Generation
    "assets:generate": {
        "description": "Generate AI assets and media",
        "endpoints": ["POST /api/v1/assets/generate"],
        "level": "write"
    },
    "assets:read": {
        "description": "List and download generated assets",
        "endpoints": ["GET /api/v1/assets", "GET /api/v1/assets/{id}"],
        "level": "read"
    },
    
    # Provider & Model Access
    "providers:read": {
        "description": "View available providers and models",
        "endpoints": ["GET /api/v0.2/providers", "GET /api/v0.2/models"],
        "level": "read"
    },
    
    # User Profile
    "profile:read": {
        "description": "Read user profile information",
        "endpoints": ["GET /api/v1/user/profile"],
        "level": "read"
    },
    "profile:write": {
        "description": "Update user profile information",
        "endpoints": ["PUT /api/v1/user/profile"],
        "level": "write"
    },
    
    # Administrative Scopes
    "admin:users": {
        "description": "Manage user accounts (admin only)",
        "endpoints": ["GET /api/v1/admin/users", "POST /api/v1/admin/users"],
        "level": "admin"
    },
    "admin:clients": {
        "description": "Manage OAuth clients (admin only)",
        "endpoints": ["GET /api/v1/oauth/clients", "DELETE /api/v1/oauth/clients"],
        "level": "admin"
    }
}
```

#### Scope Validation Middleware
```python
from functools import wraps

def require_scopes(*required_scopes):
    """Decorator to enforce OAuth scope requirements on endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract token from request
            request = kwargs.get('request') or args[0]
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                raise HTTPException(401, "Missing or invalid authorization header")
            
            token = auth_header.split(' ')[1]
            
            # Validate token and extract scopes
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                token_scopes = payload.get('scopes', [])
                user_id = payload.get('sub')
                client_id = payload.get('client_id')
            except jwt.InvalidTokenError:
                raise HTTPException(401, "Invalid access token")
            
            # Check scope requirements
            missing_scopes = set(required_scopes) - set(token_scopes)
            if missing_scopes:
                raise HTTPException(
                    403, 
                    f"Insufficient scope. Required: {list(missing_scopes)}"
                )
            
            # Add scope context to request
            kwargs['oauth_context'] = {
                'user_id': user_id,
                'client_id': client_id,
                'scopes': token_scopes
            }
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage example
@app.post("/api/v1/chat")
@require_scopes("chat:write")
async def chat_endpoint(request: ChatRequest, oauth_context: dict = None):
    # oauth_context contains validated user_id, client_id, and scopes
    return await process_chat_request(request, oauth_context)
```

### 4. Client Credentials Flow

#### Server-to-Server Authentication
```python
@app.post("/oauth/token")
async def client_credentials_flow(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    scope: str = Form(None)
):
    if grant_type != "client_credentials":
        raise HTTPException(400, "Invalid grant type")
    
    # Validate client credentials
    client = await validate_oauth_client(client_id, client_secret)
    if client.client_type != ClientType.SERVICE:
        raise HTTPException(400, "Client credentials grant not allowed for this client type")
    
    # Validate requested scopes
    requested_scopes = scope.split() if scope else ["chat:read"]
    invalid_scopes = set(requested_scopes) - set(client.allowed_scopes)
    if invalid_scopes:
        raise HTTPException(400, f"Invalid scopes: {list(invalid_scopes)}")
    
    # Generate service access token
    access_token = generate_jwt_token(
        user_id=f"service:{client_id}",
        client_id=client_id,
        scopes=requested_scopes,
        expires_in=3600,
        token_type="service"
    )
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": " ".join(requested_scopes)
    }
```

### 5. Token Introspection & Management

#### Token Introspection Endpoint (RFC 7662)
```python
@app.post("/oauth/introspect", tags=["OAuth 2.0"])
async def introspect_token(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    # Validate client credentials
    client = await validate_oauth_client(client_id, client_secret)
    
    try:
        # Decode and validate token
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        # Check if token is expired
        if payload.get('exp', 0) < time.time():
            return {"active": False}
        
        return {
            "active": True,
            "scope": " ".join(payload.get('scopes', [])),
            "client_id": payload.get('client_id'),
            "username": payload.get('email'),
            "sub": payload.get('sub'),
            "exp": payload.get('exp'),
            "iat": payload.get('iat'),
            "token_type": payload.get('token_type', "access_token")
        }
        
    except jwt.InvalidTokenError:
        return {"active": False}

@app.post("/oauth/revoke", tags=["OAuth 2.0"])  
async def revoke_token(
    token: str = Form(...),
    token_type_hint: str = Form(None),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    # Validate client credentials
    client = await validate_oauth_client(client_id, client_secret)
    
    # Add token to revocation list
    await add_to_token_blacklist(token)
    
    return {"revoked": True}
```

## Benefits

### 1. **Developer Ecosystem Enablement**
- **Third-party integrations**: Slack bots, Zapier connectors, custom business tools
- **Mobile/desktop apps**: Secure authentication without storing passwords
- **Partner platforms**: White-label AI integration opportunities
- **API marketplace readiness**: Foundation for public API program

### 2. **Enterprise Security & Compliance**
- **Granular permissions**: Scope-based access control reduces security risk
- **Audit trails**: Complete OAuth flow logging for compliance
- **SSO integration**: Foundation for SAML/OIDC enterprise authentication
- **Zero-trust architecture**: Every API call validated with proper scopes

### 3. **Operational Excellence** 
- **Rate limiting by client**: Different tiers for different app types
- **Usage analytics**: Track API usage by client and scope
- **Client management**: Self-service developer portal capability
- **Monitoring & alerting**: OAuth-specific metrics and security alerts

### 4. **Backward Compatibility**
- **Existing integrations unchanged**: API keys and password login continue working
- **Progressive adoption**: Teams can migrate to OAuth when ready
- **Dual authentication**: Both OAuth and legacy auth work simultaneously

## Migration Path

### Phase 1: Core OAuth Infrastructure (Week 1-2)
- [ ] Database schema migration for OAuth clients and codes
- [ ] Client registration API endpoints
- [ ] Basic authorization code flow implementation  
- [ ] JWT token generation with scope support
- [ ] Scope validation middleware framework

**Success Criteria:**
- Developer can register a client application
- Authorization code flow works end-to-end
- Scoped tokens properly restrict API access

### Phase 2: Client Credentials & Enterprise Features (Week 3-4)
- [ ] Client credentials flow for server-to-server auth
- [ ] Token introspection and revocation endpoints
- [ ] Comprehensive scope definitions for all API endpoints
- [ ] Rate limiting integration with OAuth clients
- [ ] OAuth-specific monitoring and logging

**Success Criteria:**
- Server applications can authenticate via client credentials
- Token management (introspection/revocation) works
- All API endpoints properly enforce scopes

### Phase 3: Developer Experience & Management (Week 5-6)
- [ ] Developer console for client management
- [ ] PKCE support for mobile applications
- [ ] Webhook integration for OAuth events
- [ ] OAuth flow testing tools
- [ ] Documentation and SDK examples

**Success Criteria:**
- Developers can self-manage OAuth applications
- Mobile apps can securely authenticate
- Complete developer documentation available

### Phase 4: Enterprise Integration Preparation (Week 7-8)
- [ ] SAML/OIDC integration framework
- [ ] Multi-tenant client isolation
- [ ] Advanced audit logging
- [ ] Compliance reporting tools
- [ ] Load testing and performance optimization

**Success Criteria:**
- Enterprise SSO integration patterns defined
- System handles high OAuth traffic volume
- Compliance and audit requirements met

## Configuration

### Environment Variables
```bash
# OAuth 2.0 Configuration
OAUTH_ENABLED=true
OAUTH_ISSUER=https://api.gaia.ai
OAUTH_JWT_SECRET=your-oauth-jwt-secret-key
OAUTH_JWT_EXPIRATION=3600

# Authorization Code Settings
OAUTH_CODE_EXPIRATION=600  # 10 minutes
OAUTH_REFRESH_TOKEN_EXPIRATION=2592000  # 30 days

# Client Registration
OAUTH_CLIENT_SECRET_LENGTH=64
OAUTH_REQUIRE_CLIENT_SECRET=true  # Set false for public clients only

# Rate Limiting
OAUTH_RATE_LIMIT_ENABLED=true
OAUTH_DEFAULT_RATE_LIMIT=1000  # requests per hour

# Security
OAUTH_REQUIRE_HTTPS=true  # Enforce HTTPS for OAuth flows
OAUTH_PKCE_REQUIRED=true  # Require PKCE for public clients
```

### Database Configuration
```sql
-- OAuth client registration table
CREATE TABLE oauth_clients (
    client_id VARCHAR(64) PRIMARY KEY,
    client_secret_hash VARCHAR(64),
    client_name VARCHAR(255) NOT NULL,
    client_type VARCHAR(20) NOT NULL,
    redirect_uris TEXT[] NOT NULL,
    allowed_scopes TEXT[] NOT NULL,
    grant_types TEXT[] NOT NULL,
    organization_id UUID,
    rate_limit_tier VARCHAR(50) DEFAULT 'standard',
    webhook_url VARCHAR(500),
    created_by UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Authorization codes (short-lived)  
CREATE TABLE oauth_authorization_codes (
    code VARCHAR(128) PRIMARY KEY,
    client_id VARCHAR(64) NOT NULL,
    user_id UUID NOT NULL,
    redirect_uri VARCHAR(500) NOT NULL,
    scopes TEXT[] NOT NULL,
    code_challenge VARCHAR(128),
    code_challenge_method VARCHAR(10),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

-- Token blacklist for revocation
CREATE TABLE oauth_revoked_tokens (
    token_hash VARCHAR(64) PRIMARY KEY,
    revoked_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

-- OAuth event logging
CREATE TABLE oauth_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    client_id VARCHAR(64),
    user_id UUID,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

## Monitoring & Analytics

### Key Metrics to Track
```python
# OAuth Flow Metrics
oauth_authorization_requests = Counter('oauth_authorization_requests_total', 
                                     ['client_id', 'response_type'])
oauth_token_requests = Counter('oauth_token_requests_total', 
                              ['client_id', 'grant_type'])
oauth_scope_usage = Counter('oauth_scope_usage_total', 
                           ['scope', 'client_id'])

# Security Metrics  
oauth_failed_validations = Counter('oauth_failed_validations_total',
                                  ['error_type', 'client_id'])
oauth_token_revocations = Counter('oauth_token_revocations_total',
                                 ['client_id', 'reason'])

# Performance Metrics
oauth_request_duration = Histogram('oauth_request_duration_seconds',
                                  ['endpoint', 'grant_type'])
```

### Success Measurements
1. **Developer Adoption**: Number of registered OAuth clients
2. **API Usage**: OAuth vs legacy authentication traffic ratio  
3. **Security Posture**: Scope compliance rate, token validation success rate
4. **Performance**: OAuth flow completion time, token validation latency
5. **Enterprise Readiness**: SSO integration successful completion rate

### Alerting Thresholds
- OAuth flow failure rate > 5%
- Token validation latency > 100ms
- Unusual scope access patterns (potential security issue)
- Client credential compromise indicators

## Future Enhancements

### 1. **OpenID Connect Layer**
- Add identity layer on top of OAuth 2.0
- User info endpoint with standardized claims
- ID tokens with user identity information
- Support for enterprise identity federation

### 2. **Device Authorization Grant (RFC 8628)**
- OAuth flow for smart TVs, IoT devices, and limited-input devices
- User codes and device codes for secure pairing
- Polling mechanism for token retrieval

### 3. **Pushed Authorization Requests (RFC 9126)**
- Enhanced security for authorization requests
- Prevent authorization request tampering
- Support for complex enterprise authentication scenarios

### 4. **Dynamic Client Registration (RFC 7591)**
- Runtime client registration without manual approval
- Automated client lifecycle management
- Template-based client configuration

### 5. **Enterprise SSO Integration**
- SAML 2.0 identity provider integration
- Active Directory / LDAP authentication
- Multi-factor authentication (MFA) support
- Just-in-time (JIT) user provisioning

### 6. **Advanced Security Features**
- Mutual TLS (mTLS) client authentication
- JWT-secured authorization requests (JAR)
- Proof of Possession (DPoP) tokens
- Rich authorization requests for fine-grained permissions

This OAuth 2.0 extension transforms GAIA from a single-tenant AI service into a platform-ready ecosystem that enterprises and developers can build upon with confidence.