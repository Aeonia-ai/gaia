# Shared Modules Documentation


## Overview

The shared modules (`app/shared/`) provide common functionality used across all microservices.

## Critical Modules

### Authentication & Security
- `supabase_auth.py` - Supabase authentication integration
- `jwt_service.py` - JWT token management
- `security.py` - Security utilities and validation
- `mtls_client.py` - Mutual TLS certificate handling

### Database
- `database.py` - Legacy database connections
- `database_compat.py` - PostgreSQL URL compatibility layer (converts postgres:// to postgresql://)

### Service Infrastructure
- `service_registry.py` - Service registration and discovery
- `service_discovery.py` - Dynamic service URL resolution
- `nats_client.py` - NATS messaging client
- `redis_client.py` - Redis caching client

### AI/LLM Support
- `prompt_manager.py` - Manages and templates LLM prompts
- `tool_provider.py` - Provides tools/functions for LLM agents

### Monitoring & Logging
- `instrumentation.py` - APM and metrics instrumentation
- `logging.py` - Centralized logging configuration

### Access Control
- `rbac.py` - Original RBAC implementation
- `rbac_simple.py` - Simplified RBAC (current production)
- `rbac_fixed.py` - Bug fixes for original RBAC (deprecated)

## Module Status

| Module | Status | Usage |
|--------|--------|-------|
| `database_compat.py` | ✅ Active | All services |
| `database.py` | ⚠️ Legacy | Being phased out |
| `rbac_simple.py` | ✅ Active | Current RBAC |
| `rbac.py` | ⚠️ Legacy | Original implementation |
| `rbac_fixed.py` | ❌ Deprecated | Not used |
| `supabase_auth.py` | ✅ Active | Auth service |
| `jwt_service.py` | ✅ Active | All services |
| `redis_client.py` | ✅ Active | Gateway, Chat |
| `nats_client.py` | ⚠️ Optional | When NATS enabled |
| `service_registry.py` | ✅ Active | Service discovery |
| `instrumentation.py` | ✅ Active | Performance monitoring |
| `prompt_manager.py` | 🔍 Unknown | Needs investigation |
| `tool_provider.py` | 🔍 Unknown | Needs investigation |

## Key Implementation Details

### Database Compatibility
The `database_compat.py` module handles the postgres:// to postgresql:// URL conversion required by SQLAlchemy when using Fly.io databases.

### RBAC Evolution
- Started with `rbac.py` (complex)
- Fixed bugs in `rbac_fixed.py` (still complex)
- Simplified to `rbac_simple.py` (current production)

### Service Discovery
Two related modules handle service location:
- `service_registry.py` - Maintains registry of available services
- `service_discovery.py` - Dynamically resolves service URLs

## Usage Examples

### Import Authentication
```python
from app.shared.supabase_auth import get_current_auth_unified
from app.shared.jwt_service import create_jwt_token
```

### Import Database
```python
from app.shared.database_compat import get_database_url
```

### Import Caching
```python
from app.shared.redis_client import get_redis_client
```