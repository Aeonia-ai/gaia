# Intelligent Admin Introspection & Editing System

**Date**: 2025-11-13
**Goal**: Enable admins to examine JSON structure, identify property paths, and intelligently edit nested properties with natural language

---

## User Workflow Vision

```bash
# Step 1: Examine object to see its JSON structure
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

Location: woander_store.areas.spawn_zone_1
Path: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery]

Editable properties:
- semantic_name (string)
- description (string)
- collectible (boolean)
- visible (boolean)
- state.glowing (boolean)
- state.dream_type (string)
- state.symbol (string)

Examples:
  @edit item bottle_mystery visible false
  @edit item bottle_mystery state.glowing false
  @edit item bottle_mystery description "New description"

# Step 2: Edit a property using natural path syntax
> @edit item bottle_mystery visible false

🔄 Updating item: bottle_mystery

Property: visible
Path: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery].visible
Old value: true
New value: false

✅ Update successful!

The item is now hidden from players. It will not appear in AOI updates.

To verify: @examine item bottle_mystery

# Step 3: Verify the change
> @examine item bottle_mystery

📦 Item: bottle_mystery (Bottle of Mystery)

JSON Structure:
{
  "instance_id": "bottle_mystery",
  "template_id": "bottle_mystery",
  "semantic_name": "Bottle of Mystery",
  "description": "A bottle with deep turquoise glow, swirling with mysterious dreams and spiral symbols",
  "collectible": true,
  "visible": false,  ⬅️  CHANGED
  "state": {
    "glowing": true,
    "dream_type": "mystery",
    "symbol": "spiral"
  }
}
```

---

## Architecture Design

### 1. @examine Command

**Purpose**: Show actual JSON structure + metadata for any object

**Command Signatures:**
```bash
@examine item <item_id>
@examine location <location_id>
@examine area <location_id>.<area_id>
@examine npc <npc_id> [user_id]
@examine waypoint <waypoint_id>
@examine quest <quest_id> [user_id]
```

**Output Format:**
```json
{
  "success": true,
  "narrative": "📦 Item: bottle_mystery (Bottle of Mystery)\n\nJSON Structure:\n{...}\n\nLocation: woander_store.areas.spawn_zone_1\nPath: locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery]\n\nEditable properties:\n- semantic_name (string)\n- visible (boolean)\n...",
  "raw_json": {
    "instance_id": "bottle_mystery",
    "template_id": "bottle_mystery",
    "semantic_name": "Bottle of Mystery",
    "collectible": true,
    "visible": true,
    "state": {
      "glowing": true,
      "dream_type": "mystery",
      "symbol": "spiral"
    }
  },
  "metadata": {
    "object_type": "item",
    "object_id": "bottle_mystery",
    "world_path": "locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery]",
    "editable_properties": {
      "semantic_name": {"type": "string", "current": "Bottle of Mystery"},
      "description": {"type": "string", "current": "A bottle with..."},
      "collectible": {"type": "boolean", "current": true},
      "visible": {"type": "boolean", "current": true},
      "state.glowing": {"type": "boolean", "current": true},
      "state.dream_type": {"type": "string", "current": "mystery"},
      "state.symbol": {"type": "string", "current": "spiral"}
    }
  }
}
```

### 2. @edit Command with Intelligent Path Resolution

**Purpose**: Edit any property using natural property paths

**Command Signature:**
```bash
@edit <object-type> <object-id> <property-path> <new-value>
```

**Examples:**
```bash
# Simple properties
@edit item bottle_mystery visible false
@edit item bottle_mystery collectible true
@edit item bottle_mystery semantic_name "Dream Bottle of Mystery"

# Nested properties (dot notation)
@edit item bottle_mystery state.glowing false
@edit item bottle_mystery state.dream_type "adventure"
@edit item bottle_mystery state.symbol "star"

# Deep nesting
@edit npc louisa dialogue.greeting "Hello, dear friend!"
@edit waypoint 4 media.audio "peaceful_music.wav"
@edit location woander_store areas.counter.description "The main counter..."

# Natural language alternatives (LLM resolves to above)
@edit item bottle_mystery set visible to false
@edit bottle_mystery visible false  # Infers type=item
@set bottle_mystery visible false
```

### 3. Smart Path Resolution Algorithm

**Challenge**: Find and update deeply nested properties in world.json

**Input:**
- Object type: `item`
- Object ID: `bottle_mystery`
- Property path: `state.glowing`
- New value: `false`

**Resolution Steps:**

```python
async def resolve_and_update_property(
    experience_id: str,
    object_type: str,
    object_id: str,
    property_path: str,
    new_value: Any
) -> dict:
    """
    Intelligently resolve property path and update value.

    Returns:
        {
            "success": bool,
            "world_path": "locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery]",
            "property_path": "state.glowing",
            "old_value": true,
            "new_value": false,
            "full_path": "locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery].state.glowing"
        }
    """

    # Step 1: Find object location in world state
    object_location = await find_object_in_world(
        experience_id=experience_id,
        object_type=object_type,
        object_id=object_id
    )
    # Returns: {
    #     "world_path": "locations.woander_store.areas.spawn_zone_1.items",
    #     "index": 0  # Array index if applicable
    # }

    # Step 2: Get current object data
    current_data = await get_object_data(
        experience_id=experience_id,
        world_path=object_location["world_path"],
        object_id=object_id
    )
    # Returns: {
    #     "instance_id": "bottle_mystery",
    #     "visible": true,
    #     "state": {"glowing": true, "dream_type": "mystery"}
    # }

    # Step 3: Resolve property path to get old value
    old_value = resolve_nested_property(current_data, property_path)
    # property_path="state.glowing" → current_data["state"]["glowing"] → true

    # Step 4: Validate new value type matches old value type
    validate_type_match(old_value, new_value)
    # Ensures: bool → bool, str → str, int → int

    # Step 5: Build update payload for UnifiedStateManager
    updates = build_nested_update(
        world_path=object_location["world_path"],
        object_id=object_id,
        property_path=property_path,
        new_value=new_value
    )
    # Returns: {
    #     "locations": {
    #         "woander_store": {
    #             "areas": {
    #                 "spawn_zone_1": {
    #                     "items": {
    #                         "$update": [{
    #                             "instance_id": "bottle_mystery",
    #                             "state": {
    #                                 "glowing": false
    #                             }
    #                         }]
    #                     }
    #                 }
    #             }
    #         }
    #     }
    # }

    # Step 6: Apply update to world state
    await state_manager.update_world_state(
        experience=experience_id,
        updates=updates,
        user_id=None  # Admin operation, no player-specific AOI rebuild
    )

    # Step 7: Return confirmation
    return {
        "success": True,
        "world_path": object_location["world_path"],
        "property_path": property_path,
        "old_value": old_value,
        "new_value": new_value,
        "full_path": f"{object_location['world_path']}.{property_path}"
    }
```

### 4. Find Object in World Algorithm

**Challenge**: Items can be in multiple locations with different nesting levels

**Examples:**
```json
// Top-level location items
"locations": {
  "waypoint_28a_store": {
    "items": [{"instance_id": "dream_bottle_1"}]
  }
}

// Area items (current wylding-woods pattern)
"locations": {
  "woander_store": {
    "areas": {
      "spawn_zone_1": {
        "items": [{"instance_id": "bottle_mystery"}]
      }
    }
  }
}

// Player inventory (not in world state, in player view)
"player": {
  "inventory": [{"instance_id": "bottle_joy"}]
}
```

**Implementation:**
```python
async def find_object_in_world(
    experience_id: str,
    object_type: str,
    object_id: str
) -> dict:
    """
    Search world state for object by type and ID.

    Returns world path and metadata about location.
    """

    if object_type == "item":
        return await find_item_location(experience_id, object_id)
    elif object_type == "npc":
        return await find_npc_location(experience_id, object_id)
    elif object_type == "waypoint":
        return {"world_path": f"waypoints.{object_id}", "index": None}
    elif object_type == "location":
        return {"world_path": f"locations.{object_id}", "index": None}
    elif object_type == "area":
        location_id, area_id = object_id.split(".")
        return {"world_path": f"locations.{location_id}.areas.{area_id}", "index": None}


async def find_item_location(experience_id: str, item_id: str) -> dict:
    """
    Find item in world state - checks both top-level and area items.
    """
    world_state = await state_manager.get_world_state(experience_id)

    # Search all locations
    for location_id, location_data in world_state.get("locations", {}).items():

        # Check top-level items
        if "items" in location_data:
            for idx, item in enumerate(location_data["items"]):
                if item.get("instance_id") == item_id:
                    return {
                        "world_path": f"locations.{location_id}.items",
                        "index": idx,
                        "location": location_id,
                        "area": None
                    }

        # Check area items
        if "areas" in location_data:
            for area_id, area_data in location_data["areas"].items():
                if "items" in area_data:
                    for idx, item in enumerate(area_data["items"]):
                        if item.get("instance_id") == item_id:
                            return {
                                "world_path": f"locations.{location_id}.areas.{area_id}.items",
                                "index": idx,
                                "location": location_id,
                                "area": area_id
                            }

    # Check collected items (in player inventories)
    # NOTE: This requires scanning player views, not world state
    player_location = await find_in_player_inventories(experience_id, item_id)
    if player_location:
        return player_location

    raise ObjectNotFoundError(f"Item '{item_id}' not found in world state")
```

### 5. Nested Property Resolution

**Challenge**: Parse dot-notation paths and traverse nested objects

```python
def resolve_nested_property(data: dict, property_path: str) -> Any:
    """
    Resolve dot-notation property path to actual value.

    Examples:
        resolve_nested_property(
            {"state": {"glowing": true}},
            "state.glowing"
        ) → true

        resolve_nested_property(
            {"media": {"audio": "music.wav"}},
            "media.audio"
        ) → "music.wav"
    """
    parts = property_path.split(".")
    current = data

    for part in parts:
        if not isinstance(current, dict):
            raise PropertyPathError(
                f"Cannot access '{part}' on non-dict value: {current}"
            )

        if part not in current:
            raise PropertyNotFoundError(
                f"Property '{part}' not found in {current.keys()}"
            )

        current = current[part]

    return current


def build_nested_update(
    world_path: str,
    object_id: str,
    property_path: str,
    new_value: Any
) -> dict:
    """
    Build nested update structure for UnifiedStateManager.

    Input:
        world_path: "locations.woander_store.areas.spawn_zone_1.items"
        object_id: "bottle_mystery"
        property_path: "state.glowing"
        new_value: false

    Output:
        {
            "locations": {
                "woander_store": {
                    "areas": {
                        "spawn_zone_1": {
                            "items": {
                                "$update": [{
                                    "instance_id": "bottle_mystery",
                                    "state": {
                                        "glowing": false
                                    }
                                }]
                            }
                        }
                    }
                }
            }
        }
    """
    # Parse world path
    path_parts = world_path.split(".")
    # ["locations", "woander_store", "areas", "spawn_zone_1", "items"]

    # Parse property path
    property_parts = property_path.split(".")
    # ["state", "glowing"]

    # Build nested property update
    property_update = new_value
    for part in reversed(property_parts):
        property_update = {part: property_update}
    # {"state": {"glowing": false}}

    # Build item update with instance_id
    item_update = {
        "instance_id": object_id,
        **property_update
    }
    # {"instance_id": "bottle_mystery", "state": {"glowing": false}}

    # Build world path update
    updates = {}
    current = updates

    for i, part in enumerate(path_parts[:-1]):  # Skip last part (items)
        current[part] = {}
        current = current[part]

    # Add $update operator for array items
    current[path_parts[-1]] = {"$update": [item_update]}

    return updates
```

### 6. Type Validation

**Challenge**: Ensure type safety when editing properties

```python
def validate_type_match(old_value: Any, new_value: Any) -> None:
    """
    Validate that new value matches type of old value.

    Raises TypeMismatchError if types don't match.
    """
    old_type = type(old_value)
    new_type = type(new_value)

    # Special case: None can be replaced by any type
    if old_value is None:
        return

    # Type must match
    if old_type != new_type:
        raise TypeMismatchError(
            f"Type mismatch: property expects {old_type.__name__}, "
            f"got {new_type.__name__}"
        )

    # Additional validation for specific types
    if isinstance(new_value, bool):
        # Already validated by type check
        pass
    elif isinstance(new_value, str):
        # Could add max length validation
        if len(new_value) > 1000:
            raise ValidationError("String too long (max 1000 characters)")
    elif isinstance(new_value, (int, float)):
        # Could add range validation
        pass


def infer_value_type(value_str: str) -> Any:
    """
    Intelligently infer type from string input.

    Examples:
        "true" → True (boolean)
        "false" → False (boolean)
        "123" → 123 (int)
        "45.67" → 45.67 (float)
        "hello" → "hello" (string)
        '{"key": "value"}' → {"key": "value"} (JSON object)
    """
    # Try boolean
    if value_str.lower() in ("true", "yes", "on", "1"):
        return True
    if value_str.lower() in ("false", "no", "off", "0"):
        return False

    # Try int
    try:
        return int(value_str)
    except ValueError:
        pass

    # Try float
    try:
        return float(value_str)
    except ValueError:
        pass

    # Try JSON object/array
    if value_str.startswith(("{", "[")):
        try:
            return json.loads(value_str)
        except json.JSONDecodeError:
            pass

    # Default to string
    return value_str
```

---

## Command Implementation Examples

### @examine item

**Markdown Definition:**
```yaml
---
command: @examine
aliases: [@examine, @inspect-json, @show-json, @view-json]
description: View JSON structure and editable properties of any object
requires_location: false
requires_target: true
requires_admin: true
state_model_support: [shared, isolated]
---

# @examine - View Object JSON Structure

## Intent Detection

Natural language patterns:
- @examine item <id>
- @examine location <id>
- @show json for item <id>
- @view item <id> as json

## Execution Logic

1. Parse object type and ID from command
2. Find object in world state (or player view for NPCs/quests)
3. Extract full JSON representation
4. Analyze editable properties with types
5. Show JSON + metadata + editing examples

## Response Format

Success:
```json
{
  "success": true,
  "narrative": "📦 Item: bottle_mystery...",
  "raw_json": {/* actual object data */},
  "metadata": {
    "object_type": "item",
    "object_id": "bottle_mystery",
    "world_path": "locations.woander_store.areas.spawn_zone_1.items[instance_id=bottle_mystery]",
    "editable_properties": {/* property metadata */}
  }
}
```
```

**Python Handler:**
```python
async def handle_examine(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Show JSON structure and editable properties for any object.
    """
    object_type = command_data.get("object_type")  # item, location, npc, etc.
    object_id = command_data.get("object_id")

    if not object_type or not object_id:
        return CommandResult(
            success=False,
            message_to_player="Please specify object type and ID.\n\nExamples:\n- @examine item bottle_mystery\n- @examine location woander_store\n- @examine npc louisa"
        )

    try:
        # Find object in world state
        location_info = await find_object_in_world(
            experience_id=experience_id,
            object_type=object_type,
            object_id=object_id
        )

        # Get full object data
        object_data = await get_object_data(
            experience_id=experience_id,
            world_path=location_info["world_path"],
            object_id=object_id
        )

        # Analyze editable properties
        editable_props = analyze_editable_properties(object_data)

        # Format JSON with syntax highlighting (if terminal supports)
        json_formatted = json.dumps(object_data, indent=2)

        # Build narrative
        narrative = f"""📦 {object_type.title()}: {object_id}

JSON Structure:
```json
{json_formatted}
```

Location: {location_info.get('location', 'N/A')}.{location_info.get('area', 'N/A')}
Path: {location_info['world_path']}

Editable properties:
{format_editable_properties(editable_props)}

Examples:
{generate_edit_examples(object_type, object_id, editable_props)}
"""

        return CommandResult(
            success=True,
            message_to_player=narrative,
            metadata={
                "command_type": "examine",
                "object_type": object_type,
                "object_id": object_id,
                "world_path": location_info["world_path"],
                "raw_json": object_data,
                "editable_properties": editable_props
            }
        )

    except ObjectNotFoundError as e:
        return CommandResult(
            success=False,
            message_to_player=f"❌ {object_type.title()} '{object_id}' not found.\n\nTry:\n- @list {object_type}s\n- @where (if you're looking for items near you)"
        )


def analyze_editable_properties(data: dict, prefix: str = "") -> dict:
    """
    Recursively analyze object data to find editable properties.

    Returns:
        {
            "visible": {"type": "boolean", "current": true, "path": "visible"},
            "state.glowing": {"type": "boolean", "current": true, "path": "state.glowing"},
            ...
        }
    """
    properties = {}

    for key, value in data.items():
        # Skip system keys
        if key in ("instance_id", "template_id", "id"):
            continue

        property_path = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            # Recurse into nested objects
            nested = analyze_editable_properties(value, property_path)
            properties.update(nested)
        else:
            # Leaf property
            properties[property_path] = {
                "type": type(value).__name__,
                "current": value,
                "path": property_path
            }

    return properties


def format_editable_properties(props: dict) -> str:
    """Format editable properties as bullet list."""
    lines = []
    for path, info in sorted(props.items()):
        lines.append(f"- {path} ({info['type']}) = {info['current']}")
    return "\n".join(lines)


def generate_edit_examples(
    object_type: str,
    object_id: str,
    props: dict
) -> str:
    """Generate example edit commands."""
    examples = []

    # Show first 3 properties as examples
    for path in list(props.keys())[:3]:
        prop_type = props[path]["type"]
        current = props[path]["current"]

        # Generate example new value
        if prop_type == "bool":
            new_value = "false" if current else "true"
        elif prop_type == "str":
            new_value = '"New description"'
        elif prop_type in ("int", "float"):
            new_value = str(current + 1)
        else:
            new_value = '"new_value"'

        examples.append(f"  @edit {object_type} {object_id} {path} {new_value}")

    return "\n".join(examples)
```

### @edit with Intelligent Resolution

**Python Handler:**
```python
async def handle_edit(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Intelligently edit any property on any object.
    """
    object_type = command_data.get("object_type")
    object_id = command_data.get("object_id")
    property_path = command_data.get("property_path")
    new_value_str = command_data.get("new_value")

    try:
        # Resolve and update property
        result = await resolve_and_update_property(
            experience_id=experience_id,
            object_type=object_type,
            object_id=object_id,
            property_path=property_path,
            new_value=infer_value_type(new_value_str)
        )

        # Build confirmation narrative
        narrative = f"""🔄 Updating {object_type}: {object_id}

Property: {property_path}
Path: {result['full_path']}
Old value: {result['old_value']}
New value: {result['new_value']}

✅ Update successful!

{get_property_impact_message(object_type, property_path, result['new_value'])}

To verify: @examine {object_type} {object_id}
"""

        return CommandResult(
            success=True,
            message_to_player=narrative,
            state_changes={
                "world": result.get("world_updates", {})
            },
            metadata={
                "command_type": "edit",
                "object_type": object_type,
                "object_id": object_id,
                "property_path": property_path,
                "old_value": result['old_value'],
                "new_value": result['new_value']
            }
        )

    except TypeMismatchError as e:
        return CommandResult(
            success=False,
            message_to_player=f"❌ Type mismatch: {str(e)}\n\nUse @examine {object_type} {object_id} to see property types."
        )
    except PropertyNotFoundError as e:
        return CommandResult(
            success=False,
            message_to_player=f"❌ Property not found: {str(e)}\n\nUse @examine {object_type} {object_id} to see available properties."
        )


def get_property_impact_message(
    object_type: str,
    property_path: str,
    new_value: Any
) -> str:
    """
    Provide context about what this property change means.
    """
    if object_type == "item" and property_path == "visible":
        if new_value:
            return "The item is now visible to players. It will appear in AOI updates."
        else:
            return "The item is now hidden from players. It will not appear in AOI updates."

    if object_type == "item" and property_path == "collectible":
        if new_value:
            return "Players can now collect this item."
        else:
            return "Players cannot collect this item (it's scenery only)."

    if "state.glowing" in property_path:
        if new_value:
            return "The object is now glowing with magical energy."
        else:
            return "The object's magical glow has faded."

    return ""
```

---

## Benefits of This Design

### 1. Developer Experience

**Old way (manual world.json editing):**
```bash
# 1. SSH into server
# 2. Open world.json in vim
# 3. Navigate to line 67
# 4. Change "visible": true to "visible": false
# 5. Save and exit
# 6. Restart service or trigger reload
```

**New way (intelligent introspection):**
```bash
> @examine item bottle_mystery  # See structure
> @edit item bottle_mystery visible false  # Update
> @examine item bottle_mystery  # Verify
```

### 2. Type Safety

- Automatically infers types from values
- Validates type compatibility before update
- Prevents "stringly-typed" errors (e.g., `"true"` string vs `true` boolean)

### 3. Path Intelligence

- Supports dot-notation for nested properties
- Automatically finds object location in world.json
- Handles arrays, nested objects, and complex structures

### 4. Confirmation Feedback

- Shows before/after values
- Displays full path for transparency
- Provides context about impact ("item now hidden from players")

### 5. Natural Language

```bash
# All of these work:
@edit item bottle_mystery visible false
@set bottle_mystery visible to false
@change bottle_mystery visible to false
@update item bottle_mystery visible false
```

LLM intent detection resolves to canonical command structure.

---

## Implementation Checklist

### Week 1: Core @examine Command
- [ ] Implement `find_object_in_world()` for items
- [ ] Implement `analyze_editable_properties()`
- [ ] Create `@examine item <id>` command
- [ ] Test with wylding-woods items

### Week 2: Intelligent @edit Command
- [ ] Implement `resolve_nested_property()`
- [ ] Implement `build_nested_update()`
- [ ] Implement type inference and validation
- [ ] Create `@edit item <id> <property> <value>` command
- [ ] Test nested property updates (state.glowing, etc.)

### Week 3: Extend to Other Object Types
- [ ] Extend `find_object_in_world()` for locations, areas, NPCs
- [ ] Create `@examine location/area/npc` variants
- [ ] Create `@edit location/area/npc` handlers
- [ ] Test across all object types

### Week 4: Polish & Natural Language
- [ ] Add natural language aliases
- [ ] Improve error messages
- [ ] Add property impact messages
- [ ] Create comprehensive test suite

---

## Open Questions

1. **Allow arbitrary new properties?**
   - Should `@edit item bottle_mystery foo bar` create a new property?
   - Or only allow editing existing properties?
   - Recommendation: Warn but allow (enable extensibility)

2. **Handle array properties?**
   - What about editing arrays: `state.tags[0]`?
   - Recommendation: Phase 2 - start with simple properties

3. **Undo/rollback?**
   - Should we implement `@undo` command?
   - Recommendation: Use existing backup mechanism + manual rollback

4. **Multi-property updates?**
   - Should we support: `@edit item bottle_mystery visible=false collectible=false`?
   - Recommendation: Phase 2 - start with single property updates

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document proposes a design for an intelligent admin introspection and editing system. The verification confirms that the core features for `item` objects have been implemented as described.

-   **✅ `@examine` Command:** **VERIFIED**.
    -   **Evidence:** The `handle_admin_examine` function in `app/services/kb/handlers/admin_examine.py` implements the described functionality. It supports `item`, `location`, and `area` types, and its output includes the JSON structure, location path, and a list of editable properties with examples.

-   **✅ `@edit` Command with Intelligent Path Resolution:** **VERIFIED**.
    -   **Evidence:** The `handle_admin_edit_item` function in `app/services/kb/handlers/admin_edit_item.py` implements the proposed logic.
    -   **Smart Path Resolution:** The `_find_item_in_world` function correctly searches for items in various locations.
    -   **Nested Property Resolution:** The `_resolve_nested_property` function handles dot-notation paths.
    -   **Type Safety:** The `_infer_value_type` and `_validate_type_match` functions provide type inference and validation.
    -   **State Updates:** The `_build_nested_update` function correctly constructs the payload for the `UnifiedStateManager`.

**Conclusion:** The design for the intelligent admin introspection and editing system for items has been successfully implemented. The code in `admin_examine.py` and `admin_edit_item.py` directly reflects the architecture and features outlined in this document. The plan to extend this functionality to other object types (`location`, `area`, `npc`) is noted as future work.
