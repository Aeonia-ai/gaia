# Deployment Guide

The complete guide for deploying the GAIA platform to local, dev, staging, and production environments.

## 🚀 Quick Start (90% of use cases)

### ⚠️ CRITICAL: Always Use nohup (Claude Code has 2-minute timeout!)

**Deployments take 5-20 minutes. You MUST use nohup or the command will fail:**

```bash
# Deploy to dev - THE CORRECT WAY (ALWAYS USE THIS PATTERN)
nohup ./scripts/deploy.sh --env dev --services all --remote-only --rebuild > deploy.log 2>&1 &
tail -f deploy.log

# Deploy to production - ALSO USE NOHUP
nohup ./scripts/deploy.sh --env production --services all --remote-only --rebuild > deploy.log 2>&1 &
tail -f deploy.log

# Deploy single service (e.g., after streaming fix) - YES, STILL USE NOHUP
nohup ./scripts/deploy.sh --env dev --services chat --remote-only --rebuild > deploy.log 2>&1 &
tail -f deploy.log

# Check if deployment is still running
ps aux | grep deploy.sh

# Rollback if something goes wrong
fly releases rollback -a gaia-gateway-dev
```

**Why nohup?** Claude Code (and most terminals) timeout after 2 minutes. Deployments take 5-20 minutes. Without nohup, your deployment WILL be killed mid-process.

**Docker Hub Issues?** Always use `--remote-only` flag or authenticate:
```bash
docker login -u ops@aeonia.ai -p what-is-that-called-again?
```

## 📋 Deployment Workflow

### 1. Test Locally First
```bash
# Start services
docker compose up -d

# Run tests (use async runner to avoid timeouts)
./scripts/pytest-for-claude.sh tests/ -v

# Check health
./scripts/test.sh --local health
```

### 2. Deploy to Development
```bash
# Deploy with remote builder (avoids Docker Hub limits)
./scripts/deploy.sh --env dev --services all --remote-only

# Validate deployment
./scripts/validate-deployment-env.sh dev

# Check status
fly status -a gaia-gateway-dev
fly status -a gaia-chat-dev
```

### 3. Validate
```bash
# Health check
curl https://gaia-gateway-dev.fly.dev/health | jq '.'

# Test core functionality
./scripts/test.sh --dev all
```

### 4. Deploy to Production
```bash
# Only after dev validation passes
./scripts/deploy.sh --env production --services all --remote-only

# Monitor deployment
fly logs -a gaia-gateway-production --tail
```

## 🔧 Service Management

### Deploy Individual Services
```bash
# Just the chat service (after streaming fix, for example)
./scripts/deploy.sh --env dev --services chat --remote-only --rebuild

# Multiple specific services
./scripts/deploy.sh --env dev --services "gateway chat" --remote-only
```

### Service URLs
- **Local**: `http://localhost:8666` (gateway), `:8001` (auth), `:8002` (chat)
- **Dev**: `https://gaia-{service}-dev.fly.dev`
- **Production**: `https://gaia-{service}-production.fly.dev`

⚠️ **Important**: Never use `.internal` DNS - it's unreliable. Use public URLs for inter-service communication in Fly.io.

## 🚨 Troubleshooting

### Docker Hub Rate Limit (429)
**Error**: "toomanyrequests: You have reached your pull rate limit"

**Solutions**:
1. Use remote builds: `--remote-only` flag
2. Authenticate Docker Hub: `docker login -u ops@aeonia.ai`
3. Wait 6 hours (100 pulls/6hrs for anonymous)

### Deployment Hangs
**Symptom**: Deploy process stuck at "Monitoring deployment"

**Fix**:
```bash
# Check logs
fly logs -a gaia-{service}-{env} --tail

# Usually Redis URL issue - check secrets
fly secrets list -a gaia-{service}-{env}
```

### Service Not Responding
**Symptom**: Health checks fail after deployment

**Fix**:
```bash
# Check machine status
fly machine list -a gaia-{service}-{env}

# Restart if needed
fly machine restart {machine-id} -a gaia-{service}-{env}

# Check secrets are set
fly secrets list -a gaia-{service}-{env}
```

### Rollback Failed Deployment
```bash
# View recent releases
fly releases list -a gaia-{service}-{env}

# Rollback to previous version
fly releases rollback -a gaia-{service}-{env}

# Or rollback to specific version
fly releases rollback v23 -a gaia-{service}-{env}
```

## 🔑 Secret Management

### Set Secrets for a Service
```bash
# Single secret
fly secrets set ANTHROPIC_API_KEY="sk-ant-..." -a gaia-chat-dev

# Multiple secrets
fly secrets set -a gaia-auth-dev \
  SUPABASE_URL="https://your-project.supabase.co" \
  SUPABASE_ANON_KEY="eyJ..." \
  SUPABASE_JWT_SECRET="your-secret"
```

### Sync Secrets from .env
```bash
# Sync all secrets to all services
./scripts/sync-secrets.sh --env dev --services all

# Validate secrets are correct
./scripts/validate-secrets.sh --env dev
```

## 📊 Validation & Monitoring

### Health Checks
```bash
# Local
curl http://localhost:8666/health

# Remote
curl https://gaia-gateway-dev.fly.dev/health
```

### Comprehensive Validation
```bash
# Full validation with auto-fix
./scripts/validate-deployment-env.sh dev --fix

# Check specific service
fly status -a gaia-chat-dev
fly logs -a gaia-chat-dev --tail
```

## 🏗️ Initial Setup (First Time Only)

### 1. Create Fly.io Apps
```bash
# Create all apps for an environment
for service in gateway auth chat kb asset web; do
  fly apps create gaia-${service}-dev
done
```

### 2. Create Volumes (if needed)
```bash
# For KB service (Git repository storage)
fly volumes create gaia_kb_data --size 10 -a gaia-kb-dev --region lax
```

### 3. Initialize Database
```bash
# Local
./scripts/init-database-portable.sh --env local

# Remote (using Fly.io Postgres)
fly postgres create --name gaia-db-dev --region lax
```

## 🎯 Best Practices

1. **Always test locally first** - Hot-reload makes this fast
2. **Use --remote-only for cloud deploys** - Avoids Docker Hub limits
3. **Deploy to dev before production** - Catch issues early
4. **Check health after deploy** - Ensure services started correctly
5. **Keep secrets in sync** - Use validation scripts
6. **Document what you deploy** - Update CHANGELOG.md

## 📝 Environment Variables

### Critical for All Services
```env
ENVIRONMENT={local|dev|staging|production}
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...
```

### Service-Specific
- **Auth**: `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`
- **Chat**: AI provider keys (OpenAI, Anthropic, etc.)
- **KB**: `GIT_REPO_URL`, `GIT_BRANCH`
- **Gateway**: Service URLs for routing

## 🔄 Hot Reload Development

**Code changes apply instantly** - no restart needed for:
- Python files (.py)
- Templates (.html)
- Static files (.js, .css)

**Restart required for**:
- New dependencies (requirements.txt)
- Docker configuration changes
- Environment variable changes

## 📚 Related Documentation

- [Fly.io Setup](./flyio-setup.md) - Platform-specific configuration
- [Supabase Setup](./supabase-setup.md) - Auth service configuration
- [Deployment Reference](./deployment-reference.md) - Quick command lookup

---

*Last updated: 2025-10-01 | For issues, check logs first: `fly logs -a {app-name}`*