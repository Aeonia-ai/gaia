# Unity Local Testing Guide - WorldUpdate v0.4

**Date**: 2025-11-10
**Status**: Ready for Unity Client Testing
**Server Version**: v0.4 WorldUpdate Implementation Complete

---

## Quick Start

### 1. Local Server Connection

**WebSocket Endpoint:**
```
ws://localhost:8666/ws/experience?token={JWT}&experience=wylding-woods
```

**Alternative (direct to KB Service):**
```
ws://localhost:8001/ws/experience?token={JWT}&experience=wylding-woods
```

### 2. Get Test JWT Token

```bash
# From server repository
cd /Users/jasbahr/Development/Aeonia/server/gaia

# Generate JWT for test user
python3 tests/manual/get_test_jwt.py

# Output will be JWT token (copy this)
```

### 3. Test Connection

**Using Python WebSocket Test:**
```bash
# Install dependencies (one-time)
pip install websockets

# Run test
python3 tests/manual/test_websocket_experience.py --url ws://localhost:8666/ws/experience
```

**Using wscat (interactive):**
```bash
# Install wscat (one-time)
npm install -g wscat

# Get JWT
JWT=$(python3 tests/manual/get_test_jwt.py 2>/dev/null | tail -1)

# Connect
wscat -c "ws://localhost:8666/ws/experience?experience=wylding-woods&token=$JWT"

# Send test messages:
{"type": "ping"}
{"type": "action", "action": "collect_bottle", "item_id": "dream_bottle_woander_1"}
```

---

## v0.4 WorldUpdate Format

### Example Messages You'll Receive

**1. Welcome Message:**
```json
{
  "type": "connection_established",
  "connection_id": "abc-123",
  "user_id": "user-uuid",
  "experience": "wylding-woods"
}
```

**2. World Update (Item Collection):**
```json
{
  "type": "world_update",
  "version": "0.4",
  "experience": "wylding-woods",
  "user_id": "user-uuid",
  "base_version": 1731240000000,
  "snapshot_version": 1731240001000,
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
        "description": "A small glass bottle that glows with inner light",
        "collectible": true,
        "visible": true,
        "state": {
          "glowing": true,
          "dream_type": "peaceful",
          "collected_at": "2025-11-10T12:00:00Z"
        }
      }
    }
  ],
  "timestamp": 1731240001000
}
```

**3. Area of Interest (AOI) Message:**
```json
{
  "type": "update_location",
  "areas": {
    "spawn_zone_1": {
      "area_id": "spawn_zone_1",
      "name": "Display Shelf Area",
      "items": [
        {
          "instance_id": "dream_bottle_woander_1",
          "template_id": "dream_bottle",
          "semantic_name": "dream bottle",
          "description": "A small glass bottle that glows with inner light",
          "collectible": true,
          "visible": true,
          "state": {
            "glowing": true,
            "dream_type": "peaceful"
          }
        }
      ]
    }
  },
  "snapshot_version": 1731240000000
}
```

---

## Unity Implementation Checklist

### Phase 1: Message Parsing
- [ ] Add v0.4 message types to `ExperienceMessages.cs`
- [ ] Parse `base_version` and `snapshot_version` fields
- [ ] Parse `changes` array (not dict)
- [ ] Handle `area_id: null` for inventory items

### Phase 2: Instance Tracking
- [ ] Create `_activeInstances` dictionary (instance_id → GameObject)
- [ ] Store `snapshot_version` from AOI
- [ ] Validate `base_version` matches local `snapshot_version`
- [ ] Request fresh AOI if versions mismatch

### Phase 3: Change Operations
- [ ] **Remove**: `_activeInstances.Remove(instance_id)` + Destroy GameObject
- [ ] **Add to World**: Spawn at `area_id`, add to `_activeInstances`
- [ ] **Add to Inventory**: Add to UI, no world spawn
- [ ] **Update**: Modify existing instance state

---

## Testing Scenarios

### Scenario 1: Item Collection Flow
1. Unity sends GPS location
2. Server responds with AOI (snapshot_version: 12345)
3. Unity spawns bottles in world
4. Unity triggers collect action
5. Server publishes world_update:
   - `base_version: 12345` (matches AOI)
   - `snapshot_version: 12346` (new version)
   - Changes: remove from world, add to inventory
6. Unity validates base_version, applies delta
7. Unity updates local version to 12346

### Scenario 2: Out-of-Sync Detection
1. Unity has `snapshot_version: 12345`
2. Another client collects item (server now at 12350)
3. Unity sends action
4. Server publishes world_update with `base_version: 12350`
5. Unity detects mismatch (12345 ≠ 12350)
6. Unity sends new GPS location to request fresh AOI
7. Server responds with current state

### Scenario 3: Multiple Rapid Changes
1. Unity collects 3 bottles quickly
2. Server publishes 3 separate world_update messages
3. Unity queues changes if base_version sequential
4. Unity applies deltas in order
5. Unity updates version after each successful apply

---

## Troubleshooting

### Connection Refused
```bash
# Check services are running
docker compose ps

# Check KB service
curl http://localhost:8001/health

# Check Gateway
curl http://localhost:8666/health

# Restart if needed
docker compose restart kb-service gateway
```

### Authentication Errors
```bash
# Generate fresh JWT
python3 tests/manual/get_test_jwt.py

# Verify test user exists
./scripts/manage-users.sh list | grep pytest

# Create test user if needed
./scripts/manage-users.sh create pytest@aeonia.ai
```

### No World Updates Received
```bash
# Check NATS is running
docker compose ps nats

# Check KB logs for world_update publishing
docker compose logs -f kb-service | grep "world_update"

# Test with Python script
python3 tests/manual/test_websocket_experience.py --url ws://localhost:8666/ws/experience
```

### Template Data Missing
```bash
# Verify world.json has template/instance structure
cat /Users/jasbahr/Development/Aeonia/Vaults/gaia-knowledge-base/experiences/wylding-woods/state/world.json | jq '.locations.woander_store.sublocations.spawn_zone_1.items[0]'

# Should show: instance_id, template_id, state (not full properties)

# Verify template exists
ls /Users/jasbahr/Development/Aeonia/Vaults/gaia-knowledge-base/experiences/wylding-woods/templates/items/dream_bottle.md
```

---

## Performance Expectations

**Latency Targets:**
- WebSocket connection: <100ms
- Ping/pong: <50ms
- Action response: 50-200ms
- World update event: <100ms after state change
- Total item collection flow: <500ms

**Message Size:**
- AOI snapshot: 1-5KB (depends on area density)
- World update: 0.5-2KB (single change)
- Welcome message: <1KB

---

## Validation Checklist

**Format Validation:**
- [ ] `version` field is "0.4" (not "0.3")
- [ ] `changes` is array (not dict)
- [ ] `base_version` and `snapshot_version` present
- [ ] Remove uses: `area_id` + `instance_id`
- [ ] Inventory add uses: `area_id: null` + `path: "player.inventory"`
- [ ] Items have both `instance_id` and `template_id`
- [ ] Template properties merged (description, collectible, etc.)

**Functional Validation:**
- [ ] Bottles spawn in correct world locations
- [ ] Collection removes from world, adds to inventory
- [ ] Multiple collections work sequentially
- [ ] Version tracking prevents stale updates
- [ ] Out-of-sync triggers AOI refresh

---

## Unity Message Type Definitions

**Reference for `ExperienceMessages.cs`:**

```csharp
[Serializable]
public class WorldUpdateV04
{
    [JsonProperty("type")]
    public string type = "world_update";

    [JsonProperty("version")]
    public string version;

    [JsonProperty("experience")]
    public string experience;

    [JsonProperty("user_id")]
    public string user_id;

    [JsonProperty("base_version")]
    public long base_version;

    [JsonProperty("snapshot_version")]
    public long snapshot_version;

    [JsonProperty("changes")]
    public List<WorldUpdateChange> changes;

    [JsonProperty("timestamp")]
    public long timestamp;
}

[Serializable]
public class WorldUpdateChange
{
    [JsonProperty("operation")]
    public string operation;  // "add", "remove", "update"

    [JsonProperty("area_id")]
    public string area_id;    // null for inventory

    [JsonProperty("path")]
    public string path;       // "player.inventory" for inventory

    [JsonProperty("instance_id")]
    public string instance_id;

    [JsonProperty("item")]
    public WorldItem item;    // Full item data for add/update
}
```

---

## Server Files Modified (v0.4)

**Core Implementation:**
- `app/shared/events.py` - WorldUpdateEvent model
- `app/services/kb/unified_state_manager.py` - Version tracking + formatting
- `app/services/kb/template_loader.py` - Template loading service

**State Data:**
- `Vaults/gaia-knowledge-base/experiences/wylding-woods/state/world.json` - Restructured

**Documentation:**
- `docs/scratchpad/websocket-aoi-client-guide.md` - v0.4 specification

---

## Contact & Support

**Questions:** Post in Symphony `websockets` room
**Server Status:** `docker compose ps`
**Server Logs:** `docker compose logs -f kb-service`

**Ready for Monday deployment to dev environment.**
