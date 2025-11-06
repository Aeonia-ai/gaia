# GAIA Development TODO

**Last Updated**: 2025-11-05
**Current Status**: WebSocket Implementation Complete (KB Service) ✅ → Testing & Deployment Next 🎯

**Architecture Decision**: Hybrid Approach Approved
- Ship: WebSocket in KB Service for AEO-65 demo (Friday deadline)
- Migrate: Dedicated Session Service post-demo (Q1 2026)
- See: `docs/scratchpad/websocket-architecture-decision.md`

---

## ✅ Completed Work

### Phase 1B: Chat Service NATS Subscriptions (COMPLETE)

**Completed**: 2025-11-04
**Implementation**: Per-request NATS subscriptions during SSE streaming
**Git Commits**: eff101d, dd4353f, 9a5f1fa

**What Works**:
- Chat Service subscribes to `world.updates.user.{user_id}` during SSE streams
- Automatic cleanup when streams close
- Graceful degradation if NATS unavailable
- Integration tests passing

**What's Missing**:
- KB Service does NOT publish events yet
- No events being generated server-side
- Unity would need to inject events for testing

**Full Details**: `docs/scratchpad/PHASE-1B-ACTUAL-COMPLETION.md`

---

## 🎉 Latest Completion

### WebSocket Experience Endpoint - KB Service Implementation (4h)

**Completed**: 2025-11-05
**Implementation**: Fast path WebSocket directly in KB Service
**Status**: ✅ COMPLETE - All Tests Passing, Committed & Pushed

**What Works (Validated & Shipped)**:
- ✅ `/ws/experience` WebSocket endpoint with JWT auth
- ✅ ExperienceConnectionManager: connection lifecycle + NATS subscriptions
- ✅ Persistent NATS subscriptions to world.updates.user.{user_id}
- ✅ Ping/pong protocol (~5ms local latency)
- ✅ Bottle collection handlers (7/7 tested successfully)
- ✅ Quest progress tracking
- ✅ NATS event forwarding to clients
- ✅ **Auto-bootstrap player initialization** (architectural fix)

**Major Architectural Improvement**:
- ✅ Centralized player initialization in UnifiedStateManager.get_player_view()
- ✅ Industry standard lazy init (WoW/Minecraft/Roblox pattern)
- ✅ Removed protocol-layer responsibility (was duplicated in chat endpoint)
- ✅ Works for ALL protocols automatically (HTTP, WebSocket, future GraphQL)

**Files Created**:
- `app/services/kb/experience_connection_manager.py` (250 lines)
- `app/services/kb/websocket_experience.py` (450 lines)
- `app/shared/security.py` (added `get_current_user_ws()`)
- `tests/manual/test_websocket_experience.py` (300 lines)
- `tests/manual/get_test_jwt.py` (100 lines) - JWT token generator
- `tests/manual/get_user_jwt.py` (80 lines) - JWT for existing users
- `docs/scratchpad/websocket-architecture-decision.md` (1000+ lines)
- `docs/scratchpad/websocket-test-results.md` (detailed test analysis)

**Architecture Decision - Hybrid Approach**:
- ✅ **Demo (Friday)**: Ship KB Service WebSocket (Option A)
- ⏳ **Post-Demo (Q1 2026)**: Migrate to dedicated Session Service (Option C)
- 📄 **Rationale**: Documented technical debt, clear migration path, non-breaking

**Known Technical Debt**:
- ⚠️ Violates separation of concerns (connection + state in same service)
- ⚠️ Cannot scale connections independently from state management
- ⚠️ Redundant message paths (immediate + NATS echo)
- ✅ **Mitigation**: Modular code, clear migration path, no client changes needed
- ✅ **Migration benefit**: Session Service naturally eliminates redundancy

**Message Flow Understanding**:
- Current: Dual path (immediate response + NATS echo)
- Acceptable because: Common pattern (Discord/Slack), enables multi-client
- After migration: Single path (NATS only), cleaner architecture
- See: `websocket-architecture-decision.md` for full analysis

**Next Steps**:
- [ ] Deploy to dev environment (when ready for Unity testing)
- [ ] Test with wss://gaia-kb-dev.fly.dev/ws/experience
- [ ] Provide Unity team with WebSocket URL + test credentials
- [ ] Integration testing with Unity team (Thursday)
- [ ] Q1 2026: Migrate to dedicated Session Service

**Full Details**:
- Architecture: `docs/scratchpad/websocket-architecture-decision.md`
- Test Results: `docs/scratchpad/websocket-test-results.md`

---

## Active Work

### Phase 1A: NATS World Updates - KB Service Publishing (2-3h)

**Status**: 🎯 Ready to Start
**Started**: TBD (November 4, 2025)
**Owner**: TBD
**Prerequisites**: ✅ Phase 1B complete (NATS subscriptions working)

**Objective**: KB Service publishes state delta events to NATS after world state changes

#### Implementation Tasks

- [ ] Define WorldUpdateEvent schema in `app/shared/events.py`
  - Include `version: "0.3"` field
  - State delta format: `operation: add/remove/update`
  - See schema in docs/scratchpad/nats-world-updates-implementation-analysis.md:689-752

- [ ] Add world_update_user() subject helper to NATSSubjects in `app/shared/nats_client.py`
  - Method: `world_update_user(user_id: str) -> str`
  - Returns: `f"world.updates.user.{user_id}"`
  - See implementation guide: docs/scratchpad/nats-world-updates-implementation-analysis.md:754-766

- [ ] Add nats_client parameter to UnifiedStateManager.__init__()
  - File: `app/services/kb/unified_state_manager.py`
  - Add: `nats_client: Optional[NATSClient] = None`
  - See implementation guide: docs/scratchpad/nats-world-updates-implementation-analysis.md:839-850

- [ ] Implement _publish_world_update() method in UnifiedStateManager
  - Graceful degradation: log errors, don't raise
  - Publish to NATS subject: `world.updates.user.{user_id}`
  - See implementation guide: docs/scratchpad/nats-world-updates-implementation-analysis.md:830-862

- [ ] Call _publish_world_update() in state update methods
  - In `update_world_state()` after saving (line ~340)
  - In `update_player_view()` after saving (line ~390)
  - See implementation guide: docs/scratchpad/nats-world-updates-implementation-analysis.md:866-888

- [ ] Inject NATS client in KB service startup
  - File: `app/services/kb/main.py`
  - Pattern: `state_manager.nats_client = nats_client` after connect
  - See implementation guide: docs/scratchpad/nats-world-updates-implementation-analysis.md:890-946

- [ ] Add logging for published NATS events
  - Log subject, experience, user_id, changes_count
  - Already included in _publish_world_update() implementation

- [ ] Write unit tests for NATS event publishing
  - File: `tests/unit/test_world_update_publishing.py`
  - Test with mock NATS client
  - Test graceful degradation (NATS client is None)
  - Test graceful degradation (publish raises exception)

#### Validation

- [ ] Test with manual NATS subscriber
  - Script: `tests/manual/test_nats_subscriber.py`
  - Verify events published to `world.updates.user.{user_id}`
  - Confirm event payload matches WorldUpdateEvent schema
  - See test script docs: tests/manual/README.md

- [ ] Verify graceful degradation
  - Stop NATS container: `docker compose stop nats`
  - Trigger state change (take bottle)
  - Confirm game continues, logs show error but no exception
  - Restart NATS: `docker compose start nats`

- [ ] Check logs for NATS connection
  - Look for: "KB Service starting up..."
  - Look for: "Published world_update to NATS"

**Complete Checklist**: docs/scratchpad/nats-world-updates-implementation-analysis.md:997-1020

**Why Phase 1A Now (After Phase 1B)**:
Phase 1B proved the subscription infrastructure works. Now we add KB publishing to generate the events that Phase 1B will forward. This completes the full server→client real-time pipeline.

---

## Next Phases

### WebSocket Testing & Deployment (1-2h) - IMMEDIATE

**Status**: 🎯 Ready to Start
**Timeline**: Wednesday (today) → Deploy by EOD
**Owner**: Server Team

**Tasks**:
- [ ] Test WebSocket endpoint locally
  - Run test client: `python tests/manual/test_websocket_experience.py`
  - Validate bottle collection flow
  - Verify NATS event forwarding
  - Check quest progress tracking

- [ ] Deploy to dev environment
  - Update Fly.io deployment
  - Verify WebSocket endpoint accessible
  - Provide URL to Unity team

- [ ] Document for Unity integration
  - Connection URL: `ws://gaia-kb-dev.fly.dev/ws/experience`
  - Authentication: JWT in query params
  - Protocol specification

**Success Criteria**:
- ✅ Local test client completes all tests
- ✅ Dev deployment accessible from Unity
- ✅ Unity team can connect and collect bottles
- ✅ Quest win condition triggers correctly

### Phase 3: Integration Testing (2-3h)

**Status**: 📅 Pending (after Phase 1A + 1B + Unity Phase 2)
**Coordination**: Joint testing with Unity team

- [ ] E2E test: Player action → KB state change → NATS → Chat → SSE
- [ ] Test user isolation (user A doesn't see user B's events)
- [ ] Test concurrent state changes
- [ ] Measure actual latency (compare to projected sub-100ms)
- [ ] Verify event ordering (world_update before narrative)

---

### Phase 5: WebSocket Migration to Session Service (9-13h server + 3-4h Unity)

**Status**: 📋 Deferred to Post-Demo (Q1 2026)
**Added**: 2025-11-05
**Document**: `docs/scratchpad/websocket-architecture-decision.md`
**Previous Doc**: `docs/scratchpad/websocket-migration-plan.md` (SSE→WebSocket migration)

**Objective**: Migrate WebSocket from KB Service to dedicated Session Service

**Why Deferred**:
- ✅ Friday demo deadline takes priority
- ✅ Current KB implementation works correctly
- ✅ Migration is non-breaking (protocol unchanged)
- ✅ Code is modular (easy to move)

**Migration Plan** (Q1 2026):

#### Phase 5A: Create Session Service (3-4h)
- [ ] Create new microservice: `app/services/session/`
- [ ] Dockerfile, fly.toml, deployment config
- [ ] Health endpoints, logging, monitoring
- [ ] NATS client integration

#### Phase 5B: Move WebSocket Infrastructure (2-3h)
- [ ] Move `ExperienceConnectionManager` → Session Service
- [ ] Move `/ws/experience` endpoint
- [ ] Move JWT WebSocket authentication
- [ ] Wire NATS subscriptions

#### Phase 5C: State Integration (1-2h)
- [ ] Subscribe to `world.updates.user.{user_id}`
- [ ] Forward NATS events → WebSocket clients
- [ ] Handle client actions → HTTP calls to KB Service
- [ ] Test end-to-end flow

#### Phase 5D: Dual Deployment (1h)
- [ ] Run both KB and Session WebSocket endpoints
- [ ] Update Unity to Session Service URL
- [ ] Validate no regressions
- [ ] Monitor both endpoints

#### Phase 5E: Deprecation (1h)
- [ ] Remove WebSocket from KB Service
- [ ] Update documentation
- [ ] Archive technical debt ticket

**Benefits Achieved**:
- ✅ Clean separation of concerns
- ✅ Independent scaling (connections vs state)
- ✅ Production-ready architecture
- ✅ Easier monitoring and optimization

**Migration Complexity**: LOW
- Code already modular
- NATS backend unchanged
- No protocol changes
- No Unity client changes (just URL)

**Original WebSocket Migration Plan**: See `websocket-migration-plan.md` for SSE→WebSocket transition (completed)

---

### Phase 5 (OLD): WebSocket Migration (9-13h server + 3-4h Unity)

**Status**: 📋 Planning Complete → Ready for Implementation
**Added**: 2025-11-05
**Document**: `docs/scratchpad/websocket-migration-plan.md` (1000+ lines)

**Objective**: Replace SSE per-request subscriptions with persistent WebSocket connections

**Why Now**:
- Phase 1B proved NATS subscription infrastructure works with SSE
- WebSocket enables autonomous world events (NPCs, other players, world changes)
- 5-10x latency reduction (no reconnection overhead per message)
- Bidirectional communication (single connection for send/receive)

**Implementation Strategy**: Dual Support (Zero Downtime)
- Phase 5A: Add WebSocket endpoints alongside existing SSE (both work)
- Phase 5B: Make WebSocket primary, keep SSE for compatibility
- Phase 5C: Deprecate SSE after adoption stabilizes

#### Server Tasks (9-13 hours)

- [ ] **Create WebSocket Infrastructure** (2-3h)
  - `app/services/chat/websocket_manager.py` - ConnectionManager class
  - Manages WebSocket lifecycle + persistent NATS subscriptions
  - Heartbeat for connection health monitoring
  - Graceful disconnect and cleanup

- [ ] **Implement WebSocket Endpoints** (2-3h)
  - `app/services/chat/websocket_endpoints.py` - `/ws` endpoint
  - WebSocket authentication (JWT in query params)
  - Message handlers: chat, command, position, ping
  - Reuse existing `unified_chat.process_stream()` logic

- [ ] **Add WebSocket Authentication** (1h)
  - `app/shared/security.py` - `get_current_user_ws()` function
  - JWT validation for WebSocket connections
  - Support token in query params: `/ws?token=<jwt>`

- [ ] **Integrate with Chat Service** (1-2h)
  - `app/services/chat/main.py` - Initialize ConnectionManager
  - Include WebSocket router alongside SSE router
  - Update health check with WebSocket connection count

- [ ] **Testing** (2-3h)
  - Unit tests: Connection lifecycle, message sending, NATS integration
  - Integration tests: E2E WebSocket flow, NATS event delivery
  - Load tests: 100 concurrent connections

- [ ] **Documentation** (1h)
  - Update API docs with WebSocket protocol
  - Create operational runbook for WebSocket
  - Update CLAUDE.md with WebSocket info

#### Unity Client Tasks (3-4 hours, Unity team)

- [ ] Install NativeWebSocket package
- [ ] Create `GaiaWebSocketClient.cs` component
- [ ] Implement connection with JWT authentication
- [ ] Add message handlers for world_update, content, heartbeat
- [ ] Wire to existing DirectiveQueue (no changes needed!)
- [ ] Add reconnection logic with exponential backoff
- [ ] Testing: Connect, send chat, receive world_update

#### Success Criteria

**Phase 5A Complete**:
- [ ] WebSocket `/ws` endpoint accessible
- [ ] Both SSE and WebSocket work simultaneously
- [ ] NATS subscriptions persist for WebSocket lifetime
- [ ] Health check shows active WebSocket connections
- [ ] Unit tests passing

**Phase 5B Complete**:
- [ ] Unity clients default to WebSocket
- [ ] <50ms latency for WebSocket messages
- [ ] 90%+ clients using WebSocket
- [ ] Error rate <0.1%

**Phase 5C Complete**:
- [ ] SSE endpoints removed from codebase
- [ ] Documentation updated (WebSocket only)
- [ ] All clients migrated

**Key Benefits Achieved**:
- ✅ Persistent NATS subscriptions (autonomous events work)
- ✅ Bidirectional communication (client can send position updates, etc.)
- ✅ Lower latency (5-10x improvement for interactive commands)
- ✅ Native Unity support (WebSocket is standard)

**Reference**: See `websocket-migration-plan.md` for complete FastAPI implementation patterns, Unity C# examples, migration strategy, and testing guide.

---

## Documentation References

- **Implementation Guide**: docs/scratchpad/nats-world-updates-implementation-analysis.md
- **Unity Coordination**: Symphony "directives" room (2025-11-02)
- **Schema Agreement**: WorldUpdateEvent v0.3 (state deltas)
- **Test Script**: tests/manual/test_nats_subscriber.py
- **Industry Research**: Minecraft, Roblox, WoW patterns (client-side interpretation)

---

## Current Status Summary

**Completed** (November 4, 2025):
- ✅ Phase 1B: Chat Service NATS subscriptions (3 hours actual)
- ✅ Bug fixes: NATS subscription tracking, AuthenticationResult compatibility
- ✅ Integration tests: Subscription lifecycle validation
- ✅ Documentation: 500+ lines of guides and examples

**Next** (2-3 hours):
- 🎯 Phase 1A: KB Service publishing (this document)

**After Phase 1A**:
- Phase 3: End-to-end integration testing (2-3 hours)
- Unity Phase 2: DirectiveQueue interpretation (3 hours, Unity team)

**Total Remaining Time**: 7-9 hours (server + testing + Unity)
**Target**: Full real-time pipeline with sub-100ms perceived latency for December 15 demo

---

## 📋 Prompt for Future Claude Code Session

**If this conversation context gets compacted or you're starting a fresh session**, use this prompt to resume work:

### Task: Implement Phase 1A - NATS World Updates (KB Service Publishing)

#### Context

You're implementing real-time world state synchronization for the GAIA platform. When players interact with the game world (e.g., "take bottle"), the KB Service updates state but clients don't see changes for 2-3 seconds (waiting for LLM narrative).

**Goal**: Publish state changes to NATS immediately so Unity clients can update visuals in projected sub-100ms while narrative completes in background.

**Coordination Status**:
- ✅ Unity team coordinated via Symphony "directives" room
- ✅ Schema agreed: WorldUpdateEvent v0.3 (state deltas)
- ✅ Unity implementing Phase 2 in parallel (DirectiveQueue interpretation)
- ✅ Integration testing (Phase 3) after both teams complete

#### What to Implement

Read the task list above in this file. You need to:

1. Define `WorldUpdateEvent` Pydantic schema in `app/shared/events.py`
2. Add NATS subject helper to `app/shared/nats_client.py`
3. Modify `UnifiedStateManager` to publish events after state changes
4. Wire NATS client into KB service startup
5. Add logging and tests

**Estimated time**: 2-3 hours

#### Critical Documentation

**READ THIS FIRST**: `docs/scratchpad/nats-world-updates-implementation-analysis.md`

This document contains:
- Complete implementation guide with exact code placement (lines 777-1021)
- WorldUpdateEvent schema definition (lines 689-752)
- Error handling strategy (graceful degradation)
- Code examples for every step
- Validation checklist

**Also read**:
- `tests/manual/README.md` - How to test with NATS subscriber
- This file (TODO.md) - Task checklist with file paths

#### Key Decisions Already Made

**DO:**
- ✅ Use state deltas (operation: add/remove/update) - matches Minecraft/Roblox/WoW
- ✅ Client-side interpretation (Unity's DirectiveQueue) - industry best practice
- ✅ Graceful degradation - NATS failures should NOT break game logic
- ✅ Include version: "0.3" field for future compatibility

**DON'T:**
- ❌ Transform state deltas to rendering commands - that's Unity's job
- ❌ Make NATS required - it's a performance optimization, not critical path
- ❌ Send concrete Unity instructions - server stays domain-focused

#### Schema (Already Agreed with Unity)

```python
class WorldUpdateEvent(BaseModel):
    type: Literal["world_update"] = "world_update"
    version: str = Field(default="0.3")
    experience: str
    user_id: str
    changes: Dict[str, Any]  # State delta with operations
    timestamp: int
    metadata: Optional[Dict[str, Any]] = None
```

Unity team expects:
- `operation: "add"` - Object added to location/inventory
- `operation: "remove"` - Object removed
- `operation: "update"` - Properties changed

#### Testing

After implementation:
1. Start Docker services: `docker compose up`
2. Run NATS subscriber: `python tests/manual/test_nats_subscriber.py`
3. Trigger state change: `./scripts/test.sh --local chat "take dream bottle"`
4. Verify events appear in subscriber output

**Success criteria**:
- Events published to `world.updates.user.{user_id}`
- Payload matches WorldUpdateEvent schema
- Game continues if NATS is down (check logs)

#### Implementation Strategy

Follow the guide in `docs/scratchpad/nats-world-updates-implementation-analysis.md` starting at line 777 ("Phase 1 Implementation Guide").

Work through tasks in order (they have dependencies):
1. Schema first (enables everything else)
2. Subject helper (used by publishing method)
3. UnifiedStateManager modifications (core logic)
4. KB service startup wiring (dependency injection)
5. Tests (validation)

Mark tasks complete in this file by changing `- [ ]` to `- [x]`.

#### If You Get Stuck

Check:
- Implementation guide has exact line numbers and code examples
- Validation checklist at docs/scratchpad/nats-world-updates-implementation-analysis.md:997-1020
- Existing NATS usage in `app/services/chat/main.py` (same pattern)

#### When Complete

Update this TODO.md and tell the user:
- Phase 1A complete
- How to test (NATS subscriber script)
- Ready for Phase 1B (Chat Service SSE forwarding)

---

**Start by reading the implementation guide, then work through the task list sequentially.**
