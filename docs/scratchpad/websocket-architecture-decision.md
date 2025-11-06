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

## Conclusion

**Shipping with technical debt is a valid engineering decision when:**
- Timeline is firm (✅ Friday demo)
- Debt is documented (✅ This document)
- Migration path exists (✅ Clear, non-breaking)
- Code quality is high (✅ Modular, testable)

**Recommendation**: Ship Option A for demo, migrate to Option C post-demo.
