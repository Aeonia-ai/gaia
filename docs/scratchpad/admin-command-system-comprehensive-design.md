# Admin Command System: Comprehensive Design & Gap Analysis

**Date**: 2025-11-13
**Status**: Design Phase - Awaiting Discussion
**Goal**: Enable admins to view and edit any parameter on any object in the experience

---

## Current State Analysis

### Existing Admin Commands (8 total)

#### Waypoint Management (5 commands)
- `@list-waypoints` - List all GPS waypoints with coordinates
- `@inspect-waypoint <id>` - View detailed waypoint properties
- `@edit-waypoint <id> <property> <value>` - Modify waypoint properties
- `@create-waypoint <name> at <lat> <lng>` - Create new waypoint
- `@delete-waypoint <id>` - Remove waypoint (assumed to exist)

**Object Properties Covered**: name, description, location (lat/lng), waypoint_type, media.audio, media.visual_fx, media.display_text, triggers

#### Item Management (2 commands)
- `@list-items` - List all items in experience
- `@inspect-item <id>` - View detailed item properties

**Object Properties Covered**: id, name, description, item_type, properties (collectible, consumable, hidden, weight), effects, lore, location, collection history

#### Experience Management (1 command)
- `@reset-experience [CONFIRM]` - Reset world to template state
  - Variants: `@reset world`, `@reset player <user_id>`
  - Creates backup before reset
  - Requires CONFIRM flag for safety

### Existing Game Commands (7 total)

Player-facing commands (non-admin):
- `inventory` - Show player's collected items
- `look [target]` - Observe surroundings or specific item
- `go <location>` - Move between locations/areas
- `talk <npc> [message]` - Converse with NPCs (LLM-powered dialogue)
- `collect <item>` - Pick up items from location
- `help` - Get command help
- `quests` - View quest status

---

## Gap Analysis: What's Missing

### 1. Item Editing (CRITICAL GAP)
**Missing Commands:**
- ❌ `@edit-item <id> <property> <value>` - Modify item properties
- ❌ `@create-item <name>` - Create new item
- ❌ `@delete-item <id>` - Remove item

**Impact**: Cannot edit item properties like collectible, visible, consumable, description, etc.

**User Need**: "I want to set one of the bottles visibility to off via curl"

### 2. Location/Area Management (CRITICAL GAP)
**Missing Commands:**
- ❌ `@list-locations` - List all locations in experience
- ❌ `@inspect-location <id>` - View location details and areas
- ❌ `@edit-location <id> <property> <value>` - Modify location properties
- ❌ `@list-areas <location_id>` - List areas within a location
- ❌ `@inspect-area <location_id>.<area_id>` - View area details
- ❌ `@edit-area <location_id>.<area_id> <property> <value>` - Modify area properties

**Impact**: Cannot edit location descriptions, area properties, or view spatial hierarchy

**User Need**: "be able to view information about the space I am in"

### 3. NPC Management (MAJOR GAP)
**Missing Commands:**
- ❌ `@list-npcs` - List all NPCs in experience
- ❌ `@inspect-npc <id>` - View NPC properties and state
- ❌ `@edit-npc <id> <property> <value>` - Modify NPC properties
- ❌ `@reset-npc <npc_id> [user_id]` - Reset NPC conversation history

**Impact**: Cannot edit NPC dialogue, trust levels, locations, or reset relationships

### 4. Quest Management (MAJOR GAP)
**Missing Commands:**
- ❌ `@list-quests` - List all quests in experience
- ❌ `@inspect-quest <id>` - View quest details
- ❌ `@give-quest <quest_id> to <user_id>` - Manually grant quest
- ❌ `@complete-quest <quest_id> for <user_id>` - Force quest completion

**Impact**: Cannot manually manage quest states for testing or debugging

### 5. Player State Management (USEFUL GAP)
**Missing Commands:**
- ❌ `@inspect-player <user_id>` - View player state (location, inventory, quests)
- ❌ `@teleport-player <user_id> to <location>` - Move player
- ❌ `@give-item <item_id> to <user_id>` - Add item to player inventory
- ❌ `@remove-item <item_id> from <user_id>` - Remove item from inventory

**Impact**: Cannot debug player state or manually fix stuck players

### 6. Current Location Context (USER-REQUESTED)
**Missing Commands:**
- ❌ `@where` or `@current-location` - Show admin's current location context
- ❌ `@here` - Inspect the location/area I'm currently in
- ❌ `@items-here` - List items in current location only

**Impact**: Cannot easily view "the space I am in" as admin

**User Need**: "be able to view information about the space I am in"

### 7. Visibility Toggle (USER-REQUESTED)
**Missing Commands:**
- ❌ `@toggle-visibility <item_id>` - Toggle item visible flag
- ❌ `@show-item <item_id>` - Make item visible
- ❌ `@hide-item <item_id>` - Make item hidden

**Impact**: Cannot control item visibility for quest spawning or debugging

**User Need**: "I want to set one of the bottles visibility to off"

---

## Architectural Patterns from Existing Commands

### 1. Command Structure Pattern

All admin commands follow YAML frontmatter format:
```yaml
---
command: @command-name
aliases: [@alias1, @alias2]
description: One-line description
requires_location: true/false
requires_target: true/false
requires_admin: true
state_model_support: [shared, isolated]
---
```

### 2. Response Format Pattern

Standardized JSON response:
```json
{
  "success": true/false,
  "narrative": "Human-readable response with markdown formatting",
  "available_actions": ["next action 1", "next action 2"],
  "state_updates": {
    "world": { /* nested updates */ },
    "player": { /* nested updates */ }
  },
  "metadata": {
    "command_type": "command-name",
    "admin_command": true,
    /* command-specific metadata */
  }
}
```

### 3. Property Editing Pattern

From `@edit-waypoint`:
- Format: `@edit <object-type> <id> <property> <value>`
- Supports nested properties with dot notation: `media.audio`, `location.lat`
- Shows before/after values in confirmation
- Creates backup before destructive operations

### 4. Safety Mechanisms

From `@reset-experience`:
- CONFIRM flag required for destructive operations
- Preview changes before execution
- Automatic backups with rotation (keep last 5)
- Audit logging of all admin actions

### 5. Natural Language Intent Detection

Commands support aliases and natural language:
- `@inspect item joyful_dream_bottle`
- `@show item joyful_dream_bottle`
- `@what is the joyful dream bottle`

All resolve to same handler via LLM intent detection.

---

## Proposed Design: Unified Parameter Editing

### Core Philosophy

**"Edit any parameter on any object"** - User's stated goal

Instead of creating separate `@edit-*` commands for every object type, use a **unified parameter editing system** with consistent patterns.

### Design Option A: Type-Specific Edit Commands (Current Pattern)

**Pros:**
- ✅ Consistent with existing waypoint pattern
- ✅ Type-specific validation (lat/lng for waypoints, trust for NPCs)
- ✅ Clear command names (`@edit-item`, `@edit-location`)

**Cons:**
- ❌ Requires creating ~15+ new command files
- ❌ Code duplication across edit handlers
- ❌ Hard to add new object types

**Commands Needed:**
```bash
@edit-item <id> <property> <value>
@edit-location <id> <property> <value>
@edit-area <location>.<area> <property> <value>
@edit-npc <id> <property> <value>
@edit-quest <id> <property> <value>
```

### Design Option B: Universal @edit Command (NEW PATTERN)

**Pros:**
- ✅ Single command learns all object types
- ✅ Minimal markdown files needed
- ✅ Easy to extend to new object types
- ✅ Powerful dot-notation for deep nesting

**Cons:**
- ❌ Requires smart LLM intent detection
- ❌ May be harder to validate type-specific constraints
- ❌ Single point of failure

**Universal Command:**
```bash
# Syntax: @edit <object-type> <id> <property> <value>

@edit item bottle_joy visible true
@edit item bottle_joy state.glowing false
@edit location woander_store description "A mystical shop..."
@edit npc louisa trust_level 85
@edit waypoint 4 location.lat 37.9057
@edit area woander_store.counter description "The main counter..."

# Shorthand when object type is obvious:
@edit bottle_joy visible true  # Infers type=item
```

### Design Option C: Hybrid Approach (RECOMMENDED)

Combine both patterns:
- Keep existing type-specific commands (`@edit-waypoint`, `@edit-item`)
- Add universal `@edit` as power-user shortcut
- Universal command delegates to type-specific validators

**Pros:**
- ✅ Best of both worlds
- ✅ Backwards compatible
- ✅ Gradual migration path
- ✅ Type-specific safety + universal power

**Example:**
```bash
# Both work:
@edit-item bottle_joy visible true
@edit item bottle_joy visible true

# Universal command resolves to @edit-item handler internally
```

---

## Recommended Implementation Plan

### Phase 1: Fill Critical Gaps (2-3 weeks)

**Priority 1: Item Editing**
```bash
@edit-item <id> <property> <value>
@create-item <name> [properties...]
@delete-item <id> CONFIRM
@toggle-visibility <item_id>  # Alias for @edit-item <id> visible true/false
```

**Priority 2: Location/Area Inspection**
```bash
@list-locations
@inspect-location <id>
@list-areas <location_id>
@inspect-area <location>.<area>
@where  # Show admin's current location context
@here   # Inspect current location/area
```

**Priority 3: Location/Area Editing**
```bash
@edit-location <id> <property> <value>
@edit-area <location>.<area> <property> <value>
```

### Phase 2: NPC & Quest Management (2-3 weeks)

```bash
@list-npcs
@inspect-npc <id> [user_id]  # View NPC state for specific player
@edit-npc <id> <property> <value>  # Edit template properties
@reset-npc <npc_id> [user_id]  # Reset conversation history

@list-quests
@inspect-quest <id> [user_id]  # View quest state for player
@give-quest <quest_id> to <user_id>
@complete-quest <quest_id> for <user_id>
```

### Phase 3: Player State Tools (1-2 weeks)

```bash
@inspect-player <user_id>  # Full player state dump
@teleport-player <user_id> to <location>
@give-item <item_id> to <user_id>` - Add item to player inventory
@remove-item <item_id> from <user_id>
```

### Phase 4: Universal @edit Command (1 week)

Implement universal `@edit` command that delegates to type-specific handlers:
```python
async def handle_universal_edit(command_data):
    object_type = command_data["object_type"]  # item, npc, location, etc.

    # Delegate to specific handler
    handlers = {
        "item": handle_edit_item,
        "npc": handle_edit_npc,
        "location": handle_edit_location,
        "waypoint": handle_edit_waypoint
    }

    return await handlers[object_type](command_data)
```

---

## Property Editing Deep Dive

### Nested Property Updates

**Challenge**: world.json has deep nesting:
```json
{
  "locations": {
    "woander_store": {
      "areas": {
        "spawn_zone_1": {
          "items": [
            {
              "instance_id": "bottle_mystery",
              "visible": false,  // Want to edit THIS
              "state": {
                "glowing": true  // Or THIS
              }
            }
          ]
        }
      }
    }
  }
}
```

**Solution**: Dot-notation property paths
```bash
@edit item bottle_mystery visible true
# Resolves to: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery].visible

@edit item bottle_mystery state.glowing false
# Resolves to: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery].state.glowing
```

**Implementation Pattern** (from `collect_item.py`):
```python
async def update_item_property(
    experience_id: str,
    item_id: str,
    property_path: str,
    new_value: Any
) -> None:
    """Update item property using dot-notation path."""

    # 1. Find item location in world state
    location_path = await find_item_location(experience_id, item_id)
    # Returns: "locations.woander_store.areas.spawn_zone_1.items"

    # 2. Build full property path
    full_path = f"{location_path}.{property_path}"
    # Example: "locations.woander_store.areas.spawn_zone_1.items.visible"

    # 3. Use UnifiedStateManager's $update operator
    updates = {
        "locations": {
            "woander_store": {
                "areas": {
                    "spawn_zone_1": {
                        "items": {
                            "$update": [{
                                "instance_id": item_id,
                                property_path: new_value
                            }]
                        }
                    }
                }
            }
        }
    }

    await state_manager.update_world_state(
        experience=experience_id,
        updates=updates
    )
```

### Validation by Object Type

Each object type has specific validation rules:

**Items:**
- `visible`: boolean
- `collectible`: boolean
- `consumable`: boolean
- `weight`: float >= 0
- `state.*`: any valid JSON value

**Waypoints:**
- `location.lat`: -90 to 90
- `location.lng`: -180 to 180
- `waypoint_type`: enum (gps, proximity, interaction)
- `media.audio`: filename validation (file exists)

**NPCs:**
- `trust_level`: 0 to 100
- `location`: valid location ID
- `dialogue.*`: any string
- `state.*`: any valid JSON value

**Locations:**
- `description`: string
- `visited`: boolean
- `areas.*`: object with area properties

### Before/After Confirmation Pattern

From `@edit-waypoint`, always show what changed:
```
✅ Updated item: Bottle of Mystery

Property: visible
Old value: false
New value: true

The item is now visible to players.
```

---

## Current Location Context Commands

**User Need**: "be able to view information about the space I am in"

### @where - Show Admin Location

Get admin's current location context from their player view:
```bash
@where
```

**Output:**
```
📍 Current Location: Woander's Magical Shop (woander_store)

Area: spawn_zone_1 (Display Shelf Area)
Description: A shelf displaying various magical curiosities and glowing bottles.

Items here:
- Bottle of Mystery (bottle_mystery) - visible: true, collectible: true

NPCs here:
- None

Nearby areas:
- entrance (Store Entrance)
- counter (Shop Counter) - NPC: Woander
- spawn_zone_2 (Window Display)
```

### @here - Inspect Current Location

Detailed inspection of current location:
```bash
@here
```

Equivalent to: `@inspect-location <current_location>`

### @items-here - List Items in Current Area

Quick view of items in current area only:
```bash
@items-here
```

**Output:**
```
🎁 Items in spawn_zone_1 (Display Shelf Area):

1. Bottle of Mystery (bottle_mystery)
   - Type: dream_bottle
   - Visible: true
   - Collectible: true
   - State: glowing=true, dream_type=mystery, symbol=spiral

Actions:
- @edit item bottle_mystery visible false
- @inspect item bottle_mystery
```

---

## Safety & Permissions

### Admin Command Safety Checklist

From `@reset-experience` and other commands:

1. **CONFIRM flag for destructive operations**
   - Delete commands: `@delete-item <id> CONFIRM`
   - Reset commands: `@reset-experience CONFIRM`
   - Bulk operations: `@delete-all-items CONFIRM`

2. **Automatic backups before state changes**
   - world.json backup before any edit
   - Rotation: Keep last 5 backups
   - Timestamped: `world.20251113_143522.backup.json`

3. **Before/after preview**
   - Show current value
   - Show new value
   - Confirm changes applied

4. **Audit logging**
   ```python
   logger.info(f"[AUDIT] Admin {user_id} edited item {item_id}")
   logger.info(f"[AUDIT] Property: {property}, Old: {old_value}, New: {new_value}")
   ```

5. **Permission checking** (placeholder for now)
   - Check `requires_admin: true` in command frontmatter
   - Future: RBAC with admin roles

### Rollback Support

From `@edit-waypoint` pattern:
```python
# Before editing, create backup
backup_file = f"{item_file}.backup.{timestamp}"
shutil.copy2(item_file, backup_file)

# Keep last 5 backups per object
backups = sorted(glob.glob(f"{item_file}.backup.*"), reverse=True)
for old_backup in backups[5:]:
    os.remove(old_backup)
```

Allow manual rollback:
```bash
@rollback item bottle_mystery to <timestamp>
```

---

## Implementation Checklist

### Immediate Needs (This Week)
- [ ] `@edit-item <id> <property> <value>` - Edit any item property
- [ ] `@toggle-visibility <item_id>` - Quick visibility toggle
- [ ] `@where` - Show current location context
- [ ] `@here` - Inspect current location

### Phase 1 (Next 2-3 Weeks)
- [ ] `@list-locations` - List all locations
- [ ] `@inspect-location <id>` - View location details
- [ ] `@edit-location <id> <property> <value>` - Edit location
- [ ] `@list-areas <location>` - List areas in location
- [ ] `@inspect-area <location>.<area>` - View area details
- [ ] `@edit-area <location>.<area> <property> <value>` - Edit area
- [ ] `@create-item <name>` - Create new item
- [ ] `@delete-item <id> CONFIRM` - Delete item

### Phase 2 (Future)
- [ ] `@list-npcs` - List all NPCs
- [ ] `@inspect-npc <id>` - View NPC template
- [ ] `@edit-npc <id> <property> <value>` - Edit NPC properties
- [ ] `@reset-npc <npc_id> [user_id]` - Reset NPC relationship
- [ ] `@list-quests` - List all quests
- [ ] `@inspect-quest <id>` - View quest details
- [ ] Universal `@edit` command with type inference

---

## Open Questions for Discussion

1. **Unified vs Type-Specific Commands?**
   - Should we implement universal `@edit` or stick with `@edit-item`, `@edit-npc`, etc.?
   - Recommendation: Hybrid (both work, universal delegates to type-specific)

2. **Property Validation Strictness?**
   - Should `@edit item bottle_mystery foo bar` fail (unknown property)?
   - Or allow arbitrary properties for flexibility?
   - Recommendation: Warn but allow (enable custom properties)

3. **Nested Property Syntax?**
   - `@edit item bottle_mystery state.glowing false` (dot notation)
   - Or `@edit item bottle_mystery state glowing false` (space-separated)
   - Recommendation: Dot notation (standard JSON path syntax)

4. **Current Location Tracking?**
   - Should admin have persistent location state?
   - Or always require explicit location/area specification?
   - Recommendation: Track admin location, but allow overrides

5. **Permission System Timeline?**
   - When should we implement real RBAC?
   - Currently all admin commands use placeholder permission checks
   - Recommendation: Phase 3 (after core commands working)

---

## Summary

**Current State:**
- 8 admin commands (5 waypoint, 2 item, 1 reset)
- 7 game commands (player-facing)
- Strong waypoint management, weak item/location/NPC management

**Critical Gaps:**
- ❌ Cannot edit item properties (especially visibility)
- ❌ Cannot view/edit location or area properties
- ❌ Cannot inspect "the space I am in" as admin
- ❌ No NPC or quest management commands

**Recommended Approach:**
- **Phase 1**: Item editing + location inspection (user's immediate needs)
- **Phase 2**: NPC/quest management
- **Phase 3**: Player state tools + universal @edit command
- **Pattern**: Hybrid type-specific + universal commands

**Next Steps:**
1. Discuss and validate design approach
2. Prioritize commands based on user needs
3. Implement `@edit-item` and `@toggle-visibility` first
4. Add location context commands (`@where`, `@here`)

---

## Smarter Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document's claims were verified using a multi-modal strategy including static code analysis and simulated dynamic analysis (identifying specific code paths, handlers, and test locations).

### **Summary:**

The document provides a solid conceptual blueprint for the admin command system. The core architectural patterns (YAML-driven commands, standardized responses, NLP-based intent detection) are **verified** in the codebase. However, there is a significant and consistent discrepancy between the command syntax proposed in the design (`@verb-noun`) and the syntax implemented in the code (`@verb noun`). Furthermore, several safety features and game commands exist only as design concepts and are not yet implemented.

---

### **Detailed Claim Verification:**

#### **Current State Analysis (Claims 1-15)**

-   **Admin Commands (Claims 1.1-1.8):** **Partially Verified**
    -   **Evidence (Static):** Functionality for `list`, `inspect`, `edit`, `create`, `delete`, and `reset` is confirmed in `app/services/kb/kb_agent.py` and `app/services/kb/handlers/`.
    -   **Discrepancy:** The command syntax is inconsistent. The document proposes a hyphenated style (e.g., `@list-waypoints`), but the implementation uses a space-separated style (e.g., the `_admin_list` function handles `@list waypoints`). This applies to all listed admin commands.

-   **Game Commands (Claims 2.1-2.7):** **Partially Verified**
    -   **Evidence (Static):** Handlers for `inventory`, `look`, `go`, `talk`, and `collect` are present in `app/services/kb/handlers/` and registered in `app/services/kb/main.py`.
    -   **Discrepancy:** No handlers or explicit logic for `help` or `quests` commands were found. These appear to be unimplemented design concepts.

#### **Architectural Patterns (Claims 16-20)**

-   **Claim 3.1: YAML Frontmatter for Commands:** **Verified**
    -   **Evidence (Static):** The method `_discover_available_commands` in `app/services/kb/kb_agent.py` directly implements reading `.md` files and parsing their YAML frontmatter to define command aliases and properties.

-   **Claim 3.2: Standardized JSON Response:** **Verified**
    -   **Evidence (Static):** The `CommandResult` model in `app/shared/models/command_result.py` and its usage in all handlers (e.g., `handle_admin_edit_item`, `_execute_admin_command`) confirm a standardized response structure (`success`, `message_to_player`, `state_changes`, etc.).

-   **Claim 3.3: Nested Property Editing:** **Verified**
    -   **Evidence (Static):** The handler `app/services/kb/handlers/admin_edit_item.py` contains the functions `_resolve_nested_property` and `_build_nested_update`, which explicitly implement dot-notation path resolution for editing nested JSON properties.
    -   **Evidence (Dynamic/Simulated):** A unit test for `handle_admin_edit_item` should be created to confirm that a command like `@edit item bottle_mystery state.glowing false` successfully modifies the nested property.

-   **Claim 3.4: Safety Mechanisms:** **Partially Verified**
    -   **Evidence (Static):** The `CONFIRM` flag is checked in the `_admin_delete` and `_admin_reset` methods in `app/services/kb/kb_agent.py`.
    -   **Discrepancy:** No evidence of automatic backups (e.g., `shutil.copy`) or explicit audit logging (e.g., `logger.info("[AUDIT]")`) was found in the relevant command handlers. These features are unimplemented.

-   **Claim 3.5: Natural Language Intent Detection:** **Verified**
    -   **Evidence (Static):** The `_detect_command_type` method in `app/services/kb/kb_agent.py` constructs a prompt with command mappings and uses an LLM to resolve the user's message to a canonical command name.

### **Recommendations:**

1.  **Update Document:** The "Current State Analysis" should be updated to reflect the implemented space-separated command syntax (e.g., change `@list-waypoints` to `@list waypoints`).
2.  **Implement Missing Features:** The gaps identified (e.g., `help`/`quests` commands, backup/audit safety mechanisms) should be prioritized for future implementation.
3.  **Add Dynamic Verification:** Create a dedicated integration test file, such as `tests/integration/test_admin_commands.py`, to dynamically validate the behavior of each command against the claims in this document.

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document outlines a design for the admin command system. The verification focuses on comparing the "Current State Analysis" and "Architectural Patterns" sections against the existing codebase.

### Current State Analysis

-   **Existing Admin Commands:**
    *   **Claim:** `@list-waypoints`, `@inspect-waypoint <id>`, `@edit-waypoint <id> <property> <value>`, `@create-waypoint <name> at <lat> <lng>`, `@delete-waypoint <id>`, `@list-items`, `@inspect-item <id>`, `@reset-experience [CONFIRM]`.
    *   **Verification:** **PARTIALLY VERIFIED**. The functionality for listing, inspecting, editing, creating, and deleting waypoints/locations/sublocations, items, and resetting experiences exists in `app/services/kb/kb_agent.py`. However, the command names and syntax in the code differ from the document's descriptions. For example, the code uses `@list waypoints` instead of `@list-waypoints`, and `@edit waypoint <id> <field> <value>` instead of `@edit-waypoint <id> <property> <value>`. The `CONFIRM` flag is consistently required for destructive operations in the code, which is only optionally mentioned in the document for `@reset-experience`.

-   **Existing Game Commands:**
    *   **Claim:** `inventory`, `look [target]`, `go <location>`, `talk <npc> [message]`, `collect <item>`, `help`, `quests`.
    *   **Verification:** **PARTIALLY VERIFIED**. `inventory`, `look`, `go`, `talk`, and `collect` commands are handled in `app/services/kb/kb_agent.py` or have dedicated handlers in `app/services/kb/handlers/`. However, direct evidence for `help` and `quests` commands was not found in the codebase.

### Architectural Patterns

-   **Command Structure Pattern (YAML frontmatter):**
    *   **Claim:** All admin commands follow YAML frontmatter format.
    *   **Verification:** **VERIFIED**. The `_discover_available_commands` method in `app/services/kb/kb_agent.py` (lines 900-950) actively reads and parses YAML frontmatter from markdown files to define commands and their properties.

-   **Response Format Pattern (Standardized JSON response):**
    *   **Claim:** Standardized JSON response with `success`, `narrative`, `available_actions`, `state_updates`, `metadata`.
    *   **Verification:** **VERIFIED**. The `_execute_markdown_command`, `_execute_admin_command`, and `_execute_game_command_legacy_hardcoded` methods in `app/services/kb/kb_agent.py` return dictionaries with a consistent structure, including these fields.

-   **Property Editing Pattern:**
    *   **Claim:** Format: `@edit <object-type> <id> <property> <value>`. Supports nested properties with dot notation (e.g., `media.audio`, `location.lat`).
    *   **Verification:** **PARTIALLY VERIFIED**. The `@edit` command exists and supports editing properties for `waypoint`, `location`, and `sublocation` objects. However, the current implementation in `_admin_edit` (in `app/services/kb/kb_agent.py`) does not appear to directly support dot-notation for *nested* properties as described in the document's examples. It primarily handles top-level fields.

-   **Safety Mechanisms:**
    *   **Claim:** `CONFIRM` flag for destructive operations, automatic backups with rotation, before/after preview, audit logging.
    *   **Verification:** **PARTIALLY VERIFIED**. The `CONFIRM` flag is indeed used for destructive operations (`@delete`, `@reset`). However, automatic backups with rotation and explicit audit logging (`[AUDIT]`) are *not* implemented in `app/services/kb/kb_agent.py`. The `_save_locations_atomic` method ensures atomic writes but not backups.

-   **Natural Language Intent Detection:**
    *   **Claim:** Commands support aliases and natural language, resolving to the same handler via LLM intent detection.
    *   **Verification:** **VERIFIED**. The `_detect_command_type` method in `app/services/kb/kb_agent.py` uses an LLM to map natural language messages to command types, and `_discover_available_commands` loads aliases from markdown frontmatter.

**Overall Conclusion:** This design document provides a valuable blueprint for the admin command system. While many core concepts and functionalities are implemented, there are notable discrepancies in command naming conventions, the full extent of property editing capabilities, and the implementation of all proposed safety mechanisms (specifically backups and audit logging). Some game commands mentioned in the document were also not explicitly found in the current codebase. The document should be updated to reflect the current implementation details and the actual command syntax.