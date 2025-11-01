# Gaia Platform Deployment Runbook

This runbook provides step-by-step procedures for deploying and troubleshooting the Gaia Platform across all environments.

## 🚀 Quick Deployment Commands

### Local Development
```bash
# Start all services
docker compose up -d

# Validate deployment
./scripts/validate-deployment-env.sh local

# Run health checks
./scripts/test.sh --local health
```

### Remote Deployment (Fly.io)
```bash
# Deploy to development
./scripts/deploy.sh --env dev --services all

# Validate deployment
./scripts/validate-deployment-env.sh dev

# Monitor deployment
fly status -a gaia-gateway-dev
```

## 📋 Pre-Deployment Checklist

### 1. Environment Validation
- [ ] All required secrets are configured
- [ ] Service health endpoints respond
- [ ] Authentication system is operational
- [ ] Database connections are working
- [ ] Git repositories are accessible (if using KB service)

### 2. Code Quality
- [ ] All tests pass locally
- [ ] Integration tests pass
- [ ] Authentication tests pass
- [ ] No linting errors
- [ ] No type checking errors

### 3. Infrastructure
- [ ] Fly.io apps are created and configured
- [ ] Volumes are created and mounted
- [ ] Secrets are set in target environment
- [ ] DNS routing is configured

## 🔧 Deployment Procedures

### Local Environment Setup

**Step 1: Clone and Configure**
```bash
git clone https://github.com/your-org/gaia-platform.git
cd gaia-platform
cp .env.example .env
```

**Step 2: Configure Secrets**
Edit `.env` with required values:
```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_SERVICE_KEY=eyJ...

# AI Provider
ANTHROPIC_API_KEY=sk-ant-...

# Backend Configuration
AUTH_BACKEND=supabase
ENVIRONMENT=local
```

**Step 3: Start Services**
```bash
docker compose up -d
```

**Step 4: Validate Deployment**
```bash
./scripts/validate-deployment-env.sh local
```

### Remote Environment Deployment

**Step 1: Prepare Fly.io Applications**
```bash
# Create applications (one-time setup)
fly apps create gaia-gateway-dev
fly apps create gaia-auth-dev
fly apps create gaia-chat-dev
fly apps create gaia-kb-dev
fly apps create gaia-asset-dev
```

**Step 2: Create Volumes (if needed)**
```bash
# For KB service
fly volumes create gaia_kb_dev --size 10 -a gaia-kb-dev
```

**Step 3: Set Secrets**
```bash
# Set secrets for each service
fly secrets set -a gaia-auth-dev \
  SUPABASE_URL="https://your-project.supabase.co" \
  SUPABASE_ANON_KEY="eyJ..." \
  SUPABASE_JWT_SECRET="your-jwt-secret" \
  ANTHROPIC_API_KEY="sk-ant-..." \
  AUTH_BACKEND="supabase" \
  ENVIRONMENT="dev"

# Repeat for other services as needed
```

**Step 4: Deploy Services**
```bash
# Deploy all services
./scripts/deploy.sh --env dev --services all

# Or deploy individually
fly deploy --config fly.auth.dev.toml --remote-only
```

**Step 5: Validate Deployment**
```bash
./scripts/validate-deployment-env.sh dev --fix
```

## 🔍 Health Check Procedures

### Basic Health Checks
```bash
# Local environment
curl http://localhost:8666/health
curl http://auth-service:8000/health
curl http://auth-service:8000/auth/health

# Remote environment
curl https://gaia-gateway-dev.fly.dev/health
curl https://gaia-auth-dev.fly.dev/health
curl https://gaia-auth-dev.fly.dev/auth/health
```

### Comprehensive Health Validation
```bash
# Use automated validation script
./scripts/validate-deployment-env.sh [environment]

# For detailed diagnostics
./scripts/validate-deployment-env.sh dev --fix
```

### Authentication Health Check
```bash
# Test authentication endpoint
curl -X POST http://localhost:8666/auth/validate \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-api-key"}'

# Check comprehensive auth health
curl http://auth-service:8000/auth/health | jq '.overall_status'
```

## 🚨 Troubleshooting Procedures

### Common Issues and Solutions

#### 1. Authentication Failures

**Symptom:** `Authentication failed` or `Invalid API key`

**Diagnosis:**
```bash
# Check auth service health
curl http://auth-service:8000/auth/health

# Validate secrets configuration
./scripts/validate-deployment-env.sh local

# Check Supabase connectivity
curl -H "apikey: $SUPABASE_ANON_KEY" "$SUPABASE_URL/rest/v1/"
```

**Solutions:**
- Verify all Supabase secrets are set correctly
- Check if SUPABASE_SERVICE_KEY is configured for API key validation
- Restart auth service: `docker compose restart auth-service`

#### 2. Service Communication Failures

**Symptom:** Services can't reach each other

**Diagnosis:**
```bash
# Check service status
docker compose ps

# Test inter-service communication
docker exec gaia-gateway-1 curl http://auth-service:8000/health
```

**Solutions:**
- Restart all services: `docker compose restart`
- Check Docker network: `docker network ls`
- Verify service URLs in configuration

#### 3. Database Connection Issues

**Symptom:** `Database connection failed`

**Diagnosis:**
```bash
# Check database health
curl http://localhost:8666/health | jq '.database'

# Check PostgreSQL container
docker compose logs db
```

**Solutions:**
- Restart database: `docker compose restart db`
- Check DATABASE_URL configuration
- Verify database is initialized: `./scripts/init-database-portable.sh`

#### 4. Remote Deployment Issues

**Symptom:** Fly.io services not responding

**Diagnosis:**
```bash
# Check service status
fly status -a gaia-auth-dev

# Check logs
fly logs -a gaia-auth-dev

# Check secrets
fly secrets list -a gaia-auth-dev
```

**Solutions:**
- Restart machine: `fly machine restart [machine-id] -a gaia-auth-dev`
- Redeploy: `fly deploy --config fly.auth.dev.toml --remote-only`
- Update secrets: `fly secrets set KEY=value -a gaia-auth-dev`

### Emergency Recovery Procedures

#### 1. Complete Service Restart
```bash
# Local environment
docker compose down
docker compose up -d

# Wait for services to start
sleep 30

# Validate
./scripts/validate-deployment-env.sh local
```

#### 2. Database Recovery
```bash
# Backup first (if possible)
docker exec gaia-db-1 pg_dump -U postgres llm_platform > backup.sql

# Reset database
docker compose down db
docker volume rm gaia_db_data
docker compose up -d db

# Wait and reinitialize
sleep 15
./scripts/init-database-portable.sh --env local
```

#### 3. Secret Rotation
```bash
# Generate new API key in Supabase dashboard
# Update local environment
echo "SUPABASE_ANON_KEY=new-key" >> .env

# Update remote environment
fly secrets set SUPABASE_ANON_KEY="new-key" -a gaia-auth-dev

# Restart services
docker compose restart
fly machine restart [machine-id] -a gaia-auth-dev
```

## 📊 Monitoring and Alerting

### Key Metrics to Monitor

1. **Service Health**
   - All services responding to `/health` endpoints
   - Authentication service comprehensive health check
   - Database connectivity

2. **Performance Metrics**
   - Response times < 2 seconds for health checks
   - Authentication validation < 500ms
   - Service startup time < 60 seconds

3. **Error Rates**
   - Authentication failures < 1%
   - Service communication failures < 0.1%
   - Database connection failures = 0%

### Monitoring Commands
```bash
# Continuous health monitoring
while true; do
  ./scripts/validate-deployment-env.sh local --fix
  sleep 60
done

# Performance monitoring
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8666/health

# Log monitoring
docker compose logs -f --tail=100
```

### Alert Conditions

**Critical Alerts:**
- Any service health check fails
- Authentication system overall_status = "error"
- Database connectivity lost
- More than 50% of API calls failing

**Warning Alerts:**
- Authentication system overall_status = "warning"
- Service response time > 5 seconds
- Disk usage > 80%
- Memory usage > 90%

## 📚 Reference Information

### Environment Variables Reference
See [Critical Secrets Dependencies](critical-secrets-dependencies.md) for complete list.

### Service Architecture
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Gateway   │────│    Auth     │────│  Supabase   │
│   :8666     │    │   :8000     │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │
       ├─────────────┬─────────────┬─────────────┐
       │             │             │             │
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│    Chat     │ │     KB      │ │   Asset     │ │     Web     │
│   :8002     │ │   :8003     │ │   :8004     │ │   :8005     │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Port Mappings
- Gateway: 8666 (external) → 8000 (internal)
- Auth: 8001 (external) → 8000 (internal)
- Chat: 8002 (external) → 8000 (internal)
- KB: 8003 (external) → 8000 (internal)
- Asset: 8004 (external) → 8000 (internal)
- Web: 8005 (external) → 8000 (internal)

### Critical Files
- `/scripts/validate-deployment-env.sh` - Deployment validation
- `/scripts/deploy.sh` - Automated deployment
- `/docs/critical-secrets-dependencies.md` - Secret management
- `/.env` - Local environment configuration
- `/docker-compose.yml` - Service orchestration

### Support Contacts
- **Supabase Issues**: Check Supabase dashboard and docs
- **Fly.io Issues**: Check Fly.io status page and docs
- **Platform Issues**: Check service logs and health endpoints

---

*This runbook should be updated whenever new services are added or deployment procedures change.*