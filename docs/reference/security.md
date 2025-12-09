# Authentication and Security


## Overview
This document provides a consolidated overview of the authentication and security mechanisms used in the Gaia Platform. It covers the primary authentication methods, security best practices, certificate management for service-to-service communication, and troubleshooting common issues.

## Authentication Methods

The Gaia Platform supports multiple authentication methods to accommodate different client types and ensure a secure and flexible system.

### 1. Supabase JWT Authentication (Primary)
This is the primary and recommended authentication method for all new client implementations, including the Web UI and mobile applications.

- **Mechanism**: Uses JSON Web Tokens (JWTs) issued by Supabase after a user authenticates (e.g., with email/password).
- **Usage**: The JWT is sent in the `Authorization` header as a Bearer token.
- **Benefits**: Industry standard, automatic token expiration and refresh, and user metadata embedded in the token.

### 2. API Key Authentication (Legacy Support)
This method provides backward compatibility for existing clients and server-to-server integrations.

- **Mechanism**: A unique API key is associated with a user account.
- **Usage**: The API key is sent in the `X-API-Key` header.
- **Status**: Supported for legacy clients, but new implementations should use JWTs.

### 3. Service-to-Service (mTLS + JWT)
Internal communication between microservices is secured using a combination of mutual TLS (mTLS) and short-lived JWTs.

- **Mechanism**: Services establish a secure, encrypted channel using mTLS, where both client and server present and verify certificates. A short-lived JWT is also used for service identity.
- **Usage**: Handled automatically by the internal mTLS client.

## Security Best Practices

### Credential Management
- **NEVER** commit passwords or secrets to the repository.
- Use environment variables for all credentials.
- Use a secure password manager for production credentials.
- Implement role-based access control (RBAC) with individual admin accounts.
- Rotate passwords and API keys regularly (e.g., every 90 days).

### API Key Security
- Store only hashed API keys in the database.
- Implement rate limiting and permission scoping for API keys.
- Monitor and audit API key usage.

### Session Security
- Implement session timeouts.
- Use secure, HTTP-only cookies for session tokens.

## mTLS Certificate Management

### Certificate Architecture
- **Certificate Authority (CA)**: A root CA (`certs/ca.pem`) signs all service certificates.
- **Service Certificates**: Each microservice has its own certificate and private key (e.g., `certs/gateway/cert.pem`).
- **JWT Signing Keys**: An RSA key pair (`certs/jwt-signing.key` and `certs/jwt-signing.pub`) is used for signing service-to-service JWTs.

### Certificate Generation and Rotation
- **Generation**: Use the `./scripts/setup-dev-ca.sh` script to generate the entire certificate infrastructure for development.
- **Rotation**: Certificates should be rotated periodically. Use the provided scripts for rotation (e.g., `./scripts/rotate-dev-certificates.sh`).

## Troubleshooting

### Common Authentication Issues
- **"Invalid API key"**:
  1. Verify that the API key is correct and matches across services.
  2. Check that the `AUTH_BACKEND` environment variable is set correctly (`supabase` or `postgresql`).
  3. Ensure the `SUPABASE_URL` and other Supabase-related environment variables are correctly configured.
- **"Not authenticated" / JWT Validation Failures**:
  1. Check the `Authorization` header format: `Bearer <token>`.
  2. Verify that the JWT has not expired.
  3. Ensure the `SUPABASE_JWT_SECRET` is correct.

### Debugging Steps
1. **Check Service Logs**: Look for error messages related to authentication or configuration.
2. **Verify Environment Variables**: Ensure that all required secrets and configuration variables are set correctly in the environment (e.g., using `fly secrets list`).
3. **Test Services in Isolation**: Use tools like `curl` to test individual service endpoints directly.
