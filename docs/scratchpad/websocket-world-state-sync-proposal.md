# WebSocket World State Synchronization - Proposal

**Date:** 2025-11-08
**Status:** 📋 Proposal - Awaiting Implementation
**Context:** Friday Demo - Unity client needs bottle location data

---

## Problem Statement

Unity client successfully connects to WebSocket endpoint (`/ws/experience`) but **does not receive world state data** on connection. The welcome message contains only connection metadata - no information about where bottles are located in the game world.

**Unity's Current Experience:**
```
✅ WebSocket connection successful
✅ Authentication working
✅ Ping/pong health checks passing
✅ Action protocol working (collect_bottle)
❌ Server doesn't tell client WHERE bottles are located
❌ Client cannot spawn any game objects
```

**Root Cause:** Welcome message (lines 97-105 in `websocket_experience.py`) sends NO world state:
```python
await websocket.send_json({
    "type": "connected",
    "connection_id": connection_id,
    # ❌ Missing: world_state
    # ❌ Missing: player_state
    # ❌ Missing: nearby items/bottles
})
```

---

## Industry Best Practices Research

**Source:** Perplexity AI research on multiplayer AR/VR games (2025-11-08)

### Key Findings:

| Practice | Description | Used By |
|----------|-------------|---------|
| **Progressive Loading** | Send only immediate, relevant subset of world state on connection | Pokémon GO, Minecraft, VRChat |
| **Area of Interest** | Load new areas/objects as player moves into proximity | All modern multiplayer games |
| **Delta Updates** | Send only changes (deltas) after initial state, not full snapshots | Industry standard |
| **Authoritative Server** | Server is source of truth; client predicts for responsiveness | Best practice |
| **Compression & Prioritization** | Critical state updates frequently, less critical updates less often | Performance optimization |

### What NOT to Do:
❌ **Send entire world state on connection** (causes bandwidth spikes, slow loading)
❌ **Load all locations at once** (doesn't scale to large worlds)
❌ **Resend full state on every change** (use deltas instead)

---

## Proposed Solution: Area of Interest Pattern

**Implementation Target:** `app/services/kb/websocket_experience.py` (lines 97-105)

### Phase 1: Initial Connection (Friday Demo)

**Send ONLY player's starting location + nearby items:**

```javascript
// ⚠️ CONCEPTUAL SAMPLE - Not actual implementation code
{
    "type": "connected",
    "connection_id": "0c8b76a9-...",
    "user_id": "da6dbf22-...",
    "experience": "wylding-woods",
    "timestamp": 1699564123000,

    // Player's current state
    "player": {
        "current_location": "woander_store",
        "current_sublocation": null,
        "inventory": []
    },

    // ONLY current location (Area of Interest)
    "area_of_interest": {
        "location_id": "woander_store",
        "name": "Woander's Magical Shop",
        "description": "The entrance to Woander's mystical shop...",
        "sublocations": {
            "spawn_zone_1": {
                "id": "spawn_zone_1",
                "name": "Display Shelf Area",
                "items": [
                    {
                        "id": "dream_bottle_1",
                        "type": "dream_bottle",
                        "semantic_name": "peaceful dream bottle",
                        "collectible": true,
                        "visible": true,
                        "state": {
                            "glowing": true,
                            "dream_type": "peaceful",
                            "symbol": "spiral"
                        }
                    }
                ]
            },
            "spawn_zone_2": { /* ... bottle 2 ... */ },
            "spawn_zone_3": { /* ... bottle 3 ... */ }
            // ... other woander_store sublocations
        },
        "npcs": {
            "woander": { /* NPC data */ },
            "louisa": { /* NPC data */ }
        }
    },

    "message": "Connected to wylding-woods experience"
}
```

**What Unity Receives:**
- ✅ 3 bottles at woander_store (starting location)
- ✅ Full item metadata (id, type, state, symbol for visual effects)
- ✅ NPC data for Woander and Louisa
- ✅ Player's current location and inventory
- ❌ NO data for waypoint_28a (not nearby - 4 more bottles)
- ❌ NO data for waypoint_42 (not nearby)

**Benefits:**
- Small payload (~50 lines vs 306 lines for full world.json)
- Fast connection time
- Follows Pokémon GO/Minecraft pattern
- Scales to large worlds

### Phase 2: Progressive Loading (Post-Demo)

**When player moves to new location:**

```javascript
// ⚠️ CONCEPTUAL SAMPLE - Future feature
{
    "type": "location_entered",
    "location_id": "waypoint_28a",
    "area_of_interest": {
        "location_id": "waypoint_28a",
        "name": "Dream Weaver's Clearing",
        "sublocations": {
            "shelf_1": { /* bottle 4 */ },
            "shelf_2": { /* bottle 5 */ },
            "shelf_3": { /* bottle 6 */ },
            "magic_mirror": { /* bottle 7 */ }
        }
    }
}
```

**Trigger:** Player moves to new location (detected via GPS/VPS or explicit `move` action)

---

## Implementation Pseudocode

**⚠️ CONCEPTUAL SAMPLES - Not production-ready code. Actual implementation will differ.**

### Welcome Message Enhancement

```python
# Location: app/services/kb/websocket_experience.py (lines 97-105)
# ⚠️ CONCEPTUAL SAMPLE ONLY

# Get state manager
state_manager = kb_agent.state_manager

# Get player view to find current location
player_view = await state_manager.get_player_view(experience, user_id)
current_location = player_view.get("player", {}).get("current_location", "woander_store")

# Get ONLY current location from world state
world_state = await state_manager.get_world_state(experience, user_id)
current_area = world_state.get("locations", {}).get(current_location, {})

# Filter NPCs to only those in current location
all_npcs = world_state.get("npcs", {})
nearby_npcs = {
    npc_id: npc_data
    for npc_id, npc_data in all_npcs.items()
    if npc_data.get("location", "").startswith(current_location)
}

# Send welcome with ONLY current area (Area of Interest)
await websocket.send_json({
    "type": "connected",
    "connection_id": connection_id,
    "user_id": user_id,
    "experience": experience,
    "timestamp": int(datetime.utcnow().timestamp() * 1000),

    # Player state
    "player": player_view.get("player", {}),

    # ONLY current location (Area of Interest)
    "area_of_interest": {
        "location_id": current_location,
        "name": current_area.get("name"),
        "description": current_area.get("description"),
        "sublocations": current_area.get("sublocations", {}),
        "npcs": nearby_npcs
    },

    "message": f"Connected to {experience} experience"
})
```

### Error Handling

```python
# ⚠️ CONCEPTUAL SAMPLE ONLY

try:
    # Attempt to get state
    state_manager = kb_agent.state_manager
    player_view = await state_manager.get_player_view(experience, user_id)
    world_state = await state_manager.get_world_state(experience, user_id)
    # ... build area_of_interest ...
except Exception as e:
    logger.warning(f"Failed to load world state for welcome message: {e}")
    # Graceful degradation: send welcome WITHOUT state
    # Client can request state via separate action if needed
    await websocket.send_json({
        "type": "connected",
        "connection_id": connection_id,
        "message": "Connected (world state unavailable)"
    })
```

---

## Data Structures

### Current World State (wylding-woods)

**Source:** `/Vaults/gaia-knowledge-base/experiences/wylding-woods/state/world.json`

**7 Bottles Total:**

**woander_store (3 bottles):**
- `woander_store.spawn_zone_1` → `dream_bottle_1` (peaceful/spiral/azure)
- `woander_store.spawn_zone_2` → `dream_bottle_2` (adventurous/star/amber)
- `woander_store.spawn_zone_3` → `dream_bottle_3` (joyful/moon/golden)

**waypoint_28a (4 bottles):**
- `waypoint_28a.shelf_1` → `dream_bottle_1` (peaceful)
- `waypoint_28a.shelf_2` → `dream_bottle_2` (adventurous)
- `waypoint_28a.shelf_3` → `dream_bottle_3` (joyful)
- `waypoint_28a.magic_mirror` → `dream_bottle_4` (whimsical)

### Unity's Expected Format

**From Symphony message (2025-11-08 12:24 AM):**

Unity tested: `woander_store.entrance` (no bottle there - correct!)

Unity needs:
- `spot_id` format: `{location}.{sublocation}`
- `item_id` for each bottle
- Item metadata: `type`, `semantic_name`, `state` (for visual effects)

**Unity's Prefabs:**
- `Bottle_Joy.prefab` → matches `dream_type: "joyful"`
- `Bottle_Nature.prefab` → (not in current world.json)
- `Bottle_Mystery.prefab` → (not in current world.json)
- `Bottle_Energy.prefab` → (not in current world.json)

---

## Testing Plan

### Test 1: Welcome Message Contains Area of Interest

```bash
# Run existing test script
python3 tests/manual/test_websocket_experience.py --via-gateway

# Expected output includes:
✅ "area_of_interest": { "location_id": "woander_store", ... }
✅ "sublocations": { "spawn_zone_1": { "items": [...] } }
✅ 3 bottles visible in area_of_interest
```

### Test 2: Unity Can Parse and Spawn Bottles

**Unity Developer Actions:**
1. Connect to `ws://Byrne.local:8666/ws/experience`
2. Receive welcome message
3. Parse `area_of_interest.sublocations`
4. For each item where `collectible: true`, spawn prefab at spot_id
5. Verify 3 bottles appear in AR view

### Test 3: Graceful Degradation

```python
# Simulate state manager failure
# Verify welcome message still sent (without area_of_interest)
# Verify connection doesn't crash
```

---

## Success Criteria

**Friday Demo:**
- ✅ Unity receives area_of_interest in welcome message
- ✅ 3 bottles spawn at woander_store
- ✅ Unity can collect bottles using existing action protocol
- ✅ No errors in Gateway or KB Service logs
- ✅ Connection time < 500ms

**Post-Demo (Future):**
- Progressive loading when player moves to waypoint_28a
- Delta updates when world state changes (e.g., bottle collected)
- Multiple players see synchronized world state via NATS

---

## Architecture Notes

### Why Area of Interest > Full World State

| Approach | Payload Size | Scalability | Industry Pattern |
|----------|--------------|-------------|------------------|
| **Full World State** | 306 lines (all locations) | ❌ Doesn't scale | ❌ Anti-pattern |
| **Area of Interest** | ~50 lines (current location) | ✅ Scales linearly | ✅ Pokémon GO/Minecraft |

### Existing Infrastructure (Already Built!)

- ✅ `UnifiedStateManager.get_world_state()` - Retrieves world.json
- ✅ `UnifiedStateManager.get_player_view()` - Retrieves player state
- ✅ NATS pub/sub for world updates - `world.updates.user.{user_id}`
- ✅ ExperienceConnectionManager - WebSocket lifecycle management

**What's Missing:** Just need to call these methods in welcome message!

---

## Related Documentation

- [WebSocket Architecture Decision](websocket-architecture-decision.md) - Original fast-path decision
- [Command Format Comparison](command-formats-comparison.md) - WebSocket message formats
- [World vs Locations JSON Architecture](world-vs-locations-json-architecture.md) - State model design
- [Gateway WebSocket Proxy](gateway-websocket-proxy.md) - Connection routing

---

## Timeline

**Friday Demo (2025-11-08):**
- ✅ Research complete (industry best practices confirmed)
- ⏳ Implementation: 20 minutes (welcome message enhancement)
- ⏳ Testing: 10 minutes (verify with test script + Unity)
- ⏳ Documentation: 10 minutes (update this doc with results)

**Total Time:** ~40 minutes

---

## Open Questions

1. **Should we include global_state in area_of_interest?**
   - Current proposal: No (send separately if needed)
   - Reason: Global state isn't location-specific

2. **Should we send player inventory in welcome message?**
   - Current proposal: Yes (in `player` object)
   - Reason: Unity needs to know starting inventory

3. **How should Unity request other locations (waypoint_28a)?**
   - Option A: Automatic when GPS detects proximity
   - Option B: Explicit `get_area` action
   - Recommendation: Option A for AR, Option B for testing

---

**Next Steps:** Awaiting approval to proceed with implementation.

**Last Updated:** 2025-11-08 (Proposal created)
