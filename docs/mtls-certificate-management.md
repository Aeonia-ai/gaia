# mTLS Certificate Management Guide

## Overview

This guide covers the complete certificate infrastructure for the Gaia Platform's mTLS + JWT authentication system.

## Certificate Architecture

### Certificate Authority (CA)
- **Location**: `./certs/ca.pem` (public), `./certs/ca-key.pem` (private)
- **Purpose**: Root authority for all service certificates
- **Validity**: 10 years
- **Algorithm**: RSA 2048-bit

### Service Certificates
- **Gateway**: `./certs/gateway/cert.pem` + `./certs/gateway/key.pem`
- **Auth Service**: `./certs/auth-service/cert.pem` + `./certs/auth-service/key.pem`
- **Chat Service**: `./certs/chat-service/cert.pem` + `./certs/chat-service/key.pem`
- **Asset Service**: `./certs/asset-service/cert.pem` + `./certs/asset-service/key.pem`
- **Web Service**: `./certs/web-service/cert.pem` + `./certs/web-service/key.pem`

### JWT Signing Keys
- **Private Key**: `./certs/jwt-signing.key` (RSA 2048-bit)
- **Public Key**: `./certs/jwt-signing.pub`
- **Purpose**: Service-to-service JWT token signing and validation

## Certificate Generation

### Initial Setup
```bash
# Generate complete certificate infrastructure
./scripts/setup-dev-ca.sh

# Verify certificates were created
ls -la certs/
ls -la certs/*/
```

### Manual Certificate Generation

#### 1. Create Certificate Authority
```bash
# Generate CA private key
openssl genrsa -out certs/ca-key.pem 2048

# Generate CA certificate
openssl req -new -x509 -days 3650 -key certs/ca-key.pem \
  -out certs/ca.pem \
  -subj "/C=US/ST=CA/L=San Francisco/O=Gaia Platform/CN=Gaia Platform CA"
```

#### 2. Generate Service Certificate
```bash
# Example: Gateway service
SERVICE="gateway"

# Generate private key
openssl genrsa -out certs/$SERVICE/key.pem 2048

# Generate certificate signing request
openssl req -new -key certs/$SERVICE/key.pem \
  -out certs/$SERVICE/csr.pem \
  -subj "/C=US/ST=CA/L=San Francisco/O=Gaia Platform/CN=$SERVICE"

# Sign with CA
openssl x509 -req -in certs/$SERVICE/csr.pem \
  -CA certs/ca.pem -CAkey certs/ca-key.pem -CAcreateserial \
  -out certs/$SERVICE/cert.pem -days 365

# Clean up CSR
rm certs/$SERVICE/csr.pem
```

#### 3. Generate JWT Signing Keys
```bash
# Generate private key
openssl genrsa -out certs/jwt-signing.key 2048

# Extract public key
openssl rsa -in certs/jwt-signing.key -pubout -out certs/jwt-signing.pub
```

## Docker Integration

### Volume Mounting
All services mount certificates as read-only volumes:

```yaml
# docker-compose.yml
services:
  gateway:
    volumes:
      - ./certs:/app/certs:ro
  
  auth-service:
    volumes:
      - ./certs:/app/certs:ro
```

### Certificate Paths
```python
# In service code
CERT_PATH = "/app/certs/service-name/cert.pem"
KEY_PATH = "/app/certs/service-name/key.pem"
CA_PATH = "/app/certs/ca.pem"
JWT_PRIVATE_KEY_PATH = "/app/certs/jwt-signing.key"
JWT_PUBLIC_KEY_PATH = "/app/certs/jwt-signing.pub"
```

## Production Deployment

### Fly.io Certificate Storage

#### Option 1: Fly.io Secrets (Recommended)
```bash
# Set certificate as secret
fly secrets set GATEWAY_CERT="$(cat certs/gateway/cert.pem)" -a gaia-gateway-production
fly secrets set GATEWAY_KEY="$(cat certs/gateway/key.pem)" -a gaia-gateway-production
fly secrets set CA_CERT="$(cat certs/ca.pem)" -a gaia-gateway-production
```

#### Option 2: Fly.io Volumes
```bash
# Create persistent volume
fly volumes create cert_data --region lax --size 1 -a gaia-gateway-production

# Mount in fly.toml
[mounts]
source = "cert_data"
destination = "/app/certs"
```

### Production Certificate Generation
```bash
# Generate production-specific certificates
ENVIRONMENT=production ./scripts/setup-prod-ca.sh

# Deploy to all services
./scripts/deploy-certificates.sh --env production
```

## Certificate Rotation

### Development (Annual)
```bash
# Rotate all certificates
./scripts/rotate-dev-certificates.sh

# Restart services to pick up new certificates
docker compose down && docker compose up
```

### Production (Quarterly)
```bash
# Generate new certificates
./scripts/generate-prod-certificates.sh --rotate

# Deploy with zero downtime
./scripts/deploy-certificates.sh --env production --rolling-update

# Verify all services using new certificates
./scripts/verify-certificates.sh --env production
```

## Certificate Verification

### Local Development
```bash
# Verify certificate chain
openssl verify -CAfile certs/ca.pem certs/gateway/cert.pem

# Check certificate details
openssl x509 -in certs/gateway/cert.pem -text -noout

# Test mTLS connection
curl --cert certs/gateway/cert.pem \
     --key certs/gateway/key.pem \
     --cacert certs/ca.pem \
     https://auth-service:8000/health
```

### Production
```bash
# Verify remote certificate
echo | openssl s_client -connect gaia-gateway-production.fly.dev:443 -servername gaia-gateway-production.fly.dev

# Test mTLS from one service to another
fly ssh console -a gaia-gateway-production -C "curl --cert /app/certs/gateway/cert.pem --key /app/certs/gateway/key.pem --cacert /app/certs/ca.pem https://gaia-auth-production.fly.dev/health"
```

## Certificate Monitoring

### Expiration Monitoring
```bash
# Check certificate expiration
./scripts/check-cert-expiry.sh

# Sample output:
# Gateway cert expires: 2025-07-19 (358 days)
# Auth cert expires: 2025-07-19 (358 days)
# JWT signing key expires: Never (RSA key)
```

### Automated Monitoring
```bash
# Add to cron for daily checks
0 9 * * * /path/to/gaia/scripts/check-cert-expiry.sh --alert-days 30
```

### Health Check Integration
```python
# In service health checks
from app.shared.security import verify_certificate_expiry

@app.get("/health")
async def health_check():
    cert_status = verify_certificate_expiry()
    return {
        "status": "healthy",
        "certificates": {
            "service_cert_expires": cert_status.service_expires,
            "ca_cert_expires": cert_status.ca_expires,
            "days_until_expiry": cert_status.days_remaining
        }
    }
```

## Security Best Practices

### Certificate Storage
- **Never commit private keys** to repository
- **Use restrictive permissions**: `chmod 600` for private keys
- **Encrypt at rest** in production
- **Use secrets management** for production deployment

### Certificate Validation
- **Always verify certificate chain** in production
- **Check certificate expiration** before deployment
- **Validate subject names** match service names
- **Monitor certificate usage** for anomalies

### Key Management
- **Rotate certificates regularly** (quarterly for production)
- **Use strong algorithms** (RSA 2048+ or ECDSA P-256+)
- **Separate keys per environment** (dev, staging, production)
- **Backup certificates securely** before rotation

## Troubleshooting

### Common Issues

#### Certificate Not Found
```bash
# Error: Certificate file not found
# Solution: Verify Docker volume mounting
docker compose exec gateway ls -la /app/certs/
```

#### Certificate Permission Denied
```bash
# Error: Permission denied reading certificate
# Solution: Fix file permissions
chmod 644 certs/*/cert.pem
chmod 600 certs/*/key.pem
```

#### Certificate Expired
```bash
# Error: Certificate has expired
# Solution: Regenerate certificates
./scripts/setup-dev-ca.sh
docker compose restart
```

#### mTLS Handshake Failed
```bash
# Error: SSL handshake failed
# Solution: Verify certificate chain
openssl verify -CAfile certs/ca.pem certs/service/cert.pem
```

### Debug Commands
```bash
# Check certificate validity
openssl x509 -in certs/gateway/cert.pem -dates -noout

# Test certificate loading in Python
python -c "
from app.shared.security import load_certificates
certs = load_certificates()
print('Certificates loaded successfully')
"

# Verify mTLS client configuration
./scripts/test-mtls-connections.py --verbose
```

## Integration with Authentication

### JWT Service Integration
The certificate infrastructure integrates with JWT service authentication:

```python
# JWT tokens signed with certificate-based keys
from app.shared.jwt_service import generate_service_token

# Generate token for service-to-service communication
token = generate_service_token(
    service_name="gateway",
    target_service="auth-service",
    cert_path="/app/certs/gateway/cert.pem"
)
```

### mTLS Client Usage
```python
from app.shared.mtls_client import MTLSClient

# Use certificates for service communication
async with MTLSClient(
    cert_file="/app/certs/gateway/cert.pem",
    key_file="/app/certs/gateway/key.pem",
    ca_file="/app/certs/ca.pem"
) as client:
    response = await client.get("https://auth-service:8000/internal/validate")
```

This certificate infrastructure provides the foundation for secure service-to-service communication in the Gaia Platform's microservices architecture.