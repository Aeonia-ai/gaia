# Phase 6: Data Flow Tracing

**Analysis Date:** 2025-11-20

---

## Executive Summary

This document traces three critical data flows through the GAIA platform: bottle collection, NPC dialogue, and admin commands. Each flow illustrates different architectural patterns—the fast handler path, the MVP kludge path, and the deterministic admin path.

---

## Scenario 1: Unity Collects Bottle

**Timeline:** ~50ms end-to-end

### Request Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              UNITY CLIENT                                      │
│  User taps bottle → AR raycast → Send WebSocket message                       │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  WebSocket Message (ws://gateway/ws/experience?token=JWT&experience=...)     │
│  {                                                                            │
│    "type": "action",                                                         │
│    "action": "collect_item",                                                 │
│    "instance_id": "dream_bottle_woander_1",                                  │
│    "request_id": "req_abc123"                                                │
│  }                                                                           │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         GATEWAY SERVICE                                        │
│  websocket_experience.py:49 → JWT validation                                  │
│  Proxies to KB Service WebSocket endpoint                                     │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          KB SERVICE                                            │
│  websocket_experience.py:handle_message_loop() → Receives message             │
│  command_processor.py:process_command() → Routes to handler                   │
│                                                                               │
│  FAST PATH: action "collect_item" has registered handler                      │
│             → handlers/collect_item.py:handle_collect_item()                 │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
```

### Handler Processing (collect_item.py)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    handle_collect_item() [~10ms]                              │
│                                                                               │
│  1. Get state_manager from kb_agent singleton                                │
│  2. Load player_view → get current_location, current_area                    │
│  3. Load world_state → find item in zone > area > spot hierarchy            │
│  4. Validate: item exists, item.collectible=true, player at location        │
│                                                                               │
│  5. Build nested update structure:                                            │
│     {"locations": {"woander_store": {"areas": {"main_room": {                │
│       "spots": {"spot_1": {"items": {"$remove": {"instance_id": "..."}}}}    │
│     }}}}}                                                                     │
│                                                                               │
│  6. Call state_manager.update_world_state()                                  │
│     → Removes item from world.json                                           │
│     → Increments metadata._version                                            │
│     → Publishes WorldUpdateEvent to NATS                                     │
│                                                                               │
│  7. Build inventory update:                                                   │
│     {"player": {"inventory": {"$append": <item_data>}}}                      │
│                                                                               │
│  8. Call state_manager.update_player_view()                                  │
│     → Adds item to player's view.json                                        │
│     → Publishes second WorldUpdateEvent                                      │
│                                                                               │
│  9. Return CommandResult                                                     │
│     → success: true                                                          │
│     → message_to_player: "You collected dream bottle."                       │
│     → state_changes: {world: ..., player: ...}                               │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
```

### State Update & NATS Publishing

```
┌──────────────────────────────────────────────────────────────────────────────┐
│            unified_state_manager.py:update_world_state()                      │
│                                                                               │
│  1. Load config → shared model, locking enabled                              │
│  2. Get base_version from connection_manager (client's last known version)  │
│  3. Apply updates with file locking (fcntl.flock)                            │
│  4. Increment metadata._version → snapshot_version                            │
│  5. Call _publish_world_update()                                             │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│            unified_state_manager.py:_publish_world_update()                   │
│                                                                               │
│  1. Check NATS client available and connected                                │
│  2. Flatten nested dict to paths:                                            │
│     {"world.locations.woander_store.areas.main_room.spots.spot_1.items":     │
│      {"$remove": {"instance_id": "dream_bottle_woander_1"}}}                 │
│  3. Convert to v0.4 array format via _format_world_update_changes():        │
│     [{"operation": "remove", "area_id": "main_room",                         │
│       "instance_id": "dream_bottle_woander_1"}]                              │
│  4. Create WorldUpdateEvent                                                  │
│  5. Publish to NATS subject: world.updates.user.{user_id}                   │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              NATS                                              │
│  Subject: world.updates.user.a7f4370e-0af5-40eb-bb18-fcc10538b041            │
│  Message: WorldUpdateEvent JSON                                               │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
```

### NATS → WebSocket → Unity

```
┌──────────────────────────────────────────────────────────────────────────────┐
│        experience_connection_manager.py:_subscribe_to_nats()                  │
│                                                                               │
│  During connect():                                                           │
│  - Created subscription to world.updates.user.{user_id}                      │
│  - Handler: nats_event_handler() → websocket.send_json(event_data)          │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         WebSocket Response                                     │
│  {                                                                            │
│    "type": "world_update",                                                   │
│    "version": "0.4",                                                         │
│    "experience": "wylding-woods",                                            │
│    "user_id": "a7f4370e-0af5-40eb-bb18-fcc10538b041",                        │
│    "base_version": 29,                                                       │
│    "snapshot_version": 30,                                                   │
│    "changes": [                                                              │
│      {"operation": "remove", "area_id": "main_room",                         │
│       "instance_id": "dream_bottle_woander_1"}                               │
│    ],                                                                        │
│    "timestamp": 1732089600000                                                │
│  }                                                                           │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              UNITY CLIENT                                      │
│  WorldSyncManager:                                                            │
│  1. Receive world_update message                                             │
│  2. Check base_version == localVersion (29 == 29? ✓)                         │
│  3. Apply changes:                                                           │
│     - Find bottle in scene by instance_id                                    │
│     - Destroy/hide bottle GameObject                                         │
│     - Add to UI inventory                                                    │
│  4. Update localVersion = snapshot_version (30)                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key Files Involved

| File | Role |
|------|------|
| `websocket_experience.py:49-127` | WebSocket endpoint, auth, message loop |
| `command_processor.py:25-82` | Command routing |
| `handlers/collect_item.py` | Fast handler implementation |
| `unified_state_manager.py:599-686` | update_world_state() |
| `unified_state_manager.py:285-358` | _publish_world_update() |
| `experience_connection_manager.py:162-250` | NATS subscription and forwarding |
| `app/shared/events.py:11-145` | WorldUpdateEvent model |

---

## Scenario 2: User Talks to NPC (Louisa)

**Timeline:** 1-3 seconds (LLM-dependent)

### Request Flow (MVP Kludge)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              UNITY CLIENT                                      │
│  User taps NPC → Send WebSocket message                                       │
│  {"type": "action", "action": "talk", "npc_id": "louisa",                    │
│   "message": "Can you help me find the dream bottles?"}                      │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          KB SERVICE                                            │
│  command_processor.py → action="talk" registered to handle_talk()            │
│                                                                               │
│  ⚠️ MVP KLUDGE PATH: Makes HTTP call to Chat Service                         │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              handlers/talk.py:handle_talk()                                   │
│                                                                               │
│  1. Extract npc_id, player_message from command_data                         │
│  2. Build HTTP request to Chat Service:                                      │
│     POST {CHAT_SERVICE_URL}/chat/message                                     │
│     Body: {                                                                  │
│       "message": "Can you help me find the dream bottles?",                  │
│       "persona_id": "louisa",  ← HARDCODED                                   │
│       "context": {"experience": "wylding-woods", "npc_id": "louisa"}        │
│     }                                                                        │
│     Headers: X-API-Key for inter-service auth                                │
│  3. Timeout: 30 seconds (LLM can be slow)                                    │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼ HTTP
┌──────────────────────────────────────────────────────────────────────────────┐
│                          CHAT SERVICE                                          │
│  unified_chat.py:process() → Routes to persona handler                       │
│                                                                               │
│  1. Load "louisa" persona from database                                      │
│  2. Build system prompt with persona_prompt                                  │
│  3. Since persona_name="louisa", NO tools_section appended                   │
│     (fix from recent commit 8dbe2b2)                                         │
│  4. Call MultiProviderChatService → Claude API                               │
│  5. Return LLM response                                                      │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              handlers/talk.py (continued)                                     │
│                                                                               │
│  4. Parse Chat Service response                                              │
│  5. Return CommandResult:                                                    │
│     success: true                                                            │
│     message_to_player: "Of course! The dream bottles have scattered          │
│       throughout the shop. Look for glowing bottles on the shelves..."      │
│     metadata: {npc_id: "louisa", dialogue_source: "chat_service_..."}       │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         WebSocket Response                                     │
│  {                                                                            │
│    "type": "action_result",                                                  │
│    "success": true,                                                          │
│    "message": "Of course! The dream bottles have scattered...",              │
│    "request_id": "req_abc123"                                                │
│  }                                                                           │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              UNITY CLIENT                                      │
│  NPCDialogueManager:                                                          │
│  1. Display speech bubble over Louisa                                        │
│  2. Optional: TTS to speak dialogue                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Why This is a Kludge

```
CURRENT FLOW (MVP):
Unity → KB Service → HTTP → Chat Service → Claude → Chat Service → HTTP → KB Service → Unity
        [~10ms]      [~50ms]    [1-3s]                 [~50ms]

PROPER FLOW (Future):
Unity → KB Service → Claude → KB Service → Unity
        [~10ms]      [1-3s]     [~10ms]

Problems:
1. Two HTTP hops add ~100ms latency
2. Chat Service knows game mechanics (was filtering NPC tools there)
3. Hardcoded persona_id="louisa" - can't talk to other NPCs
4. Louisa persona definition tightly coupled to Chat Service database
```

### Key Files Involved

| File | Role |
|------|------|
| `handlers/talk.py` | MVP kludge - routes to Chat Service |
| `unified_chat.py:1792-1805` | System prompt building (no tools for NPCs) |
| `persona_service_postgres.py` | Louisa persona loaded from DB |
| `kb_tools.py:NPC_TOOLS` | Empty list (disabled game tools) |

---

## Scenario 3: Admin Edits Item

**Timeline:** <30ms (no LLM)

### Request Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              ADMIN CLIENT                                      │
│  Admin types: "@edit item dream_bottle_woander_1 visible false"              │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  WebSocket Message                                                            │
│  {"type": "action", "action": "@edit item dream_bottle_woander_1 visible f"} │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          KB SERVICE                                            │
│  command_processor.py:process_command()                                       │
│                                                                               │
│  action.startswith("@") → ADMIN PATH                                         │
│  → handlers/admin_command_router.py:route_admin_command()                    │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│         admin_command_router.py:route_admin_command()                         │
│                                                                               │
│  1. Parse: "@edit item dream_bottle_woander_1 visible false"                 │
│     command = "edit", parts = ["item", "dream_bottle...", "visible", "false"]│
│  2. Route to handle_admin_edit_item()                                        │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│         admin_edit_item.py:handle_admin_edit_item()                           │
│                                                                               │
│  1. Parse command parameters:                                                │
│     target_type = "item"                                                     │
│     target_id = "dream_bottle_woander_1"                                     │
│     field = "visible"                                                        │
│     value = false (parsed to boolean)                                        │
│                                                                               │
│  2. Load world state                                                         │
│  3. Find item by instance_id (recursive search)                              │
│  4. Validate field exists and value is valid type                            │
│  5. Build state update:                                                      │
│     {path_to_item: {"visible": false}}                                       │
│  6. Call state_manager.update_world_state()                                  │
│  7. Return CommandResult:                                                    │
│     success: true                                                            │
│     message: "✅ Updated item dream_bottle_woander_1.visible = false"        │
│     metadata: {changed_by: user_id, timestamp: ...}                          │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    State Persistence                                          │
│                                                                               │
│  world.json updated:                                                         │
│  {"locations": {"woander_store": {"areas": {"main_room": {"spots": {         │
│    "spot_1": {"items": [{"instance_id": "dream_bottle_woander_1",            │
│      "visible": false, ...}]}}}}}}                                           │
│                                                                               │
│  metadata._version incremented → WorldUpdateEvent published                  │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         WebSocket Response                                     │
│  {                                                                            │
│    "type": "action_result",                                                  │
│    "success": true,                                                          │
│    "message": "✅ Updated item dream_bottle_woander_1.visible = false"       │
│  }                                                                           │
│                                                                               │
│  + Separate world_update event to all subscribed clients                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Admin Command Design Principles

1. **@ Prefix**: Clearly distinguishes admin from player commands
2. **No LLM**: Fully deterministic, predictable responses
3. **Validation**: Type checking, existence checking before applying
4. **Audit Trail**: metadata includes changed_by and timestamp
5. **Broadcast**: All connected clients receive state update

### Key Files Involved

| File | Role |
|------|------|
| `command_processor.py:40-47` | Routes @ commands to admin router |
| `admin_command_router.py` | Parses and dispatches admin commands |
| `admin_edit_item.py` | Handles @edit item ... |
| `admin_examine.py` | Handles @examine ... |
| `admin_where.py` | Handles @where ... |
| `admin_reset_experience.py` | Handles @reset-experience CONFIRM |

---

## Version Tracking Detail

### Server-Authoritative Version Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          world.json                                          │
│  {                                                                          │
│    "metadata": {                                                            │
│      "_version": 30,           ← Increments on every change                 │
│      "last_modified": "..."                                                 │
│    },                                                                       │
│    "locations": {...}                                                       │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              ExperienceConnectionManager.connection_metadata                 │
│  {                                                                          │
│    "conn_abc123": {                                                         │
│      "user_id": "a7f4370e-...",                                             │
│      "snapshot_version": 28     ← Client's last known version               │
│    }                                                                        │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       WorldUpdateEvent                                       │
│  {                                                                          │
│    "base_version": 29,          ← Delta applies on this version            │
│    "snapshot_version": 30,      ← New version after applying               │
│    "changes": [...]                                                         │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Version Mismatch Handling

```
Unity receives world_update with base_version=29

IF localVersion == base_version (29 == 29):
  → Apply delta changes
  → Update localVersion = snapshot_version (30)

IF localVersion != base_version (28 != 29):
  → Version mismatch! Delta cannot be applied safely
  → Request fresh AOI snapshot via "aoi" action
  → Server sends full state with current version
```

---

## Data Flow Summary

| Scenario | Path | Duration | LLM? | State Changes? |
|----------|------|----------|------|----------------|
| Collect Bottle | Fast Handler | ~50ms | No | Yes |
| Talk to NPC | MVP Kludge (HTTP hop) | 1-3s | Yes | Optional |
| Admin Edit | Admin Router | <30ms | No | Yes |
| Look/Examine | LLM Path | 1-3s | Yes | No |
| Move/Go | Fast Handler | ~10ms | No | Yes |

---

## Recommendations Based on Flow Analysis

### High Priority

1. **Eliminate NPC double-hop**
   - Move LLM call into KB service
   - Use `MultiProviderChatService` directly
   - Saves ~100ms + reduces coupling

2. **Add transform editing to admin commands**
   - New command: `@edit spot spot_1 position.x 1.5`
   - Enable live world building

### Medium Priority

3. **Unify response format**
   - action_result and world_update have different structures
   - Consider consolidating for simpler Unity parsing

4. **Add command batching**
   - Allow multiple operations in single WebSocket message
   - Reduce round trips for complex operations

---

## Next: Phase 7 - Synthesis & Recommendations

Will provide:
- Architecture overview diagram
- Prioritized technical debt list
- Refactoring roadmap
- Experience SDK proposal
