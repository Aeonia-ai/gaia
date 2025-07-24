# Deployment Best Practices

This document outlines the deployment strategy for achieving local-remote parity in the Gaia Platform.

## Overview

The goal is to ensure that what works locally will work identically in remote environments (dev, staging, production). This eliminates "works on my machine" issues and increases deployment confidence.

## Key Principles

### 1. Configuration Consistency
- All services use the same environment variables locally and remotely
- Secrets are synchronized across all services
- Service discovery uses consistent patterns (internal DNS)

### 2. Secret Management
- Local: All services read from shared `.env` file
- Remote: Secrets are synced to all services using `sync-secrets.sh`

### 3. Smart Service Discovery (NEW)
- **Smart URL Generation**: Services auto-discover each other based on environment and cloud provider
- **Implementation**: `app/shared/config.py` - `get_service_url()` function
- **Multi-Cloud Support**: Same code works on Fly.io, AWS, GCP, Azure
- **Local Development**: Automatic localhost mapping with port detection
- **Configuration**: Only requires `ENVIRONMENT` and `CLOUD_PROVIDER` environment variables

**Pattern**:
```python
# Auto-generates appropriate URLs:
# Local: http://localhost:8001
# Fly.io: https://gaia-auth-dev.fly.dev  
# AWS: https://gaia-auth-dev.us-west-2.elb.amazonaws.com
auth_url = get_service_url("auth")
```

### 3.1 Service Communication (UPDATED)
- **NEVER use Fly.io internal DNS** (`.internal`) - it's unreliable and causes 503 errors
- **Always use public URLs** for inter-service communication on Fly.io
- **Smart discovery handles this automatically** - no manual URL configuration needed

### 4. Testing Parity
- Same test suite runs locally and remotely
- Results are compared to ensure identical behavior
- Automated parity checking before production deployment

## Service-Specific Deployment Guides

### Knowledge Base (KB) Service
The KB service requires special deployment steps due to Git repository cloning and persistent volumes:
- See [KB Deployment Checklist](kb-deployment-checklist.md) for complete deployment guide
- Requires GitHub Personal Access Token for repository access
- Uses persistent volumes to avoid re-cloning on container restarts
- Supports manual clone trigger if auto-clone fails

## NEW Service Deployment Workflow

### 1. Pre-Deployment Setup
```bash
# Ensure all secrets are in .env
cp .env.example .env
# Edit .env with your actual values

# Create .dockerignore to prevent build hangs
cat > .dockerignore << EOF
.venv/
venv/
ENV/
*.log
.git/
EOF
```

### 2. Smart Service Configuration
Create `fly.service.env.toml`:
```toml
app = "gaia-service-env"
primary_region = "lax"

[env]
  # Smart service discovery - NO hardcoded URLs needed!
  ENVIRONMENT = "dev"
  CLOUD_PROVIDER = "fly"
  SERVICE_NAME = "service"
  SERVICE_PORT = "8000"
  
  # NATS (if needed)
  NATS_HOST = "gaia-nats-dev.fly.dev"
  NATS_PORT = "4222"

# Volume configuration (use subdirectories!)
[mounts]
  source = "gaia_service_dev"
  destination = "/data"
```

### 3. Deploy with Remote Builds (REQUIRED)
```bash
# ALWAYS use remote builds for network reliability
./scripts/deploy.sh --env dev --services service --remote-only

# OR deploy directly with fly
fly deploy --config fly.service.env.toml --remote-only
```

**Why Remote Builds?**
- Eliminates local network dependency issues
- Consistent build environment
- Faster for large codebases
- No Docker Desktop required

### 4. Wait for Service Startup
```bash
# Services need 30-60 seconds to fully start
# 503 errors during startup are normal
sleep 30

# Test health endpoint
./scripts/test.sh --url https://gaia-service-env.fly.dev health
```

### 5. Legacy Deploy Script (Still Works)
```bash
# Deploy with automatic secret sync and verification
./scripts/deploy-service.sh gateway dev
```

### 3. Verify Deployment
```bash
# Check all services are healthy and properly configured
./scripts/verify-deployment.sh --env dev
```

### 4. Test Local-Remote Parity
```bash
# Run same tests locally and remotely, compare results
./scripts/test-parity.sh dev
```

## Scripts Reference

### sync-secrets.sh
Synchronizes secrets from local `.env` to Fly.io services.

```bash
# Sync to all services
./scripts/sync-secrets.sh --env dev --services "gateway auth asset chat"

# Sync to specific service
./scripts/sync-secrets.sh --env dev --services "gateway"

# Dry run to see what would be set
./scripts/sync-secrets.sh --env dev --services "gateway" --dry-run
```

### deploy-service.sh
Deploys a service with proper configuration and secret management.

```bash
# Deploy gateway to dev
./scripts/deploy-service.sh gateway dev

# Deploy asset service to staging
./scripts/deploy-service.sh asset staging
```

### verify-deployment.sh
Verifies deployment health and configuration.

```bash
# Verify dev environment
./scripts/verify-deployment.sh --env dev
```

Checks:
- Service health endpoints
- Database connectivity
- NATS connectivity (if applicable)
- Required secrets are set
- Inter-service communication

### test-parity.sh
Runs identical tests locally and remotely to ensure parity.

```bash
# Test dev environment parity
./scripts/test-parity.sh dev
```

Generates:
- Individual test results for local and remote
- Comparison report
- Summary of matches/mismatches

## Environment Variables

### Gateway Service
Required:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWT_SECRET`
- `DATABASE_URL`
- `API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

Service URLs:
- `AUTH_SERVICE_URL`
- `ASSET_SERVICE_URL`
- `CHAT_SERVICE_URL`

### Auth Service
Required:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWT_SECRET`
- `DATABASE_URL`

### Asset Service
Required:
- `DATABASE_URL`
- `OPENAI_API_KEY`

Optional (for full functionality):
- `MESHY_API_KEY`
- `STABILITY_API_KEY`
- `MUBERT_API_KEY`
- `MIDJOURNEY_API_KEY`
- `FREESOUND_API_KEY`
- `SUPABASE_URL` (for JWT validation)
- `SUPABASE_JWT_SECRET` (for JWT validation)

### Chat Service
Required:
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_JWT_SECRET`

## Troubleshooting

### Service can't connect to database
1. Check DATABASE_URL is set: `fly secrets list -a app-name`
2. Verify database is accessible from the region
3. Check connection string format

### Authentication failing between services
1. Ensure all services have Supabase secrets
2. Verify internal DNS is being used (not public URLs)
3. Check service logs for specific auth errors

### Tests pass locally but fail remotely
1. Run `test-parity.sh` to identify specific differences
2. Check secret sync completed successfully
3. Verify service URLs use internal DNS
4. Compare environment variables between local and remote

## Best Practices

1. **Always test locally first**
   ```bash
   docker compose up
   ./scripts/test.sh --local all
   ```

2. **Deploy to staging before production**
   ```bash
   ./scripts/deploy-service.sh gateway staging
   ./scripts/test-parity.sh staging
   ```

3. **Keep secrets in sync**
   - Update `.env` file
   - Run `sync-secrets.sh` after any secret changes
   - Never commit secrets to git

4. **Monitor deployments**
   ```bash
   fly logs -a app-name
   ./scripts/verify-deployment.sh --env dev
   ```

5. **Use internal networking**
   - Always use `.internal` domains for service communication
   - Reduces latency and improves security
   - Keeps traffic within Fly.io network

## Future Improvements

1. **Secret Management Service**
   - Consider HashiCorp Vault or cloud KMS
   - Centralized secret rotation
   - Audit logging

2. **Service Mesh**
   - Implement Istio or Linkerd for advanced traffic management
   - Automatic mTLS between services
   - Circuit breaking and retries

3. **GitOps**
   - Automated deployment on git push
   - Environment promotion workflows
   - Rollback capabilities

4. **Monitoring**
   - Implement distributed tracing
   - Service performance metrics
   - Alerting on deployment issues