# mTLS + JWT Migration Plan: From Legacy API Keys to Modern Microservices Auth

Based on industry best practices research (2025), this plan migrates from API_KEY patterns to modern mTLS + JWT architecture.

## Current State Analysis

### API Key Usage Patterns
- **Gateway Service**: Uses API_KEY for LLM provider access + user authentication
- **Auth Service**: No API_KEY (only validates others' keys)  
- **Web Service**: Uses WEB_API_KEY for gateway communication
- **Asset/Chat Services**: Use API_KEY for LLM provider access

### Problems with Current System
1. **Single Point of Failure**: One API key compromise affects everything
2. **Poor Auditability**: Can't trace which service made which requests
3. **Scaling Issues**: All services share same authentication secret
4. **Security Gaps**: No mutual authentication between services

## Target Architecture: mTLS + JWT

### Service-to-Service Authentication
- **mTLS (Mutual TLS)**: Transport-level security with client certificates
- **JWT Tokens**: Application-level authentication with service identity
- **Zero-Trust**: Every request authenticated and authorized
- **No Shared Secrets**: Each service has unique certificate/key pair

### Local Development Compatibility

**YES - mTLS + JWT will work locally** with these approaches:

#### Option 1: Development Certificate Authority (Recommended)
```bash
# Create local CA for development
./scripts/setup-dev-ca.sh
# Issues certificates for localhost services
# Docker Compose mounts certificates to containers
# Same security model as production, different CA
```

#### Option 2: TLS Termination Proxy
```bash
# Use Traefik/Envoy proxy locally
# Handles mTLS between proxy and services
# Services communicate via proxy with certificates
# Mirrors production load balancer setup
```

#### Option 3: Self-Signed Development Mode
```bash
# Generate self-signed certificates for local services
# Mount certificates via Docker Compose volumes
# Same code paths as production, different cert sources
```

## Migration Phases

### Phase 1: Add JWT Support (2-3 days)
**Goal**: Support both API_KEY and JWT validation

**Changes**:
- Add JWT service-to-service token generation in auth service
- Update `validate_auth_for_service()` to accept JWTs
- Add certificate infrastructure scripts
- Keep API_KEY validation for backward compatibility

**Local Development**: 
- Self-signed certificates for development
- JWT tokens signed with dev keys
- Docker Compose certificate mounting

### Phase 2: Certificate Infrastructure (3-4 days)  
**Goal**: Deploy mTLS certificates to all environments

**Changes**:
- Fly.io certificate deployment scripts
- Service certificate rotation automation
- Local CA setup for development
- Certificate monitoring and alerting

**Local Development**:
- Development CA generates certificates
- Docker containers get certificates via volumes
- Same TLS handshake as production

### Phase 3: Migrate Clients (2-3 days)
**Goal**: Switch external clients to Supabase JWTs

**Changes**:
- Update Unity XR/AR clients to use Supabase auth
- Update NextJS client authentication flow
- Migrate user API keys to Supabase user tokens
- Keep legacy API_KEY validation for transition

**Local Development**:
- Same Supabase configuration as production
- Local clients use development Supabase project
- Identical authentication flows

### Phase 4: Remove API_KEY Logic (1-2 days)
**Goal**: Clean up legacy authentication code

**Changes**:
- Remove API_KEY validation from all services
- Remove API_KEY from configuration
- Update documentation and deployment scripts
- Add security monitoring for certificate issues

## Local Development Implementation

### Docker Compose Changes
```yaml
# docker-compose.yml
services:
  auth-service:
    volumes:
      - ./certs/auth-service:/app/certs:ro
    environment:
      - TLS_CERT_PATH=/app/certs/cert.pem
      - TLS_KEY_PATH=/app/certs/key.pem
      - JWT_SIGNING_KEY_PATH=/app/certs/jwt-signing.key

  gateway:
    volumes:
      - ./certs/gateway:/app/certs:ro
      - ./certs/ca.pem:/app/ca.pem:ro
    environment:
      - TLS_CLIENT_CERT_PATH=/app/certs/cert.pem
      - TLS_CLIENT_KEY_PATH=/app/certs/key.pem
      - TLS_CA_CERT_PATH=/app/ca.pem
```

### Certificate Generation Script
```bash
#!/bin/bash
# scripts/setup-dev-ca.sh

# Create development CA
openssl genrsa -out certs/ca.key 4096
openssl req -new -x509 -key certs/ca.key -out certs/ca.pem -days 365 \
  -subj "/CN=Gaia Development CA"

# Generate service certificates
for service in gateway auth-service web-service chat-service asset-service; do
  # Generate private key
  openssl genrsa -out "certs/$service/key.pem" 2048
  
  # Generate certificate signing request
  openssl req -new -key "certs/$service/key.pem" -out "certs/$service/csr.pem" \
    -subj "/CN=$service"
  
  # Sign certificate with CA
  openssl x509 -req -in "certs/$service/csr.pem" -CA certs/ca.pem -CAkey certs/ca.key \
    -out "certs/$service/cert.pem" -days 365 -CAcreateserial
done
```

### Service Code Changes
```python
# app/shared/mtls_client.py
import ssl
import httpx
from app.shared.config import settings

def create_mtls_client():
    """Create HTTP client with mTLS certificates."""
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ssl_context.load_cert_chain(
        certfile=settings.TLS_CLIENT_CERT_PATH,
        keyfile=settings.TLS_CLIENT_KEY_PATH
    )
    ssl_context.load_verify_locations(settings.TLS_CA_CERT_PATH)
    ssl_context.check_hostname = False  # For local development
    
    return httpx.AsyncClient(verify=ssl_context)

# app/shared/jwt_service.py  
import jwt
from datetime import datetime, timedelta

async def generate_service_jwt(service_name: str) -> str:
    """Generate JWT for service-to-service communication."""
    payload = {
        'iss': 'gaia-auth-service',
        'sub': service_name,
        'aud': 'gaia-services',
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=1),
        'service': service_name
    }
    
    return jwt.encode(payload, settings.JWT_SIGNING_KEY, algorithm='RS256')
```

## Benefits of This Approach

### Security Improvements
- **Mutual Authentication**: Both client and server verify each other
- **Certificate Rotation**: Automated certificate lifecycle management
- **Audit Trail**: Each service has unique identity in logs
- **Compromise Isolation**: Certificate breach affects only one service

### Local Development Benefits
- **Production Parity**: Same security model as production
- **Easy Debugging**: Certificate issues obvious in logs
- **Team Consistency**: All developers use same security setup
- **Integration Testing**: Can test certificate rotation locally

### Operational Benefits
- **Monitoring**: Certificate expiration alerts
- **Automation**: Certificate rotation without service restarts
- **Compliance**: Industry standard security practices
- **Scalability**: No shared secrets to manage

## Migration Timeline

**Week 1**: Phase 1 - JWT Support (maintain API_KEY compatibility)
**Week 2**: Phase 2 - Certificate Infrastructure  
**Week 3**: Phase 3 - Client Migration
**Week 4**: Phase 4 - Legacy Cleanup + Documentation

**Total**: 3-4 weeks for complete migration

## Risk Mitigation

### Rollback Plan
- Keep API_KEY validation during transition
- Feature flags for mTLS/JWT vs legacy auth
- Canary deployment for certificate rollout

### Testing Strategy
- Local certificate generation testing
- Service-to-service auth integration tests
- Load testing with mTLS overhead
- Certificate rotation failure scenarios

### Monitoring
- Certificate expiration alerts (30/7/1 days)
- TLS handshake failure monitoring  
- JWT validation error tracking
- Service authentication latency metrics

## Why This Works for Local Development

1. **Same Code Paths**: Development and production use identical authentication logic
2. **Certificate Tooling**: Scripts handle certificate complexity  
3. **Docker Integration**: Certificates mounted via volumes, transparent to services
4. **Development CA**: Separate CA for local vs production certificates
5. **Debugging**: Certificate issues visible in service logs
6. **Team Onboarding**: Single `./scripts/setup-dev-ca.sh` command

The key insight: **Local development gets the same security benefits as production, with certificates managed by automation instead of manual configuration.**