# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🎯 Current Development Focus (July 16, 2025)
Working on **FastHTML Web UI improvements**. Just completed debugging critical HTMX issues including loading indicator placement and conversation switching. Created comprehensive [HTMX + FastHTML Debugging Guide](docs/htmx-fasthtml-debugging-guide.md). See [Web UI Development Status](docs/web-ui-development-status.md) for current state and next steps.

## 🧠 Development Philosophy & Problem-Solving Approach

**🛑 STOP GUESSING - START RESEARCHING**
- When deployment issues occur, resist the urge to try random fixes
- Search for documented issues: `"[platform] [error-type] [technology] troubleshooting"`
- Example: "Fly.io internal DNS connection refused microservices"

**🔬 SYSTEMATIC DIAGNOSIS**
- Test your hypothesis before implementing fixes
- Verify individual components work before assuming system-wide issues
- Use platform-specific debugging tools (e.g., `fly ssh console`)

**📚 PLATFORM-AWARE DEVELOPMENT**
- Every cloud platform has quirks - learn them early
- Example: Fly.io internal DNS is unreliable, AWS has eventual consistency, etc.
- Design around known platform limitations, don't fight them

**🚨 RECOGNIZE ANTI-PATTERNS**
- "One step forward, one step back" = you're guessing, not diagnosing
- Timeouts during deployment = often infrastructure issues, not code issues
- Services work individually but not together = networking/discovery problem

**📖 DOCUMENT SOLUTIONS & LESSONS**
- Capture both the specific fix AND the general approach that found it
- Future you will thank present you for documenting the "why" not just the "what"

## ⚠️ CRITICAL: Command Version Requirements

**ALWAYS use these command versions:**
- `docker compose` (with space) - NOT `docker-compose` (with hyphen)
- `fly postgres` or `fly mpg` - NOT `fly pg`
- `python -m pip` - NOT direct `pip`
- Test script - NOT direct `curl` commands
- `./scripts/curl_wrapper.sh` - NOT direct `curl` commands

See [Command Reference](docs/command-reference.md) for complete list.

## Development Commands

### Portable Database Management

**⚠️ IMPORTANT: Use portable database scripts for environment consistency**

```bash
# Initialize database for any environment
./scripts/init-database-portable.sh --env dev --user admin@gaia.dev
./scripts/init-database-portable.sh --env staging --user admin@gaia.com --provider fly
./scripts/init-database-portable.sh --env prod --user admin@gaia.com --provider aws

# Apply schema migrations
./scripts/migrate-database.sh --env dev --migration migrations/001_add_feature.sql
./scripts/migrate-database.sh --env prod --migration migrations/001_add_feature.sql --dry-run

# Monitor database health and performance
./scripts/monitor-database.sh --env dev --report health
./scripts/monitor-database.sh --env prod --report performance
```

See [Portable Database Architecture](docs/portable-database-architecture.md) for complete details.

### Docker Compose Operations

**⚠️ IMPORTANT: Use `docker compose` (space) not `docker-compose` (hyphen)**

```bash
# Start all services
docker compose up

# Start specific services
docker compose up gateway auth-service
docker compose up db nats  # Infrastructure only

# Rebuild services
docker compose build
docker compose build --no-cache  # Force rebuild

# View logs
docker compose logs -f gateway
docker compose logs -f auth-service
```

See [Command Reference](docs/command-reference.md) for correct command syntax.

### Testing
```bash
# Run full test suite
docker compose run test

# Run specific test files
docker compose run test pytest tests/test_auth.py
docker compose run test pytest tests/test_integration.py

# Run with specific markers
docker compose run test pytest -m integration
docker compose run test pytest -m compatibility

# Run web service tests
./scripts/test-web-quick.sh     # Quick unit test summary
./scripts/test-full-chat.sh     # Complete chat flow verification
./scripts/test-chat-automated.py # Automated conversation testing
docker compose exec -e PYTHONPATH=/app web-service pytest /app/tests/web/ -v
```

### Local Docker Development
```bash
# Start full microservices stack locally
docker compose up

# Test local deployment with user-associated authentication
./scripts/test.sh --local providers        # API key: FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE

# Gateway available at: http://localhost:8666 (LLM Platform compatible)
# Database auto-initialized with user: dev@gaia.local
```

### Development Workflow
```bash
# Initial setup
./scripts/setup.sh

# Smart testing (PREFERRED - use test script, not curl)
./scripts/test.sh --local health           # Local development
./scripts/test.sh --staging health         # Staging deployment
./scripts/test.sh --prod health            # Production deployment

# Environment-aware testing
./scripts/test.sh --local all              # Full local test suite
./scripts/test.sh --staging all            # Staging tests (expects some failures)

# Manual service health checks (if needed)
curl http://auth-service:8000/health
curl http://asset-service:8000/health
curl http://chat-service:8000/health
```

## Architecture Overview

### Microservices Structure
- **Gateway Service** (port 8666): Main entry point maintaining LLM Platform API compatibility
- **Auth Service**: JWT validation via Supabase, API key authentication
- **Asset Service**: Universal Asset Server functionality
- **Chat Service**: LLM interactions with MCP-agent workflows
- **Web Service** (port 8080): FastHTML frontend for chat interface

### Key Design Patterns
- **Backward Compatibility**: All API endpoints match LLM Platform exactly
- **User-Associated Authentication**: JWT tokens (users) + user-associated API keys (stored in database)
- **NATS Messaging**: Service coordination via subjects like `gaia.service.health`, `gaia.auth.*`
- **Shared Utilities**: Common functionality in `app/shared/`
- **Portable Database**: Same schema across local, dev, staging, production

### Service Communication
- **HTTP**: Direct service-to-service calls via configured URLs
- **NATS**: Event-driven coordination for health, auth events, processing updates
- **Database**: Shared PostgreSQL with LLM Platform-compatible schema

## Smart Scripts & Deployment

See [Smart Scripts & Deployment Guide](docs/smart-scripts-deployment.md) for comprehensive documentation on:
- curl_wrapper.sh standardized HTTP testing
- Smart testing script with environment-aware failure handling
- Intelligent deployment scripts with cloud optimizations
- Management scripts for deploy-test-monitor workflows
- Supabase configuration for multi-environment deployments
- Cloud deployment lessons learned

## Fly.io Deployment Configuration

See [Fly.io Deployment Configuration](docs/flyio-deployment-config.md) for complete setup details including:
- Organization configuration (aeonia-dev)
- Managed Postgres database commands
- Existing infrastructure overview
- Database naming conventions

## Configuration

### Environment Setup
1. Copy `.env.example` to `.env`
2. Configure required fields:
   - `API_KEY`: Primary authentication key
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`: Supabase auth
   - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`: LLM providers
   - Asset generation APIs: `STABILITY_API_KEY`, `MESHY_API_KEY`, etc.

### Supabase Email Configuration
Environment-specific email confirmation URLs must be configured in Supabase dashboard:

**4-Environment Pipeline**: local → dev → staging → production

- **Local**: `http://localhost:8080/auth/confirm`
- **Dev**: `https://gaia-web-dev.fly.dev/auth/confirm`
- **Staging**: `https://gaia-web-staging.fly.dev/auth/confirm`  
- **Production**: `https://gaia-web-production.fly.dev/auth/confirm`

See [Supabase Configuration Guide](docs/supabase-configuration.md) for detailed setup instructions.

### Service URLs (Inter-service Communication)
- Gateway: `http://gateway:8000` (external: `localhost:8666`)
- Auth: `http://auth-service:8000`
- Asset: `http://asset-service:8000`
- Chat: `http://chat-service:8000`
- Web: `http://web-service:8000` (external: `localhost:8080`)
- Redis: `redis://redis:6379` (caching layer)

## Shared Modules

### Core Utilities (`app/shared/`)
- **`config.py`**: Centralized Pydantic settings with environment variable management
- **`security.py`**: Authentication patterns, JWT validation, `AuthenticationResult` class
- **`database.py`**: SQLAlchemy setup with connection pooling
- **`logging.py`**: Color-coded structured logging with custom levels (NETWORK, SERVICE, NATS)
- **`nats_client.py`**: Async messaging client with reconnection handling
- **`redis_client.py`**: Redis caching client with connection pooling and fallback handling
- **`supabase.py`**: Supabase client integration

### Authentication Patterns
- Use `get_current_auth_legacy()` for LLM Platform compatibility
- Inter-service calls use `validate_auth_for_service()`
- Auth service provides `/internal/validate` for service coordination

## Development Guidelines

### Adding New Services
1. Create service directory in `app/services/`
2. Implement FastAPI app with `/health` endpoint
3. Add Dockerfile and docker-compose service
4. Configure service URL in `.env.example` and `config.py`
5. Add NATS message patterns if needed

### Testing Requirements
- Unit tests: `pytest -m unit`
- Integration tests: `pytest -m integration` 
- Compatibility tests: `pytest -m compatibility` (verify LLM Platform API compatibility)
- Performance tests: Redis caching validation and timing comparisons
- Use test markers defined in `pytest.ini`

### Performance Optimization (In Progress)

**Current Task**: Implementing quick-win optimizations from `/docs/optimization-guide.md`

**Completed**:
- ✅ Redis caching system (97% performance improvement locally)
- ✅ Local database indexing (composite index for `personas(is_active, created_at DESC)`)

**In Progress** (Priority order):
1. **Response compression middleware** - Add GZipMiddleware to all services (30-50% response size reduction)
2. **Database connection pooling** - Increase pool sizes for better concurrency
3. **Cache TTL optimization** - Extend TTLs for stable data (reduce DB load by 50-70%)

**Next Steps**:
- Apply database indexes to production database when connectivity available
- Container multi-stage builds for smaller images
- API pagination for large responses

**Expected Impact**: 40-60% overall performance improvement with ~1.5 hours total effort

**Notes**: 
- All optimizations maintain backward compatibility
- Changes are incremental and low-risk
- Performance gains validated locally, ready for production

### Client Compatibility
- Maintain identical API endpoints to LLM Platform
- All existing clients (Unity XR, Unity Mobile AR, Unreal Engine, NextJS) must work unchanged
- Gateway service handles routing and maintains response formats

## NATS Messaging Subjects

### Service Coordination
- `gaia.service.health`: Service health status updates
- `gaia.service.ready`: Service startup coordination

### Domain Events
- `gaia.auth.*`: Authentication events (login, logout, validation)
- `gaia.asset.generation.*`: Asset processing lifecycle events
- `gaia.chat.*`: Chat processing events

### Event Models
- `ServiceHealthEvent`: Service status with metadata
- `AssetGenerationEvent`: Asset processing lifecycle
- `ChatMessageEvent`: Chat processing coordination

## Troubleshooting

### Common Issues
```bash
# Services won't start
docker info  # Check Docker status
docker compose build --no-cache

# Database connection issues
docker compose logs db
docker compose down -v && docker compose up db

# NATS connection problems
docker compose logs nats
docker compose exec nats nats-server --help
```

### Fly.io Internal DNS Issues

⚠️ **Common Problem**: Gateway returns "Service unavailable" or 503 errors for working services.

**Symptoms:**
- Gateway health check shows "degraded" status
- Individual services are healthy when tested directly
- Error: "Failed to connect to service-name.internal"

**Root Cause**: Fly.io's `.internal` DNS occasionally stops working (documented issue)

**Diagnosis:**
```bash
# 1. Test gateway health
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev health
# Shows: "status": "degraded"

# 2. Test individual services directly
curl -H "X-API-Key: API_KEY" https://gaia-chat-dev.fly.dev/health
# Shows: working fine

# 3. Test internal DNS from gateway
fly ssh console -a gaia-gateway-dev --command "curl -I http://gaia-chat-dev.internal:8000/health"
# Shows: "Failed to connect to gaia-chat-dev.internal"
```

**Solution**: Switch from internal DNS to public URLs
```bash
# Fix gateway service URLs
fly secrets set -a gaia-gateway-dev \
  "CHAT_SERVICE_URL=https://gaia-chat-dev.fly.dev" \
  "AUTH_SERVICE_URL=https://gaia-auth-dev.fly.dev" \
  "ASSET_SERVICE_URL=https://gaia-asset-dev.fly.dev"

# Wait for deployment, then test
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev health
# Should show: "status": "healthy"
```

**Prevention**: Always use public URLs for service-to-service communication on Fly.io
```bash
# ❌ Unreliable internal DNS
CHAT_SERVICE_URL=http://gaia-chat-dev.internal:8000

# ✅ Reliable public URLs  
CHAT_SERVICE_URL=https://gaia-chat-dev.fly.dev
```

**References**: 
- [Fly.io Internal DNS Issues](https://community.fly.io/t/internal-dns-occasionally-stops-working-for-some-apps/5748)
- [Fly.io Private Networking Docs](https://fly.io/docs/networking/private-networking/)

### Debugging Methodology

When facing deployment issues, follow this systematic approach:

**🛑 STOP GUESSING** - Research first, then fix

1. **Research the Problem**
   ```bash
   # Don't guess - look up the actual issue
   # Search: "platform-name problem-description troubleshooting"
   # Example: "Fly.io internal DNS connection refused microservices"
   ```

2. **Test Your Hypothesis**
   ```bash
   # Verify the diagnosis before implementing fixes
   fly ssh console -a app-name --command "test-command"
   curl -I http://service.internal:8000/health  # Test internal connectivity
   ```

3. **Apply Documented Solutions**
   ```bash
   # Use official workarounds, not custom hacks
   # Example: Use public URLs instead of internal DNS (documented Fly.io issue)
   ```

4. **Verify the Fix**
   ```bash
   # Test that the solution actually works
   ./scripts/test.sh --url URL health
   ./scripts/test.sh --url URL chat "test message"
   ```

**Key Lesson**: "One step forward, one step back" cycles usually mean you're guessing instead of researching the actual problem.

### FastHTML/HTMX Debugging

⚠️ **Common HTMX Issues and Solutions**

**Critical Best Practices:**
1. **Loading indicators MUST be outside swap targets** - This is the #1 cause of HTMX issues
2. **Use `display` properties, not `opacity` for HTMX indicators**
3. **Always include target ID in response when using `outerHTML` swap**
4. **For non-HTMX navigation (logout), use onclick handlers**

**Debugging Steps:**
```bash
# Enable comprehensive HTMX logging
# Add this to your main chat page:
htmx.config.logger = function(elt, event, data) {
    console.debug("[HTMX]", event, elt, data);
};

# Check browser Network tab for requests
# Check browser Console for JavaScript errors
# Add server-side logging to routes
# Create minimal test endpoints to isolate issues
```

See [HTMX + FastHTML Debugging Guide](docs/htmx-fasthtml-debugging-guide.md) for complete debugging checklist.

### Performance Monitoring
```bash
# Resource usage
docker stats

# Service health (use smart test script)
./scripts/test.sh --local health

# Smart deployment management
./scripts/manage.sh status              # Overview of all environments
./scripts/manage.sh quick-test staging  # Quick health checks
./scripts/manage.sh monitor staging     # Detailed monitoring

# NATS monitoring
curl localhost:8222/varz  # NATS HTTP monitoring
```

## FastHTML Web Service Integration

See [FastHTML Web Service Guide](docs/fasthtml-web-service.md) for complete documentation on:
- Architecture and integration patterns
- Development commands and directory structure
- API integration via Gateway service
- Conversation management system
- Real-time features and session management
- Comprehensive testing framework
- Design system integration
- Deployment and scaling benefits

## Implementation Status & Future Tasks

See [Implementation Status](docs/implementation-status.md) for detailed tracking of:
- ✅ Completed systems (Provider Management, Streaming Chat, Core Infrastructure, FastHTML Web Interface)
- 🔧 Next priority systems (Asset Pricing, Persona Management, Performance Monitoring)
- 🚨 Technical debt to address
- 🎯 Recent accomplishments and immediate next tasks

### Current Web UI Development Status
See [Web UI Development Status](docs/web-ui-development-status.md) for:
- Current working features and recent fixes
- Known issues and bugs to address
- Next development priorities
- Testing commands and tips
- Recent UI flow improvements (July 15, 2025)

## Microservices Scaling Architecture

See [Microservices Scaling Guide](docs/microservices-scaling.md) for comprehensive analysis of:
- Scaling advantages over monolithic LLM Platform
- Workload-specific scaling patterns
- Real-world scaling scenarios and cost comparisons
- Reliability and fault isolation benefits
- Performance metrics and optimization strategies
- Kubernetes scaling configurations