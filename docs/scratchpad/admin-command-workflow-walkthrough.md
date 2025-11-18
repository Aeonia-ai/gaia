# Admin Command Workflow - Conceptual Walkthrough

**Date**: 2025-11-13
**Purpose**: Demonstrate complete workflows using @examine, @where, and @edit-item commands

---

## Scenario 1: Finding and Hiding a Bottle

**Goal**: Hide the mystery bottle from players so it can be revealed later via quest

### Step 1: Find where you are
```bash
> @where

📍 Current Location: woander_store (Woander's Magical Shop)
📍 Current Area: spawn_zone_1 (Display Shelf Area)

Description: A shelf displaying various magical curiosities and glowing bottles.

Items in this area:
1. bottle_mystery (Bottle of Mystery) - visible: true, collectible: true
2. bottle_energy (Bottle of Energy) - visible: true, collectible: true
3. bottle_joy (Bottle of Joy) - visible: true, collectible: true
4. bottle_nature (Bottle of Nature) - visible: true, collectible: true

NPCs in this area: None

All areas in this location:
- entrance (Store Entrance) - NPC: Louisa
- counter (Shop Counter) - NPC: Woander
- spawn_zone_1 (Display Shelf Area) ⬅️  YOU ARE HERE
- spawn_zone_2 (Window Display)
- spawn_zone_3 (Corner Nook)
- spawn_zone_4 (Book Alcove)

Actions:
  @examine item bottle_mystery
  @edit item bottle_mystery visible false
```

**Analysis**: You can see all 4 bottles are currently visible and in spawn_zone_1.

---

### Step 2: Examine the bottle's structure
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
  @edit item bottle_mystery description "New description"
```

**Analysis**: You can see the full JSON structure, current values, and property paths for editing.

---

### Step 3: Hide the bottle
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

**Analysis**: The system found the bottle, updated the property, and confirmed with before/after values.

---

### Step 4: Verify the change
```bash
> @examine item bottle_mystery

📦 Item: bottle_mystery (Bottle of Mystery)

JSON Structure:
{
  "instance_id": "bottle_mystery",
  "template_id": "bottle_mystery",
  "semantic_name": "Bottle of Mystery",
  "collectible": true,
  "visible": false,  ⬅️  CHANGED from true
  "state": {
    "glowing": true,
    "dream_type": "mystery",
    "symbol": "spiral"
  }
}
```

**Analysis**: Confirmed - visible is now false. Players won't see this bottle in AOI updates.

---

### Step 5: Check the area again
```bash
> @where

📍 Current Location: woander_store
📍 Current Area: spawn_zone_1

Items in this area:
1. bottle_mystery (Bottle of Mystery) - visible: false, collectible: true ⬅️  Now shows hidden
2. bottle_energy (Bottle of Energy) - visible: true, collectible: true
3. bottle_joy (Bottle of Joy) - visible: true, collectible: true
4. bottle_nature (Bottle of Nature) - visible: true, collectible: true
```

**Analysis**: Admin view still shows the bottle (with visible: false), but players won't see it.

---

## Scenario 2: Turning Off the Glow Effect

**Goal**: Turn off the glowing effect on all bottles to test non-glowing state

### Step 1: Edit nested state property
```bash
> @edit item bottle_mystery state.glowing false

🔄 Updating item: bottle_mystery

Property: state.glowing
Path: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery].state.glowing
Old value: true
New value: false

✅ Update successful!

The object's magical glow has faded.

To verify: @examine item bottle_mystery
```

**Analysis**: Dot notation (`state.glowing`) navigates nested properties automatically.

---

### Step 2: Verify nested change
```bash
> @examine item bottle_mystery

{
  "visible": false,
  "state": {
    "glowing": false,  ⬅️  CHANGED
    "dream_type": "mystery",
    "symbol": "spiral"
  }
}
```

**Analysis**: Only `state.glowing` changed - all other state properties preserved.

---

### Step 3: Turn off glow for all bottles
```bash
> @edit item bottle_energy state.glowing false
✅ Update successful!

> @edit item bottle_joy state.glowing false
✅ Update successful!

> @edit item bottle_nature state.glowing false
✅ Update successful!
```

**Analysis**: Can quickly edit multiple items using same command pattern.

---

## Scenario 3: Player-Facing vs Admin View

**Goal**: Understand the difference between player `look` and admin `@where`

### Player View
```bash
> look

You are in Woander's Magical Shop, standing at the Display Shelf Area.

A shelf displaying various magical curiosities and glowing bottles.

You see:
- Bottle of Energy (crackling with amber sparks)
- Bottle of Joy (shimmering with golden light)
- Bottle of Nature (pulsing with emerald energy)

Exits: counter, entrance, spawn_zone_2
```

**Analysis**:
- Narrative, atmospheric description
- Only shows 3 bottles (mystery bottle is hidden)
- Simplified names, no technical details

---

### Admin View
```bash
> @where

📍 Current Location: woander_store
📍 Current Area: spawn_zone_1

Items in this area:
1. bottle_mystery (Bottle of Mystery) - visible: false, collectible: true
2. bottle_energy (Bottle of Energy) - visible: true, collectible: true
3. bottle_joy (Bottle of Joy) - visible: true, collectible: true
4. bottle_nature (Bottle of Nature) - visible: true, collectible: true

Actions:
  @examine item bottle_mystery
  @edit item bottle_mystery visible false
```

**Analysis**:
- Technical IDs (bottle_mystery, bottle_energy)
- Shows ALL 4 bottles (including hidden one)
- Property flags (visible, collectible)
- Ready-to-use edit commands

**Key Insight**: Admin sees the "ground truth" of what exists, players see the curated experience.

---

## Scenario 4: Debugging Item Issues

**Goal**: Item appears duplicated or not showing up - investigate with admin commands

### Problem: Player reports not seeing a bottle they collected

```bash
> @where
Items in this area:
1. bottle_mystery - visible: false, collectible: true

> @examine item bottle_mystery

Path: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery]

{
  "visible": false,
  "collectible": true
}
```

**Diagnosis**: Item is hidden (visible: false). This is why player doesn't see it.

---

### Fix: Make item visible again
```bash
> @edit item bottle_mystery visible true

✅ Update successful!
The item is now visible to players.
```

**Resolution**: Item now appears in player's AOI updates.

---

## Scenario 5: Complex Property Updates

**Goal**: Update multiple nested properties to change bottle identity

### Step 1: Examine current state
```bash
> @examine item bottle_mystery

{
  "semantic_name": "Bottle of Mystery",
  "description": "A bottle with deep turquoise glow...",
  "state": {
    "glowing": true,
    "dream_type": "mystery",
    "symbol": "spiral"
  }
}
```

---

### Step 2: Change dream type
```bash
> @edit item bottle_mystery state.dream_type "adventure"

Property: state.dream_type
Old value: "mystery"
New value: "adventure"

✅ Update successful!
```

---

### Step 3: Change symbol
```bash
> @edit item bottle_mystery state.symbol "compass"

Property: state.symbol
Old value: "spiral"
New value: "compass"

✅ Update successful!
```

---

### Step 4: Update description to match
```bash
> @edit item bottle_mystery description "A bottle filled with swirling adventure dreams, marked with a golden compass"

Property: description
Old value: "A bottle with deep turquoise glow..."
New value: "A bottle filled with swirling adventure dreams, marked with a golden compass"

✅ Update successful!
```

---

### Step 5: Verify complete change
```bash
> @examine item bottle_mystery

{
  "semantic_name": "Bottle of Mystery",
  "description": "A bottle filled with swirling adventure dreams, marked with a golden compass",
  "state": {
    "glowing": true,
    "dream_type": "adventure",  ⬅️  CHANGED
    "symbol": "compass"  ⬅️  CHANGED
  }
}
```

**Analysis**: Multiple properties updated independently, state structure preserved.

---

## Scenario 6: Type Safety Protection

**Goal**: Demonstrate type validation preventing errors

### Attempt 1: Wrong type for boolean
```bash
> @edit item bottle_mystery visible "hello"

❌ Type mismatch for property 'visible'

Expected: boolean
Got: string ("hello")
Current value: true (boolean)

Try: @edit item bottle_mystery visible false
```

**Protection**: System prevents assigning string to boolean field.

---

### Attempt 2: Correct type inference
```bash
> @edit item bottle_mystery visible false

✅ Update successful!
```

**Analysis**: String input `"false"` automatically converted to boolean `false`.

---

## Scenario 7: Exploring Unknown Structure

**Goal**: Admin doesn't know item structure - discover it with @examine

### Step 1: Check what's in current area
```bash
> @where

Items in this area:
1. bottle_mystery (Bottle of Mystery) - visible: true, collectible: true
```

---

### Step 2: Explore item structure
```bash
> @examine item bottle_mystery

JSON Structure:
{
  "instance_id": "bottle_mystery",
  "semantic_name": "Bottle of Mystery",
  "collectible": true,
  "visible": true,
  "state": {
    "glowing": true,
    "dream_type": "mystery",
    "symbol": "spiral"
  }
}

Editable properties:
- semantic_name (string)
- collectible (boolean)
- visible (boolean)
- state.glowing (boolean)
- state.dream_type (string)
- state.symbol (string)
```

**Discovery**: Now you know:
- Item has a `state` object with 3 properties
- Properties are typed (boolean, string)
- Full property paths for editing (`state.glowing`)

---

### Step 3: Edit discovered property
```bash
> @edit item bottle_mystery state.glowing false

✅ Update successful!
```

**Workflow**: Examine → Discover structure → Reference in edit command

---

## Key Workflow Patterns

### Pattern 1: Examine → Edit → Verify
```bash
@examine item <id>          # See structure and current values
@edit item <id> prop value  # Make change
@examine item <id>          # Verify change applied
```

### Pattern 2: Where → Examine → Edit
```bash
@where                      # See items in current area
@examine item <id>          # Pick item and view details
@edit item <id> prop value  # Modify property
```

### Pattern 3: Rapid Multi-Item Updates
```bash
@where                      # See all items
@edit item item1 visible false
@edit item item2 visible false
@edit item item3 visible false
@where                      # Verify all changes
```

### Pattern 4: Deep Property Exploration
```bash
@examine item <id>          # See nested structure
@edit item <id> state.prop1 value
@edit item <id> state.prop2 value
@examine item <id>          # Verify nested changes
```

---

## Command Cheat Sheet

### Location Context
- `look` - Player view (narrative)
- `@where` - Admin view (technical)

### Object Introspection
- `@examine item <id>` - View JSON + editable properties
- `@examine location <id>` - View location structure
- `@examine area <loc>.<area>` - View area structure

### Property Editing
- `@edit item <id> <prop> <value>` - Simple property
- `@edit item <id> <nested.prop> <value>` - Nested property
- Natural variants: `@set`, `@update`, `@change`

### Type Inference
- `true/false` → boolean
- `123` → integer
- `45.67` → float
- `"text"` → string

---

## What Makes This Intelligent

1. **Smart Path Finding**: You say `@edit item bottle_mystery visible false` - system finds it anywhere in world.json
2. **Type Inference**: You type `false` (string) → system converts to boolean
3. **Nested Navigation**: Dot notation `state.glowing` automatically resolves to `item.state.glowing`
4. **Before/After Transparency**: Always shows old value → new value → full path
5. **Impact Context**: "Item is now hidden from players" explains what the change means
6. **Self-Documenting**: `@examine` shows you exactly what you can edit

---

## Next: Python Implementation

Now that we've validated the workflow conceptually, ready to implement:
1. `examine_item.py` - JSON introspection handler
2. `where_command.py` - Location context handler
3. `edit_item.py` - Smart property editing handler

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document provides a conceptual walkthrough of admin commands. The verification compares the described command behaviors and outputs against the current codebase.

### Command Existence

-   **`@where` command:**
    *   **Claim:** Command exists and shows items in the area, including their `visible` status.
    *   **Verification:** **PARTIALLY VERIFIED**. The `_admin_where` method in `app/services/kb/kb_agent.py` exists. However, its current implementation is designed to find the location of a *specific item or NPC* by ID or semantic name, not to list all items in the current area with their `visible` status as depicted in the document's example output. The document's example output for `@where` aligns more with a "show current location context" command, which is listed as a *missing* command in `admin-command-system-comprehensive-design.md`.

-   **`@examine item <id>` command:**
    *   **Claim:** Command exists and shows full JSON structure and editable properties with their types and paths.
    *   **Verification:** **PARTIALLY VERIFIED**. The `_admin_inspect` method in `app/services/kb/kb_agent.py` supports `target_type == "item"`. It provides a narrative summary of item properties (template, semantic name, location, state, etc.). However, it does *not* directly output the full raw JSON structure or explicitly list "Editable properties" with their types and paths in the same structured way as shown in the document's example.

-   **`@edit item <id> <property> <value>` command:**
    *   **Claim:** Command exists.
    *   **Verification:** **VERIFIED**. The `handle_admin_edit_item` function in `app/services/kb/handlers/admin_edit_item.py` exists and handles this command.

### `@edit` Command Capabilities

-   **Supports nested properties with dot notation (e.g., `state.glowing`):**
    *   **Verification:** **VERIFIED**. The `_resolve_nested_property` and `_build_nested_update` functions in `app/services/kb/handlers/admin_edit_item.py` explicitly handle dot-notation for nested properties.

-   **Type inference (e.g., `"false"` string to `false` boolean):**
    *   **Verification:** **VERIFIED**. The `_infer_value_type` function in `app/services/kb/handlers/admin_edit_item.py` performs intelligent type inference.

-   **Shows before/after values:**
    *   **Verification:** **VERIFIED**. The `narrative` output in `handle_admin_edit_item` explicitly includes "Old value" and "New value".

**Overall Conclusion:** This walkthrough document describes an aspirational state for the admin commands. While the `@edit item` command largely matches the described capabilities, the exact behavior and output of `@where` and `@examine` commands in the current codebase differ significantly from the detailed examples provided in the document. The document should be updated to reflect the current implementation's command syntax and output formats for these commands.
