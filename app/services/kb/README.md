# KB Service Implementation Guide

## Overview

The Knowledge Base (KB) service provides document storage and retrieval for the GAIA platform. It supports multiple storage backends and can be configured for single-user or multi-user scenarios.

## Current Implementation Status

### ✅ **Fully Implemented & Active**
- Git-based storage (default mode)
- Full-text search using ripgrep
- MCP server integration
- HTTP API endpoints
- KB tools for LLM integration

### ⚠️ **Implemented But Not Active by Default**
- **Database storage** (`kb_database_storage.py`) - Set `KB_STORAGE_MODE=database`
- **Hybrid storage** (`kb_hybrid_storage.py`) - Set `KB_STORAGE_MODE=hybrid`
- **RBAC/Multi-user** (`kb_rbac_integration.py`) - Set `KB_MULTI_USER_ENABLED=true`
- **Storage manager** (`kb_storage_manager.py`) - Automatically selects backend

### 🚧 **Partially Implemented**
- **KB Editor** (`kb_editor.py`) - Web-based editing interface (needs frontend)
- **KB Cache** (`kb_cache.py`) - Redis caching layer (needs configuration)

## File Structure

```
kb/
├── main.py                 # FastAPI app entry point
├── kb_service.py           # Core service implementation
├── kb_mcp_server.py        # MCP server for Git operations (default)
├── kb_storage_manager.py   # Storage backend selector
├── kb_database_storage.py  # PostgreSQL storage (inactive)
├── kb_hybrid_storage.py    # Git + PostgreSQL (inactive)
├── kb_rbac_integration.py  # RBAC wrapper (inactive)
├── kb_storage_with_rbac.py # RBAC implementation
├── kb_git_sync.py          # Git synchronization
├── kb_editor.py            # Document editor (partial)
├── kb_cache.py             # Redis cache (partial)
├── kb_startup.py           # Service initialization
└── v0_2_api.py             # Legacy API support
```

## Continuing Development

### To Enable Database Storage

1. **Set environment variable**:
   ```bash
   KB_STORAGE_MODE=database
   ```

2. **Run migrations** (if not exists):
   ```sql
   -- See kb_database_storage.py for schema
   CREATE TABLE kb_documents (...);
   CREATE TABLE kb_versions (...);
   ```

3. **Test**:
   ```python
   from app.services.kb.kb_database_storage import kb_db_storage
   await kb_db_storage.initialize()
   await kb_db_storage.create_document(path, content, metadata)
   ```

### To Enable Hybrid Storage

1. **Set environment variables**:
   ```bash
   KB_STORAGE_MODE=hybrid
   KB_GIT_REPO_URL=https://github.com/org/kb
   KB_GIT_AUTH_TOKEN=token
   ```

2. **Initialize**:
   ```python
   from app.services.kb.kb_hybrid_storage import kb_hybrid_storage
   await kb_hybrid_storage.initialize()
   ```

### To Enable Multi-User RBAC

1. **Set environment variable**:
   ```bash
   KB_MULTI_USER_ENABLED=true
   ```

2. **Effect in kb_service.py**:
   ```python
   # Lines 15-19: Conditional import
   if getattr(settings, 'KB_MULTI_USER_ENABLED', False):
       from .kb_rbac_integration import kb_server_with_rbac as kb_server
   ```

## Adding New Features

### Storage Backend Checklist

- [ ] Implement storage interface in new file
- [ ] Add to `kb_storage_manager.py` StorageMode enum
- [ ] Add initialization in `_initialize_backend()`
- [ ] Implement required methods:
  - `search_documents()`
  - `get_document()`
  - `create_document()`
  - `update_document()`
  - `delete_document()`
  - `list_documents()`

### New Endpoint Checklist

- [ ] Add endpoint in `main.py`
- [ ] Implement logic in `kb_service.py`
- [ ] Add to KB tools if LLM-accessible
- [ ] Update OpenAPI schema
- [ ] Add tests

## Configuration Reference

```python
# app/shared/config.py - KB-related settings
KB_STORAGE_MODE = "git"  # git|database|hybrid
KB_PATH = "/kb"
KB_GIT_REPO_URL = ""
KB_GIT_AUTH_TOKEN = ""
KB_MULTI_USER_ENABLED = False
KB_DATABASE_URL = ""  # If different from main DATABASE_URL
KB_CACHE_ENABLED = False
KB_CACHE_TTL = 300
```

## Testing Features

### Check Active Storage Mode
```bash
curl http://localhost:8669/health | jq '.storage_mode'
```

### Test Search
```bash
curl -X POST http://localhost:8669/search \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "test query"}'
```

### Test Storage Manager
```python
from app.services.kb.kb_storage_manager import KBStorageManager
manager = KBStorageManager()
print(f"Active mode: {manager.storage_mode}")
```

## Common Issues

### Storage Mode Not Switching
- Check environment variable is set
- Restart service after changing
- Check logs for "KB Storage Manager initialized with mode:"

### Database Tables Missing
- Run migrations from `kb_database_storage.py`
- Check DATABASE_URL is valid

### RBAC Not Working
- Verify KB_MULTI_USER_ENABLED=true
- Check auth includes email field
- See kb_service.py lines 36-46 for email extraction

## Development Tips

1. **Start with Git mode** for simplicity
2. **Test database mode locally** before production
3. **Use hybrid for production** - best reliability
4. **Enable RBAC only when needed** - adds complexity

## Related Documentation

- [KB Architecture Guide](/docs/kb/developer/kb-architecture-guide.md)
- [KB Storage Configuration](/docs/kb/guides/kb-storage-configuration.md)
- [Chat-KB Integration](/docs/architecture/chat/chat-routing-and-kb-architecture.md)