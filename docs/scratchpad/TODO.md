# GAIA Development TODO

> **⚠️ HISTORICAL DOCUMENT** - Last updated 2025-11-06
>
> This document tracks work from early November 2025. For current status, see:
> - `/docs/_planning/PLAN.md` - Current goals and strategy
> - `/docs/_planning/SESSION-LOG.md` - Recent session progress
> - `CURRENT-STATUS-2025-11-09.md` (scratchpad) - November snapshot

**Last Updated**: 2025-11-06
**Current Status**: State Management Refactored ✅ → Game Commands Gap Identified 🎯

**Architecture Decision**: Hybrid Approach Approved
- Ship: WebSocket in KB Service for AEO-65 demo (Friday deadline)
- Migrate: Dedicated Session Service post-demo (Q1 2026)
- See: `docs/scratchpad/websocket-architecture-decision.md`

---

## Next Major Phase: Session Service Migration (Post-Demo)

**Status**: 📋 Deferred to Post-Demo (Q1 2026)
**Document**: `docs/scratchpad/websocket-architecture-decision.md`

**Objective**: Migrate WebSocket connection management from the KB Service to a new, dedicated Session Service. This resolves the technical debt incurred for the demo and aligns with a scalable, production-ready microservice architecture.

**Migration Plan** (9-13 hours):
- **Phase 1: Create Session Service (3-4h)**
  - [ ] Create new microservice: `app/services/session/`
  - [ ] Add Dockerfile, fly.toml, deployment configuration
- **Phase 2: Move WebSocket Infrastructure (2-3h)**
  - [ ] Move `ExperienceConnectionManager` to the new Session Service.
  - [ ] Move the `/ws/experience` endpoint and its authentication logic.
- **Phase 3: State Integration (1-2h)**
  - [ ] The Session Service will subscribe to NATS for `world_update` events and forward them to clients.
  - [ ] Client actions received by the Session Service will be forwarded to the KB Service via HTTP calls.
- **Phase 4: Testing & Deployment (3-4h)**
  - [ ] Deploy the new Session Service.
  - [ ] Update clients to connect to the new service URL.
  - [ ] Deprecate and remove the WebSocket endpoint from the KB Service.

---

## ✅ Completed Work

### Cleaner State Management Pattern (1.5h)

**Completed**: 2025-11-06
**Implementation**: Refactored player initialization to single entry point pattern
**Status**: ✅ COMPLETE

**Problem Solved**:
- "Player view not found" errors when new players tried actions
- Inconsistent auto-bootstrap scattered across methods
- No clear contract for when initialization happens

**Solution Implemented**:
- **`ensure_player_initialized()`** - Single entry point for player bootstrap validation
- All state methods now assume files exist (clear contract)
- Called at all entry points: WebSocket handler, chat endpoint
- Removed hidden auto-bootstrap from `get_player_view()` and `update_player_view()`

**Files Modified**:
- `app/services/kb/unified_state_manager.py` - Added ensure_player_initialized(), updated docstrings
- `app/services/kb/websocket_experience.py` - Calls ensure_player_initialized() before actions
- `app/services/kb/experience_endpoints.py` - Calls ensure_player_initialized() before chat

**Testing**:
- ✅ WebSocket tests passing (7/7 bottles collected)
- ✅ Pattern validation script: `scripts/experience/test-player-initialization.sh`
- ✅ Prevents regression with static code analysis

### WebSocket Experience Endpoint - KB Service Implementation (2.5h)

**Completed**: 2025-11-05
**Implementation**: Fast path WebSocket directly in KB Service for the AEO-65 demo.
**Status**: ✅ COMPLETE

**Details**:
- Implemented `/ws/experience` endpoint in the KB service.
- Created `ExperienceConnectionManager` to handle WebSocket lifecycle and NATS subscriptions.
- Integrated JWT authentication.
- Implemented game logic for the "Bottle Quest" demo.
- Full details in `docs/scratchpad/websocket-test-results.md`.

### Phase 1B: Chat Service NATS Subscriptions (COMPLETE)

**Completed**: 2025-11-04
**Implementation**: Per-request NATS subscriptions during SSE streaming.
**Full Details**: `docs/scratchpad/PHASE-1B-ACTUAL-COMPLETION.md`

---

## 🔧 Known Gaps (Design Needed)

### World State Discovery & Synchronization

**Status**: WebSocket protocol layer complete, but game mechanics incomplete

**What's Missing**:
- ⚠️ **Initial state sync** - Client doesn't receive world state on connect (doesn't know bottles exist/where they are)
- ⚠️ **Location-based discovery** - No mechanism for "seeing" items at current location
- ⚠️ **Complete state deltas** - Collection only updates inventory, doesn't remove from world locations
- ⚠️ **World state management** - Unclear how shared world.json updates work with multiple players

**Impact**: Current WebSocket can collect bottles but Unity client has no way to discover them first

**Design Questions** (Needs Discussion):
1. **Initial sync strategy**: Full world state vs current location vs lazy loading?
2. **Discovery mechanism**: Automatic, proximity-based, line-of-sight, or action-based?
3. **Validation approach**: Server-side (secure), client-trust (fast), or hybrid?
4. **World state updates**: How to handle shared world.json with concurrent modifications?
5. **State model handling**: How does code distinguish shared vs isolated models?

**Full Analysis**: `docs/scratchpad/websocket-world-state-discovery.md`

**Proposed Phases**:
1. **Phase 1**: Basic world state sync (client can see bottles and locations)
2. **Phase 2**: Complete state deltas (collection removes from world + adds to inventory)
3. **Phase 3**: Discovery & validation (proper gameplay flow with server-side checks)

**Next Step**: Design session to answer open questions and define schemas/protocols

### Game Command Implementation Gap

**Status**: ✅ CORRECTED - Most commands already exist, documentation was outdated
**Discovered**: 2025-11-06 during command/response testing framework creation
**Corrected**: 2025-11-06 during implementation review

**✅ ACTUALLY IMPLEMENTED** (in `game-logic/` directory):
- ✅ `talk to [NPC]` - NPC conversations with trust/relationship tracking (`talk.md`)
- ✅ `inventory` / `check inventory` - View player inventory (`inventory.md`)
- ✅ `collect [item]` - Item collection (working in WebSocket) (`collect.md`)
- ✅ `look around` - Environmental description/observation (`look.md`)
- ✅ `examine [item]` - Detailed item inspection (alias in `look.md`)
- ✅ `go to [location]` - Movement between locations and sublocations (`go.md`)
- ✅ Admin commands - `@list-waypoints`, `@inspect-waypoint`, `@create-waypoint`, `@delete-waypoint`, `@edit-waypoint`, `@list-items`, `@inspect-item`, `@reset-experience`

**❌ ACTUALLY MISSING** (only 3 commands):
- ❌ `help` - List available commands with descriptions
- ❌ `quest status` / `quests` - View active quest progress
- ❌ `list quests` - Show available/completed quests

**Impact**:
- Much smaller scope than originally thought!
- Testing framework ready - most tests should pass
- Only missing: help system and quest viewing commands
- Discovery flow IS complete (look/examine/go all work)

**Test Framework Created**:
- `scripts/experience/test-commands.sh` - General command/response testing
- Ready to test existing commands immediately
- Supports multiple test suites: basic, movement, items, NPCs, quests, performance, errors

**Next Steps** → See "Game Command Implementation" in Active Work (reduced scope)

### WebSocket Command Processing Limitation

**Status**: ⚠️ ARCHITECTURAL GAP DISCOVERED (2025-11-06)
**Discovered During**: Testing help.md and quests.md commands on both HTTP and WebSocket protocols
**Impact**: High - Affects demo capabilities and post-demo roadmap

**The Gap**:
- **HTTP `/experience/interact`**: Full LLM-powered command processing via markdown files ✅
  - Supports ALL commands: help, quests, talk, look, examine, go, inventory, collect, admin commands
  - Uses sophisticated 2-pass LLM system (deterministic logic + creative narrative)
  - Reads game-logic/*.md files with YAML frontmatter and JSON response schemas

- **WebSocket `/ws/experience`**: Hardcoded actions only ❌
  - ONLY supports: `collect_bottle`, `drop_item`, `interact_object`
  - Bypasses LLM entirely for demo speed
  - `handle_chat()` is a stub with canned responses (lines 420-431 in websocket_experience.py)
  - Natural language commands NOT supported

**What Works**:
- ✅ HTTP: `help`, `quests`, `talk to Louisa`, `look around`, `go to`, etc. (all commands)
- ✅ WebSocket: `collect_bottle`, `drop_item`, `interact_object` (3 hardcoded actions)

**What Doesn't Work**:
- ❌ WebSocket: `help`, `quests`, `talk`, `look`, `examine`, etc. (no LLM processing)
- ❌ WebSocket: Natural language input (e.g., "what can I do here?")

**Why This Exists**:
- Intentional simplification for AEO-65 demo (Friday deadline)
- WebSocket implementation labeled "SIMPLIFIED implementation" in code comments
- Fast path for bottle collection demo scenario
- Full command processing deferred to Command Bus refactoring (post-demo)

**Post-Demo Solution**: Command Bus Architecture
- **Document**: `docs/scratchpad/command-system-refactor-proposal.md` (created 2025-11-06)
- **References**: `docs/scratchpad/command-bus-industry-references.md` (industry validation)
- **Timeline**: Post-demo implementation (Q1 2026)
- **Estimated Effort**: 8-10 hours (Phase 1), 3-4 hours (Phase 2 optimization)

**Command Bus Benefits**:
- Single `ExperienceCommandProcessor` for both HTTP and WebSocket
- Hybrid handlers: fast path (10-50ms) for structured commands, slow path (1-3s) for LLM
- Transport-agnostic design (works with any protocol)
- Standardized command contract across all handlers
- Industry-validated pattern (confirmed via Perplexity AI research)

**Immediate Workaround**:
- Demo focuses on bottle collection (works on WebSocket)
- Complex interactions use HTTP endpoint (works now)
- Full WebSocket parity deferred to post-demo Command Bus implementation

**Related Work**:
- Symphony discussion with server-architect confirms Command Bus approach
- Friday demo deadline prioritizes working bottle collection over full command parity
- NPC voice/chat stays on SSE for now (not in WebSocket for demo)

---

## Active Work

### Game Command Implementation (Medium Priority)

**Status**: ✅ COMPLETE (2025-11-06)
**Actual Time**: 1 hour (est. 1-2 hours)
**Priority**: Medium (most core commands already existed)

**Completed Work**:

**Phase 1: Help Command** ✅
- ✅ Implemented `help.md` - Lists all available commands with descriptions
- ✅ Shows command categories: Movement, Items, NPCs, Quests
- ✅ Includes aliases and usage examples
- ✅ Tested successfully via HTTP `/experience/interact` endpoint

**Phase 2: Quest Commands** ✅
- ✅ Implemented `quests.md` - Single command handles all quest viewing
  - Shows active quests with progress
  - Lists offered quests not yet accepted
  - Displays completed quests
  - Handles empty quest log gracefully
- ✅ Integrated with existing quest tracking from talk.md
- ✅ Tested successfully - returns proper "no quests yet" message

**Phase 3: Testing** ✅
- ✅ Verified help command works correctly
- ✅ Verified quests command works correctly
- ✅ Both commands return proper JSON response format
- ✅ LLM generates narrative wrapping for responses

**Commands Now Complete**:
- ✅ look.md, go.md, inventory.md, collect.md, talk.md (pre-existing)
- ✅ help.md (new)
- ✅ quests.md (new)
- ✅ Admin commands: @list-waypoints, @inspect-waypoint, etc. (pre-existing)

**All critical player commands are now implemented!**

### WebSocket Testing & Deployment (1-2h) - IMMEDIATE

**Status**: 🎯 Ready to Start
**Owner**: Server Team

**Tasks**:
- [ ] Test WebSocket endpoint locally using `tests/manual/test_websocket_experience.py`.
- [ ] Deploy to dev environment.
- [ ] Provide the WebSocket URL and test credentials to the Unity team.
- [ ] Begin integration testing with the Unity client (Thursday).

### Phase 1A: NATS World Updates - KB Service Publishing (2-3h)

**Status**: 🎯 Ready to Start
**Owner**: TBD

**Objective**: KB Service publishes state delta events to NATS after world state changes. (Note: The `ExperienceConnectionManager` already leverages this by subscribing to the events the `UnifiedStateManager` *will* publish).

**Implementation Tasks**:
- [ ] Define `WorldUpdateEvent` schema in `app/shared/events.py`.
- [ ] Implement `_publish_world_update()` method in `UnifiedStateManager`.
- [ ] Call this method in `update_world_state()` and `update_player_view()`.
- [ ] Inject NATS client into KB service startup.
- [ ] Write unit tests for NATS event publishing.
