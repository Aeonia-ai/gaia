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

### 3. Service Communication
- Local: Docker DNS (`http://service-name:8000`)
- Remote: Fly.io internal DNS (`http://app-name.internal:8000`) 
- Never use public URLs for inter-service communication
- **Important**: Cloud platforms may apply transparent compression (e.g., Fly.io uses Brotli)
  - Ensure HTTP clients support all compression types: `pip install httpx[brotli]`
  - See [Troubleshooting Inter-Service Communication](../troubleshooting-inter-service-communication.md) for compression issues

### 4. Testing Parity
- Same test suite runs locally and remotely
- Results are compared to ensure identical behavior
- Automated parity checking before production deployment

## Deployment Workflow

### 1. Initial Setup
```bash
# Ensure all secrets are in .env
cp .env.example .env
# Edit .env with your actual values
```

### 2. Deploy a Service

**For Claude Code users (2-minute Bash timeout):**
```bash
# Deploy with background execution to avoid timeouts
nohup ./scripts/deploy-service.sh gateway dev --remote-only > deploy-gateway.log 2>&1 &

# Monitor progress
tail -f deploy-gateway.log

# Verify deployment
./scripts/manage.sh status dev
```

**Standard deployment:**
```bash
# Deploy with automatic secret sync and verification
./scripts/deploy-service.sh gateway dev --remote-only
```

This script:
- Deploys the service using Fly.io remote builders
- Syncs secrets from local .env
- Waits for health check
- Runs verification tests
- Executes integration tests

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