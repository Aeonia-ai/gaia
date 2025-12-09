# KB Git Sync Guide



This guide covers the Git synchronization functionality for the Knowledge Base (KB) service, enabling automatic sync between your local Git repository and the KB service.

## Overview

The KB Git sync system allows you to:
- **Edit KB files** in your Git repository using your preferred tools (Obsidian, VS Code, etc.)
- **Push changes via Git** to your repository (GitHub, GitLab, etc.)
- **Automatic repository cloning** on every container startup
- **Container-only storage** for true local-remote parity
- **Access latest content** through AI agents after container restart

## Quick Setup

### 1. Configure Your Repository

Add to your `.env` file:

```bash
# Your KB Git repository
KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git
KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Your GitHub PAT
KB_GIT_AUTO_CLONE=true
KB_STORAGE_MODE=hybrid
```

### 2. Start the KB Service

```bash
# No need to create directories - container handles everything
docker compose up kb-service

# The service will automatically:
# 1. Create /kb directory inside container
# 2. Clone your repository from GitHub
# 3. Make content available for search/access
```

### 3. Verify Repository Cloned

```bash
# Check KB contents inside container
docker compose exec kb-service ls -la /kb/

# View clone logs
docker compose logs kb-service | grep "Successfully cloned"

# You should see your repository files cloned to /kb
```

### 4. Test Git Functionality

```bash
# Verify Git is installed
docker compose exec kb-service git --version
# Output: git version 2.39.5

# Test authentication (optional)
docker compose exec kb-service git -C /kb remote -v
```

## Configuration Reference

### Environment Variables

Add these to your `.env` file:

```bash
# Required: Your KB Git repository
KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git

# Optional: Authentication for private repos
KB_GIT_AUTH_TOKEN=your_github_personal_access_token

# Optional: Sync configuration
KB_GIT_AUTO_SYNC=true          # Enable automatic sync
KB_SYNC_INTERVAL=3600          # Sync every hour (seconds)
KB_GIT_REMOTE=origin           # Git remote name
KB_GIT_BRANCH=main             # Branch to sync from
KB_GIT_AUTO_CLONE=true         # Auto-clone repo on startup

# Storage mode for Git sync
KB_STORAGE_MODE=hybrid         # Recommended for Git sync
```

### GitHub Personal Access Token

For private repositories, you need a GitHub Personal Access Token:

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo` (for private repos) or `public_repo` (for public repos)
4. Copy the token and set `KB_GIT_AUTH_TOKEN` in `.env`

## Container-Only Storage Architecture

The KB service uses **container-only storage** for local-remote parity:

```yaml
kb-service:
  volumes:
    - ./app:/app/app
    # NO local KB mount - container storage only
```

This ensures:
- **Ephemeral storage** - KB data exists only at `/kb` inside container
- **Fresh clone on startup** - Every new container gets latest from Git
- **Local-remote parity** - Local Docker behaves exactly like production
- **No false positives** - If it works locally, it works in production

## Daily Workflow

### Your Workflow
```bash
# 1. Edit KB files in your local Git repository
cd ~/your-obsidian-vault
vim gaia/specs/api-design.md  # Or use Obsidian, VS Code, etc.

# 2. Commit and push changes to GitHub
git add .
git commit -m "Update API design specs"
git push origin main

# 3. Restart KB service to get latest changes
docker compose restart kb-service

# The service will clone fresh with your latest changes
```

### Manual Sync Commands

```bash
# Sync from Git to KB service
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  http://kb-service:8000/sync/from-git

# Check sync status
curl -H "X-API-Key: $API_KEY" \
  http://kb-service:8000/sync/status

# Sync from KB service to Git (if you edited via API)
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"commit_message": "Update from KB service"}' \
  http://kb-service:8000/sync/to-git
```

## Storage Modes

### Git Mode (Default)
- **File-based storage** with Git version control
- **Direct file access** for editing
- **Good for**: Single-user scenarios, local development

### Database Mode
- **PostgreSQL storage** for fast search and collaboration
- **No Git integration** (database only)
- **Good for**: Multi-user collaboration, fast queries

### Hybrid Mode (Recommended)
- **PostgreSQL primary** + **Git backup**
- **Best of both worlds**: Fast database + Git version control
- **Automatic sync** between database and Git
- **Good for**: Production deployments, team collaboration with Git workflow

## API Endpoints

### GET /sync/status
Get current synchronization status.

**Response:**
```json
{
  "success": true,
  "git": {
    "current_commit": "abc123...",
    "remote_commit": "def456...",
    "last_sync_commit": "abc123...",
    "needs_sync_from_git": false,
    "git_ahead": false
  },
  "sync": {
    "auto_sync_enabled": true,
    "sync_in_progress": false
  }
}
```

### POST /sync/from-git
Sync content from Git repository to KB service.

**Parameters:**
- `force` (query, optional): Force sync even if no new commits

**Response:**
```json
{
  "success": true,
  "action": "sync_from_git",
  "stats": {
    "imported": 15,
    "errors": 0,
    "skipped": 2
  },
  "from_commit": "abc123...",
  "to_commit": "def456...",
  "duration_seconds": 2.5
}
```

### POST /sync/to-git
Sync content from KB service to Git repository.

**Body:**
```json
{
  "commit_message": "Update from KB service"
}
```

**Response:**
```json
{
  "success": true,
  "action": "sync_to_git",
  "stats": {
    "exported": 12,
    "errors": 0
  },
  "commit": "ghi789...",
  "pushed": true
}
```

## Troubleshooting

### Common Issues

#### 1. "Git sync not available"
**Cause**: KB service not properly initialized with Git support
**Solution**: 
- Ensure Git is installed: `docker compose exec kb-service git --version`
- If not, rebuild container: `docker compose build kb-service`
- Verify repository cloned: `ls -la ./kb-data/.git`
- Check logs: `docker compose logs kb-service`

#### 2. "exec: git: executable file not found"
**Cause**: Git not installed in container
**Solution**: 
```bash
# Rebuild KB service with Git
docker compose build kb-service --no-cache
docker compose up kb-service
```

#### 3. "mounts denied: The path /kb is not shared"
**Cause**: Docker volume mount issue
**Solution**: 
- Create local directory: `mkdir -p ./kb-data`
- Update docker compose.yml to use `./kb-data:/kb:rw`
- Restart Docker Desktop if on macOS

#### 4. "Repository not found" or Authentication failed
**Cause**: Invalid repository URL or authentication token
**Solution**: 
- Verify repository URL: `echo $KB_GIT_REPO_URL`
- Test token manually:
  ```bash
  curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
  ```
- For private repos, ensure token has `repo` scope
- Token format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### 5. Storage mode issues
**Cause**: Hybrid mode requires database tables
**Solution**: 
- Verify tables exist: 
  ```bash
  docker compose exec db psql -U postgres -d llm_platform -c "\dt kb_*"
  ```
- If missing, apply migration: 
  ```bash
  docker compose exec db psql -U postgres -d llm_platform < migrations/003_create_kb_tables.sql
  ```
- Or use `KB_STORAGE_MODE=git` for simpler file-based mode

### Testing and Debugging

```bash
# Test all KB functionality
./scripts/test-kb-git-sync.sh

# Check KB service logs
docker compose logs kb-service --tail=50

# Test specific endpoints
curl -H "X-API-Key: $API_KEY" http://kb-service:8000/health
curl -H "X-API-Key: $API_KEY" http://kb-service:8000/sync/status

# Test search to verify content is accessible
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "gaia architecture"}' \
  http://kb-service:8000/search
```

### Directory Structure

When Git sync is enabled, the KB service expects your repository structure like:

```
your-kb-repo/
├── gaia/
│   ├── specs/
│   │   ├── api-design.md
│   │   └── architecture.md
│   └── implementation/
│       └── status.md
├── influences/
│   ├── consciousness.md
│   └── philosophy.md
└── README.md
```

All `.md` files will be indexed and searchable through the KB service.

## Performance Notes

- **Auto-sync interval**: Default 1 hour, configurable via `KB_SYNC_INTERVAL`
- **Batch operations**: Multiple file changes are processed efficiently
- **Incremental sync**: Only changed files are processed
- **Background processing**: Sync doesn't block API requests
- **Caching**: Sync status is cached in Redis for performance

## Integration with AI Agents

Once Git sync is configured:

1. **AI agents automatically access latest content** from your repository
2. **MCP tools** work with synced KB content
3. **Search results** include your latest committed changes
4. **Context loading** uses the most recent synchronized content

The sync happens transparently - AI agents always see your latest knowledge base content without any additional configuration.

## Security Considerations

- **Personal Access Tokens**: Store GitHub tokens securely in environment variables
- **Private repositories**: Tokens are needed for authentication
- **Network access**: KB service needs outbound access to Git repositories
- **API keys**: Use strong API keys for KB service endpoints
- **File permissions**: Ensure proper permissions on mounted KB directories

## Migration from File-Only Mode

If you're currently using file-based KB storage:

1. **Backup current KB**: `cp -r /path/to/kb /path/to/kb-backup`
2. **Initialize Git repository** in your KB directory
3. **Push to remote repository**
4. **Run setup script**: `./scripts/setup-kb-git-repo.sh`
5. **Test sync**: `./scripts/test-kb-git-sync.sh`
6. **Switch to hybrid mode** for best performance

This migration is non-destructive and can be reversed if needed.