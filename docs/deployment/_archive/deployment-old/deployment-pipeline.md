# Gaia Platform Deployment Pipeline

This document outlines the complete development-to-production pipeline for the Gaia Platform.

## 🏗️ Pipeline Overview

```
Local Development → Dev Environment → Staging → Production
     (Docker)           (Fly.io)      (Fly.io)   (Fly.io)
```

## 🌍 Environment Breakdown

### 1. **Local Development**
- **Purpose**: Feature development and testing
- **Infrastructure**: Docker Compose with full microservices
- **Database**: Local PostgreSQL
- **NATS**: Enabled for service coordination
- **Testing**: Full test suite expected to pass

```bash
# Start local development
docker compose up
./scripts/test.sh --local all
```

### 2. **Dev Environment** (`gaia-*-dev`)
- **Purpose**: Early integration testing and experimentation
- **Apps**: Multiple microservices deployed separately
  - `gaia-gateway-dev`
  - `gaia-auth-dev` 
  - `gaia-asset-dev`
  - `gaia-chat-dev`
  - `gaia-nats-dev`
- **Database**: Shared development database
- **NATS**: Full coordination between services
- **Testing**: May have experimental features

### 3. **Staging Environment** (`gaia-*-staging`)
- **Purpose**: Production-like testing and validation
- **Pattern**: Full microservices stack (same as production)
- **Apps**: Complete microservices deployment
  - `gaia-gateway-staging`
  - `gaia-auth-staging`
  - `gaia-asset-staging` 
  - `gaia-chat-staging`
  - `gaia-nats-staging`
- **Database**: Co-located Fly.io Managed Postgres
- **NATS**: Enabled for full service coordination
- **Testing**: Full functionality expected

```bash
# Deploy full microservices to staging
./scripts/deploy.sh --env staging --services all

# Test staging
./scripts/test.sh --staging all
```

### 4. **Production Environment** (`gaia-*-production`)
- **Purpose**: Live production system
- **Pattern**: Full microservices stack (identical to staging)
- **Apps**: Complete microservices deployment
  - `gaia-gateway-production`
  - `gaia-auth-production`
  - `gaia-asset-production`
  - `gaia-chat-production`
  - `gaia-nats-production`
- **Database**: Production Fly.io Managed Postgres  
- **NATS**: Enabled for full service coordination
- **Testing**: Zero tolerance for failures

```bash
# Deploy full microservices to production
./scripts/deploy.sh --env production --services all

# Test production
./scripts/test.sh --prod all
```

## 📋 Deployment Workflow

### Feature Development Cycle

1. **Local Development**
   ```bash
   # Develop feature locally
   docker compose up
   ./scripts/test.sh --local all
   
   # Commit when tests pass
   git add . && git commit -m "Add feature X"
   ```

2. **Dev Environment Testing**
   ```bash
   # Deploy to dev for integration testing
   ./scripts/deploy.sh --env dev --services all
   ./scripts/test.sh --dev all
   ```

3. **Staging Validation**
   ```bash
   # Deploy full microservices to staging for production-like testing
   ./scripts/deploy.sh --env staging --services all
   ./scripts/test.sh --staging all
   
   # Validate full functionality works
   ./scripts/manage.sh quick-test staging
   ```

4. **Production Release**
   ```bash
   # Deploy full microservices to production after staging validation
   ./scripts/deploy.sh --env production --services all
   ./scripts/test.sh --prod all
   
   # Monitor deployment
   ./scripts/manage.sh monitor production
   ```

## 🔧 Environment-Specific Configurations

### Local (`docker compose.yml`)
```yaml
# Full microservices with NATS coordination
services:
  gateway:
    environment:
      NATS_URL: "nats://nats:4222"
      AUTH_SERVICE_URL: "http://auth-service:8000"
```

### Dev (`fly.*.dev.toml`)
```toml
# Full microservices for experimentation
app = 'gaia-gateway-dev'
NATS_URL = "nats://gaia-nats-dev.fly.dev:4222"
AUTH_SERVICE_URL = "https://gaia-auth-dev.fly.dev"
ASSET_SERVICE_URL = "https://gaia-asset-dev.fly.dev"
CHAT_SERVICE_URL = "https://gaia-chat-dev.fly.dev"
```

### Staging (`fly.*.staging.toml`)
```toml
# Full microservices for production-like testing
app = 'gaia-gateway-staging'
NATS_URL = "nats://gaia-nats-staging.fly.dev:4222"
AUTH_SERVICE_URL = "https://gaia-auth-staging.fly.dev"
ASSET_SERVICE_URL = "https://gaia-asset-staging.fly.dev"
CHAT_SERVICE_URL = "https://gaia-chat-staging.fly.dev"
```

### Production (`fly.*.production.toml`)
```toml
# Full microservices with production scaling
app = 'gaia-gateway-production'
NATS_URL = "nats://gaia-nats-production.fly.dev:4222"
AUTH_SERVICE_URL = "https://gaia-auth-production.fly.dev"
ASSET_SERVICE_URL = "https://gaia-asset-production.fly.dev"
CHAT_SERVICE_URL = "https://gaia-chat-production.fly.dev"
min_machines_running = 2  # High availability
memory = '2gb'            # More resources
```

## 🧪 Testing Strategy Per Environment

### Local Testing
```bash
# Full functionality expected
./scripts/test.sh --local all
./scripts/test.sh --local providers-all
./scripts/test.sh --local personas-all
```

### Staging Testing
```bash
# Core functionality + expected partial failures
./scripts/test.sh --staging health        # Should work
./scripts/test.sh --staging providers     # Should work  
./scripts/test.sh --staging personas-all  # May fail (expected)
```

### Production Testing
```bash
# Zero tolerance for failures
./scripts/test.sh --prod health
./scripts/test.sh --prod providers
./scripts/test.sh --prod chat "Test"
```

## 🚀 Deployment Patterns

### Full Microservices Pattern (All Environments)
- **Pros**: True microservices benefits, independent scaling, service isolation
- **Cons**: Higher resource usage, more complex coordination
- **Use Case**: Proper dev→staging→production pipeline consistency

```bash
# Deploy full microservices to any environment
./scripts/deploy.sh --env dev --services all
./scripts/deploy.sh --env staging --services all
./scripts/deploy.sh --env production --services all
```

### Gateway-Only Pattern (Legacy/Interim)
- **Pros**: Fast deployment, simple debugging, cost-effective
- **Cons**: Not true microservices, limited scaling
- **Use Case**: Rapid prototyping, interim deployments

```bash
# Note: This is an interim pattern, not recommended for full pipeline
./scripts/deploy.sh --env staging  # Gateway-only (legacy)
```

## 📊 Pipeline Status Monitoring

### Check All Environments
```bash
# Single command to see entire pipeline status
./scripts/manage.sh status

# Output:
# 🌍 staging Environment:
#   gaia-gateway-staging: ✅ Responsive
# 🌍 production Environment:  
#   gaia-gateway-production: ✅ Healthy
# 🐳 Local Development:
#   Local services: ⚠️ Stopped
```

### Environment Health Checks
```bash
# Quick health check across pipeline
./scripts/manage.sh quick-test staging
./scripts/manage.sh quick-test production

# Detailed monitoring
./scripts/manage.sh monitor staging
./scripts/manage.sh monitor production
```

## 🔄 Rollback Strategy

### Staging Rollback
```bash
# Safe to experiment - rollback if needed
./scripts/manage.sh rollback staging
```

### Production Rollback
```bash
# Emergency rollback with confirmation
./scripts/manage.sh rollback production
# Requires manual confirmation for safety
```

## 📋 Pipeline Checklist

### Before Deploying to Next Environment:

**Local → Dev:**
- [ ] All local tests pass
- [ ] Feature complete and tested
- [ ] No breaking changes to API

**Dev → Staging:**
- [ ] Dev environment stable
- [ ] Integration tests pass
- [ ] No experimental features

**Staging → Production:**
- [ ] Staging validation complete
- [ ] Core functionality verified
- [ ] Performance acceptable
- [ ] Security review complete
- [ ] Rollback plan ready

## 🎯 Current Pipeline State

### Active Environments:
- ✅ **Local**: Available (docker compose)
- ✅ **Dev**: Full microservices deployed (suspended, ready to start)
- ⚠️ **Staging**: Gateway-only (needs full microservices deployment)
- ⚠️ **Production**: Gateway-only (needs full microservices deployment)

### Next Steps for Complete Pipeline:
1. Deploy full microservices to staging: `./scripts/deploy.sh --env staging --services all`
2. Deploy full microservices to production: `./scripts/deploy.sh --env production --services all`
3. Validate full functionality across all environments

### Pipeline Maturity:
- **Infrastructure**: Dev environment complete, staging/prod need microservices
- **Automation**: Smart deployment scripts ready
- **Testing**: Environment-aware test suite
- **Monitoring**: Real-time status monitoring
- **Documentation**: Comprehensive guides

The Gaia Platform has the foundation for a complete, production-ready deployment pipeline - just needs full microservices deployment to staging and production! 🚀