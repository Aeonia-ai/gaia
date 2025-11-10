# WebSocket World State & Discovery Flow

**Date**: 2025-11-05
**Status**: Design Phase - Implementation Needed
**Context**: Current WebSocket implementation handles bottle collection but lacks world state discovery

---

## Current State

### What Works ✅
- WebSocket connection with JWT auth
- Player sends `collect_bottle` action
- KB adds bottle to player inventory
- KB publishes NATS world_update event
- Auto-bootstrap creates empty player view on first join

### What's Missing ❌
- **Initial world state sync** - Client doesn't know what bottles exist or where they are
- **Location-based discovery** - No mechanism for "seeing" items in current location
- **Complete state deltas** - Only adds to inventory, doesn't remove from world locations
- **World state management** - Unclear how shared world state updates work

---

## Desired User Experience

### Step 1: Player Enters Experience
**User Action:** Connect to WebSocket
**Expected Behavior:**
- Client receives current world state (locations, discoverable items)
- Client receives player state (current location, inventory, progress)
- Client can render the game world

**Open Questions:**
- Full world state or just current location?
- How much detail in initial sync?
- Performance impact for large worlds?

---

### Step 2: Player Discovers Items
**User Action:** Player explores location (AR view, movement, looking around)
**Expected Behavior:**
- Client knows which items are "discoverable" at current location
- Items have positions/hints for AR placement
- Client can render items in AR space

**Open Questions:**
- Is discovery proximity-based? Line-of-sight? Automatic?
- Do items need to be "discovered" before collectible?
- Is there a separate discovery action or just rendering?

---

### Step 3: Player Collects Item
**User Action:** Player taps/interacts with bottle in AR
**Expected Behavior:**
- Client sends collect action with item ID + location
- Server validates: item exists, player at location, item not collected
- Server updates state: removes from world location, adds to inventory
- Server broadcasts complete state delta to all relevant subscribers
- Client updates: removes item from AR scene, shows in inventory UI

**Open Questions:**
- Validation: server-side or client-side trust?
- Shared world: does removal affect other players immediately?
- What if two players collect same item simultaneously?

---

### Step 4: State Synchronization
**User Action:** N/A (automatic)
**Expected Behavior:**
- Other clients watching this location see item disappear
- Player's other sessions (if any) see inventory update
- Chat interface (if open) reflects state change

**Open Questions:**
- Do we broadcast to all players in experience or just the collecting player?
- How do we handle "observers" vs "active players"?
- Location-based pub/sub or global experience updates?

---

## Data Model Questions

### World State
**Current Understanding:**
- Shared model: `/experiences/{exp}/world.json` (shared by all players)
- Isolated model: player view IS the world (single-player)

**Unclear:**
- How are items represented in world.json?
- Are item locations mutable or static?
- Do we need item spawn/respawn logic?
- How do we handle item state (collected, available, hidden)?

**Example Schema (Needs Discussion):**
```json
{
  "locations": {
    "woander_store": {
      "name": "Woander's General Store",
      "items": [
        {
          "id": "bottle_of_joy_1",
          "type": "collectible",
          "status": "available",  // or "collected", "hidden"
          "position": {"x": 1.5, "y": 0.8, "z": 2.3},  // AR coordinates?
          "discoverable_from": ["entrance", "shelf_view"],  // Visibility zones?
          "metadata": {...}
        }
      ]
    }
  }
}
```

---

### Player State
**Current Understanding:**
- Player view tracks: location, inventory, progress
- Auto-bootstrapped on first join

**Unclear:**
- Does player view track "discovered" items separately from "collected"?
- Do we cache world state in player view for performance?
- How do we handle player location changes?

---

## Protocol Design Questions

### Initial State Sync
**Options:**
1. Send full world state on connect (simple, potentially large)
2. Send only current location state (efficient, requires location tracking)
3. Send "manifest" of what exists, client requests details (complex, flexible)

**Considerations:**
- Network efficiency (mobile/AR bandwidth limited)
- Client complexity (state management)
- Scalability (world size growth)

---

### State Delta Format
**Current:** NATS WorldUpdateEvent with `changes` dict

**Questions:**
- Should deltas reference paths (e.g., `"world.locations.store.items[0]"`)?
- Or structured operations (e.g., `{"target": "world", "operation": "remove"}`)?
- How granular? Full item objects or just IDs?

**Example Delta (Current):**
```json
{
  "changes": {
    "player": {
      "inventory": {
        "$append": {"id": "bottle_1", "collected_at": "..."}
      }
    }
  }
}
```

**Example Delta (Complete - Needs Design):**
```json
{
  "changes": {
    "world.locations.woander_store.items": {
      "operation": "remove",
      "item_id": "bottle_of_joy_1"
    },
    "player.inventory": {
      "operation": "add",
      "item": {"id": "bottle_of_joy_1", "collected_at": "...", "from": "woander_store"}
    }
  }
}
```

---

## Shared vs Isolated State Models

### Shared Model (Multiplayer)
**Characteristics:**
- Multiple players interact with same world
- Item collection by one player affects all players
- Requires conflict resolution (simultaneous collection)

**Implementation Questions:**
- Separate `update_world_state()` method?
- Locking/transactions for concurrent modifications?
- Do we publish to all players or just location-based?

---

### Isolated Model (Single-Player)
**Characteristics:**
- Player has own copy of entire world
- No interaction with other players
- Simpler state management

**Implementation Questions:**
- Is player view file the single source of truth?
- Do we still publish to NATS (for chat integration)?
- How do we distinguish in WebSocket handler?

---

## Technical Decisions Needed

### 1. World State Update Mechanism
**Question:** How do we modify shared world.json?

**Options:**
- A) Implement `update_world_state()` similar to `update_player_view()`
- B) Lock entire world file during updates (simple, not scalable)
- C) Location-based locking (complex, more scalable)
- D) Optimistic updates with conflict detection (game industry standard)

**Considerations:**
- Concurrency (multiple players, multiple actions)
- Performance (file I/O, locking overhead)
- Consistency (what happens on conflict?)

---

### 2. Initial State Sync Strategy
**Question:** What do we send when client connects?

**Options:**
- A) Full world + player state (simple, inefficient)
- B) Current location + player state (efficient, requires location tracking)
- C) Lazy loading (client requests what it needs)

**Considerations:**
- Unity client complexity
- Network bandwidth (mobile/AR constraints)
- User experience (loading time)

---

### 3. Discovery Mechanism
**Question:** How does a player "discover" an item?

**Options:**
- A) Automatic - all items at location are visible
- B) Proximity-based - items appear when player gets close
- C) Line-of-sight - AR raycast determines visibility
- D) Action-based - player must "look" or "search"

**Considerations:**
- AR gameplay mechanics
- Server involvement (validation, state tracking)
- Client-side vs server-side logic

---

### 4. Validation & Security
**Question:** Who validates item collection is legal?

**Options:**
- A) Server validates everything (secure, higher latency)
- B) Client-side trust (fast, exploitable)
- C) Hybrid (client optimistic, server confirms)

**Considerations:**
- Cheating prevention
- User experience (responsiveness)
- Server load

---

## Implementation Phases (Proposed)

### Phase 1: Basic World State Sync
- [ ] Define world.json schema for wylding-woods
- [ ] Implement initial state sync on WebSocket connect
- [ ] Send world state + player state to client
- [ ] Unity renders items at locations

**Goal:** Client can see bottles exist and where they are

---

### Phase 2: Complete State Deltas
- [ ] Implement world state update mechanism
- [ ] Modify collect_bottle handler to update both world + player
- [ ] Publish complete deltas to NATS
- [ ] Verify other clients see updates

**Goal:** Collection removes bottle from world for everyone

---

### Phase 3: Discovery & Validation
- [ ] Define discovery mechanism (design decision needed)
- [ ] Implement server-side validation
- [ ] Add "discovered_items" to player state
- [ ] Handle edge cases (conflicts, timing)

**Goal:** Proper gameplay flow with discovery → collect → update

---

## Open Architecture Questions

1. **Location Tracking:** Does server track player's current location or trust client?
2. **State Model Detection:** How does WebSocket handler know if shared vs isolated?
3. **NATS Fan-out:** Do we publish to all players or location-specific channels?
4. **Item Respawn:** Do bottles respawn? When? Who decides?
5. **Quest Integration:** How does quest system track bottle collection across players?
6. **Performance:** Can we handle 100 players collecting bottles simultaneously?
7. **Offline Support:** What happens if client disconnects mid-collection?

---

## Next Steps

1. **Design Session:** Discuss and decide on open questions above
2. **Schema Definition:** Finalize world.json and player view schemas
3. **Protocol Specification:** Define exact message formats for all flows
4. **Implementation Plan:** Break into concrete tasks with estimates
5. **Unity Coordination:** Ensure client-side expectations align with server design

---

## Related Documents
- `websocket-architecture-decision.md` - Migration to Session Service plan
- `websocket-test-results.md` - Current implementation test results
- `TODO.md` - Overall project tracking
- Phase 1A/1B NATS integration documentation

---

## Notes for Future Implementation

**DO NOT assume:**
- Specific file formats or schemas
- Unity's rendering or discovery mechanics
- Performance characteristics without measurement
- Security requirements without threat modeling

**DO consider:**
- Industry patterns (Minecraft, Roblox, WoW)
- Scalability from the start (even if we start simple)
- Unity team's input on client-side needs
- User experience over technical elegance
