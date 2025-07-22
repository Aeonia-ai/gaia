# Remote Authentication Setup

## Overview

The Gaia platform uses a dual authentication system:
1. **API Keys**: Stored in PostgreSQL database (environment-specific)
2. **JWT Tokens**: Validated via Supabase (shared across environments)

## Environment Architecture

### Local Development
- PostgreSQL: Local Docker container
- API Keys: Stored locally (e.g., Jason's key)
- Supabase: Shared instance

### Remote Deployments (dev/staging/prod)
- PostgreSQL: Fly.io managed database (environment-specific)
- API Keys: Must be created per environment
- Supabase: Same shared instance as local

## The Authentication Challenge

When deploying to remote environments, API keys from local development won't work because:
1. Each environment has its own PostgreSQL database
2. API keys are stored in PostgreSQL, not Supabase
3. There's no automatic sync of users/API keys between environments

## Solutions

### Option 1: Create API Keys per Environment

```bash
# SSH into the remote database
fly postgres connect -a gaia-db-dev

# Create user and API key
INSERT INTO users (email, name) VALUES ('jason@aeonia.ai', 'Jason Asbahr');
INSERT INTO api_keys (user_id, key_hash, name) 
VALUES (
  (SELECT id FROM users WHERE email = 'jason@aeonia.ai'),
  '3bd5bd20d0584585aea01bbff9346c701fabd9d6237d9a77c60b81564e94de3c',
  'Jason Dev Key'
);
```

### Option 2: Use Supabase JWT Authentication

```bash
# Register/login via Supabase to get JWT
curl -X POST https://gaia-gateway-dev.fly.dev/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}'

# Use the returned JWT token
curl -X POST https://gaia-gateway-dev.fly.dev/api/v0.2/kb/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "search query"}'
```

### Option 3: Database Initialization Script

Use the portable database initialization script:

```bash
./scripts/init-database-portable.sh --env dev --user jason@aeonia.ai
```

Note: This requires proper database credentials and may fail if password authentication is misconfigured.

## Current Status

As of July 2025:
- KB routes are properly configured in the gateway
- KB service is deployed and healthy
- Authentication fails because local API keys don't exist in remote database
- Remote database password may need to be updated in connection strings

## Recommendations

1. **For Development**: Use environment-specific API keys or JWT tokens
2. **For Testing**: Create test users in each environment's database
3. **For Production**: Use Supabase JWT authentication exclusively
4. **For CI/CD**: Generate temporary JWT tokens for testing

## Related Documentation

- [Authentication Guide](authentication-guide.md)
- [Database Architecture](database-architecture.md)
- [Deployment Best Practices](deployment-best-practices.md)