# Intelligent Admin Command System - Conceptual Design

**Date**: 2025-11-13
**Goal**: Enable natural workflow for viewing and editing any object property

---

## Core Workflow: Examine → Edit → Verify

### 1. See Where You Are (Player Command)
```bash
> look

You are in Woander's Magical Shop, standing at the Display Shelf Area.

A shelf displaying various magical curiosities and glowing bottles.

You see:
- Bottle of Mystery (glowing with turquoise light)
- Bottle of Energy (crackling with amber sparks)

Exits: counter, entrance, spawn_zone_2
```

**Note**: `look` (no @) is a **player command**, not admin. It shows you the space from a player perspective.

### 2. Examine Object Structure (Admin Command)
```bash
> @examine item bottle_mystery

📦 Item: bottle_mystery (Bottle of Mystery)

JSON Structure:
{
  "instance_id": "bottle_mystery",
  "template_id": "bottle_mystery",
  "semantic_name": "Bottle of Mystery",
  "description": "A bottle with deep turquoise glow, swirling with mysterious dreams and spiral symbols",
  "collectible": true,
  "visible": true,
  "state": {
    "glowing": true,
    "dream_type": "mystery",
    "symbol": "spiral"
  }
}

Location: woander_store → spawn_zone_1
Path: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery]

Editable properties:
- semantic_name (string) = "Bottle of Mystery"
- description (string) = "A bottle with deep turquoise glow..."
- collectible (boolean) = true
- visible (boolean) = true
- state.glowing (boolean) = true
- state.dream_type (string) = "mystery"
- state.symbol (string) = "spiral"

Examples:
  @edit item bottle_mystery visible false
  @edit item bottle_mystery state.glowing false
  @edit item bottle_mystery description "New description..."
```

### 3. Edit Property (Admin Command)
```bash
> @edit item bottle_mystery visible false

🔄 Updating item: bottle_mystery

Property: visible
Path: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery].visible
Old value: true
New value: false

✅ Update successful!

The item is now hidden from players. It will not appear in AOI updates.

To verify: @examine item bottle_mystery
```

### 4. Verify Change (Admin Command)
```bash
> @examine item bottle_mystery

📦 Item: bottle_mystery (Bottle of Mystery)

JSON Structure:
{
  "instance_id": "bottle_mystery",
  "visible": false,  ⬅️  CHANGED
  "state": {
    "glowing": true,
    "dream_type": "mystery"
  }
}
```

---

## Player vs Admin Commands

### Player Commands (No @ Prefix)

**Purpose**: Experience the world as a player

```bash
look                    # See current location and items
look at bottle          # Examine specific item
inventory               # Check your items
collect bottle          # Pick up item
go counter              # Move to different area
talk louisa             # Speak with NPC
help                    # Get command help
quests                  # View quest status
```

### Admin Commands (@ Prefix)

**Purpose**: Inspect and modify world state

```bash
@examine item <id>      # View JSON structure
@edit item <id> <property> <value>  # Update property
@where                  # Show admin location context
@list-items             # List all items in experience
@inspect-item <id>      # Detailed item info (old format)
@create-item <name>     # Create new item
@delete-item <id>       # Remove item
```

---

## Comparison: Player vs Admin View

### Player View (look)
```bash
> look

You are in Woander's Magical Shop, standing at the Display Shelf Area.

You see:
- Bottle of Mystery (glowing softly)
- Bottle of Energy (crackling with power)

NPCs here: None
Exits: counter, entrance
```

**Shows**:
- Natural language description
- Visible items only
- Simplified view for gameplay

### Admin View (@where)
```bash
> @where

📍 Current Location: woander_store (Woander's Magical Shop)
📍 Current Area: spawn_zone_1 (Display Shelf Area)

Description: A shelf displaying various magical curiosities and glowing bottles.

Items in this area:
1. bottle_mystery (Bottle of Mystery) - visible: true, collectible: true
2. bottle_energy (Bottle of Energy) - visible: true, collectible: true

NPCs in this area: None

All areas in this location:
- entrance (Store Entrance) - NPC: Louisa
- counter (Shop Counter) - NPC: Woander
- spawn_zone_1 (Display Shelf Area) ⬅️ YOU ARE HERE
- spawn_zone_2 (Window Display)
- spawn_zone_3 (Corner Nook)
- spawn_zone_4 (Book Alcove)
- back_room (Back Storage Room)

Actions:
  @examine item bottle_mystery
  @edit item bottle_mystery visible false
  @list-items
```

**Shows**:
- Technical location IDs
- All items (visible and hidden)
- System properties
- Edit commands

---

## Admin Command Categories

### 1. Location Context Commands

**See where you are and what's around you**

```bash
@where
# Shows: Current location, area, all items (visible + hidden), NPCs

@here
# Alias for: @examine location <current_location>

@items-here
# List only items in current area
```

### 2. Object Introspection Commands

**View JSON structure of any object**

```bash
@examine item <id>
@examine location <id>
@examine area <location>.<area>
@examine npc <id>
@examine waypoint <id>
@examine quest <id>
```

**Output includes**:
- Full JSON structure
- Current location/path
- List of editable properties with types
- Example edit commands

### 3. Object Editing Commands

**Modify any property on any object**

```bash
@edit item <id> <property> <value>
@edit location <id> <property> <value>
@edit area <location>.<area> <property> <value>
@edit npc <id> <property> <value>

# Natural language variants (all work):
@edit item bottle_mystery visible false
@set bottle_mystery visible to false
@change bottle_mystery visible to false
@update item bottle_mystery visible false
```

**Features**:
- Dot notation for nested properties: `state.glowing`
- Type inference: `"true"` → boolean, `"123"` → integer
- Type validation: Ensures old and new values match types
- Before/after confirmation
- Impact messages: "Item is now hidden from players"

### 4. Object Creation Commands

**Create new objects with guided prompts**

```bash
@create item <name>
# Prompts for: location, template, properties

@create waypoint <name> at <lat> <lng>
# Creates GPS waypoint

@create location <id>
# Creates new location with areas
```

### 5. Object Deletion Commands

**Remove objects with confirmation**

```bash
@delete item <id> CONFIRM
@delete waypoint <id> CONFIRM
@delete location <id> CONFIRM

# Without CONFIRM, shows preview:
@delete item bottle_mystery
⚠️ Delete Item: bottle_mystery
Current state: visible=true, location=woander_store.spawn_zone_1
To confirm: @delete item bottle_mystery CONFIRM
```

### 6. Listing Commands

**View all objects of a type**

```bash
@list-items
@list-locations
@list-areas <location>
@list-npcs
@list-waypoints
@list-quests
```

---

## Editing Examples

### Simple Properties

```bash
# Toggle visibility
@edit item bottle_mystery visible false

# Change collectible flag
@edit item bottle_mystery collectible false

# Update description
@edit item bottle_mystery description "A mysterious glowing bottle"

# Change semantic name
@edit item bottle_mystery semantic_name "Dream Bottle of Mystery"
```

### Nested Properties (Dot Notation)

```bash
# Update nested state
@edit item bottle_mystery state.glowing false
@edit item bottle_mystery state.dream_type "adventure"
@edit item bottle_mystery state.symbol "star"

# Update NPC dialogue
@edit npc louisa dialogue.greeting "Welcome, friend!"

# Update waypoint media
@edit waypoint 4 media.audio "peaceful_music.wav"

# Update location area
@edit area woander_store.counter description "The main shop counter"
```

### Type Inference Examples

```bash
# Booleans
@edit item bottle_mystery visible true    # → boolean true
@edit item bottle_mystery visible false   # → boolean false

# Numbers
@edit npc louisa trust_level 85          # → integer 85
@edit waypoint 4 location.lat 37.9057    # → float 37.9057

# Strings
@edit item bottle_mystery description "New text"  # → string

# JSON objects (for complex state)
@edit item bottle_mystery state '{"glowing": false, "symbol": "moon"}'
```

---

## Smart Path Resolution

### The Challenge

Items can be in different locations with different nesting:

```json
// Top-level location items
"locations": {
  "waypoint_28a": {
    "items": [...]
  }
}

// Area items (current wylding-woods pattern)
"locations": {
  "woander_store": {
    "areas": {
      "spawn_zone_1": {
        "items": [...]
      }
    }
  }
}

// Player inventory
"player": {
  "inventory": [...]
}
```

### The Solution

**Smart finder** automatically searches all locations:
- Top-level location items
- All area items within all locations
- Player inventories (for collected items)

**Returns full path** for transparency:
```
Path: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery]
```

You don't need to know the structure - the system finds it.

---

## Safety Features

### 1. Before/After Confirmation

Every edit shows:
```
Property: visible
Path: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery].visible
Old value: true
New value: false
```

### 2. Type Validation

```bash
> @edit item bottle_mystery visible "hello"

❌ Type mismatch: property expects boolean, got string

Current value: true (boolean)
Try: @edit item bottle_mystery visible false
```

### 3. CONFIRM Flag for Destructive Operations

```bash
> @delete item bottle_mystery

⚠️ Delete Item: bottle_mystery
To confirm: @delete item bottle_mystery CONFIRM

> @delete item bottle_mystery CONFIRM

✅ Item deleted
Backup created: world.20251113_144523.backup.json
```

### 4. Automatic Backups

Before any destructive operation:
- Create timestamped backup: `world.20251113_144523.backup.json`
- Keep last 5 backups (rotate old ones)
- Log location for recovery

### 5. Impact Messages

Explain what the change means:
```
visible: false → "The item is now hidden from players"
collectible: false → "Players cannot collect this item"
trust_level: 85 → "NPC now has high trust with player"
```

---

## Quick Reference Card

### See Where You Are
```bash
look              # Player view of current location
@where            # Admin view with all items and properties
@here             # Examine current location as admin
```

### Inspect Objects
```bash
@examine item <id>
@examine location <id>
@examine npc <id>
```

### Edit Properties
```bash
@edit item <id> <property> <value>
@edit item <id> <nested.property> <value>
```

### Common Edits
```bash
# Toggle item visibility
@edit item bottle_mystery visible false

# Update item description
@edit item bottle_mystery description "New text"

# Change nested state
@edit item bottle_mystery state.glowing false

# Update NPC trust
@edit npc louisa trust_level 85
```

### Create & Delete
```bash
@create item <name>
@delete item <id> CONFIRM
```

### List Objects
```bash
@list-items
@list-locations
@list-npcs
@list-waypoints
```

---

## Implementation Phases

### Phase 1: Core Introspection (Week 1)
- `@examine item <id>` - View JSON structure
- `@edit item <id> <property> <value>` - Update properties
- `@where` - Show admin location context
- Smart path resolution for nested properties

### Phase 2: Location Management (Week 2)
- `@examine location <id>` - View location structure
- `@examine area <location>.<area>` - View area structure
- `@edit location <id> <property> <value>` - Update locations
- `@edit area <location>.<area> <property> <value>` - Update areas

### Phase 3: Create & Delete (Week 3)
- `@create item` - Create new items
- `@delete item <id> CONFIRM` - Remove items
- Guided creation with smart prompts
- Confirmation and backup for deletes

### Phase 4: Extend to All Objects (Week 4)
- NPCs: `@examine npc`, `@edit npc`
- Quests: `@examine quest`, `@edit quest`
- Waypoints: Already have editing, add `@examine`
- Universal `@edit` that infers object type

---

## Open Questions

1. **Should @where track persistent admin location?**
   - Or always show based on player state?
   - Recommendation: Use player state, allow override

2. **Allow creating arbitrary new properties?**
   - `@edit item bottle_mystery new_property "value"`
   - Recommendation: Warn but allow (flexibility)

3. **Support editing multiple properties at once?**
   - `@edit item bottle_mystery visible=false collectible=false`
   - Recommendation: Phase 2 feature

4. **Property path shortcuts?**
   - `@edit bottle_mystery visible false` (infers type=item)
   - Recommendation: Yes, via LLM intent detection

---

## Summary

**Core Insight**: Show JSON structure → Reference properties naturally → Get confirmation

**Key Commands**:
- `look` - Player view (no @)
- `@where` - Admin location context
- `@examine <type> <id>` - View JSON structure
- `@edit <type> <id> <property> <value>` - Update property

**Key Features**:
- Smart path resolution (finds objects anywhere)
- Dot notation for nested properties (`state.glowing`)
- Type inference and validation
- Before/after confirmation
- Automatic backups
- Impact messages

**Next Steps**: Discuss and prioritize implementation phases

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document provides a conceptual workflow for an intelligent admin command system. The verification confirms that many of the core features have been implemented, though some discrepancies exist between the design and the current codebase.

-   **✅ Core Workflow Commands:**
    -   **`@examine item <id>`:** **VERIFIED**. Implemented in `app/services/kb/handlers/admin_examine.py`.
    -   **`@edit item <id> <property> <value>`:** **VERIFIED**. Implemented in `app/services/kb/handlers/admin_edit_item.py`.
    -   **`@where`:** **PARTIALLY VERIFIED**. A `@where` command exists, but its implementation in `app/services/kb/handlers/admin_where.py` is for finding a specific item, not for showing the current location context as described in this document.

-   **✅ Player vs Admin Commands:** **PARTIALLY VERIFIED**.
    -   **Player Commands:** Most player commands (`look`, `inventory`, `go`, `talk`, `collect`) are implemented. `help` and `quests` were not found.
    -   **Admin Commands:** The core admin commands (`@examine`, `@edit`, `@where`, `@create`, `@delete`, `@list`) are implemented.

-   **✅ Admin Command Categories:** **PARTIALLY VERIFIED**.
    -   **Object Introspection (`@examine`), Editing (`@edit`), Creation (`@create`), Deletion (`@delete`), and Listing (`@list`) commands are all implemented.**
    -   **Location Context (`@where`, `@here`, `@items-here`):** Only `@where` is implemented, and with different functionality than described.

-   **✅ Smart Features:** **VERIFIED**.
    -   **Smart Path Resolution:** Implemented in `_find_item_in_world`.
    -   **Type Inference:** Implemented in `_infer_value_type`.
    -   **Nested Navigation (Dot notation):** Implemented in `_resolve_nested_property`.
    -   **Before/After Transparency & Impact Context:** Implemented in the narrative responses of the handlers.
    -   **Self-Documenting (`@examine`):** The output of `@examine` includes editable properties and examples.

**Conclusion:** The core concepts of the intelligent admin workflow, particularly for item introspection and editing, are well-established in the codebase. The main discrepancy is the functionality of the `@where` command, which does not yet provide the "location context" described in this document. The document is a good representation of the implemented features and a solid plan for future development.
