# WebSocket Area of Interest (AOI) - Client Integration Guide

**Version**: 0.4
**Last Updated**: 2025-11-12
**Status**: Phase 1 MVP Complete + Fast Command Handlers Implemented
**Source of Truth**: [AOI WebSocket Design](./aoi-websocket-design-2025-11-10.md)
**Implementation**: `/app/services/kb/unified_state_manager.py` (build_aoi at line 1226)

---

## Overview

This guide describes how Unity (or other AR) clients connect to GAIA's WebSocket API and receive location-based world state data.

**Current Implementation Status**: Phase 1 MVP is complete and tested. All JSON examples in this document reflect the actual server responses you will receive.

**Key Concept**: Progressive Loading
- Connect first, authenticate, get connection acknowledgment
- **Receive initial room state automatically** (new in v0.4)
- Send your GPS location when ready (for AR experiences)
- Receive Area of Interest (AOI) with nearby items, NPCs, locations
- Use fast commands for instant gameplay (<10ms response time)
- Receive real-time updates as world changes

### Phase 1 vs Phase 2 Features

**✅ Phase 1 MVP (Currently Implemented)**:
- Basic zone structure: `id`, `name`, `description`, `gps` with `lat`/`lng` only
- Areas: `id`, `name`, `description`, `items[]`, `npcs[]` arrays
- Full item/NPC data with instance_id, template_id, state
- Player state tracking: `current_location`, `current_area`, `inventory`
- Timestamp-based versioning for synchronization

**⏳ Phase 2 (Planned - Not Yet Implemented)**:
- Zone enhancements: `geography_id`, `geofence_radius_m` in gps object
- Area enhancements: `location`, `accessible_from`, `ambient` properties
- Zone environment properties
- Monotonic counter versioning
- Enhanced geofencing and GPS validation

All JSON examples below show **Phase 1 structure only**. Do not expect Phase 2 fields in server responses yet.

### Spatial Terminology

The system uses industry-standard game hierarchy (matches Unity/Unreal/MMO conventions):

- **Geography**: GPS anchor (real-world waypoint), may have optional region metadata
- **Zone**: Experience-specific themed location at a Geography (e.g., "Woander's Shop" at Waypoint 28A)
- **Area**: Functional subdivisions within a Zone (e.g., "counter", "display_shelf")
- **Spot**: Precise interactable points (not yet in AOI, future feature)

**Client queries by GPS distance** - the server returns the nearest Zone, not hierarchical navigation.

---

## WebSocket Connection

### Endpoint

```
ws://localhost:8666/ws/experience?token=<JWT>&experience=<experience_id>
```

**Production**:
```
wss://gaia-gateway-prod.fly.dev/ws/experience?token=<JWT>&experience=wylding-woods
```

**Important**: All JSON examples below show the **Phase 1 MVP structure** that is currently implemented. Phase 2 enhancements are clearly marked where applicable.

### Query Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `token` | ✅ Yes | JWT token from authentication |
| `experience` | ✅ Yes | Experience ID (e.g., `wylding-woods`) |

### Connection Flow

```
1. Client opens WebSocket connection
2. Server validates JWT
3. Server sends "connected" message
4. Client sends GPS location ("update_location")
5. Server sends "area_of_interest" with world state
6. Server streams "world_update" events as things change
```

---

## Message Format

All messages are JSON with a `type` field:

```json
{
  "type": "message_type",
  "timestamp": 1730678400000,
  ...type-specific fields...
}
```

- `type`: Required string identifying message purpose
- `timestamp`: Optional Unix milliseconds (UTC)

---

## Client → Server Messages

### 1. Update Location

Tell server your current GPS coordinates to receive nearby content.

```json
{
  "type": "update_location",
  "lat": 37.906512,
  "lng": -122.544217
}
```

**When to send**:
- After receiving `connected` message
- When player moves significantly (>10m recommended)
- When entering new geofence area

**Response**: `area_of_interest` message

---

### 2. Action Commands (Legacy - Slow Path)

⚠️ **Deprecated**: Use Fast Commands (section 3) for better performance. This path routes through LLM processing (25-30s response time).

Execute game actions via natural language processing.

```json
{
  "type": "action",
  "action": "collect the dream bottle",
  "location": "woander_store"
}
```

**Response**: `action_response` message (slow: 25-30s)

---

### 3. Fast Commands (Recommended)

**Performance**: <10ms response time (5,000x faster than LLM path)

Execute structured game commands with instant server response. These bypass LLM processing for production-ready gameplay.

#### 3.1 Navigation (go)

Move between areas within your current location.

```json
{
  "type": "action",
  "action": "go",
  "destination": "spawn_zone_1"
}
```

**Response**: `action_response` + `world_update` (6ms avg)

---

#### 3.2 Collect Item (collect_item)

Pick up an item from the world.

```json
{
  "type": "action",
  "action": "collect_item",
  "instance_id": "dream_bottle_1"
}
```

**Validation**: Player must be in same location/area as item. Item must be `collectible: true`.

**Response**: `action_response` + `world_update` (1-10ms)

---

#### 3.3 Drop Item (drop_item)

Drop an item from inventory into the world at your current location.

```json
{
  "type": "action",
  "action": "drop_item",
  "instance_id": "health_potion_1"
}
```

**Validation**: Item must exist in player inventory.

**Response**: `action_response` + `world_update` (7ms avg)

---

#### 3.4 Examine Item (examine)

Inspect an item for detailed information (read-only, no state change).

```json
{
  "type": "action",
  "action": "examine",
  "instance_id": "dream_bottle_2"
}
```

**Search Order**: Player inventory → current area → current location

**Response**: `action_response` with formatted description (2-3ms)

---

#### 3.5 Use Item (use_item)

Consume or activate an item from inventory.

```json
{
  "type": "action",
  "action": "use_item",
  "instance_id": "health_potion_1"
}
```

**Effects**:
- Health restoration: Updates `player.stats.health`
- Status effects: Adds to `player.status_effects[]`
- Consumables: Removed from inventory after use

**Response**: `action_response` + `world_update` (4ms avg)

---

#### 3.6 Inventory List (inventory)

Get formatted list of items in player inventory (read-only).

```json
{
  "type": "action",
  "action": "inventory"
}
```

**Response**: `action_response` with grouped item list (2ms avg)

---

#### 3.7 Give Item (give_item)

Transfer item from player to NPC or another player.

```json
{
  "type": "action",
  "action": "give_item",
  "instance_id": "dream_bottle_1",
  "target_npc_id": "louisa"
}
```

**Validation**:
- Item must be in player inventory
- Player must be in same location/area as target
- NPC must exist (player-to-player transfer not yet implemented)

**Response**: `action_response` with NPC dialogue (5ms avg)

---

### 4. Ping (Health Check)

```json
{
  "type": "ping",
  "timestamp": 1730678400000
}
```

**Response**: `pong` message

---

## Server → Client Messages

### 1. Connected (Welcome)

Sent immediately after successful connection.

```json
{
  "type": "connected",
  "connection_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "a7f4370e-0af5-40eb-bb18-fcc10538b041",
  "experience": "wylding-woods",
  "timestamp": 1730678400000,
  "message": "Connected to wylding-woods experience"
}
```

**Client Action**: Wait for `initial_state` (automatic), then optionally send `update_location` for AR/GPS features

---

### 2. Initial State (Automatic)

**Status**: 💭 **Future Feature** - Deferred for room-based games only

**Unity Team Feedback (2025-11-12)**: Use `area_of_interest` for GPS/AR games instead. Initial state only makes sense for indoor/room-based games (MUD-style) where player location is deterministic from database.

**Proposal**: For future room-based games, send automatically after `connected` message with player's current room state.

```json
{
  "type": "initial_state",
  "timestamp": 1731439200000,
  "player": {
    "current_location": "woander_store",
    "current_area": "spawn_zone_1",
    "inventory": [],
    "stats": {
      "health": 100,
      "max_health": 100
    }
  },
  "location": {
    "id": "woander_store",
    "name": "Woander's Magical Shop",
    "description": "The entrance to Woander's mystical shop where magical items and curiosities are sold."
  },
  "area": {
    "id": "spawn_zone_1",
    "name": "Display Shelf Area",
    "description": "A shelf displaying various magical curiosities and glowing bottles.",
    "items": [
      {
        "instance_id": "dream_bottle_2",
        "template_id": "dream_bottle",
        "semantic_name": "adventurous dream bottle",
        "description": "A bottle with warm amber radiance...",
        "collectible": true,
        "visible": true,
        "state": {
          "glowing": true,
          "dream_type": "adventurous",
          "symbol": "star"
        }
      }
    ],
    "npcs": [],
    "exits": ["entrance", "counter", "fairy_door_main", "spawn_zone_2"]
  }
}
```

**Use Cases**:
- ✅ Indoor/room-based games (MUD-style text adventures)
- ✅ Turn-based games where location is saved in database
- ❌ GPS/AR games (use `area_of_interest` instead - GPS is source of truth)

**Why NOT for GPS/AR Games**:
- Player's physical location changes in real world
- Database state could be stale (player moved since last session)
- Client sends GPS coordinates immediately after connection anyway
- No practical "blind connection" period

**For GPS/AR Games** (like Wylding Woods):
Use the standard flow: `connected` → client sends `update_location` → server responds with `area_of_interest`

---

### 3. Area of Interest (World State)

Sent in response to `update_location`. Contains everything visible at your location (GPS/AR mode).

**Scope Clarification** (Unity feedback 2025-11-12):
- Returns **ONE Zone** (nearest to GPS coordinates)
- Includes **ALL Areas** within that Zone
- Client spawns all items/NPCs across all areas simultaneously

**Example**: GPS at Woander's Shop returns entire "woander_store" Zone with all 5 areas: spawn_zone_1, spawn_zone_2, counter, entrance, fairy_door_main.

```json
{
  "type": "area_of_interest",
  "timestamp": 1730678400000,
  "snapshot_version": 12345,

  "zone": {
    "id": "woander_store",
    "name": "Woander's Magical Shop",
    "description": "The entrance to Woander's mystical shop...",
    "gps": {
      "lat": 37.906512,
      "lng": -122.544217
    }
  },

  # NOTE: Phase 1 MVP structure - geography_id and geofence_radius_m coming in Phase 2

  "areas": {
    "spawn_zone_1": {
      "id": "spawn_zone_1",
      "name": "Display Shelf Area",
      "description": "A shelf displaying various magical curiosities...",
      "items": [
        {
          "instance_id": "dream_bottle_1",
          "template_id": "dream_bottle",
          "type": "dream_bottle",
          "semantic_name": "peaceful dream bottle",
          "description": "A bottle glowing with soft azure light...",
          "collectible": true,
          "visible": true,
          "state": {
            "glowing": true,
            "dream_type": "peaceful",
            "symbol": "spiral"
          }
        }
      ],
      "npcs": []
    },
    "counter": {
      "id": "counter",
      "name": "Shop Counter",
      "npcs": [
        {
          "instance_id": "woander_1",
          "template_id": "woander",
          "name": "Woander",
          "type": "shopkeeper_fairy",
          "description": "A cheerful blue elf shopkeeper...",
          "state": {
            "greeting_given": false,
            "shop_open": true
          }
        }
      ],
      "items": []
    }
  },

  "player": {
    "current_location": "woander_store",
    "current_area": null,
    "inventory": []
  }
}
```

#### Key Fields

**`snapshot_version`**: Version number for synchronization
- Store this value
- Used to validate `world_update` deltas
- If you miss updates, you'll need to request fresh AOI

**`zone`**: The location you're at
- `id`: Unique location identifier (from waypoint data)
- `name`: Human-readable name
- `description`: Location description
- `gps`: GPS coordinates (`lat`, `lng`)

**Phase 2 Enhancements** (not yet implemented):
- `geography_id`: Shared geography identifier across experiences
- `geofence_radius_m`: Radius for zone boundary detection in gps object

**`areas`**: Sublocations within zone
- Dictionary keyed by area ID
- Each area contains `items` and `npcs` arrays
- Use for spatial organization and rendering

**`items[]`**: Collectible/interactive items
- `instance_id`: Unique runtime ID (use for actions)
- `template_id`: Item type/blueprint
- `collectible`: Can player pick this up?
- `visible`: Should this render?
- `state`: Dynamic properties (glow, opened, etc.)

#### Template/Instance Architecture

**Important**: The item data you receive is a merge of two sources:

**Templates** (Immutable Blueprints):
- Defined in `/experiences/{exp}/templates/items/{template_id}.md`
- Contain shared properties: `semantic_name`, `description`, `collectible`, `visual_prefab`
- Single source of truth - update template once, affects all instances
- Examples: `dream_bottle.md`, `fairy_house.md`, `woander.md`

**Instances** (Runtime Entities):
- Defined in `/experiences/{exp}/state/world.json`
- Contain unique IDs and mutable state: `instance_id`, `template_id`, `state{}`
- Track per-instance properties: visibility, glow status, symbol variant
- Each instance references a template via `template_id`

**What You Receive** (Merged at Runtime):
```json
{
  "instance_id": "dream_bottle_1",    // From instance (unique)
  "template_id": "dream_bottle",      // From instance (reference)
  "semantic_name": "dream bottle",    // From template (shared)
  "description": "A bottle glowing...", // From template (shared)
  "collectible": true,                // From template (shared)
  "state": {                          // From instance (unique)
    "glowing": true,
    "dream_type": "peaceful",
    "symbol": "spiral"
  }
}
```

**Why This Matters**:
- ✅ Content updates: Change template once → all instances updated
- ✅ Smaller payloads: Instance state only tracks what's unique
- ✅ Matches Unity prefab pattern: template = prefab, instance = GameObject
- ✅ Use `instance_id` for actions (collect, interact), not `template_id`

**For Actions**: Always use `instance_id`, never `template_id`:
```json
{
  "type": "action",
  "action": "collect_item",
  "instance_id": "dream_bottle_1",  // ✅ Correct - specific instance
  "location": "woander_store"
}
```

**`npcs[]`**: Non-player characters
- `instance_id`: Use for `talk` actions
- `template_id`: NPC type
- `state`: NPC-specific state (shop_open, quest_available, etc.)

**`player`**: Your current state
- `current_location`: Zone ID you're in
- `inventory`: Items you've collected

#### Empty Response

If no locations nearby:

```json
{
  "type": "area_of_interest",
  "snapshot_version": 12345,
  "zone": null,
  "areas": {},
  "player": {
    "current_location": null,
    "inventory": []
  }
}
```

**Not an error** - just means you're not near any registered locations.

---

### 4. World Update (Real-time Changes) - v0.4

Sent when world state changes (someone collects item, NPC moves, etc.).

**Protocol Version**: v0.4 (aligned with AOI - uses `instance_id`/`template_id`)

```json
{
  "type": "world_update",
  "version": "0.4",
  "experience": "wylding-woods",
  "user_id": "user_123",
  "base_version": 12345,
  "snapshot_version": 12346,
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
      "item": {
        "instance_id": "dream_bottle_woander_1",
        "template_id": "dream_bottle",
        "semantic_name": "dream bottle",
        "description": "A bottle glowing with inner light...",
        "collectible": true,
        "visible": true,
        "state": {
          "collected_at": "2025-11-10T12:00:00Z"
        }
      }
    }
  ],
  "timestamp": 1731240000000,
  "metadata": {
    "source": "kb_service",
    "state_model": "shared"
  }
}
```

#### Key Fields

**`version`**: Protocol version ("0.4")
- Matches AOI structure (instance_id/template_id)
- Array-based changes format
- Full template data merged

**`base_version`**: Version this delta applies on top of
- Must match your current `snapshot_version`
- If mismatch → request fresh AOI

**`snapshot_version`**: New version after applying delta
- Update your local version to this value
- Use for next delta validation

**`changes[]`**: Array of change operations
- Each change has: operation, area_id, instance_id, item data
- See "Change Operations" below

#### Delta Application Protocol

```typescript
// 1. Receive world_update
const update = JSON.parse(message);

// 2. Validate version
if (update.base_version !== localSnapshotVersion) {
    // Out of sync! Request fresh AOI
    sendUpdateLocation(currentGPS);
    return;
}

// 3. Apply changes
for (const change of update.changes) {
    switch (change.operation) {
        case "remove":
            removeInstance(change.area_id, change.instance_id);
            break;
        case "add":
            if (change.area_id === null) {
                // Add to inventory
                addToInventory(change.item);
            } else {
                // Spawn in world
                spawnInstance(change.area_id, change.item);
            }
            break;
        case "update":
            updateInstance(change.instance_id, change.item);
            break;
    }
}

// 4. Update local version
localSnapshotVersion = update.snapshot_version;
```

#### Change Operations

**Remove Operation**:
```json
{
  "operation": "remove",
  "area_id": "spawn_zone_1",  // Where item was
  "instance_id": "dream_bottle_woander_1"  // Which instance
}
```
- Look up instance in `_activeInstances[instance_id]`
- Destroy GameObject
- Remove from tracking

**Add to World**:
```json
{
  "operation": "add",
  "area_id": "spawn_zone_1",  // Where to spawn
  "item": {
    "instance_id": "new_item_1",
    "template_id": "dream_bottle",
    // ... full item data with template merged
  }
}
```
- Load prefab from `template_id`
- Instantiate at area location
- Store in `_activeInstances[instance_id]`

**Add to Inventory**:
```json
{
  "operation": "add",
  "area_id": null,  // null = inventory
  "path": "player.inventory",
  "item": {
    "instance_id": "dream_bottle_woander_1",
    "template_id": "dream_bottle",
    // ... full item data
  }
}
```
- Don't spawn in world
- Add to inventory UI
- Track in inventory list

**Update Operation**:
```json
{
  "operation": "update",
  "area_id": "spawn_zone_1",
  "instance_id": "npc_1",
  "item": {
    "instance_id": "npc_1",
    "template_id": "louisa",
    "state": {
      "shop_open": false  // Changed property
    }
  }
}
```
- Find existing instance
- Update properties
- Re-render if needed

#### Version Synchronization

**Success Case:**
```
Client: snapshot_version = 12345
Server: Sends update with base_version=12345, snapshot_version=12346
Client: Validates (12345 == 12345) ✅
Client: Applies changes
Client: Updates to snapshot_version = 12346
```

**Out of Sync Case:**
```
Client: snapshot_version = 12345
Server: Sends update with base_version=12347 (client missed 12346!)
Client: Validates (12345 != 12347) ❌
Client: Requests fresh AOI via update_location
Server: Sends new AOI with current snapshot_version
Client: Resets to fresh state
```

#### Benefits of v0.4

1. **Unified Parsing**: Same structure as AOI (one code path)
2. **Template Data Included**: Full item properties automatically merged
3. **Version Tracking**: Detect out-of-sync, automatic recovery
4. **Explicit Operations**: Clear add/remove/update semantics

---

### 5. Action Response

Sent after processing your `action` message.

```json
{
  "type": "action_response",
  "action": "collect_item",
  "success": true,
  "message": "You picked up the Peaceful Dream Bottle!",
  "timestamp": 1730678400000,
  "metadata": {
    "item_id": "dream_bottle_1",
    "item_name": "Peaceful Dream Bottle"
  }
}
```

**Note**: State changes come separately via `world_update`, not in action_response.

---

### 6. Error Messages

```json
{
  "type": "error",
  "code": "invalid_action",
  "message": "Item not found in location",
  "timestamp": 1730678400000
}
```

#### Error Codes

| Code | Meaning |
|------|---------|
| `invalid_json` | Malformed JSON message |
| `missing_type` | No `type` field in message |
| `missing_action` | Action message missing `action` field |
| `unknown_message_type` | Unrecognized message type |
| `processing_error` | Exception during command handling |
| `not_implemented` | Feature not yet available |

---

## Example Flow

### Complete Session

```
1. Client: Connect to ws://host/ws/experience?token=JWT&experience=wylding-woods

2. Server: {"type": "connected", "user_id": "...", "experience": "wylding-woods"}

3. Server: {"type": "initial_state", "player": {...}, "location": {...}, "area": {...}}
   → Client immediately renders current room
   → Client spawns items/NPCs in spawn_zone_1
   → Client displays exits: ["entrance", "counter", "fairy_door_main"]

4. Client: {"type": "action", "action": "collect_item", "instance_id": "dream_bottle_1"}

5. Server: {"type": "action_response", "success": true, "message": "You picked up..."} (1-10ms)

6. Server: {"type": "world_update", "version": "0.4", "changes": [{"operation": "remove"...}]}
   → Client removes bottle from world (instance_id: dream_bottle_1)
   → Client adds bottle to inventory UI

7. Client: {"type": "action", "action": "go", "destination": "counter"}

8. Server: {"type": "action_response", "success": true} (6ms)

9. Server: {"type": "world_update", "changes": [{"operation": "update", "path": "player.current_area"...}]}
   → Client transitions to counter area
   → Client renders Woander NPC

10. (Optional) Client sends GPS for AR features:
    Client: {"type": "update_location", "lat": 37.906, "lng": -122.544}

11. Server: {"type": "area_of_interest", "snapshot_version": 12345, "zone": {...}, "areas": {...}}
    → Client validates GPS alignment
    → Client may update zone boundaries/geofencing
```

---

## Best Practices

### Performance: Fast Commands vs Legacy Path

**Use Fast Commands** for gameplay actions:

| Command | Fast Path | Legacy Path | Speedup |
|---------|-----------|-------------|---------|
| go | 6ms | 25-30s | 5,000x |
| collect_item | 1-10ms | 25-30s | 3,000x |
| drop_item | 7ms | 25-30s | 4,000x |
| examine | 2-3ms | 25-30s | 10,000x |
| use_item | 4ms | 25-30s | 7,000x |
| inventory | 2ms | 25-30s | 15,000x |
| give_item | 5ms | 25-30s | 6,000x |

**Rule of Thumb**: If the action has structured parameters (instance_id, destination, etc.), use fast commands. Reserve legacy `"action"` type for natural language interactions.

---

### Connection Management

✅ **Do**:
- Check JWT expiry before connecting
- Reconnect on disconnect with exponential backoff
- Send ping every 30s to keep connection alive
- Buffer `world_update` messages if processing slowly
- Use fast commands for all gameplay actions
- Wait for `initial_state` before allowing player input

❌ **Don't**:
- Don't send location updates more than once per second
- Don't ignore `snapshot_version` - leads to desync
- Don't send actions for items not in your current AOI
- Don't use legacy action path for structured commands

### GPS Updates

**When to send `update_location`**:
- After initial connection
- When GPS accuracy improves (±50m → ±5m)
- When player moves >10m from last sent position
- When exiting geofence of current zone
- After long pause in GPS updates (>30s)

**When NOT to send**:
- GPS jitter (<5m movement)
- While indoors with poor GPS
- More than once per second

### State Synchronization

**Handling `world_update` messages**:
1. Store `snapshot_version` from AOI
2. For each update:
   - If `base_version == snapshot_version`: Apply immediately
   - If `base_version > snapshot_version`: Buffer for later
   - If `base_version < snapshot_version`: Discard (outdated)
3. After applying update: `snapshot_version = update.version`
4. If gaps detected: Request fresh AOI

**Resync triggers**:
- Version gap >10 detected
- Update older than 5 seconds arrives
- Multiple buffered updates pile up
- Rendering issues observed

---

## Unity Integration Example

```csharp
public class GAIAWebSocketClient : MonoBehaviour
{
    private WebSocket ws;
    private int snapshotVersion = 0;
    private List<WorldUpdate> bufferedUpdates = new();

    async void Start()
    {
        string jwt = await AuthManager.GetJWT();
        string url = $"wss://gaia-gateway-prod.fly.dev/ws/experience?token={jwt}&experience=wylding-woods";

        ws = new WebSocket(url);
        ws.OnMessage += HandleMessage;
        await ws.Connect();
    }

    void HandleMessage(string message)
    {
        var data = JsonUtility.FromJson<Dictionary<string, object>>(message);
        string type = data["type"];

        switch (type)
        {
            case "connected":
                OnConnected(data);
                break;
            case "area_of_interest":
                OnAreaOfInterest(data);
                break;
            case "world_update":
                OnWorldUpdate(data);
                break;
            case "action_response":
                OnActionResponse(data);
                break;
            case "error":
                OnError(data);
                break;
        }
    }

    void OnConnected(Dictionary<string, object> data)
    {
        Debug.Log($"Connected: {data["connection_id"]}");
        SendLocationUpdate();
    }

    void SendLocationUpdate()
    {
        var location = LocationService.GetCurrentLocation();
        var msg = new {
            type = "update_location",
            lat = location.latitude,
            lng = location.longitude
        };
        ws.SendText(JsonUtility.ToJson(msg));
    }

    void OnAreaOfInterest(Dictionary<string, object> data)
    {
        snapshotVersion = (int)data["snapshot_version"];

        // Despawn old zone
        WorldRenderer.ClearAll();

        // Spawn new zone
        var zone = data["zone"];
        var areas = data["areas"];

        foreach (var area in areas)
        {
            foreach (var item in area["items"])
            {
                WorldRenderer.SpawnItem(item);
            }
            foreach (var npc in area["npcs"])
            {
                WorldRenderer.SpawnNPC(npc);
            }
        }
    }

    void OnWorldUpdate(Dictionary<string, object> data)
    {
        int version = (int)data["version"];
        int baseVersion = (int)data["base_version"];

        // Check synchronization
        if (baseVersion != snapshotVersion)
        {
            // Buffer or discard
            if (baseVersion > snapshotVersion)
            {
                bufferedUpdates.Add(new WorldUpdate(data));
            }
            return;
        }

        // Apply changes
        ApplyChanges(data["changes"]);
        snapshotVersion = version;

        // Apply buffered updates
        ProcessBufferedUpdates();
    }

    void ProcessBufferedUpdates()
    {
        bufferedUpdates.Sort((a, b) => a.baseVersion.CompareTo(b.baseVersion));

        while (bufferedUpdates.Count > 0 &&
               bufferedUpdates[0].baseVersion == snapshotVersion)
        {
            var update = bufferedUpdates[0];
            bufferedUpdates.RemoveAt(0);

            ApplyChanges(update.changes);
            snapshotVersion = update.version;
        }
    }
}
```

---

## Troubleshooting

### Connection Issues

**Problem**: WebSocket connects but immediately disconnects

**Solution**: Check JWT validity - may be expired or malformed

---

**Problem**: `1008` close code received

**Solution**: Authentication failed - get fresh JWT token

---

### No World State Received

**Problem**: Connected but no items spawn

**Solution**: Send `update_location` message - AOI not sent automatically

---

**Problem**: Empty AOI response

**Solution**:
- Check GPS coordinates are valid
- Verify you're within 100m of a registered location
- Not an error - just no nearby content

---

### State Desynchronization

**Problem**: Items appear/disappear incorrectly

**Solution**:
- Check you're applying `world_update` deltas correctly
- Verify `base_version` matches before applying
- Send fresh `update_location` to resync

---

**Problem**: Duplicate items spawn

**Solution**: Don't apply updates with `base_version < snapshot_version` (outdated)

---

## Testing

### Local Testing

```bash
# Terminal 1: Start server
docker compose up

# Terminal 2: Test connection
wscat -c "ws://localhost:8666/ws/experience?token=YOUR_JWT&experience=wylding-woods"

# After connected:
{"type": "update_location", "lat": 37.906512, "lng": -122.544217}
```

### Test Locations

**Woander's Magical Shop**:
- Lat: `37.906512`
- Lng: `-122.544217`
- Contains: 3 dream bottles in spawn zones
- NPC: Woander at counter

---

## API Versioning

**Current Version**: `0.4`

**What's New in v0.4**:
- Fast command handlers (<10ms response time)
- Automatic initial_state push (proposed, pending Unity confirmation)
- v0.4 WorldUpdate format (instance_id/template_id)
- 7 production-ready command handlers

Breaking changes will increment version number. Non-breaking additions (new optional fields) maintain version.

**Version Header**:
```json
{"type": "connected", "experience": "wylding-woods", ...}
```

---

## Support

**Documentation**: See [AOI WebSocket Design](../scratchpad/aoi-websocket-design-2025-11-10.md) for implementation details

**Issues**: Report at https://github.com/anthropics/gaia/issues

**Questions**: Contact jason@aeonia.ai

---

**Last Updated**: 2025-11-10
**Status**: Phase 1 MVP - Implemented and Tested

---

## Reference Implementation: Actual Server Response

**This is the exact JSON structure you will receive from the server** (taken from actual implementation in `build_aoi()` method):

```json
{
  "type": "area_of_interest",
  "timestamp": 1731254400000,
  "snapshot_version": 1731254400000,

  "zone": {
    "id": "woander_store",
    "name": "Woander's Magical Shop",
    "description": "A cozy magical shop filled with curiosities...",
    "gps": {
      "lat": 37.906512,
      "lng": -122.544217
    }
  },

  "areas": {
    "spawn_zone_1": {
      "id": "spawn_zone_1",
      "name": "Display Shelf Area",
      "description": "A shelf displaying various magical curiosities...",
      "items": [
        {
          "instance_id": "dream_bottle_1",
          "template_id": "dream_bottle",
          "type": "dream_bottle",
          "semantic_name": "peaceful dream bottle",
          "description": "A bottle glowing with soft azure light...",
          "collectible": true,
          "visible": true,
          "state": {
            "glowing": true,
            "dream_type": "peaceful",
            "symbol": "spiral"
          }
        }
      ],
      "npcs": []
    },
    "counter": {
      "id": "counter",
      "name": "Shop Counter",
      "description": "The main counter...",
      "items": [],
      "npcs": [
        {
          "instance_id": "woander_1",
          "template_id": "woander",
          "name": "Woander",
          "type": "shopkeeper_fairy",
          "description": "A cheerful blue elf shopkeeper...",
          "state": {
            "greeting_given": false,
            "shop_open": true
          }
        }
      ]
    }
  },

  "player": {
    "current_location": "woander_store",
    "current_area": null,
    "inventory": []
  }
}
```

**Key Points**:
- ✅ `zone.gps` contains ONLY `lat` and `lng` (no `geofence_radius_m`)
- ✅ `zone` does NOT have `geography_id` field
- ✅ `areas` contain ONLY `id`, `name`, `description`, `items[]`, `npcs[]`
- ✅ `areas` do NOT have `location`, `accessible_from`, or `ambient` fields
- ✅ `snapshot_version` is Unix timestamp in milliseconds
- ✅ This structure has been tested and matches actual server implementation

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

The core architectural and implementation claims in this document have been verified against the source code.

-   **✅ Spatial Terminology (Section "Spatial Terminology" of this document):**
    *   **Claim:** The system uses Geography, Zone, and Area for spatial organization.
    *   **Verification:** Confirmed the usage of these concepts in `app/services/kb/unified_state_manager.py` (e.g., `get_zone_by_geography`, `_build_aoi`).

-   **✅ Client → Server Messages (Section "Client → Server Messages" of this document):**
    *   **Claim:** `update_location` and various "Fast Commands" (`go`, `collect_item`, etc.) are supported.
    *   **Code Reference:** `app/services/kb/websocket_experience.py` (lines 347-402 for `update_location`), `app/services/kb/command_processor.py` (lines 10-60 for command routing).
    *   **Verification:** Confirmed the `update_location` handler and the routing of fast commands through the `ExperienceCommandProcessor`.

-   **✅ Server → Client Messages - Connected (Section "Server → Client Messages - Connected" of this document):**
    *   **Claim:** A `connected` message is sent after successful connection.
    *   **Code Reference:** `app/services/kb/websocket_experience.py` (lines 98-105).
    *   **Verification:** Confirmed the `connected` message is sent with the specified payload.

-   **❌ Discrepancy: Server → Client Messages - Initial State (Section "Server → Client Messages - Initial State" of this document):**
    *   **Claim:** An `initial_state` message is "Proposed Feature - Not yet implemented" but the client action states "Wait for `initial_state` (automatic)".
    *   **Verification:** The `initial_state` message is indeed *not* implemented in `app/services/kb/websocket_experience.py`. The client must send an `update_location` message to receive the `area_of_interest`. This is a discrepancy between the client guide's expectation and the server's current implementation.

-   **✅ Server → Client Messages - Area of Interest (Section "Server → Client Messages - Area of Interest" of this document):**
    *   **Claim:** An `area_of_interest` message is sent in response to `update_location`, containing `zone`, `areas`, `items`, `npcs`, and `player` data, with template/instance merging.
    *   **Code Reference:** `app/services/kb/websocket_experience.py` (lines 380-402), `app/services/kb/unified_state_manager.py` (lines 1321-1390 for `_build_aoi`).
    *   **Verification:** Confirmed the `area_of_interest` message structure and content, including the merging of template and instance data as described.

-   **✅ Server → Client Messages - World Update (Section "Server → Client Messages - World Update" of this document):**
    *   **Claim:** `world_update` messages (v0.4) are sent for real-time changes, including `base_version` and `snapshot_version`.
    *   **Code Reference:** `app/shared/events.py` (lines 11-97 for `WorldUpdateEvent`), `app/services/kb/experience_connection_manager.py` (lines 146-160 for forwarding).
    *   **Verification:** Confirmed the `WorldUpdateEvent` structure and the mechanism for forwarding these NATS events to WebSocket clients.

-   **✅ Template/Instance Architecture (Section "Template/Instance Architecture" of this document):**
    *   **Claim:** Items are a merge of templates (immutable blueprints) and instances (runtime entities).
    *   **Code Reference:** `app/services/kb/template_loader.py` (lines 10-281), `app/services/kb/unified_state_manager.py` (lines 1294-1330).
    *   **Verification:** Confirmed the `TemplateLoader` and its integration into the `UnifiedStateManager` to perform the described merging.

**Conclusion:** The `websocket-aoi-client-guide.md` accurately describes the implemented AOI and WebSocket message flows, with the exception of the `initial_state` message, which is documented as expected by the client but not yet implemented on the server. This document is **PARTIALLY VERIFIED** due to this specific discrepancy.
