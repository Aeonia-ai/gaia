# GAIA Development TODO

**Last Updated**: 2025-11-05
**Current Status**: WebSocket Implementation Complete (KB Service) ✅ → Testing & Deployment Next 🎯

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

---

## Active Work

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
