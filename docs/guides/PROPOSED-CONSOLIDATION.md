# Proposed Deployment Documentation Consolidation



## From 12 Documents → 4 Essential Documents

### 1. `deployment-guide.md` (Combines 6 docs)
**The main guide everyone reads**

Absorbs:
- deployment-runbook.md
- deployment-best-practices.md
- deployment-pipeline.md
- production-deployment.md
- deployment-validation-checklist.md
- smart-scripts-deployment.md

Contents:
```markdown
# Deployment Guide

## Quick Start (90% of needs)
- Deploy to dev: `./scripts/deploy.sh --env dev --services all`
- Deploy to prod: `./scripts/deploy.sh --env production --services all --remote-only`
- Rollback: `fly releases rollback -a gaia-gateway-dev`

## Deployment Workflow
1. Test locally
2. Deploy to dev
3. Validate
4. Deploy to production

## Troubleshooting
- Docker Hub limits: Use `--remote-only` or authenticate
- Failed deploy: See rollback section
- Service not responding: Check health endpoints
```

### 2. `flyio-setup.md` (Combines 2 docs)
**Platform-specific configuration**

Absorbs:
- flyio-deployment-config.md
- database-migration-strategy.md (Fly.io parts)

Contents:
- Initial Fly.io setup
- Secrets management
- Database configuration
- Region selection

### 3. `supabase-setup.md` (Combines 3 docs)
**Auth service configuration**

Absorbs:
- supabase-configuration.md
- supabase-multi-environment-setup.md
- supabase-single-project-setup.md

Contents:
- Single consolidated Supabase guide
- Environment-specific settings
- Email configuration

### 4. `deployment-reference.md` (New)
**Quick lookup for commands and troubleshooting**

Contents:
```markdown
# Deployment Reference

## Commands
Deploy: `./scripts/deploy.sh --env {env} --services {services}`
Rollback: `fly releases rollback -a {app-name}`
Status: `fly status -a {app-name}`
Logs: `fly logs -a {app-name}`

## Troubleshooting
| Problem | Solution |
|---------|----------|
| Docker Hub 429 | Use --remote-only or docker login |
| Deploy hangs | Check Redis URL secret |
| Service unreachable | Use public URLs, not .internal |

## Health Endpoints
- Gateway: http://localhost:8666/health
- Auth: http://localhost:8000/health
- Chat: http://localhost:8001/health
```

## Benefits of Consolidation

### Before (12 docs):
- 🔴 Find info: Search 12 files
- 🔴 Update process: Edit 5+ files
- 🔴 Onboarding: "Where do I start?"
- 🔴 Maintenance: 12 files to keep in sync

### After (4 docs):
- ✅ Find info: Check 1 main guide
- ✅ Update process: Edit 1 file
- ✅ Onboarding: Start with deployment-guide.md
- ✅ Maintenance: 75% fewer files

## Migration Plan

### Phase 1: Create New Structure
```bash
# Create consolidated docs
cat deployment-runbook.md deployment-best-practices.md > deployment-guide.md
cat supabase-*.md > supabase-setup.md

# Create reference
grep -h "scripts/deploy.sh" *.md | sort -u > deployment-reference.md
```

### Phase 2: Archive Old Docs
```bash
mkdir _archive/deployment-old/
mv deployment-pipeline.md deployment-validation-checklist.md _archive/deployment-old/
```

### Phase 3: Update References
- Update CLAUDE.md to point to new docs
- Update README.md navigation
- Fix any internal links

## What Gets Deleted

These can be safely removed after consolidation:
1. deployment-pipeline.md (merged into guide)
2. deployment-validation-checklist.md (becomes a section)
3. deployment-best-practices.md (merged into guide)
4. smart-scripts-deployment.md (merged into guide)
5. production-deployment.md (merged into guide)
6. deployment-runbook.md (becomes the base of new guide)
7. database-migration-strategy.md (split between flyio and guide)
8. Individual supabase-*.md files (consolidated)

## Decision Criteria

Keep separate docs only when:
1. **Different audience** (developers vs DevOps)
2. **Different frequency** (daily reference vs one-time setup)
3. **Different platforms** (Fly.io vs AWS vs local)

Otherwise, consolidate!

## Example: Your Streaming Fix

With consolidated docs, deploying the streaming fix would be:

1. Check `deployment-guide.md` → Quick Start section
2. Run: `./scripts/deploy.sh --env dev --services chat --remote-only`
3. If issues, check `deployment-reference.md` → Troubleshooting table

Instead of searching through 12 documents wondering which is correct!