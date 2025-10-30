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

1. **Database Setup** → MUST run [Database Initialization Guide](docs/current/development/database-initialization-guide.md) - Required for persona functionality
2. **Web UI Changes** → MUST read [HTMX + FastHTML Debugging Guide](docs/htmx-fasthtml-debugging-guide.md) and [Auth Layout Isolation](docs/auth-layout-isolation.md)
3. **Authentication Setup** → Always check [API Key Configuration Guide](docs/api-key-configuration-guide.md)
4. **Testing** → Review [Testing Guide](docs/testing/TESTING_GUIDE.md) - ALWAYS use pytest-for-claude.sh, NOT curl
5. **Adding Services** → Follow [Adding New Microservice](docs/adding-new-microservice.md)
6. **Deployment** → Check [Smart Scripts & Deployment](docs/smart-scripts-deployment.md)

## ⚠️ REMINDER TO CLAUDE CODE
**BEFORE ANY WEB UI CHANGES:** You MUST read the HTMX + FastHTML Debugging Guide and Auth Layout Isolation docs first. The user will remind you if you don't, because layout bugs "keep coming back" when documentation is ignored. Always use `auth_page_replacement()` for auth responses and proper HTMX container targeting patterns.

**COMMUNICATION REQUIREMENT:** Tell the user what you are planning to do before you do it and what you actually did after you accomplished the goal. This helps with transparency and ensures alignment between expectations and results. Make sure you explain your hypothesis and assumptions.

## 🤖 Claude Code Agents

### Available Agents
Agents are defined in `.claude/agents/` directory. Available agents:

- **Tester** (`.claude/agents/tester.md`) - Writing tests, running tests, debugging, and distributed systems troubleshooting
  - Use when: Writing new tests, running tests, debugging failures, investigating issues, creating test patterns
  - Knows: All test patterns, async runners, E2E requirements, common issues, how to write proper tests

- **Builder** (`.claude/agents/builder.md`) - Implementing features and fixing bugs
  - Use when: Need to implement code to make tests pass, fix bugs, refactor code
  - Knows: GAIA architecture, code patterns, microservices structure

- **Reviewer** (`.claude/agents/reviewer.md`) - Code quality and security review
  - Use when: Need code review, security audit, performance check
  - Knows: Security best practices, code standards, performance patterns

More agents coming soon: Deployer, Documenter

### When to Use Agents vs Direct Claude
- **Use Agents for**:
  - Modular, well-defined tasks (writing tests, implementing features)
  - Tasks requiring specialized expertise or perspective
  - Multi-step workflows with clear handoffs
  - Parallel workstreams that can be isolated

- **Use Direct Claude for**:
  - Exploratory debugging and investigation
  - One-off commands or quick fixes
  - Interactive problem-solving
  - Tasks requiring broad context awareness

### Agent Invocation Best Practices
1. **Be Explicit**: "Use the Tester Agent to write integration tests for the new chat endpoint"
2. **Provide Context**: Give agents clear summaries of current state and objectives
3. **Use Structured Handoffs**: Pass data between agents using clear formats (JSON, Markdown)
4. **Maintain Focus**: Keep each agent session focused on its specific task

### How to Invoke Agents
For detailed invocation instructions, see [How to Invoke Agents](docs/agents/how-to-invoke-agents.md).

**Quick Commands**:
```bash
/agents                    # List all available agents
/agents:tester            # Switch to the Tester Agent
/clear                    # Reset conversation context
/compact                  # Summarize long conversations
```

### Example Multi-Agent Workflow
```bash
# 1. Tester Agent writes failing tests
/agents:tester
Write tests for the new user registration feature

# 2. Builder Agent implements code (coming soon)
/agents:builder
Implement code that makes the registration tests pass

# 3. Tester Agent validates
/agents:tester
Run all tests and verify they pass

# 4. Reviewer Agent checks quality (coming soon)
/agents:reviewer
Review the implementation for security and best practices
```

### Agent Context Management
- **Curate Working Directory**: Only include files relevant to the agent's task
- **Separate Sessions**: Use different conversations for different agent tasks
- **Provide Recaps**: When switching agents, summarize what's been done
- **Limit Scope**: Don't overload agents with unnecessary context

## 🌐 Symphony Network: Multi-Agent Collaboration

**What is Symphony**: A distributed messaging system enabling multiple Claude agents across different repositories/contexts to collaborate on complex tasks.

**Key Concept**: Symphony is NOT for immediate responses. It's a coordination layer where agents share knowledge, ask questions, and collaborate asynchronously.

### Available Symphony Tools
- `room_join` / `room_leave` - Join/leave collaboration channels
- `send_message` / `get_messages` - Communicate with other agents
- `get_notifications` - Check for @mentions and tasks
- `create_task` / `get_tasks` - Coordinate work across agents
- `memory_store` / `memory_retrieve` - Persistent cross-agent memory
- `file_read` / `file_write` / `file_list` - Shared workspace

### 🚨 CRITICAL: Symphony Response Protocol

**NEVER respond immediately to Symphony messages!** Messages are immutable once sent.

**Before responding, you MUST:**
1. **Read carefully**: Understand what's being asked and who it's directed to
2. **Verify facts**: Check actual codebase/docs, don't make assumptions
3. **Consider relevance**: Is your response needed? Are you the right agent?
4. **Check tags**: If message tags specific roles (e.g., `@unity-dev`), they may not want your input
5. **Wait and observe**: Let agents with direct knowledge respond first

**When to respond:**
- ✅ You have **verified** information from the codebase
- ✅ The question directly relates to work you just completed
- ✅ You're tagged/mentioned specifically
- ✅ No other agent has provided the answer after reasonable time

**When NOT to respond:**
- ❌ Making assumptions about code you haven't seen
- ❌ Speculating about architecture without verification
- ❌ Immediately after seeing a message (take time to think!)
- ❌ Questions tagged for other agent types

### Symphony Rooms
- **`interactions`**: AR/game interaction design, MMOIRL architecture
- **`kb`**: Knowledge Base implementation, Git sync, RBAC
- **`testing`**: Testing strategies, E2E coordination
- *(More rooms as needed)*

### Example: Proper Symphony Usage

**❌ WRONG** (what NOT to do):
```
User: "get latest message from kb on symphony"
Claude: [reads message] → [immediately responds with assumptions]
Result: Incorrect information, can't delete message
```

**✅ RIGHT** (proper approach):
```
User: "get latest message from kb on symphony"
Claude: [reads message] → [analyzes question] → [checks codebase]
        → [verifies facts] → [considers if response adds value]
        → [either responds with verified info OR stays silent]
```

### Symphony Best Practices
1. **Think first, respond later** - Messages are permanent
2. **Verify everything** - Check code, don't assume
3. **Add value** - Only respond if you have something verified and useful
4. **Correct mistakes** - Send follow-up if you realize you were wrong
5. **Use for coordination** - Great for asking questions, sharing findings, coordinating work

### Integration with Claude Agents
- **Claude Agents**: Execute local tasks (testing, building, reviewing)
- **Symphony**: Coordinate across repositories and agent contexts
- **Pattern**: Use local agents for work, Symphony for collaboration/knowledge sharing

## 🎯 Current Development Focus (October 2025)

**Completed Systems**:
- ✅ Supabase Authentication (no PostgreSQL fallback when AUTH_BACKEND=supabase)
- ✅ KB Git Sync with deferred initialization (fast startup, 10GB volumes)
- ✅ MCP-Agent hot loading (response time: 5-10s → 1-3s)
- ✅ Intelligent chat routing (simple: ~1s, complex: ~3s)
- ✅ mTLS + JWT infrastructure (Phases 1-2, 100% backward compatible)
- ✅ Redis caching (97% performance improvement)
- ✅ AR Waypoints System - `/api/v0.3/locations/nearby` endpoint (AEO-10 partial)
- ✅ Admin Command System - @ prefix commands for world building (<30ms response time)
- ✅ NPC Interaction System - Natural language conversations with trust/relationship tracking

**AR Waypoints Implementation** (AEO-10):
- ✅ 37 waypoints loaded from KB markdown files (`/kb/experiences/wylding-woods/waypoints/`)
- ✅ GPS-based filtering (Haversine distance calculation)
- ✅ Unity JSON format transformation
- ✅ TDD implementation (5/5 tests passing)
- ⏸️ Mission parameters (deferred - to be added with full mission system)
- ⏸️ Mission-based waypoint ordering (Unity expects array order)
- ⚠️ Technical debt: Logic in Gateway (should be separate Locations service)

**Admin Command System** (Complete):
- ✅ Auto-discovery from `/kb/experiences/{exp}/admin-logic/` directory
- ✅ @ prefix distinguishes admin from player commands
- ✅ Zero LLM latency (<30ms response time vs 1-3s for player commands)
- ✅ 8+ admin commands: @list-waypoints, @inspect-waypoint, @edit-waypoint, @create-waypoint, @delete-waypoint, @list-items, @inspect-item
- ✅ Safety mechanisms: CONFIRM required for destructive operations
- ✅ Metadata tracking: created_by, last_modified, timestamps
- ⚠️ Permission enforcement: Placeholder only (future RBAC implementation)
- 📚 See: [Admin Command System](docs/admin-command-system.md) for complete reference

**NPC Interaction System** (Complete):
- ✅ Natural language conversations via `talk` command
- ✅ LLM-powered authentic, in-character dialogue
- ✅ Per-player state tracking: trust level (0-100), conversation history (last 20 turns)
- ✅ Relationship progression: trust gates content and quest availability
- ✅ Quest integration foundation: NPCs can offer quests based on trust level
- ✅ Tested with Louisa (Dream Weaver fairy) in wylding-woods
- 📚 See: [NPC Interaction System](docs/npc-interaction-system.md) for complete reference

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

**🚨 CRITICAL PRINCIPLE: Tests Define Truth** - When tests fail, FIX THE CODE, not the test! Tests are specifications of correct behavior. Changing tests to match broken code is a critical anti-pattern.

**🤖 USE THE TESTER AGENT**: For ALL testing tasks, use `/agents:tester`. The Tester Agent has comprehensive knowledge of testing patterns, debugging strategies, and infrastructure details.

**🚨 ALWAYS USE ASYNC TEST RUNNER**
```bash
# ❌ WRONG: Direct pytest (will timeout after 2 minutes)
pytest tests/ -v

# ✅ RIGHT: Async execution for Claude Code
./scripts/pytest-for-claude.sh tests/ -v
./scripts/check-test-progress.sh  # Monitor progress
```

**🔐 E2E TESTS: REAL AUTHENTICATION ONLY**
- NO MOCKS IN E2E TESTS - Use real Supabase authentication
- Requires valid `SUPABASE_SERVICE_KEY` in `.env`
- Use `TestUserFactory` for consistent test user creation
- Always clean up test users after tests

See [Testing Guide](docs/testing/TESTING_GUIDE.md) for comprehensive documentation.

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
- [Web Service Standardization](docs/web-service-standardization-spec.md) - **NEW** - Accessibility and testing standards
- [Web Testing Strategy](docs/web-testing-strategy-post-standardization.md) - **NEW** - How testing will improve

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

### Long-Running Operations (Docker Builds & Deployments)

**⚠️ CRITICAL: All long operations WILL timeout in Claude Code after 2 minutes!**

This includes:
- Docker builds (5-10 minutes)
- Multi-service deployments (15-20 minutes) 
- Large test suites (10+ minutes)

**Universal Pattern for Long Operations:**

```bash
# TEMPLATE: Replace {COMMAND} with your actual command
nohup {COMMAND} > operation.log 2>&1 &

# Monitor progress
tail -f operation.log

# Check status (use appropriate status command)
{STATUS_CHECK_COMMAND}
```

**Examples:**

**Docker Builds:**
```bash
# Run build in background
nohup docker compose build --no-cache > docker-build.log 2>&1 &

# Monitor
tail -f docker-build.log

# Check status
docker compose ps
```

**Deployments:**
```bash
# Deploy all services to dev (no code changes)
nohup ./scripts/deploy.sh --env dev --services all --remote-only > deploy.log 2>&1 &

# Deploy with code changes (ALWAYS use --rebuild!)
nohup ./scripts/deploy.sh --env dev --services all --remote-only --rebuild > deploy.log 2>&1 &

# Monitor progress
tail -f deploy.log

# Check deployment status
./scripts/manage.sh status dev

# Verify deployment has latest code
curl https://gaia-gateway-dev.fly.dev/health | jq
```

**Large Test Suites:**
```bash
# Run tests in background
nohup ./scripts/pytest-for-claude.sh tests/e2e -v > test-results.log 2>&1 &

# Monitor progress
tail -f test-results.log

# Check if tests are still running
ps aux | grep pytest
```

### Docker Container Building (Legacy Documentation)

**Note: Use the universal pattern above instead of this Docker-specific script**

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
- **Deployment**: [Guide](docs/deployment/deployment-guide.md) | [Quick Reference](docs/deployment/deployment-reference.md) | [Fly.io](docs/deployment/flyio-setup.md) | [Supabase](docs/deployment/supabase-setup.md)
- **Knowledge Base**: Git sync, multi-user, deployment
- **Troubleshooting**: Common issues and solutions
- **Development**: Testing, optimization, UI guidelines

### Recent Important Additions
- [MCP-Agent Hot Loading](docs/mcp-agent-hot-loading.md)
- [Intelligent Chat Routing](docs/intelligent-chat-routing.md)
- [Deferred Initialization Pattern](docs/deferred-initialization-pattern.md)
- [PostgreSQL Simplicity Lessons](docs/postgresql-simplicity-lessons.md)