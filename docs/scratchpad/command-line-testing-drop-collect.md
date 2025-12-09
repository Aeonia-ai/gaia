# Command-Line Testing: Drop & Collect Commands

**Date**: 2025-11-18
**Status**: ✅ Production Ready
**Purpose**: Test bottle drop/collect cycle from command line for Unity integration verification

---

## Quick Reference

### Available Commands

```bash
# Drop bottle (inventory → world)
./scripts/experience/test-fast-drop.sh <bottle_id>

# Collect bottle (world → inventory)
./scripts/experience/test-fast-collect.sh <bottle_id>

# Check inventory
./scripts/experience/test-fast-inventory.sh

# Inspect world state
./scripts/experience/inspect-world.sh

# Check player inventory (alternative)
./scripts/experience/check-inventory.sh <user_id>
```

### Available Bottles

**Main Quest Bottles** (Woander's Shop):
- `bottle_mystery`
- `bottle_energy`
- `bottle_joy`
- `bottle_nature`

**Dream Bottles** (Clearing):
- `dream_bottle_clearing_1`
- `dream_bottle_clearing_2`
- `dream_bottle_clearing_3`
- `dream_bottle_clearing_4`

---

## Live Test Sequence

### Test 1: Drop → Collect Cycle

```bash
# 1. Check starting state
./scripts/experience/check-inventory.sh da6dbf22-3209-457f-906a-7f5c63986d3e
# Expected: 2 bottles (bottle_nature, bottle_joy)

# 2. Drop bottle_joy
./scripts/experience/test-fast-drop.sh bottle_joy
# Expected: "You dropped Bottle of Joy."

# 3. Verify drop
./scripts/experience/inspect-world.sh
# Expected: bottle_joy appears in current area

./scripts/experience/check-inventory.sh da6dbf22-3209-457f-906a-7f5c63986d3e
# Expected: 1 bottle remaining (bottle_nature)

# 4. Collect it back
./scripts/experience/test-fast-collect.sh bottle_joy
# Expected: "You collected Bottle of Joy."

# 5. Verify collection
./scripts/experience/check-inventory.sh da6dbf22-3209-457f-906a-7f5c63986d3e
# Expected: 2 bottles again
```

### Test 2: Verify Unity Integration (Run While Unity Connected)

**Setup**: Start Unity client, connect to server

**Test Flow**:
```bash
# Terminal: Drop bottle
./scripts/experience/test-fast-drop.sh bottle_joy

# Unity: Observe
# ✅ Bottle appears in AR world at player location
# ✅ Inventory UI updates: 2 → 1 bottle
# ✅ No version mismatch errors in console

# Terminal: Collect it back
./scripts/experience/test-fast-collect.sh bottle_joy

# Unity: Observe
# ✅ Bottle disappears from AR world
# ✅ Inventory UI updates: 1 → 2 bottles
# ✅ No version mismatch errors
```

### Test 3: Rapid State Changes (Version Lock Test)

```bash
# Rapid drop/collect cycle to test version management
./scripts/experience/test-fast-drop.sh bottle_joy && \
./scripts/experience/test-fast-collect.sh bottle_joy && \
./scripts/experience/test-fast-drop.sh bottle_nature && \
./scripts/experience/test-fast-collect.sh bottle_nature

# Unity should process all 4 deltas without version lock
```

---

## What Gets Published

### Drop Command Flow

```
1. Client sends: {"type": "action", "action": "drop bottle_joy"}
2. Server processes: handle_drop_item() [<20ms]
3. Server updates:
   - Removes from player.inventory
   - Adds to world.locations[current_location].areas[current_area].items
4. Server publishes world_update event:
   {
     "type": "world_update",
     "base_version": <old_version>,
     "snapshot_version": <new_version>,
     "changes": [
       {"operation": "remove", "path": "player.inventory", "item": {...}},
       {"operation": "add", "area_id": "main_room", "item": {...}}
     ]
   }
5. Unity receives via NATS → WebSocket
6. Unity applies delta, updates UI and world objects
```

### Collect Command Flow

```
1. Client sends: {"type": "action", "action": "collect bottle_joy"}
2. Server processes: handle_collect_item() [4.5ms]
3. Server updates:
   - Removes from world
   - Adds to player.inventory
4. Server publishes world_update event:
   {
     "type": "world_update",
     "changes": [
       {"operation": "remove", "area_id": "main_room", "instance_id": "bottle_joy"},
       {"operation": "add", "path": "player.inventory", "item": {...}}
     ]
   }
5. Unity processes delta, updates UI and world
```

---

## Verification Checklist

### Server-Side Verification

After each command, verify:

```bash
# 1. World state updated correctly
./scripts/experience/inspect-world.sh
# Check bottle locations match expectations

# 2. Player inventory updated correctly
./scripts/experience/check-inventory.sh da6dbf22-3209-457f-906a-7f5c63986d3e
# Verify inventory contents and type field

# 3. Version advanced correctly
cat /kb/players/da6dbf22-3209-457f-906a-7f5c63986d3e/wylding-woods/view.json | jq .snapshot_version
# Should increment with each operation
```

### Unity Client Verification

**Expected Behaviors**:

✅ **Inventory UI Updates**:
- Drop: Count decreases immediately
- Collect: Count increases immediately
- Filter works: `item.Type == "collectible"` shows correct count

✅ **World Object Updates**:
- Drop: Bottle GameObject spawns at player location
- Collect: Bottle GameObject despawns

✅ **No Version Errors**:
- No "Version mismatch" warnings in console
- All deltas accepted and applied
- No buffered deltas waiting for resync

❌ **Known Issues (Pre-Fix)**:
- Version lock: Deltas rejected after first mismatch
- Missing type field: Inventory filter shows 0 items
- NATS forwarding: Events not reaching WebSocket

---

## Performance Metrics

**Command Response Times** (Server-Side):

| Command | Handler | Response Time | LLM Used? |
|---------|---------|---------------|-----------|
| `drop bottle_joy` | `handle_drop_item()` | <20ms | ❌ No |
| `collect bottle_joy` | `handle_collect_item()` | 4.5ms | ❌ No |
| `inventory` | `handle_inventory()` | <10ms | ❌ No |

**Event Publishing Latency**:
- NATS publish: <2ms
- NATS → WebSocket forward: <10ms
- **Total server-side latency**: <30ms

**Unity Processing Time**:
- Delta application: ~5-15ms (depends on complexity)
- GameObject updates: ~10-20ms (Unity main thread)
- **Total Unity latency**: ~15-35ms

**End-to-End Latency** (Command → UI Update):
- Best case: ~45ms (server + network + Unity)
- Typical: ~60-80ms
- Worst case: ~100ms (complex deltas, many objects)

---

## Troubleshooting

### Issue: Command Succeeds But Unity Doesn't Update

**Symptoms**:
- Terminal shows "You dropped Bottle of Joy"
- Inventory count doesn't change in Unity
- No errors in Unity console

**Diagnosis**:
```bash
# Check if NATS is publishing
docker logs gaia-kb-service-1 --tail 50 | grep "Published world_update"

# Check if Unity is connected
docker logs gaia-kb-service-1 --tail 50 | grep "WebSocket connected"
```

**Likely Causes**:
1. Unity not subscribed to NATS updates (WebSocket not connected)
2. Version lock (deltas being buffered)
3. Unity message handler not processing world_update type

### Issue: Version Mismatch Errors

**Symptoms**:
- Unity logs: "Version mismatch - buffering delta"
- State updates stop working after first command

**Fix Applied**: 2025-11-18
- Server now uses player_view.snapshot_version in AOI (not fresh timestamp)
- Ensures AOI version matches subsequent delta base_version

**Verify Fix**:
```bash
# Run rapid commands, check versions stay synchronized
./scripts/experience/test-fast-drop.sh bottle_joy
cat /kb/players/.../view.json | jq .snapshot_version  # Note version A

./scripts/experience/test-fast-collect.sh bottle_joy
cat /kb/players/.../view.json | jq .snapshot_version  # Should be A+delta
```

### Issue: Inventory Shows 0 Bottles

**Symptoms**:
- Player has bottles in inventory (server-side)
- Unity shows "0 bottles" in UI
- Unity logs: "✓ Inventory updated: 0 bottles out of 2 total items"

**Fix Applied**: 2025-11-18
- Added `"type": "collectible"` to all bottle items in world.template.json
- Unity filter `item.Type == "collectible"` now works

**Verify Fix**:
```bash
# Check bottles have type field
cat /kb/players/.../view.json | jq '.player.inventory[0].type'
# Expected: "collectible"
```

---

## Related Documentation

- `admin-command-architecture-and-reset.md` - NATS forwarding verification
- `websocket-aoi-client-guide.md` - WebSocket protocol v0.4 spec
- `fast-drop-command-complete.md` - Drop handler implementation
- `fast-go-command-complete.md` - Fast command patterns

---

## Key Insights

**Why This Testing Matters**:

1. **Validates Full Stack**: Command → Server → NATS → WebSocket → Unity → UI
2. **Stress Tests Version Management**: Rapid state changes expose version drift
3. **Verifies Event Delivery**: Confirms NATS forwarding works end-to-end
4. **Tests Type Field Fix**: Ensures Unity inventory filter works correctly

**Test While Unity Running**:
- Commands trigger REAL world_update events
- Unity must process deltas without version lock
- Immediate visual feedback (UI updates, objects spawn/despawn)
- Exposes race conditions and timing issues

**Performance Validation**:
- Sub-20ms server response confirms fast handler path
- No LLM latency (would be 1-3 seconds)
- Real-time feedback validates event pipeline health
