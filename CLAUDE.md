# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🎮 Project Context: GAIA Platform

**What you're building**: A distributed AI platform powering MMOIRL (Massively Multiplayer Online In Real Life) games that blend real-world data with gameplay. Think Pokémon GO + AI agents + persistent memory.

**Key technical goals**:
- Sub-second AI response times for VR/AR experiences
- 100% backward compatibility with existing clients
- Multi-provider AI orchestration (Claude, OpenAI, etc.)
- Git-synchronized knowledge bases with enterprise permissions

**Architecture**: Microservices (Gateway, Auth, Chat, KB, Asset, Web) with hot-reloading Docker setup.

→ See [README-FIRST](docs/README-FIRST.md) for full project vision and context

## 🔥 Local Development with Hot Reloading

**All Docker services are configured with `--reload` for fast local development!**

✅ **Code changes take effect immediately** - No rebuilding or restarting containers required  
✅ **Volume mounts**: `./app:/app/app` enables live code reloading  
✅ **Services with hot reload**: auth, chat, gateway, asset, kb, web  

**Development Workflow:**
1. Make code changes in your editor
2. Changes are automatically detected and services reload
3. Test immediately - no Docker restart needed

**Only restart containers when:**
- Adding new dependencies to requirements.txt
- Changing Dockerfile configuration  
- Modifying docker compose.yml settings
- Environment variable changes requiring container restart

**Quick Test After Changes:**
```bash
./scripts/test.sh --local health  # Verify all services healthy
./scripts/test.sh --local chat "test message"  # Test functionality
```

## 🚨 BEFORE YOU START: Required Reading

1. **Web UI Changes** → MUST read [HTMX + FastHTML Debugging Guide](docs/htmx-fasthtml-debugging-guide.md) and [Auth Layout Isolation](docs/auth-layout-isolation.md)
2. **Authentication Setup** → Always check [API Key Configuration Guide](docs/api-key-configuration-guide.md)
3. **Testing** → Review [Testing Guide](docs/testing/TESTING_GUIDE.md) - ALWAYS use pytest-for-claude.sh, NOT curl
4. **Adding Services** → Follow [Adding New Microservice](docs/adding-new-microservice.md)
5. **Deployment** → Check [Smart Scripts & Deployment](docs/smart-scripts-deployment.md)

## ⚠️ REMINDER TO CLAUDE CODE
**BEFORE ANY WEB UI CHANGES:** You MUST read the HTMX + FastHTML Debugging Guide and Auth Layout Isolation docs first. The user will remind you if you don't, because layout bugs "keep coming back" when documentation is ignored. Always use `auth_page_replacement()` for auth responses and proper HTMX container targeting patterns.

**COMMUNICATION REQUIREMENT:** Tell the user what you are planning to do before you do it and what you actually did after you accomplished the goal. This helps with transparency and ensures alignment between expectations and results. Make sure you explain your hypothesis and assumptions.

## 🤖 Claude Code Agents
Specialized agents are available for specific tasks. Use them when working in their domains:

- **[Tester Agent](docs/agents/tester.md)** - Writing tests, running tests, debugging, and distributed systems troubleshooting
  - Use when: Writing new tests, running tests, debugging failures, investigating issues, creating test patterns
  - Knows: All test patterns, async runners, E2E requirements, common issues, how to write proper tests

More agents coming soon: Builder, Deployer, Documenter

## 🎯 Current Development Focus (July 2025)

**Completed Systems**:
- ✅ Supabase Authentication (no PostgreSQL fallback when AUTH_BACKEND=supabase)
- ✅ KB Git Sync with deferred initialization (fast startup, 10GB volumes)
- ✅ MCP-Agent hot loading (response time: 5-10s → 1-3s)
- ✅ Intelligent chat routing (simple: ~1s, complex: ~3s)
- ✅ mTLS + JWT infrastructure (Phases 1-2, 100% backward compatible)
- ✅ Redis caching (97% performance improvement)

**Active Development**:
- 🔧 Getting Supabase service role key for full remote functionality
- 🔧 Implementing KB permission manager with RBAC
- 🔧 Multi-user KB namespaces and sharing features
- 🔧 Phase 3: Migrate web/mobile clients to Supabase JWTs
- 🔧 Phase 4: Remove legacy API key validation

**Key Insights**:
- See [Supabase Auth Migration Learnings](docs/supabase-auth-migration-learnings.md) for architectural decisions
- Check [KB Git Sync Learnings](docs/kb-git-sync-learnings.md) for deployment patterns
- Review [PostgreSQL Simplicity Lessons](docs/postgresql-simplicity-lessons.md) to avoid overengineering

## 🚀 Smart Service Deployment & Discovery

**🎯 SOLVED: No More Hardcoded Service URLs**

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

→ See [Service Registry Pattern](docs/service-registry-pattern.md) for complete implementation

## 🧪 Testing: Critical Requirements

**🤖 USE THE TESTER AGENT**: When writing tests, working with tests, debugging test failures, or investigating issues, engage the [Tester Agent](docs/agents/tester.md). This specialized agent has comprehensive knowledge of our testing infrastructure, patterns, common issues, and knows how to write proper tests following our patterns.

**🎯 THE ULTIMATE META LESSON ON TEST FAILURES:**
> **Test failures are rarely about the tests themselves.** They're usually telling you about:
> - **Missing features** (e.g., auto-scroll functionality wasn't implemented)
> - **Configuration mismatches** (e.g., Docker pytest.ini had hidden `-n auto`)
> - **Timing/ordering issues** (e.g., mocking APIs after navigation already started)
> - **Environmental differences** (e.g., Docker vs local configurations)
>
> **Listen to what tests are trying to tell you.** When you find yourself fighting to make tests pass, stop and ask: "What is this test specification telling me about what the app should do?" Often, the app is incomplete, not the test.

**🚨 ALWAYS USE ASYNC TEST RUNNER**
```bash
# ❌ WRONG: Direct pytest (will timeout after 2 minutes)
pytest tests/ -v

# ✅ RIGHT: Async execution for Claude Code
./scripts/pytest-for-claude.sh tests/ -v
./scripts/check-test-progress.sh  # Monitor progress
```

**🔐 E2E TESTS: REAL AUTHENTICATION ONLY**
- **NO MOCKS IN E2E TESTS** - Use real Supabase authentication
- Requires valid `SUPABASE_SERVICE_KEY` in `.env`
- Use `TestUserFactory` for consistent test user creation
- Always clean up test users after tests

```bash
# Run E2E tests with real auth
./scripts/pytest-for-claude.sh tests/e2e/test_real_auth_e2e.py -v
```

### 🎯 Systematic Integration Test Patterns

**🔧 SYSTEMATIC FIXES OVER INDIVIDUAL FIXES**
- When multiple tests fail with similar patterns, identify the systematic root cause
- Fix the pattern once rather than fixing each test individually
- Look for common anti-patterns that affect multiple tests

**🚨 COMMON INTEGRATION TEST PATTERNS TO FIX:**

**1. Authentication/Navigation Pattern**
```bash
# ❌ BRITTLE PATTERN: Manual login + expect navigation
await page.goto(f'{WEB_SERVICE_URL}/login')
await page.fill('input[name="email"]', 'test@test.local')  # Hardcoded!
await page.fill('input[name="password"]', 'test123')       # Hardcoded!
await page.click('button[type="submit"]')
await page.wait_for_url('**/chat')  # ← TIMES OUT

# ✅ ROBUST PATTERN: Use shared auth helper
await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)
# Handles entire flow: navigation, form filling, waiting, error handling
```

**2. Route Mocking vs Real Auth Pattern**
```bash
# ❌ WRONG ORDER: Mocks interfere with real auth
await page.route("**/auth/login", mock_handler)  # ← Blocks real login!
await BrowserAuthHelper.login_with_real_user(page, creds)  # Fails

# ✅ CORRECT ORDER: Real auth first, then mocks for specific functionality
await BrowserAuthHelper.login_with_real_user(page, creds)  # Real auth works
await page.route("**/api/v1/chat", mock_error_handler)     # Mock specific APIs
```

**3. CSS Selector Robustness Pattern**
```bash
# ❌ BRITTLE: Single selector, synchronous, no fallbacks
message_input = await page.query_selector('input[name="message"]')  # ← Fails if textarea
await message_input.fill("test")  # ← NoneType error if not found

# ✅ ROBUST: Multiple selectors, async expectations, fallbacks  
message_input = page.locator('textarea[name="message"], input[name="message"]').first
await expect(message_input).to_be_visible()  # Wait + verify
await message_input.fill("test")

# ❌ INVALID: Mixing CSS + text selectors
await page.wait_for_selector('[role="alert"], .error, text="error"')  # Syntax error

# ✅ CORRECT: Proper Playwright locator composition
error_locator = page.locator('[role="alert"], .error').or_(page.locator('text=error'))
await expect(error_locator.first).to_be_visible()
```

**4. Test Method Signature Pattern**
```bash
# ❌ MISSING: Test uses fixture but doesn't declare it
async def test_something_with_auth(self):
    await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)  # ← NameError

# ✅ COMPLETE: All required fixtures declared
async def test_something_with_auth(self, test_user_credentials):
    await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)  # ✓ Works
```

**🎯 SYSTEMATIC DIAGNOSIS APPROACH:**
1. **Identify the pattern**: Look for identical/similar failures across multiple tests
2. **Find the root cause**: Usually authentication, timing, or CSS selector issues  
3. **Create systematic fix**: Update the pattern once, applies to all affected tests
4. **Validate the fix**: Run all affected tests to ensure systematic improvement

**📊 SUCCESS METRICS:**
- Multiple test failures → Single pattern fix → Multiple tests pass
- Example: 4 navigation timeout failures → 1 auth pattern fix → 4 tests pass

### 💡 Integration Test Success Story: 53 → 4 Failures

**🎯 CRITICAL INSIGHT: Integration Tests Should Test Real System Behavior, Not Mocks**

From August 2025 integration test fixing session that achieved **85-90% improvement**:

**Started with**: 53 failing tests in `test_full_web_browser.py`  
**Result**: 4-5 failing tests through systematic pattern fixes

**Key Philosophy Shift**: User feedback: *"It's an integration test right?"*
- **Before**: Mocking responses, making tests "flexible" (essentially testing nothing)
- **After**: Using real auth endpoints, real credentials, testing actual system behavior
- **Validation**: When `test_concurrent_form_submissions` was converted from mocked to real integration testing, it **passed** - proving the system works correctly

**Root Insight**: When integration tests use mocks and those mocks aren't being called, it often indicates **real system issues** (like HTMX not loading properly), not test problems.

**Remaining failures likely indicate actual bugs**:
- `test_htmx_form_submission_without_page_reload` - HTMX JavaScript might not be loading
- `test_message_auto_scroll` - Missing scroll-to-bottom implementation
- `test_message_persistence_on_refresh` - Backend message loading not implemented
- `test_network_error_handling` - HTMX error handling + toast system integration issues

**Architecture Validation**: User observation: *"Timing has turned out to often be either parallel run resource issues or underlying bugs"* - test failures should be investigated as potential system issues, not dismissed as flaky tests.

See:
- **[Tester Agent](docs/agents/tester.md)** - Use this agent for ALL testing tasks!
- [Testing Guide](docs/testing/TESTING_GUIDE.md) - Main testing documentation
- [Testing Best Practices](docs/testing/TESTING_BEST_PRACTICES.md) - Patterns and practices
- [Test Infrastructure](docs/testing/TEST_INFRASTRUCTURE.md) - Technical details

## 🧠 Development Philosophy & Problem-Solving Approach

**🛑 STOP GUESSING - START RESEARCHING**
- When deployment issues occur, resist the urge to try random fixes
- Search for documented issues: `"[platform] [error-type] [technology] troubleshooting"`
- Example: "Fly.io internal DNS connection refused microservices"

**🔬 SYSTEMATIC DIAGNOSIS**
- Test your hypothesis before implementing fixes
- Verify individual components work before assuming system-wide issues
- Use platform-specific debugging tools (e.g., `fly ssh console`)

**🚨 RECOGNIZE ANTI-PATTERNS**
- "One step forward, one step back" = you're guessing, not diagnosing
- Timeouts during deployment = often infrastructure issues, not code issues
- Services work individually but not together = networking/discovery problem

**🧪 USE TEST SCRIPTS, NOT CURL**
- ALWAYS use automated tests instead of manual curl commands
- If you need to test something new, ADD it to the test suite
- Automated tests capture knowledge, curl commands vanish with your terminal
- See [Testing Guide](docs/testing/TESTING_GUIDE.md) for complete testing documentation

### 🎯 Problem-Solving Patterns

**1. Question the Problem Definition**
- When something fails, don't assume the obvious failure point is the root cause
- Before fixing, ask "Why was it designed this way?" and "What problem was the original design solving?"

**2. Respect Existing Abstractions**
- Well-designed systems have fixtures, patterns, and abstractions for reasons
- When you see a shared resource pattern (like `shared_test_user`), it's likely solving a resource constraint or rate limiting issue

**3. Understand the System's Constraints**
- External systems impose constraints that shape our code design
- Rate limits, validation rules, and security measures aren't bugs to work around - they're boundaries that inform architecture

**4. Complexity is a Code Smell**
- If your solution is more complex than the original, you're probably solving the wrong problem
- Simple failing test → Complex multi-step solution = Step back and reconsider

**5. Debug the Assumption, Not Just the Code**
- Failed tests often reveal incorrect assumptions about system behavior
- "User doesn't exist" wasn't a bug - it was a misunderstanding of fixture lifecycle

**6. Context Over Correctness**
- The "correct" solution in isolation may be wrong in context
- Creating fresh test users is "correct" but wrong when the system has rate limits

**7. Error Messages are Features**
- Different error messages often indicate different layers of system protection
- "Invalid email domain" → "Rate limit exceeded" → "User exists" shows a validation pipeline, not random failures

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
- [Testing Guide](docs/testing/TESTING_GUIDE.md) - **MAIN** - Complete testing documentation
- [Testing Best Practices](docs/testing/TESTING_BEST_PRACTICES.md) - Patterns and best practices
- [Test Infrastructure](docs/testing/TEST_INFRASTRUCTURE.md) - Async runner, Docker, resources
- [Command Reference](docs/current/development/command-reference.md) - Correct command syntax
- [Environment Setup](docs/current/development/dev-environment-setup.md) - Local development workflow

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
- [Mobile Testing](docs/testing/mobile-testing-guide.md) - Testing on mobile devices
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
- `docker compose` (with space) - NOT `docker compose` (with hyphen)
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
4. **DON'T** run pytest directly - use `./scripts/pytest-for-claude.sh` instead
5. **DON'T** use mock authentication in E2E tests - real auth only!
6. **DON'T** debug tests without the [Tester Agent](docs/agents/tester.md) - it knows all patterns!

## 📋 Quick Reference: Essential Commands

### Daily Development
```bash
# Start services
docker compose up

# Run tests - ALWAYS use this instead of 'pytest' command!
./scripts/pytest-for-claude.sh             # Async pytest runner (avoids timeouts)
./scripts/check-test-progress.sh           # Check test progress
./scripts/pytest-for-claude.sh tests/e2e -v   # E2E tests (requires SUPABASE_SERVICE_KEY)
./scripts/test.sh --local all              # Legacy API test suite

# User management
./scripts/manage-users.sh list
./scripts/manage-users.sh create user@example.com

# KB Git sync (Aeonia team)
./scripts/setup-aeonia-kb.sh               # Auto-configures Obsidian vault
# → Full KB config details in docs/kb-git-sync-guide.md
```

### Docker Container Building

**⚠️ CRITICAL: Docker builds WILL timeout in Claude Code!**
The Bash tool has a 2-minute timeout. Full builds take 5-10 minutes. Here's the correct approach:

```bash
# Step 1: Create the async build script (one time setup)
cat > docker-build-async.sh << 'EOF'
#!/bin/bash
# Docker Async Build Script for Claude Code

LOG_FILE="docker-build-$(date +%Y%m%d-%H%M%S).log"
PID_FILE=".docker-build.pid"

# Check if a build is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "❌ Build already in progress (PID: $OLD_PID)"
        echo "Check status with: ./docker-build-status.sh"
        exit 1
    else
        rm "$PID_FILE"
    fi
fi

# Start the build
echo "🚀 Starting Docker build in background..."
docker compose build --no-cache > "$LOG_FILE" 2>&1 &
BUILD_PID=$!
echo $BUILD_PID > "$PID_FILE"

echo "✅ Build started successfully!"
echo "📄 Log file: $LOG_FILE"
echo "🔍 PID: $BUILD_PID"
echo ""
echo "Next steps:"
echo "1. Check status: ./docker-build-status.sh"
echo "2. Watch logs: tail -f $LOG_FILE"
echo "3. When complete: docker compose up -d"
EOF

# Step 2: Create the status checker script
cat > docker-build-status.sh << 'EOF'
#!/bin/bash
# Docker Build Status Checker

PID_FILE=".docker-build.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "✅ No build in progress"
    exit 0
fi

PID=$(cat "$PID_FILE")
if ps -p "$PID" > /dev/null 2>&1; then
    echo "🔄 Build still running (PID: $PID)"
    
    # Find the latest log file
    LOG_FILE=$(ls -t docker-build-*.log 2>/dev/null | head -1)
    if [ -n "$LOG_FILE" ]; then
        echo "📊 Progress:"
        tail -5 "$LOG_FILE"
    fi
else
    echo "✅ Build completed!"
    rm "$PID_FILE"
    
    # Check if build was successful
    LOG_FILE=$(ls -t docker-build-*.log 2>/dev/null | head -1)
    if [ -n "$LOG_FILE" ] && grep -q "Successfully built" "$LOG_FILE"; then
        echo "🎉 All services built successfully!"
        echo "Run: docker compose up -d"
    else
        echo "❌ Build may have failed. Check the log:"
        echo "tail -100 $LOG_FILE"
    fi
fi
EOF

# Make scripts executable
chmod +x docker-build-async.sh docker-build-status.sh

# Step 3: Run the build
./docker-build-async.sh

# Step 4: Check status periodically
./docker-build-status.sh
```

**Quick Commands After Setup:**
```bash
# Start a new build
./docker-build-async.sh

# Check if build is done
./docker-build-status.sh

# Watch build progress live
tail -f docker-build-*.log

# Once complete, start services
docker compose up -d
```

**This approach:**
- ✅ Returns control immediately (no timeout)
- ✅ Prevents multiple concurrent builds
- ✅ Tracks build status with PID
- ✅ Shows progress updates
- ✅ Detects successful completion
- ✅ Provides clear next steps

**⏱️ Actual Build Times:**
- First build (no cache): 10-15 minutes
- Subsequent builds (with cache): 3-5 minutes
- Check periodically with `./docker-build-status.sh`
- Build continues even if you close Claude Code

### Remote Operations
```bash
# Deploy with validation
./scripts/deploy.sh --env dev --services auth

# Validate secrets
./scripts/validate-secrets.sh --env dev
./scripts/validate-secrets.sh --env dev --fix

# Monitor services
./scripts/manage.sh status
./scripts/manage.sh monitor dev
```

### Database Management
```bash
# Portable database operations
./scripts/init-database-portable.sh --env dev --user admin@gaia.dev
./scripts/migrate-database.sh --env dev --migration migrations/001_add_feature.sql
./scripts/monitor-database.sh --env dev --report health
```

## 🏗️ Architecture Quick Reference

### Service URLs (Docker Network)
- Gateway: `http://gateway:8000` (external: `localhost:8666`)
- Auth: `http://auth-service:8000`
- Chat: `http://chat-service:8000`
- KB: `http://kb-service:8000`
- Redis: `redis://redis:6379`

→ See [Architecture Overview](docs/architecture-overview.md) for complete service details

### Key Authentication Patterns
- `get_current_auth_unified()` - Handles API keys + Supabase JWTs
- `validate_auth_for_service()` - Inter-service auth validation
- `/internal/validate` - Auth service coordination endpoint

### NATS Messaging
- `gaia.service.health` - Service health updates
- `gaia.auth.*` - Authentication events
- `gaia.chat.*` - Chat processing events

→ See [Architecture Overview](docs/architecture-overview.md#asynchronous-communication) for event models

## 📁 Working on Specific Areas?

### Authentication & Security
→ [Authentication Guide](docs/authentication-guide.md) - Complete dual auth patterns  
→ [Supabase Auth Implementation](docs/supabase-auth-implementation-guide.md) - Supabase specifics  
→ [mTLS Certificate Management](docs/mtls-certificate-management.md) - Certificate infrastructure  
→ [RBAC System Guide](docs/rbac-system-guide.md) - Role-based access control  

### Knowledge Base (KB)
→ [KB Git Sync Guide](docs/kb-git-sync-guide.md) - **Full Git sync config, setup, troubleshooting**  
→ [Multi-User KB Guide](docs/multi-user-kb-guide.md) - Teams and workspaces  
→ [KB Remote Deployment Auth](docs/kb-remote-deployment-auth.md) - Production Git auth  
→ [KB Deployment Checklist](docs/kb-deployment-checklist.md) - Step-by-step deployment  

### Microservices & Deployment
→ [Adding New Microservice](docs/adding-new-microservice.md) - Service creation guide  
→ [Service Creation Automation](docs/service-creation-automation.md) - Automated setup  
→ [Deployment Best Practices](docs/deployment-best-practices.md) - Local-remote parity  
→ [Fly.io Deployment Configuration](docs/flyio-deployment-config.md) - Platform specifics  

### Troubleshooting
→ [API Key Authentication Troubleshooting](docs/troubleshooting-api-key-auth.md)  
→ [Fly.io DNS Troubleshooting](docs/troubleshooting-flyio-dns.md)  
→ [HTMX + FastHTML Debugging Guide](docs/htmx-fasthtml-debugging-guide.md)  

### Performance & Optimization
→ [Optimization Guide](docs/optimization-guide.md) - Quick wins  
→ [Redis Integration](docs/redis-integration.md) - Caching patterns  
→ [Microservices Scaling Guide](docs/microservices-scaling.md) - Scaling strategies  

## 🚨 Critical Operational Knowledge

### Secret Management
```bash
# Always validate after deployment
./scripts/validate-secrets.sh --env dev

# Emergency secret sync
fly secrets set SUPABASE_ANON_KEY="$(grep SUPABASE_ANON_KEY .env | cut -d'=' -f2-)" -a gaia-auth-dev
```

### Fly.io DNS Issues
**Problem**: Gateway shows "degraded" but services are healthy  
**Solution**: Switch to public URLs (internal DNS unreliable)
```bash
fly secrets set -a gaia-gateway-dev \
  "CHAT_SERVICE_URL=https://gaia-chat-dev.fly.dev" \
  "AUTH_SERVICE_URL=https://gaia-auth-dev.fly.dev"
```

### FastHTML FT Async Error (Unverified)
**Note**: This pattern is unproven and needs testing with a future branch merge
```python
# ❌ POSSIBLY WRONG - May cause "FT can't be used in 'await' expression"
@app.post("/route")
async def handler(request):
    return gaia_error_message("Error")  # FT object

# ✅ POSSIBLY CORRECT
@app.post("/route")  
def handler(request):
    return gaia_error_message("Error")  # FT object
```

### Layout Protection
```bash
# Before ANY web UI changes
./scripts/layout-check.sh
pytest tests/web/test_layout_integrity.py -v
```

## 📚 Complete Documentation Index

All documentation is in the `docs/` directory. Key resources for removed content:

### Core Documentation (previously in CLAUDE.md)
- [Architecture Overview](docs/architecture-overview.md) - **Service URLs, NATS subjects, shared modules**
- [Supabase Configuration](docs/supabase-configuration.md) - **Email config, redirect URLs**
- [Dev Environment Setup](docs/dev-environment-setup.md) - **Configuration details**
- [Testing and Quality Assurance](docs/testing-and-quality-assurance.md) - **Testing requirements**

### Documentation by Category
- **Architecture**: Overview, patterns, microservices design
- **Authentication**: API keys, Supabase, mTLS, RBAC
- **Deployment**: Scripts, best practices, platform guides
- **Knowledge Base**: Git sync, multi-user, deployment
- **Troubleshooting**: Common issues and solutions
- **Development**: Testing, optimization, UI guidelines

### Recent Important Additions
- [MCP-Agent Hot Loading](docs/mcp-agent-hot-loading.md)
- [Intelligent Chat Routing](docs/intelligent-chat-routing.md)
- [Deferred Initialization Pattern](docs/deferred-initialization-pattern.md)
- [PostgreSQL Simplicity Lessons](docs/postgresql-simplicity-lessons.md)