# Command and Response Format Comparison

**Date:** 2025-11-07
**Purpose:** Compare WebSocket commands, CommandResult responses, and JSON-RPC directives
**Status:** Analysis & Architectural Documentation

---

## Overview

GAIA uses **three distinct command/response formats** for different purposes:

1. **Player Commands** (Client → Server) - Semantic actions the player wants to perform
2. **CommandResult** (Server → Client) - Structured outcome of player actions
3. **JSON-RPC Directives** (Embedded in narrative) - Client-side effects during streaming responses

---

## 1. Player Commands (Client → Server)

### WebSocket Format (Current Implementation)

**Location:** `app/services/kb/websocket_experience.py:203-247`

**Client Sends:**
```json
{
  "type": "action",
  "action": "collect_item",
  "item_id": "bottle_of_joy_1"
}
```

**Processing:**
- Received by WebSocket `handle_action()` function
- Passed to `command_processor.process_command(user_id, experience, message)`
- Routes to either fast-path Python handler OR flexible-path LLM logic

### HTTP Format (Current Implementation)

**Location:** `app/services/kb/experience_endpoints.py:88`

**Client Sends:**
```json
{
  "message": "collect the glowing bottle",
  "experience": "wylding-woods"
}
```

**Processing:**
- Natural language interpreted by LLM
- Converted to structured command internally
- Passed to same `command_processor.process_command()`

### Universal Action Vocabulary (Design Spec)

**Location:** `gaia-knowledge-base/shared/mmoirl-platform/commands/universal-actions.md`

**Semantic Format:**
```json
{
  "action": "collect",
  "target": "dream_bottle",
  "context": "woander_store"
}
```

**Purpose:**
- Platform-wide semantic vocabulary
- Works across AR, text, voice, menu interfaces
- Client translates input method → universal action → sends to server

**Status:** Specification exists, not yet enforced in current implementation

---

## 2. CommandResult (Server → Client Response)

### Internal Format (Python Object)

**Location:** `app/shared/models/command_result.py:6-15`

```python
class CommandResult(BaseModel):
    success: bool
    actions: Optional[List[Dict[str, Any]]]
    state_changes: Optional[Dict[str, Any]]
    message_to_player: Optional[str]
    metadata: Optional[Dict[str, Any]]
```

**Fields:**
- `success` - Did the command succeed?
- `actions` - **Structured client actions** (e.g., play_sound, trigger_vfx)
- `state_changes` - JSON describing world/player state modifications
- `message_to_player` - Narrative text for display
- `metadata` - Flexible additional data

### WebSocket Response Translation

**Location:** `app/services/kb/websocket_experience.py:237-247`

**Server Sends:**
```json
{
  "type": "action_response",
  "action": "collect_item",
  "success": true,
  "message": "You collected the Bottle of Joy!",
  "timestamp": 1699300000000,
  "metadata": {
    "bottles_collected": 1,
    "bottles_required": 7
  }
}
```

**Key Observation:**
- `CommandResult.actions` field is **not currently included** in WebSocket response
- Only `success`, `message_to_player`, and `metadata` are transmitted
- `state_changes` are applied server-side, not sent to client

### HTTP Response Translation

**Location:** `app/services/kb/experience_endpoints.py:88`

```json
{
  "success": true,
  "narrative": "You collected the Bottle of Joy!",
  "experience": "wylding-woods",
  "state_updates": {
    "player.inventory": {
      "$append": {"id": "bottle_of_joy_1", "type": "collectible"}
    }
  },
  "metadata": {
    "command_type": "collect",
    "total_commands": 7
  }
}
```

**Key Differences from WebSocket:**
- Includes `state_updates` (equivalent to `state_changes`)
- Uses `narrative` instead of `message`
- More verbose for debugging/development

---

## 3. JSON-RPC Directives (Embedded in Narrative)

### Format

**Location:** `app/services/streaming_buffer.py:40-41`

**Pattern:** `{"m":"method_name","p":{"param":"value"}}`

**Example in Context:**
```
"Take a deep breath... {"m":"pause","p":{"secs":3.0}} ...and exhale slowly."
```

**Client Receives (SSE Stream):**
```
data: {"type":"content","content":"Take a deep breath... "}
data: {"type":"content","content":"{\"m\":\"pause\",\"p\":{\"secs\":3.0}}"}
data: {"type":"content","content":" ...and exhale slowly."}
data: {"type":"done","finish_reason":"stop"}
```

### Purpose

**Use Case:** Client-side effects synchronized with narrative flow

**Examples:**
- `{"m":"pause","p":{"secs":2.0}}` - Pause TTS/animation for 2 seconds
- `{"m":"play_sound","p":{"sound":"fairy_chime"}}` - Audio cue (proposed)
- `{"m":"spawn_character","p":{"type":"fairy","pos":[0,0,0]}}` - AR spawn (test example)

**Current Status:**
- **Only `pause` directive is implemented**
- **Disabled for Louisa persona** (natural conversation only)
- **Infrastructure exists** for future expansion

### When Enabled

**Location:** `app/services/chat/unified_chat.py:1663-1680`

```python
def _is_directive_enhanced_context(self, context: dict) -> bool:
    if context.get("response_format") == "v0.3":
        return True  # v0.3 API always uses directives
    if context.get("directive_enhanced"):
        return True  # Explicit flag
    if context.get("priority") == "vr" or context.get("context_type") == "vr":
        return True  # VR/AR contexts
    return False
```

---

## 4. Symbolic Server Directives (NATS Architecture)

### Format

**Location:** `docs/scratchpad/simulation-architecture-overview.md:22`

**Example:**
```json
{
  "entity_id": "bottle_of_joy",
  "goal": "instantiate_at_spot",
  "spot_id": "ww_store.shelf_a.slot_3"
}
```

**Purpose:**
- High-level symbolic commands from GAIA to Unity
- Separates WHAT should happen (server) from HOW it appears (client)
- Enables platform-agnostic game logic

**Transmission:**
- Sent via NATS pub/sub (not WebSocket)
- Unity subscribes to `gaia.world.{experience_id}` topic
- Real-time world state synchronization

**Client Responsibility:**
- Translate symbolic directive to concrete physical action
- Use VPS/GPS/relative positioning strategies
- Validate against Spot Registry bounding volumes
- Execute rendering and physics

**Status:** Architectural design, coordination via Symphony "directives" room

---

## Comparison Matrix

| Feature | Player Commands | CommandResult | JSON-RPC Directives | Symbolic Directives |
|---------|----------------|---------------|---------------------|---------------------|
| **Direction** | Client → Server | Server → Client | LLM → Client (embedded) | Server → Client (NATS) |
| **Format** | `{"action":"collect","item_id":"..."}` | `CommandResult(success, actions, ...)` | `{"m":"pause","p":{"secs":2}}` | `{"entity_id","goal","spot_id"}` |
| **Purpose** | Player intent | Action outcome | Narrative effects | World state sync |
| **Transport** | WebSocket/HTTP | WebSocket/HTTP response | SSE stream (in text) | NATS pub/sub |
| **Processing** | Command processor | Generated by handlers | Generated by LLM | Generated by game logic |
| **When Used** | Every player action | Every command response | v0.3 streaming only | Multiplayer world updates |
| **Current Status** | ✅ Implemented | ✅ Implemented | ⚠️ Infrastructure only | 📋 Design phase |

---

## Key Architectural Insights

### 1. CommandResult.actions vs JSON-RPC Directives

**CommandResult.actions (Structured):**
```python
actions = [
    {"type": "play_sound", "sound_id": "fairy_chime"},
    {"type": "trigger_vfx", "effect": "sparkle", "duration": 2.0}
]
```

**JSON-RPC Directives (Embedded):**
```
"Look! {"m":"play_sound","p":{"sound":"fairy_chime"}} Isn't it beautiful?"
```

**Differences:**
- **CommandResult.actions**: Discrete, parallel client actions (do these things)
- **JSON-RPC Directives**: Sequentially embedded in narrative (do this at this moment in the story)

**Current Implementation Gap:**
- `CommandResult.actions` is **defined but not transmitted** in WebSocket responses
- Only JSON-RPC directives are currently used for client effects
- Opportunity to implement `actions` field in future

### 2. State Changes Flow

**Server-Side Application:**
```python
# Handler modifies state
state_changes = {
    "player.inventory": {"$append": {"id": "bottle_1"}}
}

# Applied immediately by state_manager
await state_manager.update_player_view(experience_id, user_id, state_changes)

# Included in CommandResult
return CommandResult(
    success=True,
    state_changes=state_changes,
    message_to_player="You collected the bottle!"
)
```

**Client-Side (WebSocket):**
- **Does NOT receive `state_changes`** directly in response
- Client must query player state separately OR
- Relies on NATS world_update events for state sync

**Client-Side (HTTP):**
- **DOES receive `state_updates`** in response
- Client can optimistically update local state
- More suitable for stateless/development clients

### 3. Three Layers of Client Commands

**Layer 1: Game Logic Commands (CommandResult)**
- What happened in the game (you collected an item, quest updated, etc.)
- Transmitted via WebSocket `action_response`
- Drives game state and UI updates

**Layer 2: Presentation Directives (JSON-RPC)**
- How to present the narrative (pause, sound, effects)
- Embedded in streaming text
- Enhances immersion and pacing

**Layer 3: World State Directives (NATS Symbolic)**
- What entities exist and where (spawn, move, despawn)
- Separate NATS channel
- Enables multiplayer synchronization

---

## Usage Patterns

### Single-Player Text Adventure (West of House)

**Player Command:**
```json
{"action": "examine", "target": "mailbox"}
```

**CommandResult:**
```json
{
  "success": true,
  "message_to_player": "The mailbox is small and made of brass...",
  "metadata": {"command_type": "examine"}
}
```

**No directives needed** - Pure text adventure

### AR Game with Narrative (Wylding Woods)

**Player Command:**
```json
{"action": "collect", "item_id": "bottle_of_joy_1"}
```

**CommandResult:**
```json
{
  "success": true,
  "actions": [
    {"type": "play_sound", "sound_id": "collect_chime"},
    {"type": "trigger_vfx", "effect": "sparkle_collect"}
  ],
  "state_changes": {
    "player.inventory": {"$append": {"id": "bottle_of_joy_1"}}
  },
  "message_to_player": "You collected the Bottle of Joy!"
}
```

**With JSON-RPC Directives (if enabled):**
```
"The bottle glows warmly as you pick it up... {"m":"pause","p":{"secs":1.5}}
...and you feel a surge of happiness!"
```

**NATS Symbolic Directive:**
```json
{
  "entity_id": "bottle_of_joy_1",
  "goal": "despawn",
  "reason": "collected_by_player"
}
```

### Multiplayer World Event

**Scenario:** Fairy appears for all players in area

**No player command** - Server-initiated event

**NATS Symbolic Directive:**
```json
{
  "entity_id": "louisa_npc",
  "goal": "instantiate_at_spot",
  "spot_id": "ww_clearing.center",
  "animation": "fairy_entrance"
}
```

**All connected clients receive and render**

---

## Future Design Considerations

### 1. Should CommandResult.actions be transmitted?

**Current:** Defined in model, not included in WebSocket response

**Option A: Include in WebSocket Response**
```json
{
  "type": "action_response",
  "success": true,
  "message": "...",
  "actions": [
    {"type": "play_sound", "sound_id": "collect_chime"}
  ]
}
```

**Pros:**
- Structured, predictable client effects
- Easier to implement deterministic behavior
- Debugging and testing simpler

**Cons:**
- Separate channel from narrative
- Can't time effects to narrative flow
- More rigid than embedded directives

**Option B: Keep Directives for Effects**

**Pros:**
- Perfect narrative timing
- More immersive (effects synchronized with story beats)
- Single SSE stream for everything

**Cons:**
- LLM must generate correct JSON
- Harder to test and debug
- Client must parse embedded JSON

**Recommendation:** Use **both**:
- `CommandResult.actions` for immediate, deterministic effects (collect item → play sound)
- JSON-RPC Directives for narrative-timed effects (pause during dramatic moment)

### 2. State Changes Transmission

**Current WebSocket:** State changes applied server-side, not sent to client

**Issue:** Client doesn't know what changed without separate query

**Solution Options:**

**A) Include state_changes in response:**
```json
{
  "type": "action_response",
  "success": true,
  "message": "...",
  "state_changes": {
    "player.inventory": {"$append": {"id": "bottle_1"}}
  }
}
```

**B) Use NATS events for state sync:**
```json
{
  "type": "state_update",
  "user_id": "player_123",
  "changes": {...}
}
```

**C) Require client to poll player state:**
```
Client sends: {"type":"get_player_state"}
Server responds: {"type":"player_state", "data":{...}}
```

**Current Approach:** Combination of B (for multiplayer) and implicit C (client maintains local state)

### 3. Universal Action Vocabulary Enforcement

**Current:** Semantic action vocabulary documented but not enforced

**Future:** Validate commands against universal vocabulary

```python
# In command_processor.py
VALID_ACTIONS = {
    "collect", "take", "grab", "pick_up",  # Item interaction
    "talk", "ask", "listen",                # NPC interaction
    "go", "move", "walk",                   # Navigation
    # ... etc
}

async def process_command(self, user_id, experience_id, command_data):
    action = command_data.get("action")

    # Validate action is in universal vocabulary
    if action not in VALID_ACTIONS:
        return CommandResult(
            success=False,
            message_to_player=f"Action '{action}' not recognized"
        )

    # Continue with normal processing...
```

---

## Summary

GAIA uses **four distinct command/response formats** serving different purposes:

1. **Player Commands** - Semantic actions (client → server)
2. **CommandResult** - Structured outcomes with optional client actions (server → client)
3. **JSON-RPC Directives** - Narrative-embedded effects (LLM → client via SSE)
4. **Symbolic Directives** - High-level world state commands (server → client via NATS)

**Current Implementation:**
- Player Commands: ✅ Full WebSocket + HTTP support
- CommandResult: ✅ Implemented, `actions` field unused in WebSocket
- JSON-RPC Directives: ⚠️ Infrastructure ready, disabled for natural conversation
- Symbolic Directives: 📋 Architectural design, Unity coordination in progress

**Key Insight:**
These are **complementary systems**, not competing formats. Each serves a specific layer of the client-server interaction model.

---

**Related Documentation:**
- [Command System Refactor Completion](command-system-refactor-completion.md)
- [Wylding Woods Knowledge Base Inventory](wylding-woods-knowledge-base-inventory.md)
- [Universal Action Vocabulary](../../Vaults/gaia-knowledge-base/shared/mmoirl-platform/commands/universal-actions.md)
- [Simulation Architecture Overview](simulation-architecture-overview.md)
