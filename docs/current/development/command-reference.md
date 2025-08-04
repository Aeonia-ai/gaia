# Command Reference: Correct Syntax & Versions

This document ensures we always use the correct command syntax and versions. When in doubt, refer to this document to avoid command version errors.

## 🚀 Microservices Deployment Consistency

### Critical Rule: Shared Code Updates Require Full Deployment

**❌ WRONG: Partial deployment after shared code changes**
```bash
# Updated app/shared/security.py (used by all services)
./scripts/deploy.sh --env dev --services gateway  # Only deploys gateway!
# Result: Gateway has new auth code, chat/auth/asset services have old code = 403 errors
```

**✅ CORRECT: Deploy all services when shared code changes**
```bash
# Updated app/shared/security.py (used by all services)  
./scripts/deploy.sh --env dev --services all  # Deploys gateway, auth, asset, chat
# Result: All services have consistent auth code = working microservices
```

**Lesson Learned (2025-07-12):**
- Microservices amplify deployment consistency requirements
- Dev environment should work identically to staging/production
- Shared code changes (security.py, database.py, config.py) affect ALL services
- Always deploy the full dependency graph, not individual services

## 🐳 Docker Commands

### Docker Compose (CRITICAL: Version matters!)

```bash
# ✅ CORRECT: Modern Docker Compose (v2+)
docker compose up
docker compose down
docker compose build
docker compose logs -f gateway

# ❌ DEPRECATED: Old docker compose (v1)
docker compose up  # DO NOT USE
```

**Detection**: Check your Docker Compose version:
```bash
docker compose version
# Output: Docker Compose version v2.x.x
```

**Note**: If you only have `docker compose` (with hyphen), update Docker Desktop or install Compose v2.

### Docker Commands

```bash
# ✅ CORRECT: Current Docker CLI
docker info
docker stats
docker ps
docker logs <container>
docker exec -it <container> bash

# ⚠️ LEGACY: Still works but prefer modern syntax
docker container ls  # Use: docker ps
docker image ls      # Use: docker images
```

## 🚀 Fly.io Commands

### Postgres Database (CRITICAL: API changed!)

```bash
# ✅ CORRECT: Managed Postgres (current)
fly postgres create    # Create new database
fly postgres list      # List databases (may show deprecation warning)
fly mpg list          # New command for managed postgres
fly postgres connect -a <app-name>

# ❌ DEPRECATED: Unmanaged Postgres
fly pg create         # DO NOT USE
fly postgres db list  # DO NOT USE
```

**Note**: Fly.io migrated to Managed Postgres. Always use `fly postgres` or `fly mpg` commands.

### App Management

```bash
# ✅ CORRECT: Current Fly.io CLI
fly apps list
fly status -a <app-name>
fly logs -a <app-name>
fly deploy --config <config.toml>
fly scale count <n> -a <app-name>

# ⚠️ WATCH OUT: Organization flag placement
fly postgres create --org aeonia-dev  # Correct
fly list --org aeonia-dev            # WRONG - no org flag on list
```

### Secrets Management

```bash
# ✅ CORRECT: Set secrets properly
fly secrets set KEY=value -a <app-name>
echo "value" | fly secrets set KEY=- -a <app-name>  # From stdin
fly secrets list -a <app-name>

# ❌ WRONG: Common mistakes
fly secrets KEY=value        # Missing 'set'
fly secrets set KEY value    # Missing '='
```

## 🧪 Testing Commands

### Gaia Test Script

```bash
# ✅ CORRECT: Always use the test script
./scripts/test.sh --local health
./scripts/test.sh --staging all
./scripts/test.sh --prod chat "Hello"

# ❌ WRONG: Direct curl (unless specifically needed)
curl http://localhost:8666/health  # NO! Use test script
```

### Python/Pytest

```bash
# ✅ CORRECT: Modern Python commands
python -m pytest
python -m pip install -r requirements.txt
python -m venv venv

# ❌ DEPRECATED: Old style
pytest              # May not find modules correctly
pip install         # May install to wrong Python
```

## 📦 Package Managers

### npm (Node.js)

```bash
# ✅ CORRECT: Modern npm
npm install
npm run dev
npm test

# ⚠️ AVOID: Mixing package managers
yarn install  # Don't mix with npm
pnpm install  # Don't mix with npm
```

### pip (Python)

```bash
# ✅ CORRECT: Use python -m pip
python -m pip install package
python -m pip freeze > requirements.txt

# ❌ RISKY: Direct pip (might be wrong Python)
pip install package
```

## 🔧 Git Commands

### Git Operations

```bash
# ✅ CORRECT: Modern Git
git status
git add .
git commit -m "message"
git push origin main

# ⚠️ DEPRECATED: Old defaults
git push origin master  # Many repos use 'main' now
```

## 🛠️ System Commands

### File Operations

```bash
# ✅ CORRECT: Cross-platform safe
ls -la              # Linux/Mac
dir                 # Windows

# Use scripts for consistency
./scripts/test.sh   # Not: bash scripts/test.sh
```

### Process Management

```bash
# ✅ CORRECT: Modern syntax
ps aux | grep python
lsof -i :8000
kill -9 <pid>

# ⚠️ PLATFORM-SPECIFIC: Document which OS
netstat -an | grep 8000  # May not exist on all systems
```

## 📋 Command Detection Patterns

### How to Check Correct Version

1. **Docker Compose**:
   ```bash
   which docker compose  # Old version (hyphenated)
   which docker          # Check for 'compose' subcommand
   docker --help | grep compose
   ```

2. **Fly.io CLI**:
   ```bash
   fly version
   fly --help | grep postgres
   fly postgres --help  # Check available subcommands
   ```

3. **Python**:
   ```bash
   python --version
   python -m pip --version
   which python
   ```

## 🚨 Critical Rules

1. **ALWAYS** use `docker compose` (space) not `docker compose` (hyphen)
2. **ALWAYS** use `fly postgres` or `fly mpg`, never `fly pg`
3. **ALWAYS** use test scripts instead of raw curl for API testing
4. **ALWAYS** specify organization for Fly.io database operations
5. **ALWAYS** use `python -m` for Python module commands
6. **NEVER** assume command syntax - check this reference

## 🔄 Updating This Document

When you encounter a new command version issue:

1. Add it to the appropriate section
2. Show both correct (✅) and incorrect (❌) versions
3. Include detection method if applicable
4. Add any platform-specific notes

## 🎯 Quick Reference Card

```bash
# Most Common Corrections
docker compose up          # NOT: docker compose up
fly postgres list          # NOT: fly pg list
fly mpg list              # NEW: Managed postgres list
./scripts/test.sh         # NOT: curl commands
python -m pip install     # NOT: pip install
git push origin main      # NOT: git push origin master
```

This document is the source of truth for command syntax. When in doubt, check here first!