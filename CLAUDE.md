# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 BEFORE YOU START: Required Reading
1. **[Testing and Quality Assurance Guide](docs/testing-and-quality-assurance.md)** - Set up pre-commit hooks and run tests before making changes
2. **[API Contracts Documentation](docs/api-contracts.md)** - Understand which endpoints must remain public
3. **[API Key Configuration Guide](docs/api-key-configuration-guide.md)** - ALWAYS check this before setting up authentication
4. **[HTMX + FastHTML Debugging Guide](docs/htmx-fasthtml-debugging-guide.md)** - **MANDATORY** read before ANY web UI changes
5. **[Auth Layout Isolation Rules](docs/auth-layout-isolation.md)** - CRITICAL: Prevent recurring layout bugs
6. **[Common Mistakes to Avoid](#-common-mistakes-to-avoid)** - Review this section to prevent known issues
7. **[Essential Documentation Index](#-essential-documentation-index)** - Find the right guide for your task

## ⚠️ REMINDER TO CLAUDE CODE
**BEFORE ANY WEB UI CHANGES:** You MUST read the HTMX + FastHTML Debugging Guide and Auth Layout Isolation docs first. The user will remind you if you don't, because layout bugs "keep coming back" when documentation is ignored. Always use `auth_page_replacement()` for auth responses and proper HTMX container targeting patterns.

## 🎯 Current Development Focus (July 24, 2025)
**Latest Updates**: 
- **Supabase Authentication**: FULLY IMPLEMENTED - No PostgreSQL fallback when AUTH_BACKEND=supabase
- **KB Git Sync**: COMPLETE - Deferred initialization pattern for fast startup, 10GB volumes
- **KB Service**: Fully integrated with Aeonia's Obsidian Vault (1234 files) on remote dev environment
- **RBAC System**: Designed flexible role-based access control starting with KB, extensible platform-wide
- **Multi-User KB**: Architecture supports teams, workspaces, and granular permissions
- **mTLS + JWT Authentication**: COMPLETE (Phases 1-2) - Modern auth infrastructure with 100% backward compatibility

**Key Authentication & Authorization**:
- **Supabase-first**: API keys validated through Supabase ONLY (no fallback) when configured
- **Clean separation**: AUTH_BACKEND=supabase means Supabase-only validation
- **RBAC Integration**: Role-based permissions for KB and platform resources
- **Multi-User Ready**: User namespaces, team/workspace support, sharing mechanisms
- **Local-remote parity**: Same authentication code in both environments  
- **Redis caching**: 97% performance improvement for authentication
- **Zero breaking changes**: All existing clients continue to work unchanged
- **mTLS Infrastructure**: Certificate Authority + service certificates deployed
- **Unified Authentication**: `get_current_auth_unified()` handles API keys + Supabase JWTs

**Important**: See [Supabase Auth Migration Learnings](docs/supabase-auth-migration-learnings.md) for key architectural decisions and deployment strategies

**Recent Improvements**:
- **MCP-Agent Hot Loading**: COMPLETE - Singleton pattern reduces response time from 5-10s to 1-3s
- **Intelligent Chat Routing**: COMPLETE - Single LLM call routes simple messages in ~1s, complex in ~3s
- **Universal Language Support**: No English-specific patterns, works with all languages

**Active Development**:
- Getting Supabase service role key for full remote functionality
- Implementing KB permission manager with RBAC
- FastAPI integration for automatic permission checks
- Multi-user KB namespaces and sharing features
- Phase 3: Migrate web/mobile clients to Supabase JWTs
- Phase 4: Remove legacy API key validation

## 🚀 Smart Service Deployment & Discovery

**🎯 SOLVED: No More Hardcoded Service URLs**

We've implemented a **cloud-agnostic smart service discovery system** that eliminates the need to hardcode service URLs every time we deploy a new service.

### Smart Service Discovery Pattern

**Implementation**: Located in `app/shared/config.py`
```python
def get_service_url(service_name: str) -> str:
    # Auto-generates URLs based on environment and cloud provider:
    # Fly.io: gaia-{service}-{environment}.fly.dev
    # AWS: gaia-{service}-{environment}.{region}.elb.amazonaws.com  
    # GCP: gaia-{service}-{environment}-{region}.run.app
    # Local: localhost:{port}
```

**Service Configuration** (Example):
```toml
[env]
  ENVIRONMENT = "dev"           # Auto-discovery based on environment
  CLOUD_PROVIDER = "fly"       # Multi-cloud support  
  NATS_HOST = "gaia-nats-dev.fly.dev"    # NATS discovery
  NATS_PORT = "4222"
  # No hardcoded service URLs needed!
```

### New Service Deployment Checklist

**1. 🏗️ Remote Builds (REQUIRED)**
```bash
# Always use remote builds for network reliability
fly deploy --config fly.service.env.toml --remote-only
```

**2. 📁 .dockerignore (CRITICAL)**
Create `.dockerignore` to prevent build hangs:
```
.venv/          # Can be 500MB+ 
venv/
ENV/
*.log
.git/
```

**3. 🗂️ Volume Configuration**
For persistent storage, always use subdirectories:
```toml
[mounts]
  source = "gaia_service_dev"
  destination = "/data"

[env]
  SERVICE_DATA_PATH = "/data/repository"  # NOT just "/data"
```

**4. ⏱️ Deployment Patience**
- Remote builds: 2-5 minutes
- Service startup: 30-60 seconds after deployment
- 503 errors during startup are normal
- Wait for health checks: `./scripts/test.sh --url https://service-url health`

**5. 🌐 Network Configuration**
**CRITICAL**: Never use Fly.io internal DNS (`.internal`) - it's unreliable
```bash
# ❌ Unreliable
AUTH_SERVICE_URL = "http://gaia-auth-dev.internal:8000"

# ✅ Reliable (auto-generated by smart discovery)
AUTH_SERVICE_URL = "https://gaia-auth-dev.fly.dev"
```

### Multi-Cloud Deployment

To deploy to different cloud providers, just change the configuration:
```toml
# Fly.io
CLOUD_PROVIDER = "fly"
ENVIRONMENT = "dev"
# Results in: gaia-service-dev.fly.dev

# AWS  
CLOUD_PROVIDER = "aws"
AWS_REGION = "us-west-2"
# Results in: gaia-service-dev.us-west-2.elb.amazonaws.com

# GCP
CLOUD_PROVIDER = "gcp" 
GCP_REGION = "us-west1"
# Results in: gaia-service-dev-us-west1.run.app
```

### Service Template

**New services should follow this pattern**:
```toml
# fly.service.env.toml
app = "gaia-service-env"
primary_region = "lax"

[env]
  # Smart service discovery
  ENVIRONMENT = "dev"
  CLOUD_PROVIDER = "fly"
  SERVICE_NAME = "service"
  
  # Service-specific config
  SERVICE_PORT = "8000"
  PYTHONPATH = "/app"
  
  # NATS (if needed)
  NATS_HOST = "gaia-nats-dev.fly.dev"
  NATS_PORT = "4222"

[mounts]
  source = "gaia_service_dev"
  destination = "/data"

[[services]]
  protocol = "tcp"
  internal_port = 8000
  
  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
    
  [[services.http_checks]]
    interval = "10s"
    path = "/health"
```

**Key Insight**: This system **eliminates configuration drift** and **scales to any cloud provider** without code changes.

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

**🚀 COMMIT TO SIMPLICITY**
- When choosing PostgreSQL as the "fast approach", use it simply - don't recreate document DB complexity
- Avoid compatibility layers between different paradigms (e.g., making asyncpg work like SQLAlchemy)
- If you're building abstractions to make one tool work like another, you're using the wrong tool
- See [PostgreSQL Simplicity Lessons](docs/postgresql-simplicity-lessons.md) for detailed learnings

**🧪 USE TEST SCRIPTS, NOT CURL**
- ALWAYS use test scripts (`./scripts/test.sh`) instead of manual curl commands
- If you need to test something new, ADD it to a test script, don't just run curl
- Test scripts capture knowledge, curl commands vanish with your terminal
- See [Testing Philosophy](docs/testing-philosophy.md) for why this matters

## 📚 Essential Documentation Index

**🏠 [Complete Documentation](docs/README.md)** - Organized by role (Developer, DevOps, Architect)

**IMPORTANT**: Always consult these guides BEFORE making changes to avoid common pitfalls.

### 🟢 Current Implementation (What Works Now)

#### Authentication & Security
- [Authentication Guide](docs/current/authentication/authentication-guide.md) - **UPDATED** - Complete dual auth (API keys + JWTs + mTLS)
- [API Key Configuration](docs/current/authentication/api-key-configuration-guide.md) - **UPDATED** - Unified authentication patterns  
- [mTLS Certificates](docs/current/authentication/mtls-certificate-management.md) - Certificate infrastructure guide
- [Auth Troubleshooting](docs/current/authentication/troubleshooting-api-key-auth.md) - Common auth issues

#### Deployment & Operations  
- [Deployment Best Practices](docs/current/deployment/deployment-best-practices.md) - Local-remote parity strategies
- [Fly.io Configuration](docs/current/deployment/flyio-deployment-config.md) - Platform-specific setup
- [Smart Scripts](docs/current/deployment/smart-scripts-deployment.md) - Automated deployment tools
- [Supabase Configuration](docs/current/deployment/supabase-configuration.md) - Email confirmation URLs and auth setup

#### Development & Testing
- [Command Reference](docs/current/development/command-reference.md) - Correct command syntax
- [Testing Guide](docs/current/development/testing-and-quality-assurance.md) - Pre-commit hooks and test patterns
- [Environment Setup](docs/current/development/dev-environment-setup.md) - Local development workflow
- [Testing Philosophy](docs/testing-philosophy.md) - **IMPORTANT** - Why we use test scripts, not curl

#### Web UI Development
- [FastHTML Service](docs/current/web-ui/fasthtml-web-service.md) - Web UI architecture
- [HTMX Debugging](docs/current/web-ui/htmx-fasthtml-debugging-guide.md) - **MANDATORY** read before web changes
- [Auth Layout Rules](docs/current/web-ui/auth-layout-isolation.md) - **CRITICAL** prevent layout bugs

#### Architecture & Scaling
- [Microservices Scaling](docs/current/architecture/microservices-scaling.md) - Scaling patterns and strategies
- [Database Architecture](docs/current/architecture/database-architecture.md) - **IMPORTANT** - Hybrid database + Redis caching
- [Adding New Microservice](docs/adding-new-microservice.md) - **NEW** - Simplified service creation process
- [Service Creation Automation](docs/service-creation-automation.md) - **NEW** - Detailed automation guide
- [PostgreSQL Simplicity Lessons](docs/postgresql-simplicity-lessons.md) - **IMPORTANT** - Avoiding overengineering
- [Deferred Initialization Pattern](docs/deferred-initialization-pattern.md) - **NEW** - Fast startup with background tasks

#### Troubleshooting & Performance  
- [Fly.io DNS Issues](docs/current/troubleshooting/troubleshooting-flyio-dns.md) - Internal DNS issues
- [Mobile Testing](docs/current/troubleshooting/mobile-testing-guide.md) - Testing on mobile devices
- [Optimization Guide](docs/current/troubleshooting/optimization-guide.md) - Performance improvements

#### KB & Advanced Features
- [MCP-Agent Hot Loading](docs/mcp-agent-hot-loading.md) - **NEW** - Singleton pattern for 3x faster multiagent responses
- [Intelligent Chat Routing](docs/intelligent-chat-routing.md) - **NEW** - Single LLM call with automatic routing
- [KB Git Sync Learnings](docs/kb-git-sync-learnings.md) - **NEW** - Deferred init, volume sizing, deployment patterns
- [KB Git Sync Guide](docs/kb-git-sync-guide.md) - Complete Git synchronization setup
- [KB Remote Deployment Authentication](docs/kb-remote-deployment-auth.md) - Git auth for production
- [KB Deployment Checklist](docs/kb-deployment-checklist.md) - Step-by-step KB deployment to staging/prod
- [RBAC System Guide](docs/rbac-system-guide.md) - Role-based access control implementation
- [Multi-User KB Guide](docs/multi-user-kb-guide.md) - Teams, workspaces, and sharing

#### Authentication Implementation
- [Supabase Auth Implementation Guide](docs/supabase-auth-implementation-guide.md) - **NEW** - Complete Supabase authentication setup
- [Authentication Strategy](docs/authentication-strategy.md) - Long-term authentication approach

### 🟡 Future Plans & Roadmap
- [Implementation Status](docs/future/roadmap/implementation-status.md) - Current progress tracking
- [Web UI Development Status](docs/future/roadmap/web-ui-development-status.md) - Frontend development state
- [Feature Roadmap](docs/future/roadmap/feature-roadmap.md) - Complete feature pipeline

### 📚 API Reference
- [API Contracts](docs/api/api-contracts.md) - Which endpoints require authentication
- [Chat Endpoints](docs/api/chat-endpoints.md) - LLM interaction patterns
- [API Authentication Guide](docs/api/api-authentication-guide.md) - API authentication patterns
- [Redis Integration](docs/redis-integration.md) - Caching implementation

## 🏗️ Architecture Guidelines

### Avoid Overengineering
1. **Use tools for their strengths** - PostgreSQL for relational data, Redis for caching, etc.
2. **No unnecessary abstractions** - If you need a compatibility layer, you're probably using the wrong tool
3. **Start simple** - You can always add complexity later, but you can't easily remove it
4. **Direct is better** - `await conn.fetch()` is better than layers of abstraction

### Signs You're Overcomplicating
- Building compatibility layers between technologies
- Error messages getting more complex over time
- Writing more infrastructure code than business logic
- The "fast approach" taking longer than the "proper approach"

## ⚠️ CRITICAL: Command Version Requirements

**ALWAYS use these command versions:**
- `docker compose` (with space) - NOT `docker-compose` (with hyphen)
- `fly postgres` or `fly mpg` - NOT `fly pg`
- `python -m pip` - NOT direct `pip`
- Test script - NOT direct `curl` commands
- `./scripts/curl_wrapper.sh` - NOT direct `curl` commands

See [Command Reference](docs/command-reference.md) for complete list.

## 🚫 Common Mistakes to Avoid

### Configuration Mistakes
1. **DON'T** rely on Pydantic's `env_prefix` alone - use `Field(env="VAR_NAME")`
2. **DON'T** assume environment variables are loaded - always verify in logs
3. **DON'T** mix API key names - web service uses `WEB_API_KEY`, not `API_KEY`

### API Design Mistakes
1. **DON'T** send extra fields in API requests - only send what's in the model
2. **DON'T** assume endpoint paths - check the actual service implementation
3. **DON'T** use public URLs for inter-service communication on Fly.io

### Deployment Mistakes
1. **DON'T** deploy without checking service health first
2. **DON'T** ignore deployment timeouts - check if it succeeded anyway
3. **DON'T** forget to set Fly.io secrets for new environment variables

### Testing Mistakes
1. **DON'T** use direct `curl` - use test scripts that capture the knowledge
2. **DON'T** test in production first - always test locally
3. **DON'T** skip the verification scripts after configuration changes
4. **DON'T** create one-off test commands - add them to test scripts
5. **DON'T** forget that terminal history is temporary - test scripts are permanent

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

### Remote Authentication Setup

**⚠️ IMPORTANT: Local and remote environments use separate PostgreSQL databases**

```bash
# Setup authentication for remote environments
./scripts/setup-remote-auth.sh --env dev --email jason@aeonia.ai

# This creates a user and API key in the remote database
# SAVE THE API KEY - it's only shown once!

# Test remote authentication
API_KEY=<generated-key> ./scripts/test.sh --url https://gaia-gateway-dev.fly.dev kb-search "test"
```

See [Authentication Strategy](docs/authentication-strategy.md) for long-term solution.

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

# ALWAYS USE TEST SCRIPTS - NOT MANUAL CURL!
./scripts/test-comprehensive.sh            # Full test suite (RECOMMENDED)
./scripts/test.sh --local all              # Legacy test suite
./scripts/test-kb-operations.sh            # KB-specific tests

# Testing specific features
./scripts/test.sh --local providers        # Test provider listing
./scripts/test.sh --local chat "Hi"        # Test chat completion

# User management
./scripts/manage-users.sh list             # List all users
./scripts/manage-users.sh create user@example.com  # Create user with API key
./scripts/manage-users.sh grant-kb user@example.com # Grant KB access

# KB Git Sync Testing and Management
./scripts/setup-aeonia-kb.sh               # Configure Aeonia Obsidian vault sync
./scripts/setup-kb-git-repo.sh             # Configure any Git repository sync
./scripts/test-kb-git-sync.sh              # Test KB Git sync functionality

# Manual service health checks (if needed)
curl http://auth-service:8000/health
curl http://asset-service:8000/health
curl http://chat-service:8000/health
curl http://kb-service:8000/health
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
Due to Supabase's free tier limitation (2 projects per organization), we use a single Supabase project (`gaia-platform-v2`) configured to support all environments. The project must have ALL redirect URLs configured:

**4-Environment Pipeline**: local → dev → staging → production

**Required Redirect URLs in Supabase Dashboard**:
- `http://localhost:8080/auth/confirm`
- `http://localhost:8080/auth/callback`
- `http://localhost:8080/`
- `https://gaia-web-dev.fly.dev/auth/confirm`
- `https://gaia-web-dev.fly.dev/auth/callback`
- `https://gaia-web-dev.fly.dev/`
- `https://gaia-web-staging.fly.dev/auth/confirm`
- `https://gaia-web-staging.fly.dev/auth/callback`
- `https://gaia-web-staging.fly.dev/`
- `https://gaia-web-production.fly.dev/auth/confirm`
- `https://gaia-web-production.fly.dev/auth/callback`
- `https://gaia-web-production.fly.dev/`

See [Supabase Configuration Guide](docs/supabase-configuration.md) for detailed setup instructions.

### KB (Knowledge Base) Configuration

**NEW: Git Repository Sync Support (July 2025)**

The KB service now supports automatic synchronization with external Git repositories (e.g., Obsidian vaults, documentation repos).

**Quick Setup for Aeonia Team**:
```bash
# 1. Add GitHub Personal Access Token to .env:
KB_STORAGE_MODE=hybrid
KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git
KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Your GitHub PAT
KB_GIT_AUTO_CLONE=true

# 2. Start the KB service:
docker compose up kb-service

# 3. The service automatically clones your repository on startup
# Repository is stored inside the container at /kb (ephemeral storage)
```

**Creating GitHub Personal Access Token**:
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope (for private repos) or `public_repo` (for public)
3. Add to `.env` as `KB_GIT_AUTH_TOKEN`
4. See [KB Remote Deployment Auth Guide](docs/kb-remote-deployment-auth.md) for details

**Storage Mode Options**:
- **`git`**: File-based storage with Git version control
- **`database`**: PostgreSQL storage for fast search and collaboration
- **`hybrid`**: PostgreSQL primary + Git backup (recommended for production)

**Git Sync Features**:
- **Auto-clone**: Repository automatically cloned on every container startup (1000+ files tested)
- **Container-only storage**: KB data lives at `/kb` inside container (ephemeral)
- **Local-remote parity**: Same behavior in local Docker and production deployments
- **Authentication**: Supports GitHub, GitLab, Bitbucket with Personal Access Tokens
- **Manual sync endpoints**: `/sync/from-git`, `/sync/to-git`, `/sync/status` (when hybrid mode active)

**Your Daily Workflow**:
1. **Edit KB files** in your local Obsidian vault or Git repository
2. **Git commit and push** your changes to GitHub
3. **Redeploy or restart** KB service to get latest changes
4. **AI agents access content** through MCP tools with latest data

**Persistent Volume Storage with Deferred Clone**:
- KB uses **persistent volume** at `/kb` (not `/kb/repository`)
- **Deferred clone**: Service starts immediately, git clone happens in background
- **One-time setup**: Once cloned, repository persists across deployments
- **Fast restarts**: After initial clone, service starts instantly with existing data
- Changes persist in volume (use Git sync for remote backup)

**Troubleshooting Git Sync**:
```bash
# Verify Git is installed in container
docker compose exec kb-service git --version  # Should show: git version 2.39.5

# Check repository inside container
docker compose exec kb-service ls -la /kb/

# Check KB health with repository status
./scripts/test.sh --url https://gaia-kb-dev.fly.dev kb-health

# View clone logs
docker compose logs kb-service | grep -E "(Cloning|Successfully cloned)"

# Manual sync commands (when hybrid mode active)
curl -X POST -H "X-API-Key: $API_KEY" http://kb-service:8000/sync/from-git

# Check sync status
curl -H "X-API-Key: $API_KEY" http://kb-service:8000/sync/status

# Test everything
./scripts/test-kb-git-sync.sh
```

**Performance Comparison** (from testing):
- **Search**: PostgreSQL 79x faster (14ms vs 1,116ms)
- **Collaboration**: PostgreSQL supports real-time multi-user editing
- **Version Control**: Git provides complete history and backup
- **External Edits**: Automatic sync from your Git repository

**Setup Steps**:
1. **Configure Aeonia KB**: `./scripts/setup-aeonia-kb.sh` (handles everything automatically)
2. **Or manual setup**: `./scripts/setup-kb-git-repo.sh` for other repositories
3. **Test sync**: `./scripts/test-kb-git-sync.sh`

**Remote Deployment Authentication**:
For production deployments, configure GitHub Personal Access Token:
```bash
# Fly.io
fly secrets set KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx -a gaia-kb-prod

# Docker/AWS
KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```
See [Remote Deployment Authentication Guide](docs/kb-remote-deployment-auth.md) for complete setup.

### Service URLs (Inter-service Communication)
- Gateway: `http://gateway:8000` (external: `localhost:8666`)
- Auth: `http://auth-service:8000`
- Asset: `http://asset-service:8000`
- Chat: `http://chat-service:8000`
- **KB: `http://kb-service:8000` (Knowledge Base)**
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

### Email Testing Pattern
When creating test accounts, always use the pattern `jason.asbahr+test#@gmail.com` where `#` is a unique identifier (e.g., timestamp, test name, etc.). This ensures test emails can be received for verification.

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

### Secret Management Issues (Primary Prevention)

⚠️ **CRITICAL: Always validate secrets after deployment**

```bash
# Quick secret validation for an environment
./scripts/validate-secrets.sh --env dev

# Validate and automatically fix issues
./scripts/validate-secrets.sh --env dev --fix

# Compare secrets between environments
./scripts/validate-secrets.sh --compare dev staging

# Emergency secret sync (if validation script unavailable)
fly secrets set SUPABASE_ANON_KEY="$(grep SUPABASE_ANON_KEY .env | cut -d'=' -f2-)" -a gaia-auth-dev
fly secrets set SUPABASE_JWT_SECRET="$(grep SUPABASE_JWT_SECRET .env | cut -d'=' -f2-)" -a gaia-auth-dev
```

**Enhanced Secret Health Monitoring:**
```bash
# Check auth service secrets health (enhanced health endpoint)
curl https://gaia-auth-dev.fly.dev/health | jq '.secrets'

# Expected healthy response:
# {
#   "status": "healthy",
#   "secrets_configured": 3,
#   "last_checked": "2025-07-19T00:15:00Z"
# }

# Warning signs:
# "status": "warning" - Secrets may be misconfigured
# "status": "unhealthy" - Missing or invalid secrets
# Missing "secrets" field - Old auth service version
```

**Deployment Best Practices:**
1. **Always use enhanced deploy script**: `./scripts/deploy.sh --env dev --services auth`
2. **Validate after deployment**: Script automatically checks secret health
3. **Monitor for drift**: Use `./scripts/validate-secrets.sh --compare dev staging`
4. **See full checklist**: [Deployment Validation Guide](docs/deployment-validation-checklist.md)

### API Key Authentication Issues

**Problem**: Services returning "Invalid API key" errors despite correct configuration.

**Quick Fix**:
```bash
# 1. Run the automated verification script
./scripts/verify-api-keys.sh

# 2. If mismatches found, the script will show exact commands to fix them

# 3. For manual checking:
fly secrets list -a gaia-gateway-dev | grep API_KEY
fly secrets list -a gaia-web-dev | grep WEB_API_KEY  # Note: WEB_ prefix!
fly secrets list -a gaia-auth-dev | grep API_KEY

# 4. Check web service is reading the key correctly
fly logs -a gaia-web-dev | grep "API Key:"
```

**Root Cause**: Pydantic settings with env_prefix may not work as expected. Use explicit Field(env="VAR_NAME") instead.

See [API Key Authentication Troubleshooting Guide](docs/troubleshooting-api-key-auth.md) for detailed debugging steps.

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

### 🛡️ Layout Integrity Protection

**⚠️ CRITICAL: Preventing Layout Breakages**

We have comprehensive protection against the "mobile-width on desktop" bug:

1. **Pre-commit hooks** - Catches layout issues before commit
2. **Layout integrity tests** - Automated tests for all viewports  
3. **CI/CD checks** - GitHub Actions validates every push
4. **Layout check script** - Run locally with `./scripts/layout-check.sh`

**Before ANY web UI changes:**
```bash
# Run layout integrity checks
./scripts/layout-check.sh

# Run layout tests
pytest tests/web/test_layout_integrity.py -v

# Install pre-commit hooks (one-time setup)
pre-commit install
```

See [Layout Constraints Guide](docs/layout-constraints.md) for critical CSS rules that must NEVER be violated.

### 🚨 FastHTML FT Async Error

**CRITICAL: Never make FastHTML route handlers async if they return FT objects!**

```python
# ❌ WRONG - Causes "FT can't be used in 'await' expression"
@app.post("/route")
async def handler(request):
    return gaia_error_message("Error")  # FT object

# ✅ CORRECT
@app.post("/route")  
def handler(request):
    return gaia_error_message("Error")  # FT object
```

**Rule: If it returns HTML components (FT objects), it CANNOT be async!**

See [FastHTML FT Async Guide](docs/fasthtml-ft-async-guide.md) for complete explanation.

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