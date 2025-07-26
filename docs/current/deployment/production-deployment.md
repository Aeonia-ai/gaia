# Production Deployment Guide

This guide walks through deploying the Gaia Platform to production using the **cluster-per-game** architecture for MMOIRL games.

## Prerequisites

1. **Fly.io Account**: Must be logged in with access to `aeonia-dev` organization
2. **Environment Variables**: All API keys configured in `.env` file
3. **Staging Tested**: Verify staging deployment is working

## Cluster-Per-Game Deployment Strategy

Each MMOIRL game gets its own isolated cluster. Use this naming pattern:
- **Apps**: `gaia-{game-id}-{service}` (e.g., `gaia-zombies-gateway`)
- **Database**: `gaia-{game-id}-db` (e.g., `gaia-zombies-db`)
- **Redis**: `gaia-{game-id}-redis` (e.g., `gaia-zombies-redis`)

## Pre-Deployment Checklist

### 1. Check Existing Infrastructure

```bash
# Check organization access
fly orgs list
# Should show: aeonia-dev

# For a new game "zombies", check if resources exist:
GAME_ID="zombies"

# Check existing databases
fly mpg list | grep $GAME_ID

# Check existing apps
fly apps list | grep $GAME_ID
```

### 2. Database Setup for Your Game

Create a dedicated database for each game:

```bash
# Set your game ID
GAME_ID="zombies"  # Replace with your game name

# Create game-specific database
fly postgres create \
  --name gaia-${GAME_ID}-db \
  --region lax \
  --vm-size shared-cpu-1x \
  --volume-size 10 \
  --initial-cluster-size 1 \
  --org aeonia-dev

# Get connection string
fly postgres connect -a gaia-${GAME_ID}-db --command "echo \$DATABASE_URL"
```

### 3. Create Game-Specific Config

Create a config file for your game:

```bash
# Copy template
cp fly.production.toml fly.${GAME_ID}.toml

# Edit fly.zombies.toml:
# 1. Change app name to gaia-zombies-gateway
# 2. Update DATABASE_URL to point to gaia-zombies-db
# 3. Add game-specific environment variables
```

## Deployment Steps

### Quick Deploy Script for New Game

```bash
# Create deployment script for your game
cat > deploy-${GAME_ID}.sh << 'EOF'
#!/bin/bash
GAME_ID="zombies"  # Your game ID

# Deploy each service
for SERVICE in gateway auth chat asset; do
  echo "Deploying gaia-${GAME_ID}-${SERVICE}..."
  fly apps create gaia-${GAME_ID}-${SERVICE} --org aeonia-dev
  fly deploy --app gaia-${GAME_ID}-${SERVICE} --config fly.${GAME_ID}.${SERVICE}.toml
done
EOF

chmod +x deploy-${GAME_ID}.sh
./deploy-${GAME_ID}.sh
```

### Manual Service Deployment

```bash
GAME_ID="zombies"

# Deploy Gateway
fly apps create gaia-${GAME_ID}-gateway --org aeonia-dev
fly secrets set API_KEY=$API_KEY -a gaia-${GAME_ID}-gateway
fly secrets set OPENAI_API_KEY=$OPENAI_API_KEY -a gaia-${GAME_ID}-gateway
fly deploy --app gaia-${GAME_ID}-gateway --config fly.${GAME_ID}.gateway.toml

# Deploy Chat Service
fly apps create gaia-${GAME_ID}-chat --org aeonia-dev
fly deploy --app gaia-${GAME_ID}-chat --config fly.${GAME_ID}.chat.toml

# Continue for auth, asset services...
```

## Post-Deployment Verification

### 1. Health Check

Test your game cluster:

```bash
GAME_ID="zombies"

# Test gateway health
curl https://gaia-${GAME_ID}-gateway.fly.dev/health

# Test with API key
curl -H "X-API-Key: YOUR_API_KEY" \
  https://gaia-${GAME_ID}-gateway.fly.dev/api/v1/chat/status

# Test chat endpoint
curl -X POST https://gaia-${GAME_ID}-gateway.fly.dev/api/v1/chat/direct \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from Zombie Survival!"}'
```
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

## Game-Specific Configuration

### Custom AI Personas
```toml
# In fly.zombies.toml
[env]
  GAME_PERSONAS = "survivor_guide,zombie_expert,medic"
  GAME_THEME = "post-apocalyptic survival"
```

### MCP Tools Configuration
```yaml
# mcp_zombies.config.yaml
mcp:
  servers:
    weather:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-weather"]
    location:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-location"]
```

## Monitoring & Alerts

1. **Per-Game Dashboard**: `https://fly.io/apps/gaia-{game-id}-gateway`
2. **Unified Monitoring**: Set up Grafana with game tags
3. **Health Endpoints**: Monitor each game cluster separately

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