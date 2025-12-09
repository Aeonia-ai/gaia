# KB Feature Discovery Guide

## Problem

External agents/developers can't easily determine:
- What KB features are implemented
- What's enabled vs available
- How to continue development

## Solution: Feature Discovery Endpoint

Add this to `app/services/kb/main.py`:

```python
@app.get("/features", tags=["Admin"])
async def get_feature_status():
    """
    Feature discovery endpoint for external agents.
    Shows what's implemented, enabled, and available.
    """
    from app.services.kb.kb_storage_manager import StorageMode
    
    return {
        "storage": {
            "current_mode": getattr(settings, 'KB_STORAGE_MODE', 'git'),
            "available_modes": [mode.value for mode in StorageMode],
            "implementations": {
                "git": {
                    "status": "active" if settings.KB_STORAGE_MODE == "git" else "available",
                    "file": "kb_mcp_server.py",
                    "class": "KBMCPServer"
                },
                "database": {
                    "status": "active" if settings.KB_STORAGE_MODE == "database" else "available",
                    "file": "kb_database_storage.py",
                    "class": "KBDatabaseStorage",
                    "requires": ["PostgreSQL", "migrations"]
                },
                "hybrid": {
                    "status": "active" if settings.KB_STORAGE_MODE == "hybrid" else "available",
                    "file": "kb_hybrid_storage.py",
                    "class": "KBHybridStorage",
                    "requires": ["PostgreSQL", "Git"]
                }
            }
        },
        "features": {
            "multi_user": {
                "enabled": getattr(settings, 'KB_MULTI_USER_ENABLED', False),
                "implementation": "kb_rbac_integration.py",
                "configuration": "KB_MULTI_USER_ENABLED=true"
            },
            "caching": {
                "enabled": getattr(settings, 'KB_CACHE_ENABLED', False),
                "implementation": "kb_cache.py",
                "configuration": "KB_CACHE_ENABLED=true"
            },
            "editor": {
                "backend_ready": True,
                "frontend_ready": False,
                "implementation": "kb_editor.py",
                "note": "Needs frontend implementation"
            },
            "git_sync": {
                "enabled": bool(getattr(settings, 'KB_GIT_REPO_URL', '')),
                "implementation": "kb_git_sync.py",
                "configuration": "KB_GIT_REPO_URL, KB_GIT_AUTH_TOKEN"
            }
        },
        "api_endpoints": {
            "search": {"path": "/search", "method": "POST", "status": "active"},
            "read": {"path": "/read", "method": "POST", "status": "active"},
            "list": {"path": "/list", "method": "POST", "status": "active"},
            "context": {"path": "/context", "method": "POST", "status": "active"},
            "synthesize": {"path": "/synthesize", "method": "POST", "status": "active"},
            "threads": {"path": "/threads", "method": "POST", "status": "active"},
            "edit": {"path": "/edit", "method": "POST", "status": "partial"},
            "create": {"path": "/create", "method": "POST", "status": "partial"},
            "delete": {"path": "/delete", "method": "DELETE", "status": "partial"}
        },
        "configuration": {
            "KB_STORAGE_MODE": getattr(settings, 'KB_STORAGE_MODE', 'git'),
            "KB_MULTI_USER_ENABLED": getattr(settings, 'KB_MULTI_USER_ENABLED', False),
            "KB_PATH": getattr(settings, 'KB_PATH', '/kb'),
            "KB_GIT_REPO_URL": bool(getattr(settings, 'KB_GIT_REPO_URL', '')),  # Hide actual URL
            "KB_CACHE_ENABLED": getattr(settings, 'KB_CACHE_ENABLED', False),
            "KB_CACHE_TTL": getattr(settings, 'KB_CACHE_TTL', 300)
        },
        "development_status": {
            "core_search": "production",
            "multi_user": "implemented_not_enabled",
            "database_storage": "implemented_not_enabled",
            "hybrid_storage": "implemented_not_enabled",
            "web_editor": "backend_only",
            "caching": "partial",
            "version_control": "git_only"
        }
    }
```

## Using Feature Discovery

### For External Agents

```bash
# Discover what's available
curl http://localhost:8669/features | jq

# Response shows:
{
  "storage": {
    "current_mode": "git",
    "available_modes": ["git", "database", "hybrid"],
    "implementations": {
      "database": {
        "status": "available",  # <- Not active but ready
        "file": "kb_database_storage.py"
      }
    }
  },
  "features": {
    "multi_user": {
      "enabled": false,  # <- Ready but not enabled
      "configuration": "KB_MULTI_USER_ENABLED=true"
    }
  }
}
```

### For Continuing Development

1. **Check what's implemented but not enabled**:
   ```python
   features = requests.get("http://kb/features").json()
   available = [
       f for f in features["features"] 
       if not f["enabled"] and f.get("backend_ready")
   ]
   ```

2. **Find partial implementations**:
   ```python
   partial = [
       endpoint for endpoint in features["api_endpoints"].values()
       if endpoint["status"] == "partial"
   ]
   ```

3. **Understand configuration needs**:
   ```python
   for mode in features["storage"]["implementations"].values():
       if mode["status"] == "available":
           print(f"To enable: {mode.get('requires', [])}")
   ```

## Health Endpoint Enhancement

Update `/health` to include feature hints:

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "kb",
        "version": "0.2",
        "storage_mode": settings.KB_STORAGE_MODE,
        "multi_user": settings.KB_MULTI_USER_ENABLED,
        "features_endpoint": "/features",  # <- Hint for discovery
        "api_docs": "/docs"
    }
```

## Benefits for External Agents

1. **Zero Documentation Reading** - Feature endpoint tells everything
2. **Implementation Pointers** - Shows which files implement what
3. **Configuration Guide** - Shows exactly what env vars to set
4. **Development Roadmap** - Shows partial vs complete features
5. **No Code Diving** - Surface-level discovery of capabilities

## Implementation Checklist

- [ ] Add `/features` endpoint to `main.py`
- [ ] Update `/health` with feature hints
- [ ] Document in service README
- [ ] Add to API documentation
- [ ] Test with external agent scenario

## Example: External Agent Workflow

```python
# External agent discovering and enabling features
import requests
import os

# 1. Discover what's available
features = requests.get("http://kb-service:8000/features").json()
print("Available storage modes:", features["storage"]["available_modes"])

# 2. Check if database storage is available
db_storage = features["storage"]["implementations"]["database"]
if db_storage["status"] == "available":
    print(f"Database storage ready in {db_storage['file']}")
    print(f"Requires: {db_storage['requires']}")
    
# 3. Enable it
os.environ["KB_STORAGE_MODE"] = "database"
# Restart service...

# 4. Verify it's active
features = requests.get("http://kb-service:8000/features").json()
assert features["storage"]["current_mode"] == "database"
```

This makes the KB service completely self-documenting and discoverable!