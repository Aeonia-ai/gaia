# Production Deployment Guide

This guide walks through deploying the Gaia Platform to production on Fly.io.

## Prerequisites

1. **Fly.io Account**: Must be logged in with access to `aeonia-dev` organization
2. **Environment Variables**: All API keys configured in `.env` file
3. **Staging Tested**: Verify staging deployment is working

## Pre-Deployment Checklist

### 1. Check Existing Infrastructure

```bash
# Check organization access
fly orgs list
# Should show: aeonia-dev

# Check existing databases
fly mpg list
# Look for: gaia-db-production

# Check existing apps
fly apps list
# Look for: gaia-gateway-production
```

### 2. Database Setup

If `gaia-db-production` doesn't exist:

```bash
# Create production database
fly postgres create \
  --name gaia-db-production \
  --region lax \
  --vm-size shared-cpu-1x \
  --volume-size 10 \
  --initial-cluster-size 1 \
  --org aeonia-dev

# Get connection string
fly postgres connect -a gaia-db-production --command "echo \$DATABASE_URL"
```

### 3. Update Production Config

Edit `fly.production.toml`:
1. Replace `DATABASE_URL` with actual connection string
2. Verify all environment variables are correct
3. Confirm organization and region settings

## Deployment Steps

### Option 1: Using Smart Deploy Script (Recommended)

```bash
# Deploy gateway-only to production
./scripts/deploy.sh --env production

# Or deploy with full microservices
./scripts/deploy.sh --env production --services all
```

### Option 2: Manual Deployment

```bash
# Set secrets first
fly secrets set API_KEY=$API_KEY -a gaia-gateway-production
fly secrets set OPENAI_API_KEY=$OPENAI_API_KEY -a gaia-gateway-production
fly secrets set ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY -a gaia-gateway-production

# Deploy the application
fly deploy --config fly.production.toml

# Monitor deployment
fly logs -a gaia-gateway-production
```

## Post-Deployment Verification

### 1. Health Check

**⚠️ ALWAYS use test scripts, NOT raw curl commands**

```bash
# ✅ CORRECT: Use smart test script
./scripts/test.sh --prod health

# ❌ WRONG: Raw curl (no environment awareness, auth handling, or error context)
# curl https://gaia-gateway-production.fly.dev/health

# Expected output:
# ✅ Status: 200
# {
#   "status": "healthy",  # or "degraded" for partial deployment
#   "timestamp": "...",
#   "version": "0.2"
# }
```

### 2. Core Functionality Test

```bash
# ✅ CORRECT: Use smart test scripts with environment awareness
./scripts/test.sh --prod providers
./scripts/test.sh --prod models
./scripts/test.sh --prod chat "Hello production!"

# ❌ WRONG: Raw API calls without proper auth/error handling
# curl -X POST https://gaia-gateway-production.fly.dev/api/v0.2/chat
```

### 3. Monitor Performance

```bash
# Real-time monitoring
./scripts/manage.sh monitor production

# Check logs
./scripts/manage.sh logs production

# View status
fly status -a gaia-gateway-production
```

## Production URLs

- **API Gateway**: https://gaia-gateway-production.fly.dev
- **Health Check**: https://gaia-gateway-production.fly.dev/health
- **API Documentation**: https://gaia-gateway-production.fly.dev/docs

## Scaling Production

### Horizontal Scaling

```bash
# Scale gateway to 5 instances
./scripts/manage.sh scale production gateway 5

# Or manually
fly scale count 5 -a gaia-gateway-production
```

### Vertical Scaling

Edit `fly.production.toml`:
```toml
[[vm]]
  memory = '4gb'  # Increase memory
  cpu_kind = 'dedicated'  # Use dedicated CPU
  cpus = 4        # More CPU cores
```

Then redeploy:
```bash
fly deploy --config fly.production.toml
```

## Rollback Procedures

If issues arise:

```bash
# Quick rollback to previous version
./scripts/manage.sh rollback production

# Or manual rollback
fly releases list -a gaia-gateway-production
fly deploy --image <previous-image-id> -a gaia-gateway-production
```

## Security Checklist

- [ ] All secrets set via `fly secrets`, not in config files
- [ ] Database URL uses SSL connection
- [ ] API keys are production-specific
- [ ] Supabase JWT secrets are configured
- [ ] No development/debug endpoints exposed

## Monitoring & Alerts

1. **Fly.io Dashboard**: https://fly.io/apps/gaia-gateway-production
2. **Metrics**: Available in Fly.io dashboard
3. **Health Endpoint**: Monitor externally via uptime services

## Troubleshooting

### Database Connection Issues

```bash
# Test database connection
fly postgres connect -a gaia-db-production

# Check database logs
fly logs -a gaia-db-production
```

### Service Not Starting

```bash
# Check deployment logs
fly logs -a gaia-gateway-production

# SSH into instance
fly ssh console -a gaia-gateway-production
```

### Performance Issues

```bash
# Check resource usage
fly scale show -a gaia-gateway-production

# Monitor in real-time
./scripts/manage.sh monitor production
```

## Next Steps

After successful production deployment:

1. Set up monitoring/alerting service
2. Configure backup strategy for database
3. Document any custom configurations
4. Plan for full microservices deployment
5. Set up CI/CD pipeline for automated deployments