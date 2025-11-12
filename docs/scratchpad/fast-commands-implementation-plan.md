# Fast Commands Implementation Plan

**Date**: 2025-11-10
**Status**: Ready to Implement
**Effort**: 3-4 hours
**Priority**: HIGH (Unity integration blocker)

---

## Executive Summary

Add fast Python handlers for `"go"` and `"collect"` message types, following the existing pattern used by `"update_location"` and `"ping"`. This will reduce response time from 25-30 seconds (LLM) to <100ms (direct Python) for Unity game clients.

**Current**: All game commands go through LLM markdown processing (25-30s)
**Proposed**: Add direct Python handlers for common commands (<100ms)
**Pattern**: Already exists for `"ping"` and `"update_location"`

---

## Architecture Overview

### Current Message Routing (websocket_experience.py lines 175-189)

```python
if message_type == "action":
    # SLOW: LLM markdown processing (25-30s)
    await handle_action(websocket, ..., message)

elif message_type == "ping":
    # FAST: Direct Python (<50ms)
    await handle_ping(websocket, ..., message)

elif message_type == "update_location":
    # FAST: Direct Python (<100ms)
    await handle_update_location(websocket, ..., message)
```

### Proposed Addition

```python
elif message_type == "go":
    # FAST: Direct Python (<100ms) - NEW!
    await handle_go(websocket, ..., message)

elif message_type == "collect":
    # FAST: Direct Python (<100ms) - NEW!
    await handle_collect(websocket, ..., message)
```

---

## Implementation Tasks

### Task 1: Add "go" Message Handler (1 hour)

**File**: `app/services/kb/websocket_experience.py`

#### Step 1.1: Add Message Type Route (5 min)

**Location**: After line 189

```python
elif message_type == "go":
    await handle_go(websocket, connection_id, user_id, experience, message)
```

#### Step 1.2: Implement Handler Function (45 min)

**Location**: After line 450 (after `send_error`)

```python
async def handle_go(
    websocket: WebSocket,
    connection_id: str,
    user_id: str,
    experience: str,
    message: Dict[str, Any]
):
    """
    Handle "go" command with direct Python execution (no LLM).

    Message format:
        {"type": "go", "destination": "spawn_zone_1"}

    Response:
        {"type": "go_response", "success": true, "destination": "spawn_zone_1"}

    Speed: <100ms (direct state access, no LLM)
    """
    destination = message.get("destination")

    if not destination:
        await send_error(websocket, "missing_destination", "'destination' field required")
        return

    try:
        # Get state manager
        state_manager = kb_agent.state_manager
        if not state_manager:
            await send_error(websocket, "server_error", "State manager not initialized")
            return

        # Ensure player initialized
        await state_manager.ensure_player_initialized(experience, user_id)

        # Get player state
        player_view = await state_manager.get_player_view(experience, user_id)
        current_location = player_view.get("player", {}).get("current_location")

        if not current_location:
            await send_error(websocket, "no_location", "Player has no current location")
            return

        # Get world state to validate destination
        world_state = await state_manager.get_world_state(experience)
        location_data = world_state.get("locations", {}).get(current_location, {})
        sublocations = location_data.get("sublocations", {})

        # Check if destination is a valid sublocation
        if destination not in sublocations:
            await websocket.send_json({
                "type": "go_response",
                "success": False,
                "error": "destination_not_found",
                "message": f"Destination '{destination}' not found in {current_location}",
                "available_destinations": list(sublocations.keys()),
                "timestamp": int(datetime.utcnow().timestamp() * 1000)
            })
            return

        # Update player sublocation
        await state_manager.update_player_sublocation(
            experience=experience,
            user_id=user_id,
            sublocation=destination
        )

        # Send success response
        await websocket.send_json({
            "type": "go_response",
            "success": True,
            "destination": destination,
            "message": f"You move to {destination}",
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        })

        logger.info(
            f"Player {user_id} moved to {destination} in {current_location} "
            f"(connection_id={connection_id})"
        )

    except Exception as e:
        logger.error(f"Error handling 'go' command: {e}", exc_info=True)
        await send_error(websocket, "go_failed", str(e))
```

#### Step 1.3: Add State Manager Method (10 min)

**File**: `app/services/kb/unified_state_manager.py`

**Location**: Add new method to `UnifiedStateManager` class

```python
async def update_player_sublocation(
    self,
    experience: str,
    user_id: str,
    sublocation: str
) -> None:
    """
    Update player's current sublocation (fast path for 'go' command).

    Args:
        experience: Experience ID
        user_id: User ID
        sublocation: Target sublocation ID
    """
    player_view_path = self._get_player_view_path(experience, user_id)

    # Read current player view
    async with aiofiles.open(player_view_path, 'r') as f:
        player_view = json.loads(await f.read())

    # Update sublocation
    player_view["player"]["current_sublocation"] = sublocation

    # Write back
    async with aiofiles.open(player_view_path, 'w') as f:
        await f.write(json.dumps(player_view, indent=2))

    logger.info(f"Updated player {user_id} sublocation to {sublocation}")
```

---

### Task 2: Add "collect" Message Handler (1.5 hours)

**File**: `app/services/kb/websocket_experience.py`

#### Step 2.1: Add Message Type Route (5 min)

**Location**: After "go" route

```python
elif message_type == "collect":
    await handle_collect(websocket, connection_id, user_id, experience, message)
```

#### Step 2.2: Implement Handler Function (1 hour 15 min)

**Location**: After `handle_go`

```python
async def handle_collect(
    websocket: WebSocket,
    connection_id: str,
    user_id: str,
    experience: str,
    message: Dict[str, Any]
):
    """
    Handle "collect" command with direct Python execution (no LLM).

    Message format:
        {"type": "collect", "instance_id": "dream_bottle_woander_1"}

    Response:
        {"type": "collect_response", "success": true, "item": {...}}

    Also publishes world_update event via NATS.

    Speed: <100ms (direct state access, no LLM)
    """
    instance_id = message.get("instance_id")

    if not instance_id:
        await send_error(websocket, "missing_instance_id", "'instance_id' field required")
        return

    try:
        # Get state manager
        state_manager = kb_agent.state_manager
        if not state_manager:
            await send_error(websocket, "server_error", "State manager not initialized")
            return

        # Ensure player initialized
        await state_manager.ensure_player_initialized(experience, user_id)

        # Get player state
        player_view = await state_manager.get_player_view(experience, user_id)
        current_location = player_view.get("player", {}).get("current_location")
        current_sublocation = player_view.get("player", {}).get("current_sublocation")

        if not current_location:
            await send_error(websocket, "no_location", "Player has no current location")
            return

        # Get world state
        world_state = await state_manager.get_world_state(experience)

        # Find item at player's current location/sublocation
        item = None
        item_path = None

        location_data = world_state.get("locations", {}).get(current_location, {})

        if current_sublocation:
            # Check sublocation items
            sublocation_data = location_data.get("sublocations", {}).get(current_sublocation, {})
            items = sublocation_data.get("items", [])
            item_path = f"locations.{current_location}.sublocations.{current_sublocation}.items"
        else:
            # Check top-level location items
            items = location_data.get("items", [])
            item_path = f"locations.{current_location}.items"

        # Find item by instance_id
        item_index = None
        for idx, potential_item in enumerate(items):
            if potential_item.get("instance_id") == instance_id:
                item = potential_item
                item_index = idx
                break

        if not item:
            await websocket.send_json({
                "type": "collect_response",
                "success": False,
                "error": "item_not_found",
                "message": f"Item '{instance_id}' not found at your current location",
                "timestamp": int(datetime.utcnow().timestamp() * 1000)
            })
            return

        # Check if collectible
        if not item.get("collectible", True):
            await websocket.send_json({
                "type": "collect_response",
                "success": False,
                "error": "not_collectible",
                "message": f"You can't collect that item",
                "timestamp": int(datetime.utcnow().timestamp() * 1000)
            })
            return

        # Remove from world, add to inventory
        await state_manager.collect_item(
            experience=experience,
            user_id=user_id,
            instance_id=instance_id,
            item=item,
            world_path=item_path,
            item_index=item_index
        )

        # Send success response
        await websocket.send_json({
            "type": "collect_response",
            "success": True,
            "instance_id": instance_id,
            "item": item,
            "message": f"You collected {item.get('semantic_name', 'the item')}",
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        })

        logger.info(
            f"Player {user_id} collected {instance_id} from {current_location}"
            f"{'.' + current_sublocation if current_sublocation else ''} "
            f"(connection_id={connection_id})"
        )

        # World update event is published by collect_item method

    except Exception as e:
        logger.error(f"Error handling 'collect' command: {e}", exc_info=True)
        await send_error(websocket, "collect_failed", str(e))
```

#### Step 2.3: Add State Manager Method (10 min)

**File**: `app/services/kb/unified_state_manager.py`

```python
async def collect_item(
    self,
    experience: str,
    user_id: str,
    instance_id: str,
    item: Dict[str, Any],
    world_path: str,
    item_index: int
) -> None:
    """
    Collect item: remove from world, add to inventory, publish world_update.

    Args:
        experience: Experience ID
        user_id: User ID
        instance_id: Item instance ID
        item: Item data
        world_path: Path to items array in world state
        item_index: Index of item in array
    """
    # Get base version before changes
    base_version = await self.get_snapshot_version(experience, user_id)

    # Remove from world
    world_state_path = self._get_world_state_path(experience)
    async with aiofiles.open(world_state_path, 'r') as f:
        world_state = json.loads(await f.read())

    # Navigate to items array and remove item
    path_parts = world_path.split('.')
    container = world_state
    for part in path_parts[:-1]:
        container = container[part]

    items_array = container[path_parts[-1]]
    removed_item = items_array.pop(item_index)

    # Write world state back
    async with aiofiles.open(world_state_path, 'w') as f:
        await f.write(json.dumps(world_state, indent=2))

    # Add to player inventory
    player_view_path = self._get_player_view_path(experience, user_id)
    async with aiofiles.open(player_view_path, 'r') as f:
        player_view = json.loads(await f.read())

    if "inventory" not in player_view["player"]:
        player_view["player"]["inventory"] = []

    player_view["player"]["inventory"].append(item)

    # Increment snapshot version
    new_snapshot_version = int(datetime.utcnow().timestamp() * 1000)
    player_view["snapshot_version"] = new_snapshot_version

    async with aiofiles.open(player_view_path, 'w') as f:
        await f.write(json.dumps(player_view, indent=2))

    # Publish world_update event
    await self.publish_world_update(
        experience=experience,
        user_id=user_id,
        base_version=base_version,
        snapshot_version=new_snapshot_version,
        changes=[
            {
                "operation": "remove",
                "area_id": player_view["player"].get("current_sublocation"),
                "instance_id": instance_id
            },
            {
                "operation": "add",
                "area_id": None,
                "path": "player.inventory",
                "item": item
            }
        ]
    )

    logger.info(f"Collected item {instance_id} for user {user_id}")
```

---

### Task 3: Testing (1 hour)

#### Step 3.1: Update Test Scripts (15 min)

**File**: `scripts/experience/test_fast_commands.py` (NEW)

```python
#!/usr/bin/env python3
"""Test fast 'go' and 'collect' commands (<100ms response time)."""

import asyncio
import json
import time
import websockets

async def test_fast_commands():
    token = open("/tmp/jwt_token.txt").read().strip()
    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience=wylding-woods"

    print("=== Fast Commands Test ===\n")

    async with websockets.connect(ws_url) as ws:
        # Welcome
        welcome = json.loads(await ws.recv())
        print(f"✅ Connected: {welcome['user_id']}\n")

        # Test 1: Fast "go" command
        print("Test 1: Fast 'go' command")
        t0 = time.time()
        await ws.send(json.dumps({
            "type": "go",
            "destination": "spawn_zone_1"
        }))
        response = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        elapsed = (time.time() - t0) * 1000

        print(f"  Response time: {elapsed:.0f}ms")
        print(f"  Success: {response.get('success')}")
        print(f"  Destination: {response.get('destination')}")

        assert elapsed < 1000, f"Too slow! ({elapsed}ms)"
        assert response["success"] == True
        print("  ✅ PASS\n")

        # Test 2: Fast "collect" command
        print("Test 2: Fast 'collect' command")
        t0 = time.time()
        await ws.send(json.dumps({
            "type": "collect",
            "instance_id": "dream_bottle_woander_1"
        }))

        # Collect both response and world_update
        messages = []
        for _ in range(2):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            messages.append(msg)

        elapsed = (time.time() - t0) * 1000

        collect_response = next(m for m in messages if m["type"] == "collect_response")
        world_update = next((m for m in messages if m["type"] == "world_update"), None)

        print(f"  Response time: {elapsed:.0f}ms")
        print(f"  Success: {collect_response.get('success')}")
        print(f"  Item: {collect_response.get('instance_id')}")
        print(f"  World update: {'✅' if world_update else '❌'}")

        assert elapsed < 1000, f"Too slow! ({elapsed}ms)"
        assert collect_response["success"] == True
        assert world_update is not None
        print("  ✅ PASS\n")

        print("=== All Tests Passed! ===")

asyncio.run(test_fast_commands())
```

#### Step 3.2: Manual Testing (15 min)

```bash
# Start server
docker compose up

# Generate JWT
python3 tests/manual/get_test_jwt.py > /tmp/jwt_token.txt

# Run fast commands test
./scripts/experience/test_fast_commands.py
```

**Expected output**:
```
=== Fast Commands Test ===

✅ Connected: b18c47d8-3bb5-46be-98d4-c3950aa565a5

Test 1: Fast 'go' command
  Response time: 85ms
  Success: True
  Destination: spawn_zone_1
  ✅ PASS

Test 2: Fast 'collect' command
  Response time: 92ms
  Success: True
  Item: dream_bottle_woander_1
  World update: ✅
  ✅ PASS

=== All Tests Passed! ===
```

#### Step 3.3: Integration Testing (15 min)

Test with existing v0.4 test:

```bash
# Should still work (backward compatible)
./scripts/experience/test_websocket_v04.py
```

#### Step 3.4: Performance Benchmarking (15 min)

```python
# Benchmark script
for i in range(10):
    # Fast command
    t0 = time.time()
    response = await send_message({"type": "go", "destination": "spawn_zone_1"})
    fast_time = time.time() - t0

    # Slow command (for comparison)
    t0 = time.time()
    response = await send_message({"type": "action", "action": "go to spawn_zone_1"})
    slow_time = time.time() - t0

    print(f"Fast: {fast_time*1000:.0f}ms, Slow: {slow_time*1000:.0f}ms, Speedup: {slow_time/fast_time:.0f}x")
```

**Expected**:
```
Fast: 87ms, Slow: 26543ms, Speedup: 305x
Fast: 92ms, Slow: 28129ms, Speedup: 306x
...
Average speedup: ~300x faster
```

---

### Task 4: Documentation (30 min)

#### Step 4.1: Update WebSocket Protocol Docs (15 min)

**File**: `docs/scratchpad/websocket-aoi-client-guide.md`

Add section for fast commands:

```markdown
## Fast Commands (Direct Python)

For performance-critical game actions, use dedicated message types with
direct Python execution (no LLM processing).

### Go Command (Navigation)

**Message**:
```json
{
  "type": "go",
  "destination": "spawn_zone_1"
}
```

**Response** (<100ms):
```json
{
  "type": "go_response",
  "success": true,
  "destination": "spawn_zone_1",
  "message": "You move to spawn_zone_1",
  "timestamp": 1731301234000
}
```

### Collect Command (Item Pickup)

**Message**:
```json
{
  "type": "collect",
  "instance_id": "dream_bottle_woander_1"
}
```

**Response** (<100ms):
```json
{
  "type": "collect_response",
  "success": true,
  "instance_id": "dream_bottle_woander_1",
  "item": {...},
  "timestamp": 1731301234000
}
```

**World Update** (published via NATS):
```json
{
  "type": "world_update",
  "version": "0.4",
  "base_version": 1731301234000,
  "snapshot_version": 1731301235000,
  "changes": [
    {
      "operation": "remove",
      "area_id": "spawn_zone_1",
      "instance_id": "dream_bottle_woander_1"
    },
    {
      "operation": "add",
      "area_id": null,
      "path": "player.inventory",
      "item": {...}
    }
  ]
}
```

**Response Time**: <100ms (300x faster than LLM commands)
```

#### Step 4.2: Update Implementation Status (15 min)

**File**: `docs/scratchpad/fast-commands-implementation-plan.md` (this file)

Mark tasks as complete, add "Completed" section.

---

## Success Criteria

### Performance Targets

- [x] `go` command responds in <100ms (currently 25-30s)
- [x] `collect` command responds in <100ms (currently 25-30s)
- [x] world_update events still published correctly
- [x] Backward compatible (LLM commands still work)

### Testing Requirements

- [x] Unit tests for state manager methods
- [x] Integration tests for WebSocket handlers
- [x] Performance benchmarks showing 250-300x speedup
- [x] Existing v0.4 tests still pass

### Documentation Requirements

- [x] WebSocket protocol updated
- [x] Unity integration guide updated
- [x] Code comments added to handlers
- [x] Implementation plan marked complete

---

## Rollout Plan

### Phase 1: Local Testing (Day 1)

```bash
# Implement handlers
# Run test suite
./scripts/experience/test_fast_commands.py
./scripts/experience/test_websocket_v04.py

# Performance benchmark
./scripts/experience/benchmark_fast_vs_slow.py
```

### Phase 2: Unity Integration (Day 2)

```csharp
// Unity updates client code
public void MoveTo(string sublocation) {
    SendMessage(new {
        type = "go",
        destination = sublocation
    });
}

public void CollectItem(string instanceId) {
    SendMessage(new {
        type = "collect",
        instance_id = instanceId
    });
}
```

### Phase 3: Deploy to Dev (Day 3)

```bash
# Deploy updated KB service
./scripts/deploy.sh --env dev --services kb --remote-only --rebuild

# Validate
curl https://gaia-kb-dev.fly.dev/health
```

### Phase 4: Monitor & Iterate (Days 4-7)

- Monitor response times
- Collect Unity feedback
- Fix any edge cases
- Document lessons learned

---

## Risk Assessment

### Low Risk

- **Pattern exists**: Following established `update_location` pattern
- **Backward compatible**: Doesn't break existing LLM commands
- **Isolated changes**: Only WebSocket handler + state manager
- **Reversible**: Can disable message types if issues arise

### Potential Issues

1. **State synchronization**: Multiple fast commands in quick succession
   - **Mitigation**: Existing file locking in state manager
   - **Test**: Rapid-fire command test

2. **World update race conditions**: Item collected by multiple players
   - **Mitigation**: Check item exists before removal
   - **Test**: Multi-user concurrent collection test

3. **Error handling**: Edge cases in direct Python vs LLM
   - **Mitigation**: Comprehensive error responses
   - **Test**: Invalid destination, missing items, etc.

---

## Estimated Timeline

| Task | Time | Complexity |
|------|------|------------|
| Add "go" handler | 1h | Low |
| Add "collect" handler | 1.5h | Medium |
| Testing | 1h | Low |
| Documentation | 0.5h | Low |
| **Total** | **4h** | **Low-Medium** |

**Recommended Schedule**:
- Day 1 Morning: Implement "go" (1h)
- Day 1 Afternoon: Implement "collect" (1.5h)
- Day 2 Morning: Testing (1h)
- Day 2 Afternoon: Documentation + Deploy (0.5h)

---

## Dependencies

### Required

- ✅ v0.4 WorldUpdate implementation (complete)
- ✅ UnifiedStateManager (exists)
- ✅ NATS event publishing (working)
- ✅ WebSocket infrastructure (working)

### Optional

- ⏸️ Unity client updates (can be done in parallel)
- ⏸️ LLM command deprecation (future work)

---

## Follow-Up Work

### Immediate (Week 1-2)

1. Add more fast commands (inventory, look, etc.)
2. Performance monitoring dashboard
3. Error rate tracking

### Short-Term (Month 1)

1. Deprecate slow LLM path for simple commands
2. Optimize state manager for read-heavy workloads
3. Add caching layer for world state queries

### Long-Term (Quarter 1)

1. Move all structured commands to fast path
2. Reserve LLM for complex interactions (talk, quests)
3. Command Bus architecture (unified command processing)

---

## References

**Related Documentation**:
- `docs/scratchpad/markdown-command-architecture.md` - Current LLM system
- `docs/scratchpad/structured-command-parameters-proposal.md` - Original proposal
- `docs/scratchpad/websocket-aoi-client-guide.md` - WebSocket protocol
- `app/services/kb/websocket_experience.py` - Existing handlers

**Code Examples**:
- `handle_update_location()` - Pattern to follow
- `handle_ping()` - Simplest example
- `UnifiedStateManager` - State management API

---

## Questions & Decisions

### Q: Should we keep LLM commands available?
**A**: Yes, for backward compatibility and natural language support.

### Q: What about other commands (inventory, look, etc.)?
**A**: Add later if Unity needs them. Start with go/collect (highest priority).

### Q: Do we need rate limiting?
**A**: Not initially. Monitor and add if needed.

### Q: What about directional movement (north, south)?
**A**: Out of scope. "go" is for sublocations only. Directions handled by "action".

---

## Approval

- [ ] Technical review: _________________
- [ ] Product approval: _________________
- [ ] Unity team consulted: _________________
- [ ] Ready to implement: _________________

**Date**: _______________
**Approved by**: _______________

---

## Implementation Log

### 2025-11-10 - Plan Created
- Created comprehensive implementation plan
- Documented existing architecture
- Estimated 4 hours total effort
- Ready for implementation

### 2025-11-10 - Task 1 COMPLETE ✅
**Status**: "go" command handler implemented and validated
**Files**:
- Created `app/services/kb/handlers/go.py` (102 lines)
- Modified `app/services/kb/main.py` (registered handler)
- Created `scripts/experience/test_fast_go.py` (test script)

**Performance Results**:
- Response time: 6ms (target: <100ms) ✅
- Speedup: 4,000x faster than LLM path (25-30s → 6ms)
- State persistence: Verified ✅
- Error handling: Validated ✅

**Documentation**: See `docs/scratchpad/fast-go-command-complete.md`

### 2025-11-11 - Terminology Migration COMPLETE ✅
**Issue**: Terminology inconsistency between architecture and code
- Architecture doc specifies: Zone → Location → **Area** → Point
- Code was using: location → **sublocation** (incorrect)

**Resolution**:
- ✅ Updated `go.py` handler: All references sublocation → area
- ✅ Updated `unified_state_manager.py`: Player state initialization
- ✅ Migrated `world.json`: sublocations → areas
- ✅ Migrated player view files: current_sublocation → current_area
- ✅ Updated client documentation (WebSocket protocol docs)
- ✅ Tested and validated: State persists correctly

**Time**: 45 minutes (faster than estimated 2-3 hours)
**Analysis**: See `docs/scratchpad/terminology-sublocation-vs-area-analysis.md`

### 2025-11-11 - Task 2 READY TO START 📋
**Goal**: Improve "collect" handler for production-ready item collection

**Current State** (`app/services/kb/handlers/collect_item.py`):
- ✅ Adds items to player inventory
- ❌ Does NOT remove items from world state (items remain visible to all players)
- ❌ WorldUpdate events may not be publishing correctly
- ❌ Missing validation for item accessibility (distance, visibility)

**Required Changes**:

1. **Remove Items from World State** (Primary Goal)
   ```python
   # Current: Only adds to inventory
   await state_manager.update_player_view(
       experience=experience_id,
       user_id=user_id,
       updates={"player.inventory": {"$append": item}}
   )

   # Need: Also remove from world
   world_updates = {
       f"world.locations.{location}.areas.{area}.items": {
           "$remove": {"instance_id": instance_id}
       }
   }
   await state_manager.update_world_state(experience_id, world_updates)
   ```

2. **Publish v0.4 WorldUpdate Events**
   - Ensure `publish_world_update()` called with correct parameters
   - Include both "remove" and "add" changes in single event
   - Validate event structure matches v0.4 spec

3. **Add Validation Logic**
   - Check player is in same area as item
   - Verify item is collectible (not already collected)
   - Return proper error messages with available items

4. **Testing Requirements**
   - Create test script: `scripts/experience/test_fast_collect.py`
   - Verify item removed from world.json after collection
   - Verify item appears in player inventory
   - Verify other players see item disappear (WorldUpdate event)
   - Test error cases (item not found, wrong area, etc.)

**Files to Modify**:
- `app/services/kb/handlers/collect_item.py` - Main implementation
- `app/services/kb/unified_state_manager.py` - Add world state update method if needed
- `scripts/experience/test_fast_collect.py` - Comprehensive test

**Success Criteria**:
- ✅ Item removed from world state after collection
- ✅ Item added to player inventory
- ✅ WorldUpdate event published to all connected clients
- ✅ Response time <100ms
- ✅ Proper error handling for all edge cases
- ✅ Tests passing

**Estimated Time**: 1.5-2 hours

### 2025-11-12 - Task 2 COMPLETED ✅

**Implementation Summary**:
- Complete rewrite of `collect_item.py` from 63 lines to 269 lines
- Added comprehensive validation, error handling, and documentation
- Implemented proper world state synchronization
- WorldUpdate v0.4 event publishing verified

**Code Changes**:

1. **Main Handler** (`app/services/kb/handlers/collect_item.py`)
   - Added `_find_item_in_world()` - Validates item exists at player's current location/area
   - Added `_find_item_anywhere()` - Provides helpful error messages when item is elsewhere
   - Added `_build_nested_remove()` - Converts logical path to nested dict structure
   - Implemented two-step state update:
     ```python
     # 1. Remove from world state
     await state_manager.update_world_state(
         experience=experience_id,
         updates=world_updates,
         user_id=None  # Don't publish here - let update_player_view handle it
     )

     # 2. Add to inventory (auto-publishes WorldUpdate event)
     await state_manager.update_player_view(
         experience=experience_id,
         user_id=user_id,
         updates=inventory_updates
     )
     ```

2. **Critical Discovery**: `update_world_state()` requires **nested dictionaries**, NOT dotted path strings
   ```python
   # ❌ Wrong:
   {"locations.store.areas.zone.items": {"$remove": {"instance_id": "..."}}}

   # ✅ Correct:
   {"locations": {"store": {"areas": {"zone": {"items": {"$remove": {"instance_id": "..."}}}}}}}
   ```

3. **Documentation**: All functions now have complete Args/Returns/Examples sections matching `go.py` style

**Testing Evidence**:

- **Test File**: `/tmp/test_collect_final.py` (comprehensive 6-phase validation)
- **Test Results**:
  - ✅ `spawn_zone_1`: Cleared (bottle_1 collected)
  - ✅ `spawn_zone_2`: Cleared (bottle_2 collected)
  - ✅ `spawn_zone_3`: Cleared (bottle_3 collected)
  - ✅ Player inventory: All 3 bottles added with full state preserved
  - ✅ WorldUpdate events: Received and validated (v0.4 format)
  - ✅ Response time: ~1ms (well under 100ms target)

**Success Criteria (All Met)**:
- ✅ Item removed from world state after collection - **VERIFIED** (spawn zones empty)
- ✅ Item added to player inventory - **VERIFIED** (bottles in inventory with state)
- ✅ WorldUpdate event published to all connected clients - **VERIFIED** (v0.4 events received)
- ✅ Response time <100ms - **VERIFIED** (~1ms actual)
- ✅ Proper error handling for all edge cases - **IMPLEMENTED** (helpful messages, validation)
- ✅ Tests passing - **VERIFIED** (live testing with real world state changes)
- ✅ Production-ready documentation - **COMPLETE** (269 lines with full docstrings)

**Actual Time**: ~2.5 hours (vs estimated 1.5-2 hours)
- Implementation: 1 hour
- Debugging nested dict format: 30 minutes
- Documentation: 30 minutes
- Testing and validation: 30 minutes

**Key Learnings**:
1. State manager merge operations require nested dict structure (not dot notation)
2. `update_player_view()` auto-publishes WorldUpdate events with proper version tracking
3. Setting `user_id=None` in `update_world_state()` prevents duplicate event publishing
4. WebSocket clients receive BOTH `action_response` AND `world_update` messages
5. Auto-reload timing: Wait 8-10 seconds after code changes before testing

---

## Task 3: drop_item Handler ✅ COMPLETE

**Goal**: Enable players to drop items from inventory into the world

**Priority**: HIGH - Completes collect/drop cycle, enables player-to-player item sharing

**Implementation** (`app/services/kb/handlers/drop_item.py`):
- ✅ Validate item exists in player inventory
- ✅ Remove from `player.inventory` (using `$remove` operation)
- ✅ Add to world state at current location/area (using nested dict `$append`)
- ✅ Publish WorldUpdate v0.4 event
- ✅ Return helpful error if item not in inventory

**Actual LOC**: 227 lines (handler + tests)
**Actual Response Time**: **6.7ms** (3x faster than target!)
**Testing**: `scripts/experience/test-fast-drop.sh` - ALL TESTS PASSING

**Test Results**:
- ✅ Fast path confirmed: 6.7ms response time
- ✅ State sync verified: Item removed from inventory, added to world
- ✅ Validation working: Rejects dropping items not in inventory
- ✅ Complete cycle: Drop → collect works perfectly

---

## Task 4: examine Handler 📋

**Goal**: Fast item inspection (read-only, no state changes)

**Priority**: MEDIUM - Quality of life, helps players make decisions

**Implementation** (`app/services/kb/handlers/examine.py`):
- Look up item by instance_id in world or inventory
- Load template data for full description/properties
- Return detailed item info
- No state changes, no WorldUpdate events

**Estimated LOC**: ~40 lines
**Response Time Target**: <5ms (read-only)
**Testing**: `scripts/experience/test-fast-examine.sh`

---

## Task 5: use_item Handler ✅ COMPLETE

**Goal**: Item consumption with effects (potions, keys, consumables)

**Priority**: MEDIUM - Enables core gameplay mechanics

**Implementation** (`app/services/kb/handlers/use_item.py`):
- ✅ Validate item in player inventory
- ✅ Check item is usable (has effects or use_behavior)
- ✅ Apply effects based on item data:
  - ✅ Health effects → update player.stats.health (capped at max)
  - ✅ Status effects → add to player.status_effects array
  - ✅ Unlock effects → modify world state (extensible)
- ✅ Remove if consumable (single-use items)
- ✅ Keep if permanent (keys, equipment)
- ✅ Publish WorldUpdate v0.4 events

**Actual LOC**: 227 lines (handler) + 280 lines (tests) = 507 lines
**Actual Response Time**: **4.2ms** (3.5x faster than target!)
**Testing**: `scripts/experience/test-fast-use.sh` - ALL TESTS PASSING

**Test Results**:
- ✅ Fast path confirmed: 4.2ms response time
- ✅ Effect system: Health restoration (+20 HP) working
- ✅ Consumable: Item removed from inventory after use
- ✅ State sync: Health updated, inventory modified
- ✅ Validation: Rejects items not in inventory
- ✅ Non-usable: Rejects items without effects/use_behavior

**Effect System Architecture**:
- Data-driven: Effects defined in item JSON/state
- Extensible: New effect types via configuration
- Type-safe: Validated effect application

---

## Task 6: inventory Handler 📋

**Goal**: Fast inventory listing (read-only)

**Priority**: LOW - Nice to have, simple read operation

**Implementation** (`app/services/kb/handlers/inventory.py`):
- Return `player.inventory` array from player view
- Format for display (group by template_id, show counts)
- Enrich with template data (names, descriptions)
- No state changes

**Estimated LOC**: ~20 lines
**Response Time Target**: <2ms (read-only)
**Testing**: `scripts/experience/test-fast-inventory.sh`

---

## Task 7: give_item Handler 📋

**Goal**: Transfer items between players or to NPCs

**Priority**: LOW - Social feature, requires proximity checks

**Implementation** (`app/services/kb/handlers/give_item.py`):
- Validate item in giver's inventory
- Check receiver is nearby (same location/area)
- Check receiver can accept (player online, NPC allows, inventory space)
- Remove from giver inventory
- Add to receiver inventory or NPC state
- Publish WorldUpdate to both players
- Support both player-to-player and player-to-NPC

**Estimated LOC**: ~60 lines
**Response Time Target**: <10ms
**Testing**: `scripts/experience/test-fast-give.sh`

**Future Enhancement**: Trading system with accept/reject, item exchange

---

## Implementation Order Recommendation

**Phase 1 (Next Sprint)**:
1. **Task 3: drop_item** - High value, completes core item cycle
2. **Task 5: use_item** - Enables gameplay mechanics

**Phase 2 (Future)**:
3. **Task 4: examine** - Quality of life
4. **Task 6: inventory** - Simple utility
5. **Task 7: give_item** - Social features

**Rationale**: Prioritize gameplay enablement (drop, use) over convenience (examine, inventory, give).

---

## Shared Patterns

All handlers follow the established pattern from `collect_item.py`:

1. **Validation** - Check preconditions (location, permissions, item exists)
2. **State Updates** - Use nested dict format for world updates
3. **Event Publishing** - `update_player_view()` auto-publishes WorldUpdate v0.4
4. **Error Handling** - Helpful messages, suggest corrections
5. **Documentation** - Full docstrings with Args/Returns/Examples
6. **Testing** - Comprehensive scripts validating all scenarios

**Performance Targets**:
- Read-only operations: <5ms
- State-modifying operations: <20ms
- Complex operations (use_item with effects): <50ms

All significantly faster than LLM path (25-30s).

---

## Contact

**Questions**: Symphony `websockets` room
**Implementation**: Server team
**Testing**: Unity + Server teams
**Deployment**: DevOps team
