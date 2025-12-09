# Deployment Reference



Quick lookup for commands and troubleshooting. For detailed explanations, see [deployment-guide.md](./deployment-guide.md).

## 🚀 Commands

### Deploy (ALWAYS USE NOHUP!)
```bash
# ⚠️ CRITICAL: Deployments take 5-20 minutes. MUST use nohup or they'll timeout!

# CORRECT deployment pattern (ALWAYS USE THIS)
nohup ./scripts/deploy.sh --env {env} --services {services} --remote-only --rebuild > deploy.log 2>&1 &
tail -f deploy.log

# Flags explained:
--remote-only    # Use Fly.io builders (avoids Docker Hub limits) - ALWAYS USE
--rebuild        # Force rebuild even if no changes - ALWAYS USE for code changes
--dry-run        # Preview without deploying
--region lax     # Specify region

# Real examples (ALL WITH NOHUP)
nohup ./scripts/deploy.sh --env dev --services all --remote-only --rebuild > deploy.log 2>&1 &
nohup ./scripts/deploy.sh --env dev --services chat --remote-only --rebuild > deploy.log 2>&1 &
nohup ./scripts/deploy.sh --env production --services "gateway auth" --remote-only --rebuild > deploy.log 2>&1 &
```

### Rollback
```bash
fly releases rollback -a {app-name}              # Rollback to previous
fly releases rollback v{number} -a {app-name}    # Rollback to specific
fly releases list -a {app-name}                  # View release history
```

### Status
```bash
fly status -a {app-name}                         # Service status
fly machine list -a {app-name}                   # List machines
fly machine status {machine-id} -a {app-name}    # Machine details
./scripts/manage.sh status dev                   # All services status
```

### Logs
```bash
fly logs -a {app-name}                           # View logs
fly logs -a {app-name} --tail                    # Follow logs
fly logs -a {app-name} --tail --region lax       # Region-specific
docker compose logs -f {service}                 # Local logs
```

### Secrets
```bash
fly secrets list -a {app-name}                   # List secrets
fly secrets set KEY="value" -a {app-name}        # Set single secret
fly secrets unset KEY -a {app-name}              # Remove secret
./scripts/sync-secrets.sh --env dev --services all  # Sync from .env
./scripts/validate-secrets.sh --env dev          # Validate secrets
```

## 🚨 Troubleshooting

| Problem | Symptom | Solution |
|---------|---------|----------|
| **Docker Hub 429** | "toomanyrequests: You have reached your pull rate limit" | Use `--remote-only` or `docker login -u ops@aeonia.ai` |
| **Deploy hangs** | Stuck at "Monitoring deployment" | Check Redis URL: `fly secrets list -a {app-name}` |
| **Service unreachable** | Connection refused/timeout | Use public URLs (`https://gaia-{service}-{env}.fly.dev`), not `.internal` |
| **Auth failures** | "Invalid API key" errors | Update Supabase secrets: `fly secrets set SUPABASE_ANON_KEY="..." -a {app-name}` |
| **Health check fails** | Service unhealthy after deploy | Check logs: `fly logs -a {app-name} --tail` |
| **Memory issues** | "Out of memory" in logs | Scale up: `fly scale memory 512 -a {app-name}` |
| **DNS resolution** | Can't resolve .internal domains | Switch to public URLs in service config |
| **Slow deploys** | Deploy takes >10 minutes | Use `--remote-only` to avoid local builds |
| **Version mismatch** | "Invalid version" errors | Rollback: `fly releases rollback -a {app-name}` |
| **Secret not found** | "Missing required secret" | Set secret: `fly secrets set KEY="value" -a {app-name}` |

## 🏥 Health Endpoints

### Local
```bash
curl http://localhost:8666/health              # Gateway
curl http://localhost:8001/health              # Auth
curl http://localhost:8002/health              # Chat
curl http://localhost:8003/health              # KB
curl http://localhost:8004/health              # Asset
curl http://localhost:8005/health              # Web
```

### Remote
```bash
curl https://gaia-gateway-{env}.fly.dev/health
curl https://gaia-auth-{env}.fly.dev/health
curl https://gaia-chat-{env}.fly.dev/health
curl https://gaia-kb-{env}.fly.dev/health
curl https://gaia-asset-{env}.fly.dev/health
curl https://gaia-web-{env}.fly.dev/health
```

## 🔧 Service Management

### Restart
```bash
# Local
docker compose restart {service}
docker compose down && docker compose up -d

# Remote
fly machine restart {machine-id} -a {app-name}
fly apps restart {app-name}  # Restart all machines
```

### Scale
```bash
fly scale count 2 -a {app-name}                # Horizontal scale
fly scale memory 512 -a {app-name}             # Vertical scale (MB)
fly scale vm shared-cpu-2x -a {app-name}       # Change VM size
```

### SSH Access
```bash
fly ssh console -a {app-name}                  # SSH into container
fly ssh console -a {app-name} -C "command"     # Run command
```

## 📊 Validation Scripts

```bash
# Validate deployment
./scripts/validate-deployment-env.sh {env}
./scripts/validate-deployment-env.sh {env} --fix    # Auto-fix issues

# Test functionality
./scripts/test.sh --{env} all                  # Full test suite
./scripts/test.sh --{env} health               # Just health checks
./scripts/test.sh --{env} chat "test message"  # Test chat

# Check test progress
./scripts/check-test-progress.sh
```

## 🔑 Environment Variables

### Required for All Services
```bash
ENVIRONMENT={local|dev|staging|production}
SUPABASE_URL=https://...supabase.co
SUPABASE_ANON_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...
```

### Service URLs (Docker)
```bash
# Local/Docker
GATEWAY_URL=http://gateway:8000
AUTH_SERVICE_URL=http://auth-service:8000
CHAT_SERVICE_URL=http://chat-service:8000

# Remote/Fly.io
AUTH_SERVICE_URL=https://gaia-auth-{env}.fly.dev
CHAT_SERVICE_URL=https://gaia-chat-{env}.fly.dev
```

## 📁 File Locations

| File | Purpose |
|------|---------|
| `.env` | Local environment variables |
| `docker-compose.yml` | Local service configuration |
| `fly.{service}.{env}.toml` | Fly.io deployment config |
| `scripts/deploy.sh` | Main deployment script |
| `scripts/validate-deployment-env.sh` | Validation script |
| `scripts/sync-secrets.sh` | Secret synchronization |

## 🎯 Quick Fixes

### Fix Streaming Issues
```bash
# Deploy just the chat service with streaming fix
./scripts/deploy.sh --env dev --services chat --remote-only --rebuild
```

### Fix Auth Issues
```bash
# Update auth secrets and restart
fly secrets set -a gaia-auth-dev \
  SUPABASE_SERVICE_KEY="eyJ..." \
  SUPABASE_JWT_SECRET="..."
fly apps restart gaia-auth-dev
```

### Clear Cache
```bash
# Local
docker compose down
docker volume prune -f
docker compose up -d

# Remote (Redis)
fly ssh console -a gaia-gateway-dev -C "redis-cli FLUSHALL"
```

## 🔄 CI/CD Pipeline

```bash
# GitHub Actions workflow triggers
git push origin main           # Deploy to dev
git tag v1.0.0 && git push --tags  # Deploy to production

# Manual trigger
gh workflow run deploy.yml -f environment=dev
```

## 📞 Support Contacts

- **Fly.io Status**: https://status.fly.io
- **Supabase Status**: https://status.supabase.com
- **Docker Hub Status**: https://status.docker.com
- **Logs**: Check `fly logs -a {app-name}` first!

---

*Quick reference for GAIA platform deployment. Full guide: [deployment-guide.md](./deployment-guide.md)*