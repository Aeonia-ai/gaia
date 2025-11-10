# Testing Organization & Strategy

**Date**: 2025-11-06
**Status**: Documentation - Post-Demo Refactoring Planned
**Context**: Experience system testing has evolved organically, needs consolidation

---

## Current State (Pre-Demo)

### Test Location Matrix

```
tests/manual/
├── get_test_jwt.py              ✅ Helper: Generate JWT tokens
├── get_user_jwt.py              ✅ Helper: Get user-specific JWT
├── test_websocket_experience.py ✅ WebSocket experience testing
├── test_nats_subscriber.py      ✅ NATS event validation
├── test_nats_sse_integration.py ✅ SSE + NATS integration
└── README.md                    ✅ Documentation

scripts/experience/
├── test-commands.sh             ✅ HTTP command testing
├── test-player-initialization.sh ✅ Pattern validation
└── README.md                    ✅ Documentation (created 2025-11-06)
```

### What Each Test Does

#### Experience Testing

**`tests/manual/test_websocket_experience.py`** (Python)
- **Protocol**: WebSocket (`ws://localhost:8001/ws/experience`)
- **Tests**: Bottle collection, NATS events, quest progression
- **Limitations**: Only 3 hardcoded actions (`collect_bottle`, `drop_item`, `interact_object`)
- **Speed**: Fast (10-50ms) - bypasses LLM
- **Use Case**: Real-time interaction validation for AEO-65 demo

**`scripts/experience/test-commands.sh`** (Bash)
- **Protocol**: HTTP (`POST /experience/interact`)
- **Tests**: All markdown-driven commands (help, talk, look, go, inventory, collect, quests)
- **Capabilities**: Full LLM processing, natural language
- **Speed**: Slower (1-3s) - LLM processing
- **Use Case**: Command logic validation, regression testing

**`scripts/experience/test-player-initialization.sh`** (Bash)
- **Type**: Static code analysis
- **Tests**: `ensure_player_initialized()` pattern compliance
- **Speed**: <1s
- **Use Case**: Regression prevention for state management pattern

#### Infrastructure Testing

**`tests/manual/test_nats_subscriber.py`** (Python)
- **Tests**: NATS world_update event publishing from KB Service
- **Validates**: Event schema, latency (<100ms), user isolation
- **Use Case**: Phase 1A NATS integration validation

**`tests/manual/test_nats_sse_integration.py`** (Python)
- **Tests**: End-to-end NATS → SSE streaming
- **Validates**: Event forwarding, latency (<200ms), stream lifecycle
- **Use Case**: Phase 1B SSE integration validation

#### Helpers

**`tests/manual/get_test_jwt.py`** (Python)
- **Purpose**: Generate JWT for `pytest@aeonia.ai` test user
- **Output**: JWT token to stdout
- **Usage**: `JWT_TOKEN=$(python3 tests/manual/get_test_jwt.py 2>/dev/null | tail -1)`

**`tests/manual/get_user_jwt.py`** (Python)
- **Purpose**: Generate JWT for specific user
- **Output**: User-specific JWT
- **Usage**: For multi-user testing scenarios

---

## Problems with Current Organization

### 1. **Arbitrary Split**
- Experience testing split between `tests/manual/` (WebSocket) and `scripts/experience/` (HTTP)
- No clear principle for why WebSocket is in tests/ and HTTP is in scripts/

### 2. **Protocol-Based Separation**
- HTTP and WebSocket tests are separated despite testing the **same system**
- Makes it hard to understand full experience testing capabilities

### 3. **Helper Pollution**
- Helper scripts (`get_test_jwt.py`) mixed with test runners
- No clear "these are tools, these are tests" distinction

### 4. **Discovery Issues**
- Developer asks "how do I test experiences?" → needs to check 2 locations
- README documentation duplicated between locations

### 5. **Naming Inconsistency**
- `tests/manual/test_*.py` - Python test files
- `scripts/experience/test-*.sh` - Bash test files
- Both use "test" prefix but different locations

---

## Proposed Organization (Post-Demo)

### New Structure

```
tests/manual/
├── experience/                      # 🆕 All experience testing
│   ├── README.md                    # Overview: HTTP vs WebSocket, when to use what
│   ├── http/
│   │   ├── test-commands.sh         # Moved from scripts/experience/
│   │   ├── test-player-initialization.sh
│   │   └── README.md
│   └── websocket/
│       ├── test_websocket_experience.py
│       └── README.md
│
├── infrastructure/                  # 🆕 NATS/SSE/messaging tests
│   ├── test_nats_subscriber.py
│   ├── test_nats_sse_integration.py
│   └── README.md
│
├── helpers/                         # 🆕 Utility scripts
│   ├── get_test_jwt.py
│   ├── get_user_jwt.py
│   └── README.md
│
└── README.md                        # Updated overview with new structure
```

### Rationale

**1. Feature-Based Organization**
- Group by **what system is being tested** (experience, infrastructure)
- Not by protocol (HTTP, WebSocket) or language (Python, Bash)

**2. Clear Hierarchy**
- `experience/` = All game interaction testing
  - `http/` = Markdown-driven LLM commands
  - `websocket/` = Real-time demo actions
- `infrastructure/` = Platform components (NATS, SSE)
- `helpers/` = Tools used by tests

**3. Protocol Transparency**
- Both HTTP and WebSocket test the **experience system**
- Their differences (limitations, speed) are implementation details
- Single `experience/README.md` explains when to use which protocol

**4. Discoverability**
- "How do I test experiences?" → `tests/manual/experience/`
- "How do I test NATS?" → `tests/manual/infrastructure/`
- "How do I get a JWT?" → `tests/manual/helpers/`

---

## Migration Plan

### Phase 1: Create New Structure (30 min)
```bash
# Create directories
mkdir -p tests/manual/{experience/{http,websocket},infrastructure,helpers}

# Move experience tests
mv scripts/experience/test-commands.sh tests/manual/experience/http/
mv scripts/experience/test-player-initialization.sh tests/manual/experience/http/
mv scripts/experience/README.md tests/manual/experience/http/
mv tests/manual/test_websocket_experience.py tests/manual/experience/websocket/

# Move infrastructure tests
mv tests/manual/test_nats_subscriber.py tests/manual/infrastructure/
mv tests/manual/test_nats_sse_integration.py tests/manual/infrastructure/

# Move helpers
mv tests/manual/get_test_jwt.py tests/manual/helpers/
mv tests/manual/get_user_jwt.py tests/manual/helpers/

# Remove empty directory
rmdir scripts/experience/
```

### Phase 2: Update READMEs (30 min)

**Create `tests/manual/experience/README.md`**:
```markdown
# Experience Testing

Tests for the GAIA experience system (game commands, world interactions, player state).

## Test Types

### HTTP Tests (`http/`)
- **Protocol**: HTTP POST `/experience/interact`
- **Processing**: Full LLM markdown-driven commands
- **Commands**: ALL (help, talk, look, go, inventory, collect, quests, admin)
- **Speed**: 1-3s (LLM processing)
- **Use**: Command logic validation, regression testing

### WebSocket Tests (`websocket/`)
- **Protocol**: WebSocket `ws://*/ws/experience`
- **Processing**: Hardcoded Python actions (demo only)
- **Commands**: 3 actions (`collect_bottle`, `drop_item`, `interact_object`)
- **Speed**: 10-50ms (pure Python)
- **Use**: Real-time interaction validation for AEO-65 demo

## When to Use Which

**Use HTTP tests** when:
- Testing command logic and markdown specifications
- Validating natural language understanding
- Testing NPC interactions, complex state changes
- Regression testing after command file changes

**Use WebSocket tests** when:
- Testing real-time update delivery (NATS events)
- Validating connection lifecycle (auth, ping/pong)
- Performance testing (latency measurement)
- Integration testing with Unity client

**Post-Demo**: Command Bus architecture will unify both protocols.
See `docs/scratchpad/command-system-refactor-proposal.md`.

## Quick Start

```bash
# HTTP command testing
cd tests/manual/experience/http
./test-commands.sh basic

# WebSocket testing
cd tests/manual/experience/websocket
python3 test_websocket_experience.py --url ws://localhost:8001/ws/experience
```
```

**Update `tests/manual/README.md`**:
- Add overview of new structure
- Update paths to reflect new locations
- Add "See `experience/README.md` for experience testing"

### Phase 3: Update Documentation References (15 min)

Files to update:
- `docs/scratchpad/TODO.md` - Update script paths
- `docs/testing/TESTING_GUIDE.md` - Update manual test references
- `.github/workflows/*.yml` - Update CI paths (if any reference these scripts)

### Phase 4: Create Symlinks (Optional - for transition period)

```bash
# Provide temporary backward compatibility
ln -s tests/manual/experience/http/test-commands.sh scripts/experience/test-commands.sh
ln -s tests/manual/experience/http/test-player-initialization.sh scripts/experience/test-player-initialization.sh

# Add deprecation notice
cat > scripts/experience/README.md << 'EOF'
# DEPRECATED

This directory has been moved to `tests/manual/experience/`.

Please update your scripts to use:
- `tests/manual/experience/http/test-commands.sh`
- `tests/manual/experience/websocket/test_websocket_experience.py`

These symlinks will be removed after Q1 2026.
EOF
```

---

## Testing Workflow Examples

### Before Reorganization (Current)
```bash
# Developer workflow is confusing
# "Where are experience tests?"
# → Check tests/manual/ → Find WebSocket
# → Check scripts/ → Find HTTP in scripts/experience/

# HTTP testing
./scripts/experience/test-commands.sh basic

# WebSocket testing
python3 tests/manual/test_websocket_experience.py --url ws://localhost:8001/ws/experience

# Different locations, different paradigms
```

### After Reorganization (Proposed)
```bash
# Developer workflow is clear
# "Where are experience tests?" → tests/manual/experience/

# Navigate to experience tests
cd tests/manual/experience

# See both HTTP and WebSocket options
ls -la
# http/
# websocket/
# README.md  (explains when to use which)

# HTTP testing
./http/test-commands.sh basic

# WebSocket testing
python3 websocket/test_websocket_experience.py --url ws://localhost:8001/ws/experience

# Single location, clear organization
```

---

## Documentation Updates Required

### Files to Create
- [x] `tests/manual/experience/README.md` - Overview of experience testing
- [ ] `tests/manual/infrastructure/README.md` - NATS/SSE testing guide
- [ ] `tests/manual/helpers/README.md` - Helper script documentation

### Files to Update
- [x] `tests/manual/README.md` - Update with new structure (already updated)
- [x] `scripts/experience/README.md` - Already created (will be moved)
- [ ] `docs/scratchpad/TODO.md` - Update script paths
- [ ] `docs/testing/TESTING_GUIDE.md` - Update manual test references

### Files to Deprecate
- [ ] `scripts/experience/` directory (remove after migration)
- [ ] Add deprecation notice if keeping symlinks

---

## Benefits Summary

### Immediate Benefits
1. **Single location** for all experience testing
2. **Clear categorization**: Experience, Infrastructure, Helpers
3. **Better discovery**: Obvious where to look for tests
4. **Consistent naming**: All tests under `tests/manual/`

### Long-Term Benefits
1. **Easier onboarding**: New developers find tests faster
2. **Maintenance**: Less confusion about where to add new tests
3. **Documentation**: Single source of truth for experience testing
4. **CI/CD**: Clearer test organization in automation pipelines

### Migration Risk
- **Low**: Tests are independent scripts, no code dependencies
- **Effort**: ~1 hour for full migration + documentation
- **Timing**: Post-demo (avoid path confusion before Friday)

---

## Recommendation

**✅ APPROVED FOR POST-DEMO IMPLEMENTATION**

**Timeline**:
- **Friday (Demo Day)**: Keep current structure, use existing paths
- **Monday (Post-Demo)**: Execute migration plan
- **Week of Nov 11**: Update all documentation references
- **Week of Nov 18**: Remove symlinks/deprecation notices

**Rationale**:
- Current structure is documented and working
- Demo depends on existing paths
- Post-demo is natural time for cleanup
- Low-risk refactor, high organizational value

---

## Related Work

**Post-Demo Refactoring**:
- Command Bus implementation (8-10 hours) - Unifies HTTP/WebSocket
- Session Service migration (9-13 hours) - Moves WebSocket to dedicated service
- Testing reorganization (1 hour) - **This document**

**Dependencies**:
- Command Bus architecture: `docs/scratchpad/command-system-refactor-proposal.md`
- Industry references: `docs/scratchpad/command-bus-industry-references.md`
- Current status: `docs/scratchpad/TODO.md`

---

## Questions & Answers

**Q: Why not keep HTTP in `scripts/` and WebSocket in `tests/`?**
A: They test the same system (experiences). Separation by protocol obscures that they're testing the same functionality with different implementation approaches.

**Q: Why not move everything to `scripts/`?**
A: `tests/` is the conventional location for test code. `scripts/` is typically for operational/deployment scripts (deploy.sh, manage.sh, etc.).

**Q: What about automated tests (`tests/integration/`, `tests/unit/`)?**
A: Those stay where they are. This proposal only affects manual tests that require human observation.

**Q: Will this break CI/CD?**
A: No current CI/CD references these paths. If added later, updating paths is trivial.

**Q: Do we need approval for this?**
A: No code changes, pure organization refactor. Document for visibility, execute post-demo.
