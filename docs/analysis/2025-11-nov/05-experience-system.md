# Phase 5: Experience System Deep Dive

**Analysis Date:** 2025-11-20

---

## Executive Summary

The GAIA Experience System implements a **data-driven game engine** where game logic is defined in markdown files, state is stored in JSON, and Python handlers execute deterministic operations. The architecture supports both **fast handlers** (<10ms for deterministic actions) and **LLM-interpreted commands** (1-3s for creative/narrative responses). The system uses a **zone > area > spot > items** hierarchy for world state.

---

## World State Model

### Hierarchy Structure

```
World State (world.json)
├── metadata
│   ├── version: "1.1.0"
│   ├── _version: 30 (incremental for delta sync)
│   └── last_modified: ISO timestamp
│
└── locations (zones)
    └── woander_store
        ├── id, name, description
        └── areas
            └── main_room
                ├── id, name, description
                └── spots
                    ├── spot_1 { items: [...] }
                    ├── spot_2 { items: [...] }
                    ├── fairy_door { npc: "louisa" }
                    └── counter { npc: "woander" }
```

### Key Properties

| Level | Purpose | Contains |
|-------|---------|----------|
| **Zone** (`locations`) | GPS-based location | Areas, NPCs, metadata |
| **Area** (`areas`) | Logical subdivision | Spots, area-level items |
| **Spot** (`spots`) | Physical position (AR anchor) | Items, NPC reference |
| **Item** | Collectible/interactive object | State, template_id, instance_id |

### Item Structure

```json
{
  "instance_id": "dream_bottle_clearing_1",
  "template_id": "dream_bottle",
  "semantic_name": "dream bottle",
  "description": "A glowing bottle containing swirling dreams",
  "type": "collectible",
  "collectible": true,
  "visible": true,
  "state": {
    "glowing": true,
    "dream_type": "peaceful"
  }
}
```

**Template-Instance Pattern:** Items reference templates (blueprints) via `template_id` and have unique `instance_id` for tracking. The `TemplateLoader` merges template properties with instance overrides at runtime.

---

## Command System Architecture

### Three Command Paths

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ExperienceCommandProcessor                        │
│                       (command_processor.py)                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Admin Commands  │    │  Fast Handlers   │    │   LLM Path      │
│   (@ prefix)    │    │ (Python, <10ms) │    │  (1-3 seconds)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
  route_admin_command    Registered handlers     kb_agent.process_llm_command
  - @examine             - collect_item          - Reads markdown
  - @where               - drop_item             - Calls Claude
  - @edit                - examine               - Parses response
  - @reset               - inventory             - Returns CommandResult
                         - give_item
                         - use_item
                         - go
                         - talk (MVP kludge)
```

### Command Routing Logic

```python
# command_processor.py:25-82
async def process_command(user_id, experience_id, command_data, connection_id):
    action = command_data.get("action")

    # Path 1: Admin Commands (@ prefix)
    if action.startswith("@"):
        from .handlers.admin_command_router import route_admin_command
        return await route_admin_command(user_id, experience_id, command_data)

    # Path 2: Fast Handlers (registered Python functions)
    handler = self._handlers.get(action)
    if handler:
        return await handler(user_id, experience_id, command_data, connection_id)

    # Path 3: LLM Path (markdown-driven, slow but flexible)
    return await kb_agent.process_llm_command(user_id, experience_id, command_data)
```

### Response Time Comparison

| Path | Response Time | Use Case |
|------|---------------|----------|
| Admin Commands | <30ms | World building, debugging |
| Fast Handlers | <10ms | Deterministic game actions |
| LLM Path | 1-3 seconds | Creative/narrative responses |

---

## Admin Command System

### Design Principles

1. **@ Prefix**: All admin commands start with `@` (e.g., `@examine`, `@reset`)
2. **Zero LLM**: Deterministic responses, no AI involvement
3. **CONFIRM Pattern**: Destructive operations require explicit confirmation
4. **Metadata Tracking**: Created_by, last_modified timestamps

### Available Commands

| Command | Purpose | Handler |
|---------|---------|---------|
| `@examine [type] [id]` | Inspect world state | `admin_examine.py` |
| `@where [type] [name]` | Find objects in world | `admin_where.py` |
| `@edit [type] [id] [field] [value]` | Modify object properties | `admin_edit_item.py` |
| `@reset-experience [CONFIRM]` | Reset world to template | `admin_reset_experience.py` |

### Markdown-Driven Admin Logic

Located at: `experiences/{exp}/admin-logic/`

```
admin-logic/
├── @create-waypoint.md
├── @delete-waypoint.md
├── @edit-item.md
├── @edit-waypoint.md
├── @examine.md
├── @inspect-item.md
├── @inspect-waypoint.md
├── @list-items.md
├── @list-waypoints.md
├── @reset-experience.md
└── @where.md
```

These markdown files define command syntax, validation rules, and response formats.

---

## Fast Handler Pattern

### Handler Interface

```python
async def handle_[action](
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any],
    connection_id: Optional[str] = None
) -> CommandResult
```

### Handler Registration

```python
# In kb/main.py or dedicated registration
from .handlers.collect_item import handle_collect_item
command_processor.register("collect_item", handle_collect_item)
command_processor.register("collect", handle_collect_item)  # alias
```

### collect_item.py Analysis

**Key Pattern: Nested Dict Updates with `$remove` Operation**

```python
# collect_item.py:356-377
def _build_nested_remove(item_path, instance_id, location_id, area_id, spot_id):
    """Build nested dict for removing item from world state."""
    remove_op = {"$remove": {"instance_id": instance_id}}

    if spot_id:
        # NEW HIERARCHY: zone > area > spot > items
        return {
            "locations": {
                location_id: {
                    "areas": {
                        area_id: {
                            "spots": {
                                spot_id: {
                                    "items": remove_op
                                }
                            }
                        }
                    }
                }
            }
        }
```

**Dual Update Flow:**
1. Remove from world state (publishes delta: version N → N+1)
2. Add to player inventory (publishes delta: version N+1 → N+2)

---

## Player vs World State

### Two-File Model

| File | Path | Purpose |
|------|------|---------|
| World State | `experiences/{exp}/state/world.json` | Shared world (multiplayer) |
| Player View | `players/{user}/{exp}/view.json` | Per-player data (inventory, quests) |

### Player View Structure

```json
{
  "player": {
    "user_id": "user_123",
    "current_location": "woander_store",
    "current_area": "main_room",
    "inventory": [...],
    "quests": {
      "bottle_quest": {
        "status": "active",
        "progress": {"bottles_collected": 2, "bottles_required": 4}
      }
    }
  }
}
```

### State Model Types

| Model | World State | Player Collisions | Use Case |
|-------|-------------|-------------------|----------|
| **Shared** | Single file, locking | Yes (race conditions) | Multiplayer |
| **Isolated** | Copy per player | No | Single-player |

---

## NPC Integration

### Current Architecture (MVP Kludge)

```
Unity → WebSocket → KB Service (talk handler)
                          ↓
                    HTTP call to Chat Service
                          ↓
                    Chat uses Louisa persona
                          ↓
                    Chat calls KB tools (HTTP)
                          ↓
Unity ← WebSocket ← KB wraps response
```

**Problems:**
- Double HTTP hop (KB → Chat → KB)
- Chat service knows game mechanics (bottles, quests)
- Hardcoded persona ID ("louisa")

### NPC Definition in World State

```json
{
  "spots": {
    "fairy_door": {
      "id": "fairy_door",
      "name": "Main Fairy Door",
      "npc": "louisa"  // NPC reference
    }
  }
}
```

### Future Architecture (Proposed)

```
Unity → WebSocket → KB Service
                          ↓
                    KB calls MultiProviderChatService directly
                    (NPC templates in KB markdown)
                          ↓
Unity ← WebSocket ← KB returns response
```

---

## Quest System Design

### Quest State Structure (from `player.quests`)

```json
{
  "bottle_quest": {
    "status": "active",
    "offered_by": "louisa",
    "offered_at": "2025-10-28T10:00:00Z",
    "accepted_at": "2025-10-28T10:05:00Z",
    "objectives": [
      {
        "id": "find_bottles",
        "description": "Find dream bottles in the shop",
        "completed": true
      },
      {
        "id": "return_bottles",
        "description": "Return bottles to fairy houses",
        "completed": false,
        "progress": {"current": 2, "required": 4}
      }
    ],
    "rewards": {
      "trust": {"louisa": 10}
    }
  }
}
```

### Quest Lifecycle

```
offered → active → completed
                 ↘ failed
```

### Markdown-Driven Quest Logic

Located at: `experiences/{exp}/game-logic/quests.md`

Defines:
- Quest list command handling
- Status grouping (offered, active, completed, failed)
- Progress display formatting
- Narrative generation rules

---

## Experience Configuration

### config.json Structure

```json
{
  "id": "wylding-woods",
  "name": "The Wylding Woods",
  "version": "1.0.0",
  "state": {
    "model": "shared",
    "coordination": {
      "locking_enabled": true,
      "lock_timeout_ms": 5000,
      "optimistic_versioning": true
    }
  },
  "multiplayer": {
    "enabled": true,
    "shared_entities": true,
    "entity_ownership": "first_interaction"
  },
  "capabilities": {
    "gps_based": true,
    "ar_enabled": true,
    "inventory_system": true,
    "quest_system": true,
    "combat_system": false
  }
}
```

### Capability Flags

| Flag | Purpose |
|------|---------|
| `gps_based` | Require GPS for location validation |
| `ar_enabled` | AR features available |
| `inventory_system` | Enable collect/drop/use commands |
| `quest_system` | Enable quest tracking |
| `combat_system` | Enable combat mechanics (future) |

---

## Real-Time State Sync

### Version Tracking for Delta Sync

**Server-Authoritative Pattern:**
- `world.metadata._version`: Increments on every change
- Client tracks last-known version
- Delta contains changes between versions

### NATS Publishing Flow

```python
# unified_state_manager.py:668-676
await self._publish_world_update(
    experience=experience,
    user_id=user_id,
    changes=updates,
    base_version=base_version,      # Client's last version
    snapshot_version=snapshot_version  # New version
)
```

### WebSocket → Unity Flow

```
State Change
    ↓
update_world_state()
    ↓
_publish_world_update() → NATS
    ↓
WebSocket connection → Unity
    ↓
Unity applies delta if base_version matches
```

---

## Architectural Strengths

1. **Data-Driven Design**: Game logic in markdown, easily editable
2. **Fast Path Optimization**: Sub-10ms for common actions
3. **Template-Instance Pattern**: Reusable item templates
4. **Version-Based Delta Sync**: Efficient state updates
5. **Shared/Isolated Flexibility**: Supports both multiplayer and single-player

---

## Architectural Weaknesses

1. **NPC Double-Hop**: KB → Chat → KB adds latency and coupling
2. **Hardcoded Values**: Persona IDs, quest IDs in code
3. **God Class (kb_agent.py)**: 3,932 lines, needs decomposition
4. **No Markdown Execution**: game-logic/*.md only used by LLM path
5. **Quest Logic in Chat**: Quest mechanics coupled to chat service tools

---

## Recommendations

### High Priority

1. **Move NPC dialogue to KB service**
   - Call `MultiProviderChatService` directly
   - Eliminate HTTP hop to chat service
   - Keep persona definitions in KB markdown

2. **Data-drive hardcoded values**
   - Extract persona IDs to config
   - Quest IDs from world state
   - Experience names from bootstrap

### Medium Priority

3. **Implement markdown-driven fast handlers**
   - Parse game-logic/*.md for execution rules
   - Reduce LLM calls for known patterns

4. **Extract quest manager**
   - Move quest state operations to KB service
   - Remove quest tools from chat

### Low Priority

5. **Unify spot transforms**
   - Add transform data (position, rotation) to spots
   - Enable live editing from admin commands

---

## Next: Phase 6 - Data Flow Tracing

Will trace:
1. Unity collects bottle → state changes → delta → Unity update
2. User talks to NPC → chat service → response → Unity
3. Admin edits waypoint → state update → persistence
