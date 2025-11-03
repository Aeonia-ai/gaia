# GAIA Development TODO

## Active Work

### Phase 1A: NATS World Updates - KB Service Publishing (2-3h)

**Status**: 🚧 In Progress
**Started**: 2025-11-02
**Owner**: server-coder
**Coordination**: Unity team via Symphony "directives" room (Phase 2 in parallel)

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

---

## Next Phases

### Phase 1B: Chat Service SSE Forwarding (3-4h)

**Status**: 📅 Pending (after Phase 1A)
**Objective**: Chat Service subscribes to NATS and forwards world_update events to SSE stream

- [ ] Create merge_async_streams() utility in app/shared/stream_utils.py
- [ ] Add NATS subscription in unified_chat.py:process_stream()
- [ ] Multiplex world_update events into SSE stream
- [ ] Handle subscription cleanup on disconnect
- [ ] Add error handling for NATS failures
- [ ] Unit tests for stream multiplexing

**Documentation**: docs/scratchpad/nats-world-updates-implementation-analysis.md (Phase 2 section)

### Phase 3: Integration Testing (2-3h)

**Status**: 📅 Pending (after Phase 1A + 1B + Unity Phase 2)
**Coordination**: Joint testing with Unity team

- [ ] E2E test: Player action → KB state change → NATS → Chat → SSE
- [ ] Test user isolation (user A doesn't see user B's events)
- [ ] Test concurrent state changes
- [ ] Measure actual latency (compare to projected sub-100ms)
- [ ] Verify event ordering (world_update before narrative)

---

## Documentation References

- **Implementation Guide**: docs/scratchpad/nats-world-updates-implementation-analysis.md
- **Unity Coordination**: Symphony "directives" room (2025-11-02)
- **Schema Agreement**: WorldUpdateEvent v0.3 (state deltas)
- **Test Script**: tests/manual/test_nats_subscriber.py
- **Industry Research**: Minecraft, Roblox, WoW patterns (client-side interpretation)

---

**Last Updated**: 2025-11-02
**Total Estimated Time**: 9-13 hours (server-side only)
**Target**: 100-user prototype with sub-100ms perceived latency
