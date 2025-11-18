# WebSocket Architecture Decision Document

**Date**: 2025-11-05
**Status**: Decision Required
**Timeline**: Friday Demo Deadline (3 days)

---

## Executive Summary

Implemented WebSocket in KB Service following "fast path" approach, but Perplexity analysis identifies this as **industry anti-pattern**. Need architectural decision: ship with technical debt for demo, or refactor now?

---

## Current Implementation (Option A: KB Service)

### What Was Built (2.5 hours)

**Files Created**:
- `app/services/kb/experience_connection_manager.py` (250 lines)
- `app/services/kb/websocket_experience.py` (450 lines)
- `app/shared/security.py` (added `get_current_user_ws()`)
- `tests/manual/test_websocket_experience.py` (300 lines)

**Architecture**:
```
Unity Client → ws://kb-service:8000/ws/experience
                ↓
         ExperienceConnectionManager
                ↓
         UnifiedStateManager (same service)
                ↓
         NATS publish (world updates)
```

### Pros ✅
- **Fastest path** - Direct connection to state manager
- **Minimal latency** - Projected sub-100ms
- **90% complete** - 1 hour to test + deploy
- **Leverages existing** - Phase 1A/1B NATS already done

### Cons ❌
- **Violates separation of concerns** - Mixes connection + state management
- **Harder to scale** - Can't scale connections independently
- **Technical debt** - Not production-ready architecture
- **Operational complexity** - State and connections compete for resources

### Industry Best Practice Rating
❌ **Not Recommended** (per Perplexity, FastAPI patterns)

---

## Alternative: Option B (Gateway Service)

### Proposed Architecture

```
Unity Client → ws://gateway:8666/ws/experience
                ↓
         Gateway WebSocket Handler
                ↓
         HTTP/NATS to KB Service
                ↓
         UnifiedStateManager
                ↓
         NATS publish
                ↓
         Gateway forwards to client
```

### Implementation Required (2-3 hours)

1. **Move WebSocket endpoint to Gateway** (1h)
   - Copy `ExperienceConnectionManager` → Gateway
   - Add `/ws/experience` route to Gateway
   - Wire NATS client in Gateway

2. **Add HTTP bridge KB Service** (30 min)
   - Keep KB Service HTTP endpoints for state changes
   - Gateway calls KB via HTTP for bottle collection
   - KB publishes to NATS as before

3. **Update Unity client** (Unity team, 30 min)
   - Change URL: `ws://gateway/ws/experience`
   - Protocol unchanged

4. **Testing** (1h)
   - Validate end-to-end flow
   - Check latency (should be <200ms)

### Pros ✅
- **Centralized entry point** - Single public endpoint
- **Better separation** - Gateway handles connections, KB handles state
- **Easier load balancing** - Standard patterns apply
- **Simpler ops** - One less service exposed

### Cons ⚠️
- **Adds latency** - Extra hop (Gateway → KB)
- **Gateway becomes critical** - Single point of failure
- **Still not ideal** - Gateway doing too much

### Industry Best Practice Rating
⚖️ **Acceptable** (better than Option A, not perfect)

---

## Recommended: Option C (Dedicated Session Service)

### Proposed Architecture

```
Unity Client → ws://session-service:8003/ws/experience
                ↓
         SessionConnectionManager
                ↓ (WebSocket)
         Client
                ↑ (NATS)
         KB Service publishes state changes
```

### Implementation Required (9-13 hours)

**Phase 1: New Service Creation** (3-4h)
- Create `app/services/session/` microservice
- Dockerfile, fly.toml, deployment config
- Health endpoints, logging, monitoring

**Phase 2: WebSocket Infrastructure** (2-3h)
- Move `ExperienceConnectionManager` → Session Service
- Add `/ws/experience` endpoint
- JWT authentication
- NATS subscription management

**Phase 3: State Integration** (1-2h)
- Subscribe to NATS `world.updates.user.{user_id}`
- Forward NATS events → WebSocket clients
- Handle client actions → HTTP calls to KB Service

**Phase 4: Testing & Deployment** (2-3h)
- Unit tests (connection lifecycle)
- Integration tests (E2E flow)
- Load tests (100 concurrent connections)
- Deploy to dev

**Phase 5: Unity Integration** (Unity team, 1h)
- Update connection URL
- Test with dev environment

### Pros ✅
- **Clean separation** - Connection management vs State management
- **Independent scaling** - Scale connections without KB
- **Production-ready** - Industry best practice
- **Future-proof** - Easy to add features (presence, chat, etc.)
- **Monitoring** - Dedicated metrics for connections

### Cons ⚠️
- **Timeline risk** - 9-13 hours may miss Friday deadline
- **Operational complexity** - One more service to manage
- **Initial overhead** - More setup work

### Industry Best Practice Rating
✅ **Highly Recommended** (Perplexity, microservices patterns)

---

## Decision Matrix

| Criteria | Option A (KB) | Option B (Gateway) | Option C (Session) |
|----------|---------------|-------------------|-------------------|
| **Timeline** | ✅ 1h | ⚠️ 2-3h | ❌ 9-13h |
| **Demo Ready** | ✅ Wed EOD | ⚠️ Thu EOD | ❌ Maybe not |
| **Latency** | ✅ <100ms | ⚠️ <200ms | ✅ <100ms |
| **Scalability** | ❌ Poor | ⚠️ OK | ✅ Excellent |
| **Separation** | ❌ Violation | ⚠️ Better | ✅ Clean |
| **Tech Debt** | ❌ High | ⚠️ Medium | ✅ None |
| **Ops Complexity** | ⚠️ Medium | ⚠️ Medium | ⚠️ High |

---

## Recommended Path: Hybrid Approach

### Ship Path 1 for Demo, Migrate to Path 3 Post-Demo

**Week 1 (Now → Friday Demo)**:
1. Keep current KB implementation (Option A)
2. Document technical debt in CLAUDE.md
3. Test + deploy to dev by Wednesday EOD
4. Unity integration Thursday
5. Demo Friday ✅

**Week 2 (Post-Demo)**:
1. Create dedicated Session service (Option C)
2. Run dual services (KB WebSocket + Session Service)
3. Migrate Unity clients to Session Service
4. Deprecate KB WebSocket endpoints

**Why This Works**:
- ✅ Meets Friday deadline
- ✅ No client-breaking changes (protocol stays same)
- ✅ Modular code already written (easy to move)
- ✅ NATS backend unchanged
- ✅ Production-ready architecture achieved

---

## Migration Complexity Analysis

### KB → Session Service Migration

**Easy** ✅
- Copy `ExperienceConnectionManager` class (no changes needed)
- Copy `websocket_experience.py` endpoint
- Wire NATS client (same pattern as KB Service)
- Update Unity client URL (one line change)

**No Business Logic Changes**:
- UnifiedStateManager stays in KB Service
- NATS publishing stays in KB Service
- State update logic unchanged
- Protocol unchanged

**Why Migration is Simple**:
- Connection management already separated in `ExperienceConnectionManager`
- No tight coupling to KB Service internals
- Communication happens via NATS (location-independent)
- Unity client protocol-agnostic

---

## Cost-Benefit Analysis

### Option A (Ship Now)
- **Cost**: Technical debt, future refactor required
- **Benefit**: Friday demo achieved, Unity team unblocked
- **Refactor Cost**: 9-13 hours (post-demo, no deadline pressure)

### Option B (Gateway)
- **Cost**: 2-3 hours now, Thursday deadline risk
- **Benefit**: Better architecture, still demo-ready
- **Refactor Cost**: Still need Session service eventually (7-10h later)

### Option C (Session Service Now)
- **Cost**: 9-13 hours now, Friday deadline at risk
- **Benefit**: Production-ready from day one
- **Refactor Cost**: None

---

## Recommendation

**For AEO-65 Demo**: Option A (KB Service)
**Post-Demo (Q1 2026)**: Migrate to Option C (Session Service)

**Rationale**:
1. Friday deadline is firm
2. Unity team blocked on integration testing
3. Technical debt is contained (ExperienceConnectionManager is modular)
4. Migration path is clear and non-breaking
5. Existing code quality is high (easy to move)

**Action Items**:
- [ ] Document technical debt in CLAUDE.md
- [ ] Test KB WebSocket implementation (1h)
- [ ] Deploy to dev by Wednesday EOD
- [ ] Create migration plan for Session Service
- [ ] Schedule post-demo refactor (Q1 2026)

---

## Questions for Decision Maker

1. **Is Friday demo deadline firm?** (affects go/no-go on Option C)
2. **Risk tolerance**: Ship with tech debt or risk deadline?
3. **Post-demo timeline**: When can we prioritize Session service migration?
4. **Unity team**: Can they wait until Thursday for dev endpoint?

---

## Technical Debt Tracking

If we ship Option A, document as:

```markdown
## Known Technical Debt

### WebSocket in KB Service (AEO-65 Demo Fast Path)

**Issue**: WebSocket endpoint in KB Service violates separation of concerns.

**Impact**:
- Cannot scale WebSocket connections independently
- KB Service doing double duty (state + connections)
- Not production-ready architecture

**Mitigation**:
- Code is modular (ExperienceConnectionManager)
- Migration path defined
- No breaking changes to clients

**Remediation Plan** (Q1 2026):
1. Create dedicated Session service
2. Move WebSocket infrastructure
3. Update Unity clients
4. Deprecate KB WebSocket endpoints

**Estimated Effort**: 9-13 hours
**Priority**: High (before production scale-up)
```

---

## Message Flow Analysis

### Current Flow (WebSocket in KB Service)

**Redundant but Functional:**
```
Unity → WebSocket: collect_bottle
  ↓
KB Handler → update_player_view()
  ↓
State Manager: write to disk + publish NATS
  ↓
Two paths:
  Path A (Immediate): Handler → Client (action_response, quest_update)
  Path B (NATS Echo): NATS → Same Connection → Client (world_update)
```

**Why This is Acceptable Technical Debt:**
- Immediate response = good UX (fast feedback)
- NATS echo = enables future multi-client scenarios
- Common pattern in real-time systems (Discord, Slack do this)

### After Migration (Session Service - Cleaner)

**Single Message Path:**
```
Unity → Session Service WebSocket: collect_bottle
  ↓
Session Service → HTTP POST to KB Service API
  ↓
KB Service: update state + publish NATS
  ↓
Session Service NATS subscription receives event
  ↓
Session Service → WebSocket Client (SINGLE source of truth)
```

**Natural Architecture Improvements:**
- ✅ No direct state manager access (can't send immediate responses)
- ✅ Single message path (only NATS events)
- ✅ Session Service is pure message forwarder
- ✅ Consistent with Chat SSE (same NATS events)
- ✅ Eliminates redundancy automatically

**Migration Benefits:**
Not just moving code - forces cleaner architecture naturally. WebSocket becomes "dumb pipe" forwarding NATS events, which is exactly what it should be.

---

## Conclusion

**Shipping with technical debt is a valid engineering decision when:**
- Timeline is firm (✅ Friday demo)
- Debt is documented (✅ This document)
- Migration path exists (✅ Clear, non-breaking)
- Code quality is high (✅ Modular, testable)
- Migration naturally fixes the debt (✅ Session Service eliminates redundancy)

**Recommendation**: Ship Option A for demo, migrate to Option C post-demo.

**Status**: ✅ SHIPPED (2025-11-05)
- Commit: 5b51ae1 on feature/unified-experience-system
- Local testing: All tests passing (7/7 bottles, NATS working)
- Auto-bootstrap: Implemented (industry standard lazy init)

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

The core architectural claims in this document have been verified against the source code.

-   **✅ Current Implementation (Option A: KB Service) (Section "Current Implementation" of this document):**
    *   **Claim:** WebSocket endpoint is implemented in the KB Service.
    *   **Code Reference:** `app/services/kb/websocket_experience.py` (lines 47-125).
    *   **Verification:** Confirmed the presence of the WebSocket endpoint in the KB service, handling authentication and connection management.

-   **✅ Alternative: Option B (Gateway Service) (Section "Alternative: Option B" of this document):**
    *   **Claim:** A Gateway WebSocket proxy is implemented.
    *   **Code Reference:** `app/gateway/main.py` (lines 1195-1344).
    *   **Verification:** Confirmed the implementation of the Gateway WebSocket proxy, which transparently tunnels connections to the KB Service. This aligns with the "Recommended Path: Hybrid Approach" to ship Option A for demo and migrate to Option C post-demo, with Option B being an interim step that has been implemented.

-   **✅ Technical Debt Acknowledgment (Section "Technical Debt Tracking" of this document):**
    *   **Claim:** The WebSocket in KB Service is acknowledged as technical debt with a remediation plan.
    *   **Verification:** This document itself serves as the primary evidence of this acknowledgment and the planned migration to a dedicated Session Service (Option C). The modularity of `ExperienceConnectionManager` in `app/services/kb/experience_connection_manager.py` (lines 31-285) supports the ease of migration as described.

**Conclusion:** The architectural decisions and the current state of the WebSocket implementation are highly consistent with the details described in this document. The document accurately reflects the "fast path" approach taken for the demo and the subsequent implementation of the Gateway proxy as an interim solution.
