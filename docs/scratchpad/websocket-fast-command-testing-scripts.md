# WebSocket Fast Command Testing Scripts

**Created**: 2025-11-17
**Status**: Complete reference for all experience testing scripts
**Location**: `scripts/experience/`

## Overview

Collection of bash scripts for testing WebSocket fast commands (v0.4 protocol) with <100ms response times. These scripts bypass LLM processing and directly test the structured command handlers.

**Key Distinction**:
- **Fast Commands** (these scripts): WebSocket, structured JSON, <100ms, no LLM
- **Chat Commands** (`chat-game-testing-guide.md`): HTTP, natural language, 2-5s, LLM-powered

## User ID Reference

All scripts support user_id as an argument, with sensible defaults:

| Email | User ID | Default For |
|-------|---------|-------------|
| `admin@aeonia.ai` | `da6dbf22-3209-457f-906a-7f5c63986d3e` | Utility scripts, reset |
| `pytest@aeonia.ai` | `b18c47d8-3bb5-46be-98d4-c3950aa565a5` | Test scripts |

**Usage Pattern**:
```bash
# Use default user (usually pytest@aeonia.ai for tests)
./scripts/experience/test-fast-collect.sh

# Specify admin user
./scripts/experience/check-inventory.sh da6dbf22-3209-457f-906a-7f5c63986d3e

# Or use variable
ADMIN_USER="da6dbf22-3209-457f-906a-7f5c63986d3e"
./scripts/experience/reset-experience.sh $ADMIN_USER
```

## Fast Command Scripts

### Player Action Commands

#### `test-fast-collect.sh` - Collect Item
**Purpose**: Test bottle/item collection from world spots

**What it tests**:
- Fast path (<100ms response time)
- Item removal from world state (v0.5 spot hierarchy)
- Item addition to player inventory
- Duplicate collection prevention
- WorldUpdate v0.4 delta publishing

**Usage**:
```bash
./scripts/experience/test-fast-collect.sh
```

**Expected Output**:
```
========================================
Fast 'collect_item' Command Test (v0.5)
========================================
NEW HIERARCHY: zone > area > spot > items

✅ JWT token obtained
User ID: b18c47d8-3bb5-46be-98d4-c3950aa565a5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test 1: Fast 'collect_item' (structured)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Command: {"action": "collect_item", "instance_id": "bottle_mystery"}
Expected: <100ms (fast path, no LLM)

Response time: 51.3ms
Success: True
Message: You collected Bottle of Mystery.

✅ FAST PATH CONFIRMED (<100ms)
```

**Validates**:
- ✅ Response time <100ms
- ✅ Item removed from `main_room.spot_1`
- ✅ Item added to player inventory
- ✅ Duplicate rejection works

---

#### `test-fast-drop.sh` - Drop Item
**Purpose**: Drop item from inventory back to world

**Usage**:
```bash
./scripts/experience/test-fast-drop.sh
```

**Tests**:
- Item removal from inventory
- Item addition to current location
- Validation of item ownership

---

#### `test-fast-examine.sh` - Examine Item/Location
**Purpose**: Get detailed description of item or location

**Usage**:
```bash
./scripts/experience/test-fast-examine.sh
```

**Tests**:
- Item description retrieval
- Location description
- Response formatting

---

#### `test-fast-give.sh` - Give Item to NPC
**Purpose**: Transfer item from player to NPC

**Usage**:
```bash
./scripts/experience/test-fast-give.sh
```

**Response Time**: ~5ms
**Tests**:
- Item transfer mechanics
- NPC interaction
- Quest progression (if applicable)

---

#### `test-fast-go.sh` - Navigate to Location
**Purpose**: Move player between areas/locations

**Usage**:
```bash
./scripts/experience/test-fast-go.sh
```

**Tests**:
- Location transitions
- Area updates in player state
- Navigation validation

---

#### `test-fast-inventory.sh` - Check Inventory
**Purpose**: View current player inventory

**Usage**:
```bash
./scripts/experience/test-fast-inventory.sh
```

**Tests**:
- Inventory listing
- Item count
- Response formatting

---

#### `test-fast-use.sh` - Use Item
**Purpose**: Activate/use an item from inventory

**Usage**:
```bash
./scripts/experience/test-fast-use.sh
```

**Tests**:
- Item activation
- State changes from item use
- Consumable item handling

---

### Admin Command Scripts

#### Spot Position Updates (World → Client)
Use the unified state manager to tweak spot transforms and immediately push them to connected clients. Any nested dict passed to `update_world_state` is merged server-side, increments the `_version`, and emits the standard `world_update` delta over NATS.

**Ad-hoc update example (Python REPL / `python3 - <<'PY'`):**
```python
await state_manager.update_world_state(
    experience="wylding-woods",
    user_id="da6dbf22-3209-457f-906a-7f5c63986d3e",  # whoever should receive the delta
    updates={
        "locations": {
            "woander_store": {
                "areas": {
                    "main_room": {
                        "spots": {
                            "spot_6": {
                                "position": {"x": 12.3, "y": 4.5, "z": 0.0},
                                "rotation": {"y": 180}
                            }
                        }
                    }
                }
            }
        }
    }
)
```

**Notes**
- Always send nested dicts (no dotted paths); the merge logic and `_flatten_nested_changes` will broadcast the change automatically.
- `user_id` determines which client receives the realtime delta; include a `connection_id` if you want the version tracker to align with a specific WebSocket.
- These mutations live in `world.json`, so Unity/mobile clients get consistent positions after reconnect or world reload.

#### `test-admin-examine.sh` - Admin Examine
**Purpose**: Deep inspection of items/locations (admin-only)

**Usage**:
```bash
./scripts/experience/test-admin-examine.sh
```

**Command**: `@examine <target>`
**Response Time**: <30ms (no LLM)
**Returns**: Full item/location metadata including internal IDs

---

#### `test-admin-where.sh` - Admin Location Query
**Purpose**: Check player or item location

**Usage**:
```bash
./scripts/experience/test-admin-where.sh
```

**Command**: `@where <target>`
**Tests**: Location tracking, player position

---

#### `test-admin-edit.sh` - Admin Edit
**Purpose**: Modify item/location properties (requires CONFIRM)

**Usage**:
```bash
./scripts/experience/test-admin-edit.sh
```

**Command**: `@edit <target> <property> <value> CONFIRM`
**Safety**: Requires explicit CONFIRM keyword

---

### Quest & Game Flow Scripts

#### `test-louisa-quest.sh` - Louisa Quest Flow
**Purpose**: Test complete quest flow with Louisa NPC

**Usage**:
```bash
./scripts/experience/test-louisa-quest.sh
```

**Tests**:
- NPC dialogue
- Quest acceptance
- Item collection for quest
- Quest completion
- Reward distribution

---

#### `test-commands.sh` - General Command Testing
**Purpose**: Comprehensive command testing framework

**Usage**:
```bash
# Run all test suites
./scripts/experience/test-commands.sh

# Run specific suite
./scripts/experience/test-commands.sh basic      # Basic commands
./scripts/experience/test-commands.sh movement   # Navigation
./scripts/experience/test-commands.sh items      # Item interaction
./scripts/experience/test-commands.sh npcs       # NPC dialogue
```

---

## Utility Scripts

### `reset-experience.sh` - Reset World State
**Purpose**: Reset experience to pristine state (all bottles back, inventories cleared)

**Usage**:
```bash
# Reset with default admin user
./scripts/experience/reset-experience.sh

# Reset for specific user
./scripts/experience/reset-experience.sh da6dbf22-3209-457f-906a-7f5c63986d3e
```

**Command Used**: `@reset experience CONFIRM`
**Safety**: Uses admin-only command with confirmation

**Output**:
```
🔄 Resetting wylding-woods experience...
   User: da6dbf22-3209-457f-906a-7f5c63986d3e

✅ Experience reset complete
   ✅ Reset Complete: wylding-woods

📦 Backup: world.20251118_044522.json

♻️  Summary:
- World state restored from template
- Quest progress reset (0/4 bottles)
- 1 player views cleared

Experience is now in pristine state! ✨
```

---

### `check-inventory.sh` - View Player Inventory
**Purpose**: Quick inventory check for any player

**Usage**:
```bash
# Check default admin user inventory
./scripts/experience/check-inventory.sh

# Check specific user inventory
./scripts/experience/check-inventory.sh b18c47d8-3bb5-46be-98d4-c3950aa565a5
```

**Output**:
```
🎒 Checking inventory for user: b18c47d8-3bb5-46be-98d4-c3950aa565a5

📦 Current inventory:
  - Bottle of Mystery
  - Bottle of Nature

📊 Inventory count: 2
```

**Implementation**: Reads directly from player state file in Docker container

---

### `inspect-world.sh` - Inspect World State
**Purpose**: View current world state (items, NPCs, locations)

**Usage**:
```bash
./scripts/experience/inspect-world.sh
```

**Shows**:
- All items in world (by location/area/spot)
- NPC states
- Quest progress
- Active events

---

### `randomize-bottles.sh` - Randomize Bottle Placement
**Purpose**: Randomize bottle placement across all 8 spots in woander_store

**Usage**:
```bash
./scripts/experience/randomize-bottles.sh
```

**What it does**:
- Collects all 4 bottles from current locations
- Randomly assigns them to any of spots 1-8
- Increments world version
- Updates world.json directly

**Output**:
```
🎲 Randomizing bottle placement in woander_store...
📦 Found 4 bottles
🎯 New random placement:
   spot_8: Bottle of Mystery
   spot_2: Bottle of Energy
   spot_1: Bottle of Joy
   spot_6: Bottle of Nature

🔧 Updating world.json...
✅ World state updated
   New version: 7

✨ Bottle randomization complete!
```

**Use case**: Testing Unity's AOI refresh with different bottle placements

---

### `move-bottles-5-8.sh` - Move Bottles to Higher Spots
**Purpose**: Move all bottles from spots 1-4 to spots 5-8

**Usage**:
```bash
./scripts/experience/move-bottles-5-8.sh
```

**What it does**:
- Moves bottle from spot_1 → spot_5
- Moves bottle from spot_2 → spot_6
- Moves bottle from spot_3 → spot_7
- Moves bottle from spot_4 → spot_8
- Increments world version

**Output**:
```
🔄 Moving bottles from spots 1-4 to spots 5-8...
📦 Found 4 bottles in spots 1-4
✅ Bottles moved successfully
   spot_1 → spot_5: Bottle of Mystery
   spot_2 → spot_6: Bottle of Energy
   spot_3 → spot_7: Bottle of Joy
   spot_4 → spot_8: Bottle of Nature

   New version: 7
```

**Use case**: Testing Unity's AOI update when bottles move without client disconnect

---

### `monitor-all-events.sh` - Real-Time Event Monitor
**Purpose**: Monitor all KB service events in real-time

**Usage**:
```bash
# Start monitoring (already running in your session!)
./scripts/experience/monitor-all-events.sh
```

**Shows**:
- WebSocket connections
- NATS subscription events
- World state updates
- Player state changes
- Merge operations with debug logging

**Debug Logging**:
```
[MERGE-L6] Processing $remove for key='items', key_exists=True, current_type=list
[PUBLISH-DEBUG] ✅ Published world_update v0.4: changes_count=1
[WS-FORWARD-DEBUG] ✅ Forwarded NATS event to WebSocket
```

---

## Protocol Testing

### `test-ws-protocol.sh` - WebSocket Protocol Tests
**Purpose**: Validate WebSocket v0.4 protocol compliance

**Usage**:
```bash
./scripts/experience/test-ws-protocol.sh
```

**Tests**:
- Connection handshake
- Initial state delivery
- WorldUpdate delta format
- Message ordering

---

## Common Workflows

### Debugging Unity Integration

**1. Reset world state**:
```bash
./scripts/experience/reset-experience.sh
```

**2. Monitor events in real-time**:
```bash
./scripts/experience/monitor-all-events.sh &
```

**3. Test specific command**:
```bash
./scripts/experience/test-fast-collect.sh
```

**4. Check inventory to verify**:
```bash
./scripts/experience/check-inventory.sh b18c47d8-3bb5-46be-98d4-c3950aa565a5
```

**5. Inspect world state**:
```bash
./scripts/experience/inspect-world.sh
```

---

### Testing Bottle Collection for Unity

**Complete test sequence**:
```bash
# 1. Reset to pristine state
./scripts/experience/reset-experience.sh

# 2. Start monitoring (in background)
./scripts/experience/monitor-all-events.sh > /tmp/events.log 2>&1 &

# 3. Test collection
./scripts/experience/test-fast-collect.sh

# 4. Verify inventory
./scripts/experience/check-inventory.sh b18c47d8-3bb5-46be-98d4-c3950aa565a5

# 5. Check world state
./scripts/experience/inspect-world.sh

# 6. Review events
tail -100 /tmp/events.log | grep -E "(MERGE|world_update|NATS)"
```

---

### Admin Testing with admin@aeonia.ai

**Using admin user for all operations**:
```bash
ADMIN_USER="da6dbf22-3209-457f-906a-7f5c63986d3e"

# Reset as admin
./scripts/experience/reset-experience.sh $ADMIN_USER

# Check admin inventory
./scripts/experience/check-inventory.sh $ADMIN_USER

# Test admin commands
./scripts/experience/test-admin-examine.sh
./scripts/experience/test-admin-where.sh
```

---

## Performance Benchmarks

### Fast Command Response Times

| Command | Target | Typical | Notes |
|---------|--------|---------|-------|
| `collect_item` | <100ms | 51ms | Includes state update + NATS publish |
| `drop_item` | <100ms | 45ms | Reverse of collect |
| `give_item` | <10ms | 5ms | Fastest command |
| `go` | <100ms | 60ms | Includes location transition |
| `inventory` | <50ms | 30ms | Read-only operation |
| `examine` | <50ms | 35ms | Read-only operation |
| `@examine` (admin) | <30ms | 15ms | No authorization checks |
| `@reset` (admin) | <500ms | 300ms | Includes file I/O |

**Comparison to LLM Path**:
- Fast commands: **50-100ms**
- Natural language (LLM): **2,000-5,000ms** (40-100x slower)

---

## Technical Details

### WebSocket v0.4 Protocol

**Connection**:
```
ws://localhost:8001/ws/experience?token={JWT}&experience=wylding-woods
```

**Message Format**:
```json
{
  "type": "action",
  "action": "collect_item",
  "instance_id": "bottle_mystery"
}
```

**Response Format**:
```json
{
  "type": "action_response",
  "success": true,
  "message": "You collected Bottle of Mystery.",
  "timestamp": "2025-11-18T04:42:15.123Z"
}
```

**WorldUpdate Delta (v0.4)**:
```json
{
  "type": "world_update",
  "version": "0.4",
  "experience": "wylding-woods",
  "base_version": 123,
  "snapshot_version": 124,
  "changes": [
    {
      "operation": "remove",
      "area_id": "main_room",
      "spot_id": "spot_1",
      "instance_id": "bottle_mystery"
    }
  ]
}
```

---

### v0.5 World Hierarchy

**Structure**: `zone > area > spot > items`

**Example**:
```
woander_store (zone/location)
  └─ main_room (area)
      └─ spot_1 (spot/position)
          └─ items: [bottle_mystery, bottle_nature, ...]
```

**Unity Integration Note**: Unity must track items by `spot_id`, not just `area_id`, to match this hierarchy.

---

## Troubleshooting

### Script Fails with "Connection Refused"

**Check services**:
```bash
docker compose ps
curl http://localhost:8001/health
```

**Restart KB service**:
```bash
docker compose restart kb-service
```

---

### Script Fails with "401 Unauthorized"

**Regenerate JWT**:
```bash
python3 tests/manual/get_test_jwt.py
```

**Check test user exists**:
```bash
./scripts/manage-users.sh list | grep pytest@aeonia.ai
```

---

### "Item not found" Errors

**Reset experience**:
```bash
./scripts/experience/reset-experience.sh
```

**Check world state**:
```bash
./scripts/experience/inspect-world.sh
```

---

### Slow Response Times (>500ms)

**Check for hot-reload restarts**:
```bash
docker logs gaia-kb-service-1 | grep "Reloading"
```

**Monitor resource usage**:
```bash
docker stats gaia-kb-service-1
```

---

## Related Documentation

- [WebSocket AOI Client Guide](websocket-aoi-client-guide.md) - Unity integration
- [WebSocket Architecture Decision](websocket-architecture-decision.md) - Protocol design
- [Admin Commands Quick Start](../concepts/deep-dives/dynamic-experiences/phase-1-mvp/000-admin-commands-quick-start.md)
- [Chat Game Testing Guide](../guides/chat-game-testing-guide.md) - LLM-based testing

---

## Zombie Subscription Fix (2025-11-17)

**Issue**: Unity persistent connections creating zombie NATS subscriptions on reconnect

**Root Cause**: `NATSClient` tracks subscriptions by subject (not connection ID), causing old subscriptions to become untrackable when new connections subscribe to same subject.

**Fix**: `experience_connection_manager.py` now cleans up old subscriptions before creating new ones:

```python
# Lines 200-229: Zombie subscription cleanup
for old_conn_id, old_subject in list(self.nats_subscriptions.items()):
    if old_subject == nats_subject and old_conn_id != connection_id:
        await self.nats_client.unsubscribe(old_subject)
        del self.nats_subscriptions[old_conn_id]
```

**Result**: Unity now receives world_update deltas correctly on every reconnection.

---

## Future Enhancements

- [ ] Add user_id parameter support to all `test-fast-*.sh` scripts
- [ ] Create parallel test runner for all fast commands
- [ ] Add performance regression tracking
- [ ] Create visual diff for state changes
- [ ] Add automated Unity integration tests
- [ ] Create test data generator for bulk testing
