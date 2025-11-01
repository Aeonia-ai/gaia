# KB Storage Configuration Guide

**Created**: January 2025  
**Purpose**: How to configure and enable different KB storage backends

## Overview

The KB service supports multiple storage backends that can be selected via environment variables. While Git storage is the default for simplicity, database and hybrid modes are fully implemented and available for production use.

## Verified Working Configurations

### Simple Configuration (Recommended for Getting Started)

**Last Verified**: September 2025
**Status**: ✅ Fully Working with Search

This configuration has been thoroughly tested and provides reliable KB search functionality:

```bash
# Storage Configuration
KB_STORAGE_MODE=git              # Use pure Git storage (not hybrid)
KB_PATH=/kb                      # Container path for KB files

# Multi-User Features (DISABLED)
KB_MULTI_USER_ENABLED=false      # Critical: Must be false for Git mode
KB_USER_ISOLATION=none           # No user isolation
KB_DEFAULT_VISIBILITY=public     # All content is public
KB_SHARING_ENABLED=false         # No sharing features
KB_WORKSPACE_ENABLED=false       # No workspaces
KB_TEAM_ENABLED=false           # No teams

# Git Configuration (for backup/sync)
KB_GIT_AUTO_SYNC=true
KB_GIT_AUTO_CLONE=true
KB_GIT_REPO_URL=https://github.com/your-org/knowledge-base
KB_GIT_AUTH_TOKEN=your_github_token  # For private repos
KB_GIT_BRANCH=main
```

**What This Provides:**
- ✅ Full-text search using ripgrep (fast and reliable)
- ✅ File-based KB operations
- ✅ Git synchronization for backup
- ✅ No database dependencies for search
- ✅ No Redis caching issues

**Known Issues Fixed by This Configuration:**
- Resolves "relation kb_search_index does not exist" errors
- Eliminates Redis async/await compatibility issues
- Bypasses RBAC UUID validation problems
- Ensures ripgrep-based search works correctly

**When to Use:**
- Initial setup and testing
- Single-user or small team deployments
- When troubleshooting search issues
- As a fallback when complex configurations fail

## Storage Modes

### Git Storage (Default)

The default mode uses Git for all KB operations.

**Configuration:**
```bash
# This is the default - no configuration needed
KB_STORAGE_MODE=git  # Optional, this is the default

# Required for Git storage
KB_GIT_REPO_URL=https://github.com/your-org/knowledge-base
KB_GIT_AUTH_TOKEN=your_github_token  # For private repos
KB_PATH=/kb  # Local directory for Git clone
```

**Use Cases:**
- Single-user development
- Simple deployments
- Version control priority
- Familiar Git workflow

**Limitations:**
- No real-time multi-user editing
- Potential merge conflicts
- Slower for large repositories

### Database Storage

PostgreSQL-based storage for multi-user environments.

**Configuration:**
```bash
# Enable database storage
KB_STORAGE_MODE=database

# Database connection (uses main app database by default)
DATABASE_URL=postgresql://user:pass@localhost/gaia_kb

# Optional: separate KB database
KB_DATABASE_URL=postgresql://user:pass@localhost/kb_only
```

**Use Cases:**
- Multi-user teams
- Real-time collaboration
- Fast queries and search
- No merge conflicts

**Features:**
- Optimistic locking prevents conflicts
- Full-text search with PostgreSQL
- User isolation support
- Transaction safety

**Setup:**
```sql
-- Run migrations to create KB tables
-- Located in: migrations/kb_storage_tables.sql
CREATE TABLE kb_documents (
    id UUID PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    content TEXT,
    metadata JSONB,
    version INTEGER DEFAULT 1,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE kb_versions (
    -- Version history table
);
```

### Hybrid Storage

Best of both worlds: PostgreSQL for real-time operations, Git for backup.

**Configuration:**
```bash
# Enable hybrid mode
KB_STORAGE_MODE=hybrid

# Both Git and database configs needed
KB_GIT_REPO_URL=https://github.com/your-org/knowledge-base
KB_GIT_AUTH_TOKEN=your_github_token
DATABASE_URL=postgresql://user:pass@localhost/gaia_kb

# Optional: control Git sync frequency
KB_GIT_SYNC_INTERVAL=300  # Seconds between Git commits (default: 300)
KB_GIT_AUTO_PUSH=true      # Auto-push to remote (default: false)
```

**Use Cases:**
- Production environments
- Disaster recovery needs
- Compliance requirements
- Best performance + reliability

**How It Works:**
1. All reads/writes go to PostgreSQL (fast)
2. Changes queued for Git commit
3. Background process commits to Git periodically
4. Git serves as backup/audit trail

## Multi-User Support (RBAC)

Enable role-based access control for any storage mode.

**Configuration:**
```bash
# Enable multi-user mode
KB_MULTI_USER_ENABLED=true

# Works with any storage mode
KB_STORAGE_MODE=database  # Recommended for multi-user

# Optional: configure permissions
KB_DEFAULT_USER_PERMISSIONS=read,write
KB_ADMIN_EMAILS=admin@company.com,manager@company.com
```

**Features:**
- User isolation by email
- Path-based permissions
- Team workspaces
- Audit logging

**User Namespaces:**
```
/shared/              # Public documents
/team/{team-id}/      # Team workspaces  
/user/{email}/        # Personal workspace
/projects/{project}/  # Project-specific
```

## Configuration Examples

### Development Setup
```bash
# .env.development
KB_STORAGE_MODE=git
KB_GIT_REPO_URL=https://github.com/dev/test-kb
KB_PATH=/tmp/kb-dev
```

### Team Setup
```bash
# .env.team
KB_STORAGE_MODE=database
KB_MULTI_USER_ENABLED=true
DATABASE_URL=postgresql://kb:pass@db.internal/knowledge
KB_DEFAULT_USER_PERMISSIONS=read
```

### Production Setup
```bash
# .env.production
KB_STORAGE_MODE=hybrid
KB_MULTI_USER_ENABLED=true
KB_GIT_REPO_URL=https://github.com/company/knowledge
KB_GIT_AUTH_TOKEN=${SECRET_GITHUB_TOKEN}
KB_GIT_AUTO_PUSH=true
KB_GIT_SYNC_INTERVAL=600
DATABASE_URL=postgresql://kb:pass@db.internal/knowledge
```

## Switching Storage Modes

### From Git to Database

1. Export existing Git content:
```bash
# The KB service provides migration endpoints
curl -X POST http://localhost:8669/admin/export-git-to-db \
  -H "X-Admin-Key: $ADMIN_KEY"
```

2. Update configuration:
```bash
KB_STORAGE_MODE=database
```

3. Restart KB service

### From Database to Hybrid

1. Already have database? Just add Git:
```bash
KB_STORAGE_MODE=hybrid
KB_GIT_REPO_URL=https://github.com/company/kb-backup
KB_GIT_AUTH_TOKEN=token
```

2. Initial Git sync will create repository structure

## Performance Considerations

| Mode | Search Speed | Write Speed | Multi-User | Conflict Resolution |
|------|-------------|-------------|------------|-------------------|
| Git | ~14ms (ripgrep) | Slow (git ops) | ❌ | Manual |
| Database | ~5ms (indexed) | Fast (<10ms) | ✅ | Automatic |
| Hybrid | ~5ms (DB primary) | Fast (<10ms) | ✅ | Automatic |

## Troubleshooting

### KB Search Returns No Results

**Common Causes and Solutions:**

1. **RBAC/Multi-User Issues**
   - Error: "relation kb_search_index does not exist"
   - Solution: Disable multi-user mode and switch to Git storage
   ```bash
   KB_MULTI_USER_ENABLED=false
   KB_STORAGE_MODE=git
   ```

2. **Redis Cache Async/Await Errors**
   - Error: "object NoneType can't be used in 'await' expression"
   - Solution: Temporarily disable cache in kb_cache.py or fix async calls
   ```python
   # In kb_cache.py, change:
   self.enabled = False  # Temporary fix
   ```

3. **Hybrid Mode Database Issues**
   - Error: Search returns 0 results despite content existing
   - Solution: Switch to pure Git mode for reliable ripgrep search
   ```bash
   KB_STORAGE_MODE=git  # Not "hybrid"
   ```

4. **Environment Variables Not Reloading**
   - Issue: Changes to .env not taking effect after restart
   - Solution: Recreate containers, not just restart
   ```bash
   docker compose up -d --force-recreate kb-service
   ```

### Verifying KB Search is Working

1. **Test ripgrep directly in container:**
   ```bash
   docker exec gaia-kb-service-1 rg "search-term" /kb --type md
   ```

2. **Test KB service endpoint:**
   ```bash
   docker exec gaia-kb-service-1 curl -X POST "http://localhost:8000/search" \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"message": "test"}'
   ```

3. **Check via chat API:**
   ```bash
   curl -X POST "http://localhost:8666/api/v1/chat" \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"message": "Search the knowledge base for test", "stream": false}'
   ```

### Storage Mode Not Switching

Check the KB service logs:
```bash
docker logs gaia-kb-service | grep "Storage Manager initialized"
# Should show: "KB Storage Manager initialized with mode: database"
```

### Database Tables Missing

Run migrations:
```bash
docker exec gaia-kb-service python -m app.migrations.kb_storage
```

### Git Sync Failing in Hybrid Mode

Check Git credentials:
```bash
# Test Git access
docker exec gaia-kb-service git ls-remote $KB_GIT_REPO_URL
```

### Multi-User Not Working

Verify configuration:
```bash
# Check if RBAC is enabled
curl http://localhost:8669/health | jq '.config'
# Should show: "multi_user_enabled": true
```

## Related Documentation

- [KB Architecture Guide](../developer/kb-architecture-guide.md) - Technical architecture details
- [Multi-User KB Guide](multi-user-kb-guide.md) - Setting up team workspaces
- [KB Git Sync Guide](kb-git-sync-guide.md) - Git-specific configuration