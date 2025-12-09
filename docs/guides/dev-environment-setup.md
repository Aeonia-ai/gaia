# Dev Environment Setup: The Gold Standard

This document captures the complete process for setting up a production-ready dev environment that serves as the **shining exemplar** for all future environments.

## 🏆 Architecture Overview

### Clean Database Strategy
- **One database per environment**: `gaia-db-dev`, `gaia-db-staging`, `gaia-db-prod`
- **Shared tables across services**: All services use the same `users` and `api_keys` tables
- **No service-specific databases**: Eliminates data duplication and sync issues

### Authentication Pattern
- **User-associated API keys**: Stored in database with SHA256 hashing
- **No global API_KEY environment variable**: Forces proper user management
- **Database-driven validation**: All services query the same authentication tables

### Microservices Architecture
```
gaia-gateway-dev     → Entry point, routes to services
gaia-chat-dev        → LLM interactions, provider management  
gaia-auth-dev        → JWT validation, user management
gaia-asset-dev       → Asset generation and management
gaia-nats-dev        → Service coordination (optional)
gaia-db-dev          → Shared PostgreSQL database
```

## 🚀 Step-by-Step Setup Process

### 1. Database Initialization
```bash
# Create the main database
fly postgres create --name gaia-db-dev --region lax --vm-size shared-cpu-1x --volume-size 10

# Initialize with users and API keys
./scripts/init-database.sh --env dev --user admin@gaia.dev

# CRITICAL: Initialize persona tables (required for persona functionality)
fly postgres connect -a gaia-db-dev < scripts/create_persona_tables.sql
```

**⚠️ IMPORTANT**: Persona functionality requires additional database setup. See [Database Initialization Guide](database-initialization-guide.md) for complete setup requirements.

### 2. Service Configuration
Each service uses the **same database** with proper URL conversion:

```toml
# fly.{service}.dev.toml
[env]
  DATABASE_URL = "postgresql://postgres@gaia-db-dev.internal:5432/postgres"
  ENVIRONMENT = "dev"
  SERVICE_NAME = "{service}"
```

**Critical:** Database URL conversion in `app/shared/database_compat.py`:
```python
# Convert postgres:// to postgresql:// for SQLAlchemy compatibility
raw_database_url = os.getenv("DATABASE_URL", "postgresql://...")
DATABASE_URL = raw_database_url.replace("postgres://", "postgresql://", 1) if raw_database_url.startswith("postgres://") else raw_database_url
```

### 3. Deployment Sequence
```bash
# Deploy all services with updated authentication
./scripts/deploy.sh --env dev --services all

# Verify each service
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev health
./scripts/test.sh --url https://gaia-chat-dev.fly.dev health
./scripts/test.sh --url https://gaia-auth-dev.fly.dev health
./scripts/test.sh --url https://gaia-asset-dev.fly.dev health
```

### 4. Authentication Verification
```bash
# Test end-to-end authentication
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev providers
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev models
```

## 🔧 Configuration Details

### Shared Code Requirements
When updating shared modules (`app/shared/*`), **ALL services must be redeployed**:
```bash
# ❌ WRONG: Partial deployment creates inconsistency
./scripts/deploy.sh --env dev --services gateway

# ✅ CORRECT: Deploy all services when shared code changes
./scripts/deploy.sh --env dev --services all
```

### Database Connection Pattern
```python
# app/shared/security.py - User API Key Validation
async def validate_user_api_key(api_key: str, db: Session) -> Optional[AuthenticationResult]:
    key_hash = hash_api_key(api_key)  # SHA256 hash
    result = db.execute(
        text("SELECT id, user_id FROM api_keys WHERE key_hash = :key_hash AND is_active = true"),
        {"key_hash": key_hash}
    ).fetchone()
    
    if result:
        return AuthenticationResult(
            auth_type="user_api_key",
            user_id=str(result.user_id),
            api_key=api_key
        )
```

### Fly.io Database Attachment (AVOID)
```bash
# ❌ DON'T DO THIS: Creates separate databases per service
fly postgres attach gaia-db-dev -a gaia-chat-dev  # Creates gaia_chat_dev database

# ✅ DO THIS: Use shared database with proper configuration
# Configure DATABASE_URL in fly.{service}.dev.toml to point to main database
```

## 🧪 Testing Protocol

### Core Functionality Tests
```bash
# Gateway routing
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev providers

# Authentication flow
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev models

# Service health
./scripts/test.sh --url https://gaia-chat-dev.fly.dev health
```

### Database Verification
```bash
# Verify user and API key setup
echo "SELECT u.email, ak.name FROM users u JOIN api_keys ak ON u.id = ak.user_id;" | fly postgres connect -a gaia-db-dev
```

## ⚠️ Common Pitfalls & Solutions

### Issue: "relation api_keys does not exist"
**Cause**: Service connecting to wrong database
**Solution**: Ensure all services use main `postgres` database, not service-specific ones

### Issue: "sqlalchemy.exc.NoSuchModuleError: postgres"
**Cause**: SQLAlchemy expects `postgresql://` but Fly.io provides `postgres://`
**Solution**: URL conversion in `database_compat.py` (see configuration above)

### Issue: "ImportError: cannot import name 'get_api_key'"
**Cause**: Removed function still referenced in imports
**Solution**: Update `app/shared/__init__.py` to remove deleted function references

### Issue: 403 Authentication Errors After Deployment
**Cause**: Only some services deployed with new authentication code
**Solution**: Always deploy ALL services when changing shared authentication code

## 🎯 Success Criteria

A properly configured dev environment should achieve:

- ✅ **Gateway Health**: `GET /health` returns 200 OK
- ✅ **Provider Listing**: `GET /api/v0.2/providers` returns 200 with provider data
- ✅ **Model Listing**: `GET /api/v0.2/models` returns 200 with model data  
- ✅ **Service Health**: All individual services return 200 on `/health`
- ✅ **Database Connectivity**: All services show `"database": {"status": "connected"}`
- ✅ **Authentication**: User API key validation working end-to-end

## 📋 Replication Checklist

To replicate this setup for staging/production:

1. [ ] Create environment-specific database (`gaia-db-{env}`)
2. [ ] Copy and modify fly config files (`fly.*.{env}.toml`)
3. [ ] Initialize database with admin user and API key
4. [ ] Deploy all services simultaneously
5. [ ] Verify authentication chain works
6. [ ] Test core endpoints return expected data
7. [ ] Monitor logs for any import/connection errors

## 🌟 Why This is the Gold Standard

This dev environment setup represents production-ready architecture:

- **Scalable**: Each service can be scaled independently
- **Secure**: Database-driven authentication with proper hashing
- **Maintainable**: Shared database eliminates data sync issues
- **Consistent**: Same patterns work for staging and production
- **Debuggable**: Clear separation of concerns with comprehensive logging
- **Portable**: Not tied to any specific cloud provider patterns

**This is the exemplar that all future environments should follow.**