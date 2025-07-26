# Smart Scripts & Deployment

## Overview
Gaia Platform includes intelligent scripts that handle environment-aware testing, deployment, and management based on lessons learned from production deployments.

## curl_wrapper.sh - Standardized HTTP Testing

**⚠️ IMPORTANT: Use `./scripts/curl_wrapper.sh` instead of direct `curl` commands**

The curl wrapper provides standardized HTTP testing with consistent options, validation, and colored output:

```bash
# Web interface testing
./scripts/curl_wrapper.sh -v http://localhost:8080/health
./scripts/curl_wrapper.sh -X POST -f -D "email=dev@gaia.local&password=test" http://localhost:8080/auth/login
./scripts/curl_wrapper.sh -X POST -f -D "message=Hello!" -H "Cookie: session=..." http://localhost:8080/api/chat/send

# API endpoint testing  
./scripts/curl_wrapper.sh -X POST -j -D '{"message": "test"}' -H "X-API-Key: key" http://localhost:8666/api/v0.2/chat
./scripts/curl_wrapper.sh -H "Authorization: Bearer token" http://localhost:8666/api/v1/conversations

# Advanced usage
./scripts/curl_wrapper.sh --dry-run -X POST -j -D '{"test": "data"}' http://localhost:8080/api/test  # See command without executing
./scripts/curl_wrapper.sh -v -t 60 -L http://example.com  # 60s timeout, follow redirects, verbose
./scripts/curl_wrapper.sh -o response.json http://localhost:8080/health  # Save output to file
```

**Key Features:**
- **Consistent defaults:** 30s timeout, proper user agent, colored output  
- **Input validation:** URL format checking, parameter validation
- **Debugging support:** Verbose mode shows exact curl commands executed
- **Dry run mode:** Preview commands without execution
- **Error handling:** Clear error messages with exit codes
- **Session support:** Cookie handling for authenticated requests
- **Content-type shortcuts:** `-j` for JSON, `-f` for form data

**Benefits over direct curl:**
- No permission prompts required
- Standardized options across all HTTP testing
- Built-in validation prevents common errors
- Colored output for better readability
- Consistent logging and error reporting

## Smart Testing Script (`scripts/test.sh`)
Environment-aware API testing with intelligent failure handling:

```bash
# Environment options
./scripts/test.sh --local all              # Full local testing
./scripts/test.sh --staging all            # Staging (expects partial failures)
./scripts/test.sh --prod all               # Production (expects full functionality)
./scripts/test.sh --url URL all            # Custom environment

# Individual tests
./scripts/test.sh --staging health         # Health check with context
./scripts/test.sh --local chat "Hello"     # Chat functionality
./scripts/test.sh --prod stream "Test"     # Streaming chat

# Test categories
./scripts/test.sh --local providers-all    # All provider endpoints
./scripts/test.sh --staging personas-all   # Persona management (may fail in staging)
./scripts/test.sh --prod performance-all   # Performance monitoring
```

**Key Features:**
- 🌍 **Environment Detection**: Automatically sets expectations per environment
- ⚠️ **Smart Failure Handling**: Staging failures marked as expected vs actual errors
- 🎨 **Color-coded Results**: Green (success), Yellow (expected failure), Red (error)
- 🔑 **Environment-specific Auth**: Different API keys per environment

## Smart Deployment Script (`scripts/deploy.sh`)
Intelligent deployment with lessons learned from cloud deployments:

```bash
# Basic deployments
./scripts/deploy.sh --env staging                    # Gateway-only deployment
./scripts/deploy.sh --env production --services all  # Full microservices

# Advanced options
./scripts/deploy.sh --env staging --region lax --rebuild
./scripts/deploy.sh --env production --database fly --services "gateway auth"
```

**Deployment Patterns:**
- 🚀 **Gateway-Only**: Fast deployment, embedded services, NATS disabled
- 🏗️ **Full Microservices**: Independent services, NATS enabled, service mesh
- 🌎 **Co-located Database**: Fly.io Postgres in same region for <1ms latency
- 🔐 **Secret Management**: Automatic .env secret deployment to Fly.io

## Management Script (`scripts/manage.sh`)
Comprehensive platform management combining deploy, test, and monitor:

```bash
# Deployment workflows
./scripts/manage.sh deploy-and-test staging    # Deploy + comprehensive test
./scripts/manage.sh status                     # Overview of all environments

# Testing workflows  
./scripts/manage.sh quick-test production      # Fast health checks
./scripts/manage.sh full-test staging          # Complete test suite

# Operations
./scripts/manage.sh monitor staging            # Real-time monitoring
./scripts/manage.sh scale production gateway 5 # Scale to 5 instances
./scripts/manage.sh logs staging gateway       # Stream logs
./scripts/manage.sh rollback staging           # Emergency rollback
```

**Smart Features:**
- 🧪 **Deploy-and-Test**: Automated deployment with validation
- 📊 **Multi-Environment Status**: Real-time health across local/staging/prod
- 🔄 **Zero-Downtime Operations**: Safe scaling and rollbacks
- 📱 **Environment-Aware Testing**: Different test expectations per environment

## Supabase Configuration for Deployments

**Important**: After deploying to a new environment, update Supabase email redirect URLs:

```bash
# 4-Environment Pipeline Examples:

# 1. Deploy to DEV
./scripts/deploy.sh --env dev
fly secrets set -a gaia-web-dev WEB_SERVICE_BASE_URL=https://gaia-web-dev.fly.dev

# 2. Deploy to STAGING  
./scripts/deploy.sh --env staging
fly secrets set -a gaia-web-staging WEB_SERVICE_BASE_URL=https://gaia-web-staging.fly.dev

# 3. Deploy to PRODUCTION
./scripts/deploy.sh --env production
fly secrets set -a gaia-web-production WEB_SERVICE_BASE_URL=https://gaia-web-production.fly.dev

# 4. Update Supabase dashboard for each environment:
#    - Site URL: https://gaia-web-{env}.fly.dev
#    - Redirect URLs: https://gaia-web-{env}.fly.dev/auth/confirm

# 5. Test email verification flow
./scripts/test.sh --dev auth "test-email@example.com"
./scripts/test.sh --staging auth "test-email@example.com"
./scripts/test.sh --prod auth "test-email@example.com"
```

## Cloud Deployment Lessons Learned

**Database Co-location:**
```toml
# Optimal: Both app and database in same region
app = 'gaia-gateway-staging'
primary_region = 'lax'

# Database URL: Co-located Fly.io Postgres in LAX
DATABASE_URL = "postgresql://postgres:...@direct.xxx.flympg.net:5432/postgres"
```

**NATS Configuration:**
```toml
# Local development: Full NATS coordination
NATS_URL = "nats://localhost:4222"

# Cloud deployment: NATS disabled for gateway-only pattern
NATS_URL = "disabled"
```

**Service Expectations by Environment:**
- **Local**: Full microservices, all endpoints working
- **Staging**: Gateway-only, asset/persona endpoints may fail (expected)
- **Production**: All services operational, full functionality