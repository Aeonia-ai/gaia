# app/services/kb/handlers/admin_examine.py
"""
Admin command handler for examining JSON structure of any object.

Provides full JSON introspection with editable property analysis.
Bypasses LLM for <5ms response time.

This is a read-only operation - no state changes, no WorldUpdate events.
Admins can examine items, locations, areas, NPCs, waypoints to see complete structure.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from app.shared.models.command_result import CommandResult

logger = logging.getLogger(__name__)


async def handle_admin_examine(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handles the '@examine' admin command for JSON structure inspection.

    Admin implementation:
    - Shows full JSON structure (not just player-facing description)
    - Analyzes all editable properties with types
    - Returns object location path in world state
    - Provides example edit commands
    - Read-only: No state changes

    Args:
        user_id: Admin user ID
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data with action string "@examine item bottle_mystery"

    Returns:
        CommandResult with full JSON structure and edit examples

    Response time: <5ms (read-only operation)

    Example:
        >>> await handle_admin_examine(
        ...     user_id="admin@example.com",
        ...     experience_id="wylding-woods",
        ...     command_data={"action": "@examine item bottle_mystery"}
        ... )
        CommandResult(success=True, message_to_player="📦 Item: bottle_mystery...")
    """
    from ..kb_agent import kb_agent

    state_manager = kb_agent.state_manager
    if not state_manager:
        return CommandResult(
            success=False,
            message_to_player="State manager not initialized."
        )

    # Parse command string: "@examine item bottle_mystery" -> ["examine", "item", "bottle_mystery"]
    action_str = command_data.get("action", "")
    parts = action_str.lstrip("@").split()

    if len(parts) < 3:
        return CommandResult(
            success=False,
            message_to_player="Please specify object type and ID.\\n\\nExamples:\\n- @examine item bottle_mystery\\n- @examine location woander_store\\n- @examine area woander_store.spawn_zone_1"
        )

    # parts[0] = "examine" (command)
    # parts[1] = "item" (object_type)
    # parts[2] = "bottle_mystery" (object_id) or "woander_store.spawn_zone_1" for areas
    object_type = parts[1]
    object_id = " ".join(parts[2:])  # Handle multi-word IDs

    if not object_type or not object_id:
        return CommandResult(
            success=False,
            message_to_player="Please specify object type and ID.\n\nExamples:\n- @examine item bottle_mystery\n- @examine location woander_store\n- @examine npc louisa"
        )

    try:
        # Route to type-specific handler
        if object_type == "item":
            return await _examine_item(state_manager, experience_id, object_id)
        elif object_type == "location":
            return await _examine_location(state_manager, experience_id, object_id)
        elif object_type == "area":
            return await _examine_area(state_manager, experience_id, object_id)
        else:
            return CommandResult(
                success=False,
                message_to_player=f"❌ Object type '{object_type}' not yet supported.\n\nSupported types:\n- item\n- location\n- area (format: location.area)"
            )

    except Exception as e:
        logger.error(f"Failed to examine {object_type} '{object_id}': {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"Failed to examine {object_type} '{object_id}'."
        )


async def _examine_item(state_manager, experience_id: str, item_id: str) -> CommandResult:
    """Examine item with full JSON structure."""
    world_state = await state_manager.get_world_state(experience_id)

    # Find item in world state
    item_data, world_path, location_context = await _find_item_in_world(
        world_state, item_id
    )

    if not item_data:
        return CommandResult(
            success=False,
            message_to_player=f"❌ Item '{item_id}' not found.\n\nUse @list-items to see available items."
        )

    # Analyze editable properties
    editable_props = _analyze_editable_properties(item_data)

    # Format JSON with proper indentation
    json_str = json.dumps(item_data, indent=2)

    # Build narrative
    semantic_name = item_data.get("semantic_name", item_id)
    location_str = location_context.get("location", "unknown")
    area_str = location_context.get("area")
    if area_str:
        location_str = f"{location_str} → {area_str}"

    # Format editable properties list
    props_list = []
    for path, info in sorted(editable_props.items()):
        current_val = info["current"]
        # Truncate long strings
        if isinstance(current_val, str) and len(current_val) > 50:
            current_val = current_val[:47] + "..."
        props_list.append(f"- {path} ({info['type']}) = {json.dumps(current_val)}")

    props_str = "\n".join(props_list) if props_list else "No editable properties found"

    # Generate example commands
    examples = []
    for path in list(editable_props.keys())[:3]:  # First 3 properties
        prop_info = editable_props[path]
        example_val = _generate_example_value(prop_info["type"], prop_info["current"])
        examples.append(f"  @edit item {item_id} {path} {example_val}")

    examples_str = "\n".join(examples) if examples else "  (no editable properties)"

    narrative = f"""📦 Item: {item_id} ({semantic_name})

JSON Structure:
```json
{json_str}
```

Location: {location_str}
Path: {world_path}

Editable properties:
{props_str}

Examples:
{examples_str}
"""

    return CommandResult(
        success=True,
        message_to_player=narrative,
        metadata={
            "command_type": "admin_examine",
            "object_type": "item",
            "object_id": item_id,
            "world_path": world_path,
            "raw_json": item_data,
            "editable_properties": editable_props
        }
    )


async def _examine_location(state_manager, experience_id: str, location_id: str) -> CommandResult:
    """Examine location with full JSON structure."""
    world_state = await state_manager.get_world_state(experience_id)
    locations = world_state.get("locations", {})
    location_data = locations.get(location_id)

    if not location_data:
        return CommandResult(
            success=False,
            message_to_player=f"❌ Location '{location_id}' not found.\n\nUse @list-locations to see available locations."
        )

    # Analyze editable properties (skip 'areas' and 'items' - they're structural)
    location_props = {k: v for k, v in location_data.items() if k not in ("areas", "items", "id")}
    editable_props = _analyze_editable_properties(location_props)

    # Count areas
    areas = location_data.get("areas", {})
    area_count = len(areas)
    area_list = ", ".join(areas.keys()) if areas else "None"

    json_str = json.dumps(location_data, indent=2)

    narrative = f"""📍 Location: {location_id} ({location_data.get('name', location_id)})

JSON Structure:
```json
{json_str}
```

Areas: {area_count} total ({area_list})

Editable properties:
{_format_properties(editable_props)}

Examples:
  @edit location {location_id} description "New description"
  @examine area {location_id}.<area_id>
"""

    return CommandResult(
        success=True,
        message_to_player=narrative,
        metadata={
            "command_type": "admin_examine",
            "object_type": "location",
            "object_id": location_id,
            "raw_json": location_data,
            "editable_properties": editable_props
        }
    )


async def _examine_area(state_manager, experience_id: str, area_path: str) -> CommandResult:
    """Examine area with full JSON structure. area_path format: 'location.area'"""
    parts = area_path.split(".")
    if len(parts) != 2:
        return CommandResult(
            success=False,
            message_to_player=f"❌ Area path must be format: location.area\n\nExample: woander_store.spawn_zone_1"
        )

    location_id, area_id = parts
    world_state = await state_manager.get_world_state(experience_id)
    locations = world_state.get("locations", {})
    location_data = locations.get(location_id, {})
    areas = location_data.get("areas", {})
    area_data = areas.get(area_id)

    if not area_data:
        return CommandResult(
            success=False,
            message_to_player=f"❌ Area '{area_id}' not found in location '{location_id}'.\n\nUse @examine location {location_id} to see valid areas."
        )

    # Analyze editable properties (skip 'items' - it's structural)
    area_props = {k: v for k, v in area_data.items() if k not in ("items", "id")}
    editable_props = _analyze_editable_properties(area_props)

    # Count items
    items = area_data.get("items", [])
    item_count = len(items)
    item_list = ", ".join([item.get("instance_id", "?") for item in items]) if items else "None"

    json_str = json.dumps(area_data, indent=2)

    narrative = f"""📦 Area: {location_id}.{area_id} ({area_data.get('name', area_id)})

JSON Structure:
```json
{json_str}
```

Parent location: {location_id}
Items: {item_count} items ({item_list})

Editable properties:
{_format_properties(editable_props)}

Examples:
  @edit area {location_id}.{area_id} description "New area description"
  @examine item {items[0].get('instance_id') if items else '<item_id>'}
"""

    return CommandResult(
        success=True,
        message_to_player=narrative,
        metadata={
            "command_type": "admin_examine",
            "object_type": "area",
            "object_id": area_path,
            "raw_json": area_data,
            "editable_properties": editable_props
        }
    )


async def _find_item_in_world(world_state: Dict, item_id: str) -> Tuple[Optional[Dict], str, Dict]:
    """
    Find item in world state and return (item_data, world_path, location_context).

    Searches:
    - Top-level location items: locations.*.items
    - Area items: locations.*.areas.*.items
    """
    locations = world_state.get("locations", {})

    for location_id, location_data in locations.items():
        # Check top-level items
        items = location_data.get("items", [])
        for idx, item in enumerate(items):
            if item.get("instance_id") == item_id:
                world_path = f"locations.{location_id}.items[instance_id={item_id}]"
                context = {"location": location_id, "area": None}
                return (item, world_path, context)

        # Check area items
        areas = location_data.get("areas", {})
        for area_id, area_data in areas.items():
            area_items = area_data.get("items", [])
            for idx, item in enumerate(area_items):
                if item.get("instance_id") == item_id:
                    world_path = f"locations.{location_id}.areas.{area_id}.items[instance_id={item_id}]"
                    context = {"location": location_id, "area": area_id}
                    return (item, world_path, context)

    return (None, "", {})


def _analyze_editable_properties(data: Dict, prefix: str = "") -> Dict[str, Dict]:
    """
    Recursively analyze object to find editable properties.

    Returns: {
        "property.path": {"type": "string", "current": "value"},
        ...
    }
    """
    properties = {}

    for key, value in data.items():
        # Skip system keys
        if key in ("instance_id", "template_id", "id", "metadata"):
            continue

        property_path = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            # Recurse into nested objects
            nested = _analyze_editable_properties(value, property_path)
            properties.update(nested)
        elif isinstance(value, list):
            # Skip arrays for now (complex editing)
            continue
        else:
            # Leaf property
            properties[property_path] = {
                "type": type(value).__name__,
                "current": value
            }

    return properties


def _format_properties(props: Dict[str, Dict]) -> str:
    """Format editable properties as bullet list."""
    if not props:
        return "No editable properties found"

    lines = []
    for path, info in sorted(props.items()):
        current_val = info["current"]
        # Truncate long strings
        if isinstance(current_val, str) and len(current_val) > 50:
            current_val = current_val[:47] + "..."
        lines.append(f"- {path} ({info['type']}) = {json.dumps(current_val)}")
    return "\n".join(lines)


def _generate_example_value(type_name: str, current_value: Any) -> str:
    """Generate example new value for edit command."""
    if type_name == "bool":
        return "false" if current_value else "true"
    elif type_name == "str":
        return '"New description"'
    elif type_name in ("int", "float"):
        return str(int(current_value) + 1) if isinstance(current_value, (int, float)) else "123"
    else:
        return '"new_value"'
