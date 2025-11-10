# Experience Testing Scripts

Automated bash scripts for testing the GAIA experience system (game commands, player state, world interactions).

## Purpose

These scripts provide **quick, automated validation** of:
- Game command functionality (HTTP `/experience/interact` endpoint)
- Player state initialization patterns
- Command/response contracts
- Regression prevention for critical game mechanics

**Key Difference from Manual Tests**:
- `tests/manual/`: Python scripts for WebSocket, NATS, SSE integration testing
- `scripts/experience/`: Bash scripts for HTTP endpoint command testing

## Available Scripts

### `test-commands.sh`

**Purpose**: Comprehensive command testing framework for the HTTP `/experience/interact` endpoint.

**What It Tests**:
- All markdown-driven commands: `help`, `quests`, `look`, `go`, `inventory`, `collect`, `talk`
- Command/response format validation
- State persistence across commands
- Error handling (invalid commands, missing targets)
- Performance benchmarking

**Requirements**:
- Docker services running (`docker compose up`)
- KB Service at `http://localhost:8001`
- Test user created (`pytest@aeonia.ai`)
- JWT token generation (`tests/manual/get_test_jwt.py`)

**Usage**:
```bash
# Run all test suites
./scripts/experience/test-commands.sh

# Run specific suite
./scripts/experience/test-commands.sh basic      # Basic commands (help, inventory)
./scripts/experience/test-commands.sh movement   # Go/look commands
./scripts/experience/test-commands.sh items      # Collect/drop commands
./scripts/experience/test-commands.sh npcs       # Talk command
./scripts/experience/test-commands.sh quests     # Quest viewing
./scripts/experience/test-commands.sh performance # Latency benchmarks
./scripts/experience/test-commands.sh errors     # Error handling
```

**Test Suites**:

**1. Basic Suite** (`basic`)
- `help` - List available commands
- `inventory` - Check empty inventory
- Response format validation

**2. Movement Suite** (`movement`)
- `look around` - Observe location
- `go to [location]` - Navigate to sublocations
- Location description validation

**3. Items Suite** (`items`)
- `collect [item]` - Pick up items
- `inventory` - Verify collection
- State persistence

**4. NPCs Suite** (`npcs`)
- `talk to [npc]` - Initiate conversation
- NPC response validation
- Trust level tracking

**5. Quests Suite** (`quests`)
- `quests` - View quest status
- Empty quest log handling
- Quest progress display

**6. Performance Suite** (`performance`)
- Response time benchmarking
- Target: <2s for simple commands, <4s for complex
- Latency distribution analysis

**7. Error Suite** (`errors`)
- Invalid command handling
- Missing target errors
- Malformed input resilience

**Expected Output**:
```
============================================
GAIA Experience Command Testing Framework
============================================

Test User: b18c47d8-3bb5-46be-98d4-c3950aa565a5
Experience: wylding-woods
Endpoint: http://localhost:8001/experience/interact

============================================
Running Suite: basic
============================================

[TEST 1/5] Testing command: help
  Command: help

  ✅ PASS - Response received
  ✅ PASS - Contains "success": true
  ✅ PASS - Contains narrative
  Duration: 1.2s

[TEST 2/5] Testing command: inventory
  Command: inventory

  ✅ PASS - Response received
  ✅ PASS - Empty inventory message
  Duration: 0.8s

============================================
SUMMARY: 5/5 tests passed (100%)
============================================
```

**Implementation Details**:
- Uses `tests/manual/get_test_jwt.py` for authentication
- Calls HTTP `/experience/interact` endpoint (NOT WebSocket)
- Tests **markdown-driven LLM command processing** (2-pass system)
- Validates JSON response structure
- Captures timing for performance analysis

**Current Limitations**:
- ⚠️ Tests HTTP only (WebSocket has different limitations - see `tests/manual/README.md`)
- ⚠️ Sequential execution (no parallel test running)
- ⚠️ Requires manual observation of narrative quality

**Future Enhancements**:
- [ ] JSON schema validation (automated contract testing)
- [ ] Parallel test execution
- [ ] LLM response quality scoring
- [ ] Integration with pytest for CI/CD

---

### `test-player-initialization.sh`

**Purpose**: Validate the `ensure_player_initialized()` pattern is used correctly throughout the codebase.

**What It Tests**:
- Entry points call `ensure_player_initialized()` before state operations
- No hidden auto-bootstrap in state methods
- Clear contract: all state methods assume files exist

**Background**:
This script prevents regression of the pattern refactoring completed 2025-11-06 (see `docs/scratchpad/TODO.md` - "Cleaner State Management Pattern").

**Problem Solved**:
- Before: "Player view not found" errors scattered throughout code
- After: Single entry point with explicit initialization check

**Requirements**:
- None (static code analysis only)

**Usage**:
```bash
# Run validation
./scripts/experience/test-player-initialization.sh

# Expected output if pattern is correct:
✅ PASS - All entry points call ensure_player_initialized()
✅ PASS - No auto-bootstrap in get_player_view()
✅ PASS - No auto-bootstrap in update_player_view()

# If pattern is violated:
❌ FAIL - Missing ensure_player_initialized() in websocket_experience.py:123
❌ FAIL - Auto-bootstrap detected in unified_state_manager.py:456
```

**What It Checks**:

**1. Entry Point Validation**:
```bash
# Checks these files call ensure_player_initialized():
- app/services/kb/websocket_experience.py (WebSocket handler)
- app/services/kb/experience_endpoints.py (HTTP endpoint)
```

**2. State Method Validation**:
```bash
# Ensures these methods DON'T auto-bootstrap:
- unified_state_manager.py::get_player_view()
- unified_state_manager.py::update_player_view()
```

**3. Contract Enforcement**:
```bash
# All state methods should have docstrings stating:
# "Assumes player files exist. Call ensure_player_initialized() first."
```

**Implementation**:
- Uses `grep` to search for pattern violations
- Static analysis only (no runtime testing)
- Fast (<1 second execution)
- Can be run in pre-commit hooks

**Integration with CI**:
```bash
# Add to .github/workflows/tests.yml
- name: Validate player initialization pattern
  run: ./scripts/experience/test-player-initialization.sh
```

**Related Documentation**:
- [TODO.md - Cleaner State Management Pattern](../../docs/scratchpad/TODO.md#cleaner-state-management-pattern-15h)
- [unified_state_manager.py](../../app/services/kb/unified_state_manager.py) - Implementation

---

## Testing Workflow

### Quick Validation (After Code Changes)
```bash
# 1. Validate pattern compliance (static)
./scripts/experience/test-player-initialization.sh

# 2. Test basic commands (runtime)
./scripts/experience/test-commands.sh basic

# 3. Test changed functionality
./scripts/experience/test-commands.sh [relevant-suite]
```

### Full Test Suite (Pre-Deploy)
```bash
# 1. Pattern validation
./scripts/experience/test-player-initialization.sh

# 2. All command suites
./scripts/experience/test-commands.sh

# 3. WebSocket tests (if changed)
python3 tests/manual/test_websocket_experience.py --url ws://localhost:8001/ws/experience

# 4. Integration tests
./scripts/pytest-for-claude.sh tests/integration/experience/
```

### Regression Prevention (CI/CD)
```bash
# Add to GitHub Actions or pre-commit hooks
./scripts/experience/test-player-initialization.sh || exit 1
./scripts/experience/test-commands.sh basic || exit 1
```

## Architecture Context

### HTTP vs WebSocket Command Processing

**HTTP `/experience/interact`** (Tested by these scripts):
- ✅ Full markdown-driven LLM command processing
- ✅ Supports ALL commands (help, talk, look, go, inventory, collect, quests)
- ✅ Two-pass system: deterministic logic (temp=0.1) + creative narrative (temp=0.7)
- ⚠️ Slower: 1-3 seconds (LLM processing)

**WebSocket `/ws/experience`** (Tested by `tests/manual/test_websocket_experience.py`):
- ❌ Only 3 hardcoded actions: `collect_bottle`, `drop_item`, `interact_object`
- ❌ No LLM processing (bypassed for demo speed)
- ❌ No natural language support
- ✅ Faster: 10-50ms (pure Python)

**Post-Demo**: Command Bus architecture will unify both (see `docs/scratchpad/command-system-refactor-proposal.md`).

### Markdown-Driven Commands

Commands are defined in markdown files: `/kb/experiences/{exp}/game-logic/{command}.md`

**Structure**:
```markdown
---
command: collect
aliases: [take, pick up, get, grab]
description: Pick up an item
requires_location: true
requires_target: true
---

# Collect Command

## Execution Logic
1. Validate target
2. Find item at location
3. Check collectible flag
4. Update world state (remove from location)
5. Update player state (add to inventory)

## Response Format
{
  "success": true,
  "narrative": "You take the brass lantern.",
  "state_updates": {...},
  "available_actions": [...]
}
```

The LLM reads these markdown files and executes the logic, generating structured JSON responses.

## Best Practices

1. **Run Pattern Validation First**: Always run `test-player-initialization.sh` before other tests
2. **Test Incrementally**: Run specific suites during development, full suite pre-deploy
3. **Observe Narrative Quality**: Automated checks can't validate story quality - manual review needed
4. **Document Failures**: When tests fail, add examples to the test suite
5. **Keep Scripts Fast**: These are for quick feedback loops (<10s total)

## Troubleshooting

### Tests Fail with "Connection Refused"
```bash
# Check services are running
docker compose ps

# Restart KB service
docker compose restart kb-service

# Check logs
docker compose logs kb-service | tail -50
```

### Tests Fail with "401 Unauthorized"
```bash
# Regenerate JWT token
python3 tests/manual/get_test_jwt.py

# Check test user exists
./scripts/manage-users.sh list | grep pytest@aeonia.ai
```

### Slow Response Times (>5s)
```bash
# Check LLM service health
docker compose logs chat-service | grep "LLM"

# Monitor resource usage
docker stats

# Check for rate limiting
docker compose logs kb-service | grep "rate"
```

### State Persistence Issues
```bash
# Check player state files
ls -la /data/repository/experiences/wylding-woods/players/{user_id}/

# Reset player state (destructive!)
rm -rf /data/repository/experiences/wylding-woods/players/{user_id}/*

# Re-run initialization
./scripts/experience/test-commands.sh basic
```

## Related Documentation

- [Testing Guide](../../docs/testing/TESTING_GUIDE.md) - Overall testing strategy
- [Manual Tests README](../../tests/manual/README.md) - WebSocket/NATS/SSE testing
- [Command System Refactor Proposal](../../docs/scratchpad/command-system-refactor-proposal.md) - Future architecture
- [TODO.md](../../docs/scratchpad/TODO.md) - Current implementation status

## Future Work

- [ ] Add JSON schema validation to `test-commands.sh`
- [ ] Create performance regression tracking
- [ ] Add LLM response quality scoring
- [ ] Integrate with pytest for unified test reporting
- [ ] Add mutation testing for state operations
- [ ] Create visual diff for narrative changes
