# KB Service Deployment Checklist

This checklist ensures successful deployment of the Knowledge Base (KB) service to staging and production environments.

## Pre-Deployment Requirements

### 1. GitHub Personal Access Token
- [ ] Create GitHub PAT with `repo` scope (for private repos) or `public_repo` (for public)
- [ ] Token created at: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- [ ] Token saved securely for deployment

### 2. Configuration Files
- [ ] `fly.kb.staging.toml` exists (created)
- [ ] `fly.kb.production.toml` exists (created)
- [ ] Verify volume names match environment:
  - Dev: `gaia_kb_dev_3gb`
  - Staging: `gaia_kb_staging_3gb`
  - Production: `gaia_kb_production_3gb`

## Deployment Steps

### Step 1: Create Persistent Volume (First-time only)

**Option A: Using automated script (recommended)**
```bash
# For staging
./scripts/create-kb-volume.sh --env staging

# For production (with larger volume)
./scripts/create-kb-volume.sh --env production --size 5
```

**Option B: Manual creation**
```bash
# For staging
fly volumes create gaia_kb_staging_3gb \
  --region lax \
  --size 3 \
  -a gaia-kb-staging

# For production
fly volumes create gaia_kb_production_3gb \
  --region lax \
  --size 3 \
  -a gaia-kb-production
```

### Step 2: Set Secrets

```bash
# For staging
fly secrets set \
  KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git \
  KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  -a gaia-kb-staging

# For production
fly secrets set \
  KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git \
  KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  -a gaia-kb-production
```

### Step 3: Deploy Service

```bash
# Deploy to staging
./scripts/deploy.sh --env staging --services kb --remote-only

# Deploy to production
./scripts/deploy.sh --env production --services kb --remote-only
```

### Step 4: Trigger Initial Clone (If Auto-Clone Fails)

If the service starts but Git clone doesn't trigger automatically:

```bash
# Trigger manual clone for staging
curl -X POST https://gaia-kb-staging.fly.dev/trigger-clone

# Trigger manual clone for production
curl -X POST https://gaia-kb-production.fly.dev/trigger-clone
```

### Step 5: Verify Deployment

```bash
# Check health status
curl https://gaia-kb-staging.fly.dev/health | jq

# Expected response should show:
# - "status": "healthy"
# - "git_initialized": true
# - "file_count": 1074+ (or current repo size)

# Check Git sync status (requires API key)
curl -H "X-API-Key: YOUR_API_KEY" \
  https://gaia-kb-staging.fly.dev/sync/status | jq
```

## Post-Deployment Verification

### 1. Service Health Checks
- [ ] Health endpoint returns `"status": "healthy"`
- [ ] Git repository is cloned (`"git_initialized": true`)
- [ ] File count matches expected repository size

### 2. Functional Tests

**Option A: Using automated test script (recommended)**
```bash
# Test staging deployment
./scripts/test-kb-remote.sh --env staging --api-key YOUR_API_KEY

# Test production deployment  
./scripts/test-kb-remote.sh --env production --api-key YOUR_API_KEY
```

**Option B: Manual testing**
```bash
# Test search functionality
curl -X POST https://gaia-kb-staging.fly.dev/api/v0.2/kb/search \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Aeonia"}' | jq

# Test file reading
curl -X POST https://gaia-kb-staging.fly.dev/api/v0.2/kb/read \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "README.md"}' | jq
```

### 3. Monitor Logs
```bash
# View deployment logs
fly logs -a gaia-kb-staging

# Look for:
# - "Cloning repository..."
# - "Successfully cloned repository"
# - "Git sync monitoring started"
```

## Troubleshooting

### Clone Not Starting
1. Check secrets are set correctly:
   ```bash
   fly secrets list -a gaia-kb-staging
   ```
2. Manually trigger clone:
   ```bash
   curl -X POST https://gaia-kb-staging.fly.dev/trigger-clone
   ```
3. Check logs for errors:
   ```bash
   fly logs -a gaia-kb-staging | grep -E "(ERROR|WARN|Clone)"
   ```

### Volume Issues
1. Verify volume exists:
   ```bash
   fly volumes list -a gaia-kb-staging
   ```
2. Check volume is mounted:
   ```bash
   fly ssh console -a gaia-kb-staging -C "df -h /kb"
   ```

### Git Authentication Failures
1. Verify token has correct permissions
2. Test token locally:
   ```bash
   git clone https://YOUR_TOKEN@github.com/Aeonia-ai/Obsidian-Vault.git test-clone
   ```
3. Check token format in secrets (no quotes or extra characters)

## Environment-Specific Configurations

### Staging
- **App Name**: `gaia-kb-staging`
- **Volume**: `gaia_kb_staging_3gb`
- **VM**: 1 CPU, 512MB RAM
- **Concurrency**: 25 connections

### Production
- **App Name**: `gaia-kb-production`
- **Volume**: `gaia_kb_production_3gb`
- **VM**: 2 CPUs, 1024MB RAM
- **Concurrency**: 50 connections
- **Consider**: Multi-region deployment for HA

## Security Considerations

1. **Token Rotation**: Rotate GitHub PAT every 90 days
2. **Minimal Permissions**: Use `public_repo` scope if repository is public
3. **Audit Access**: Review who has access to KB secrets in Fly.io
4. **RBAC**: Ensure proper user permissions are configured

## Monitoring & Maintenance

1. **Regular Sync Checks**: Monitor `/sync/status` endpoint
2. **Volume Usage**: Monitor disk usage with `fly ssh console -C "df -h /kb"`
3. **Performance**: Track search and read operation latencies
4. **Updates**: Pull latest changes with manual sync if auto-sync is disabled

## Related Documentation

- [KB Remote Deployment Auth Guide](kb-remote-deployment-auth.md)
- [KB Git Sync Guide](kb-git-sync-guide.md)
- [Deferred Initialization Pattern](deferred-initialization-pattern.md)
- [Smart Deployment Script](../scripts/deploy.sh)