# ADR-009: KB Ephemeral Container Storage

**Date**: 2025-10-03
**Status**: Implemented
**Decision**: Use ephemeral container storage (no Docker volume) for KB repository, with Git clone on startup

## Context

The KB service needs to store a Git repository containing game experiences, rules, and platform knowledge. We had to decide between:

1. **Ephemeral storage** - Clone from GitHub into container on startup
2. **Persistent Docker volume** - Clone once, persist across container restarts
3. **Host filesystem mount** - Mount local directory into container

Key factors:
- KB repository is small (828KB, 38 markdown files)
- Git clone takes ~1 second (non-blocking background operation)
- Production environment (Fly.io) uses ephemeral container storage
- Container typically runs for days/weeks without restart (current: 8 days uptime)
- Repository changes are infrequent (source of truth is GitHub)

## Decision

**Use ephemeral container storage with deferred Git clone on startup.**

Configuration:
```yaml
# docker-compose.yml
kb-service:
  volumes:
    - ./app:/app/app  # Code only, NO KB data mount
  environment:
    - KB_PATH=/kb  # Ephemeral container path
    - KB_GIT_REPO_URL=https://github.com/Aeonia-ai/gaia-knowledge-base
    - KB_GIT_AUTO_CLONE=true
    - KB_STORAGE_MODE=git
```

Startup behavior:
```python
# kb_startup.py
async def initialize_kb_repository():
    if (kb_path / '.git').exists():
        return True  # Skip clone, instant startup

    # Schedule background clone (non-blocking)
    asyncio.create_task(_background_clone())
    return True  # Service starts immediately
```

## Rationale

### 1. Production Parity (Primary Driver)

**Local development matches production exactly:**
```
Local Development        Production (Fly.io)
──────────────────────────────────────────────
Ephemeral /kb       =    Ephemeral /kb
Git clone on start  =    Git clone on start
No volumes          =    No volumes
```

This eliminates an entire class of "works on my machine" bugs where local persistent state differs from production ephemeral state.

### 2. Cost-Benefit Analysis

**Cost**: 1-second clone after `docker-compose down` (rare event)

**Benefits**:
- ✅ Clean state on every restart
- ✅ Impossible to have stale KB data
- ✅ No volume management overhead
- ✅ Tested deployment path matches production
- ✅ Simple debugging (no hidden volume state)

**Measured Performance**:
- Repository size: 828KB
- Clone time: ~1 second (background, non-blocking)
- Service startup: Instant (doesn't wait for clone)
- Container uptime: 8 days (proves restarts are rare)

### 3. Deferred Initialization Pattern

The implementation already optimizes for container persistence:
```
First Start:
  Container starts → /kb empty → Background clone (~1s) → Files available

Subsequent Starts (while container alive):
  Container starts → /kb/.git exists → Skip clone → Instant!
```

**Result**: We get the benefits of persistence (fast restarts) WITHOUT the drawbacks (hidden state) for the common case where containers stay running.

### 4. Small Repository Size

At 828KB, the KB repository is tiny:
- Entire clone takes ~1 second
- Network transfer is negligible
- No meaningful performance impact

**Threshold for reconsideration**: If repository grows to >100MB or clone time exceeds >10 seconds, persistent volumes become more attractive.

### 5. Debugging Simplicity

Ephemeral storage prevents hidden state bugs:

**With Persistent Volume (Bad)**:
```bash
# Developer updates .env with new KB_GIT_REPO_URL
docker-compose restart kb-service

# Volume still has old repository!
# Service reads stale data
# "Why isn't my change showing up?"
```

**With Ephemeral (Good)**:
```bash
# Developer updates .env with new KB_GIT_REPO_URL
docker-compose down && docker-compose up kb-service

# Fresh clone from new URL
# Guaranteed to be correct
```

### 6. Git as Source of Truth

With ephemeral storage:
- ✅ GitHub is the authoritative source
- ✅ Every restart guarantees latest content (if container rebuilds)
- ✅ No sync issues between volume and Git
- ✅ No need to manually `git pull` in volumes

## Consequences

### Positive

1. **Production Parity**: Development environment exactly matches production
   - Prevents deployment surprises
   - Same startup sequence
   - Same failure modes

2. **Clean State Debugging**: Every restart is a fresh start
   - No hidden volume state
   - Easier to reproduce issues
   - "Turn it off and on" actually works

3. **No Volume Management**: One less thing to maintain
   - No volume backups needed
   - No volume pruning needed
   - No volume inspection needed

4. **Simple Configuration**: Zero volume declarations
   - Clear in docker-compose.yml
   - No external dependencies
   - Easy to understand

5. **Guaranteed Correctness**: Always uses Git HEAD
   - No stale data possible
   - No manual sync required
   - No drift over time

### Negative

1. **Network Dependency**: Requires internet for fresh starts
   - **Mitigation**: Container stays up for days (8+ days observed)
   - **Mitigation**: Deferred init means cached .git persists while container alive
   - **Impact**: Low - developers have internet, and restarts are rare

2. **Re-clone on Full Restart**: 1-second delay after `docker-compose down`
   - **Mitigation**: Clone is background/non-blocking
   - **Mitigation**: Service starts instantly, clone happens async
   - **Impact**: Negligible - 828KB clones in ~1 second

3. **GitHub Token Required**: Must have valid KB_GIT_AUTH_TOKEN
   - **Mitigation**: Already required for private repository access
   - **Impact**: None - token needed anyway

### Neutral

1. **Container Lifecycle Coupling**: KB lifetime tied to container lifetime
   - This is actually desired behavior (ephemeral by design)
   - Matches production container lifecycle

2. **No Offline Development**: After `docker-compose down`, need internet
   - Rare scenario - developers typically have internet
   - Can work offline as long as container stays running

## Alternatives Considered

### Alternative 1: Persistent Docker Volume

```yaml
kb-service:
  volumes:
    - kb_data:/kb
volumes:
  kb_data:
```

**Rejected because**:
- ❌ Creates local-remote parity gap
- ❌ Adds hidden state debugging complexity
- ❌ Requires volume management overhead
- ❌ Benefit (save 1 second) doesn't justify costs

**When to reconsider**: If repository grows to >100MB or restarts become frequent (>10/day)

### Alternative 2: Host Filesystem Mount

```yaml
kb-service:
  volumes:
    - /Users/username/kb:/kb
```

**Rejected because**:
- ❌ Completely different from production (Fly.io doesn't have host mounts)
- ❌ Hardcodes developer-specific paths
- ❌ Makes docker-compose.yml non-portable
- ❌ Can't share across team without path adjustments
- ❌ Massive local-remote parity violation

**Never reconsider**: This breaks the fundamental "dev = prod" principle

### Alternative 3: Conditional Volume (Dev Override)

```yaml
# docker-compose.override.yml (gitignored)
services:
  kb-service:
    volumes:
      - kb_dev_data:/kb
```

**Not implemented but available**: Developers can add this locally if they restart frequently

**Why not default**:
- Default behavior should match production
- Let developers opt-in to convenience if needed
- Keeps CI/CD using correct (ephemeral) path

## Implementation Notes

### Deferred Initialization

The implementation uses a deferred initialization pattern:

```python
async def initialize_kb_repository():
    kb_path.mkdir(parents=True, exist_ok=True)  # Immediate

    if (kb_path / '.git').exists():
        return True  # Instant startup

    # Schedule background clone
    task = asyncio.create_task(_background_clone())
    return True  # Don't block service startup
```

**Key insight**: Service starts in <2 seconds regardless of KB state. Clone happens in background.

### Container Lifecycle

```
docker-compose up
  ↓
Container starts → /kb empty
  ↓
Service initializes
  ├─ Check /kb/.git → Not found
  ├─ Schedule background clone
  └─ Return immediately (service ready)
  ↓
Background: git clone completes (~1s)
  ↓
Container runs for days/weeks
  ↓
Next restart (while container alive):
  ├─ Check /kb/.git → Found!
  └─ Skip clone (instant)
```

### Verification

```bash
# Check current status
docker exec gaia-kb-service-1 sh -c '
  echo "Uptime: $(ps -p 1 -o etime=)"
  echo "Files: $(find /kb -name "*.md" | wc -l)"
  echo "Size: $(du -sh /kb)"
  echo "Source: $(git -C /kb remote get-url origin)"
'

# Current results:
# Uptime: 8 days
# Files: 38
# Size: 828K
# Source: https://github.com/Aeonia-ai/gaia-knowledge-base
```

## Review Criteria

This decision should be reviewed if:

1. **KB repository grows significantly** (>100MB)
2. **Clone time becomes problematic** (>10 seconds)
3. **Container restart frequency increases** (>10/day)
4. **Production switches to persistent storage** (breaks parity argument)
5. **Network reliability becomes an issue** (unlikely with GitHub)

**Current metrics support the decision**: 828KB, ~1s clone, 8+ day uptimes

## Related Decisions

- **[ADR-003: PostgreSQL Simplicity](003-postgresql-simplicity.md)** - Similar principle: use simple, direct approaches over complex abstractions
- **KB Git Sync Guide** - Documents sync patterns for production
- **KB Repository Structure** - Documents the actual content being cloned

## References

- Implementation: `app/services/kb/kb_startup.py`
- Configuration: `docker-compose.yml` (kb-service section)
- Documentation: `docs/kb/developer/kb-repository-structure-and-behavior.md`
- Repository: https://github.com/Aeonia-ai/gaia-knowledge-base
