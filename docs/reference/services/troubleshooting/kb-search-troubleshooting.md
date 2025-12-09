# KB Search Troubleshooting Guide

**Created**: September 2025
**Purpose**: Quick reference for resolving KB search issues

## Quick Fix: Use Simple Configuration

If KB search is not working, switch to the verified simple configuration:

```bash
# In .env file:
KB_STORAGE_MODE=git              # Not "hybrid" or "database"
KB_MULTI_USER_ENABLED=false      # Critical: Must be false
KB_USER_ISOLATION=none
KB_DEFAULT_VISIBILITY=public
KB_SHARING_ENABLED=false
KB_WORKSPACE_ENABLED=false
KB_TEAM_ENABLED=false

# Then recreate the container:
docker compose up -d --force-recreate kb-service
```

## Common Issues and Solutions

### Issue 1: "relation kb_search_index does not exist"

**Cause**: Multi-user mode trying to use database tables that don't exist or aren't properly initialized.

**Solution**:
1. Disable multi-user mode: `KB_MULTI_USER_ENABLED=false`
2. Switch to Git storage: `KB_STORAGE_MODE=git`
3. Recreate container: `docker compose up -d --force-recreate kb-service`

### Issue 2: Search Returns 0 Results Despite Content Existing

**Cause**: Multiple possible causes:
- Hybrid mode using database search instead of ripgrep
- Cache returning empty results
- RBAC filtering out all results

**Diagnosis Steps**:
```bash
# 1. Verify files exist in container
docker exec gaia-kb-service-1 find /kb -name "*.md"

# 2. Test ripgrep directly
docker exec gaia-kb-service-1 rg "your-search-term" /kb --type md

# 3. Test KB service endpoint
docker exec gaia-kb-service-1 curl -X POST "http://localhost:8000/search" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "your-search-term"}'
```

**Solution**: Use Git storage mode with RBAC disabled (see Quick Fix above)

### Issue 3: Redis Cache Errors

**Symptoms**:
- "object NoneType can't be used in 'await' expression"
- "object bool can't be used in 'await' expression"

**Cause**: KB cache trying to await synchronous Redis methods

**Solution**:
1. Temporarily disable cache by editing `/app/services/kb/kb_cache.py`:
   ```python
   self.enabled = False  # In __init__ method
   ```
2. Or fix the async/await calls:
   ```python
   # Change from:
   data = await redis_client.get(key)
   # To:
   data = redis_client.get(key)
   ```

### Issue 4: Environment Variables Not Taking Effect

**Symptom**: Changed .env but KB service still using old configuration

**Cause**: Docker containers don't reload environment variables on restart

**Solution**: Force recreate the container:
```bash
docker compose up -d --force-recreate kb-service
```

## Testing Chain

Test each component in order to isolate issues:

### 1. Test Files Exist
```bash
docker exec gaia-kb-service-1 ls -la /kb
```
Expected: Should see your KB files

### 2. Test Ripgrep
```bash
docker exec gaia-kb-service-1 rg "test" /kb --type md -i
```
Expected: Should find matches in markdown files

### 3. Test KB MCP Server
```python
docker exec gaia-kb-service-1 python -c "
import asyncio
from app.services.kb.kb_mcp_server import KBMCPServer
async def test():
    kb = KBMCPServer('/kb')
    result = await kb.search_kb('test', limit=5)
    print(f'Found {result.get(\"total_results\", 0)} results')
asyncio.run(test())
"
```
Expected: Should report number of results found

### 4. Test KB Service Endpoint
```bash
docker exec gaia-kb-service-1 curl -X POST "http://localhost:8000/search" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```
Expected: Should return JSON with search results

### 5. Test Chat Service Integration
```bash
curl -X POST "http://localhost:8666/api/v1/chat" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Search the knowledge base for test", "stream": false}'
```
Expected: Should return chat response with KB search results

## Architecture Overview

Understanding the search flow helps with troubleshooting:

```
Unity/Client
    ↓
Gateway (port 8666)
    ↓
Chat Service
    ↓ (uses KB tools)
KB Service (/search endpoint)
    ↓ (based on storage mode)
    ├── Git Mode → KB MCP Server → ripgrep (files)
    ├── Database Mode → KB Database Storage → PostgreSQL
    └── Hybrid Mode → KB Hybrid Storage → PostgreSQL + Git backup
```

**Key Points**:
- Git mode uses ripgrep directly on files (most reliable)
- Database/Hybrid modes require proper table initialization
- RBAC adds complexity and can filter out results
- Cache can cause stale or empty results

## Logs to Check

```bash
# KB Service logs
docker logs gaia-kb-service-1 2>&1 | tail -50

# Look for:
# - "Storage Manager initialized with mode: X"
# - "Single-user KB mode enabled" (good for Git mode)
# - "Multi-user KB mode enabled with RBAC" (requires database)
# - Error messages about missing tables or relations

# Chat Service logs
docker logs gaia-chat-service-1 2>&1 | grep -i "kb\|knowledge"

# Gateway logs
docker logs gaia-gateway-1 2>&1 | grep -i "kb\|401\|403\|500"
```

## Emergency Recovery

If nothing works, reset to known-good state:

```bash
# 1. Stop services
docker compose down

# 2. Reset .env to simple configuration
cat > .env.kb.simple << 'EOF'
KB_STORAGE_MODE=git
KB_MULTI_USER_ENABLED=false
KB_PATH=/kb
KB_GIT_AUTO_CLONE=true
KB_GIT_REPO_URL=https://github.com/your-org/kb
EOF

# 3. Merge with main .env
grep -v "^KB_" .env > .env.tmp
cat .env.kb.simple >> .env.tmp
mv .env.tmp .env

# 4. Start fresh
docker compose up -d

# 5. Verify
./scripts/test_kb_search.py
```

## Related Documentation

- [KB Storage Configuration Guide](../guides/kb-storage-configuration.md) - Detailed configuration options
- [KB Architecture Guide](../developer/kb-architecture-guide.md) - Technical architecture
- [KB Git Sync Guide](../guides/kb-git-sync-guide.md) - Git-specific setup