# app/services/kb/handlers/admin_edit_item.py
"""
Admin command handler for editing item properties with intelligent path resolution.

Provides smart property editing with:
- Automatic item finding in nested world state
- Dot-notation for nested properties (state.glowing)
- Type inference and validation
- Before/after confirmation
- Impact messages

Bypasses LLM for <20ms response time.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from app.shared.models.command_result import CommandResult

logger = logging.getLogger(__name__)


async def handle_admin_edit_item(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handles the '@edit-item' admin command for property modification.

    Admin implementation:
    - Finds item anywhere in world state (top-level or nested areas)
    - Resolves nested property paths with dot notation
    - Infers types from string input (e.g., "false" → boolean False)
    - Validates type compatibility (prevents string-vs-boolean bugs)
    - Builds nested update structure for UnifiedStateManager
    - Returns before/after confirmation with full path

    Args:
        user_id: Admin user ID
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data with action string "@edit item bottle_mystery visible false"

    Returns:
        CommandResult with confirmation and state updates

    Response time: <20ms (direct state update)

    Example:
        >>> await handle_admin_edit_item(
        ...     user_id="admin@example.com",
        ...     experience_id="wylding-woods",
        ...     command_data={"action": "@edit item bottle_mystery visible false"}
        ... )
        CommandResult(success=True, message_to_player="🔄 Updating item...")
    """
    from ..kb_agent import kb_agent

    state_manager = kb_agent.state_manager
    if not state_manager:
        return CommandResult(
            success=False,
            message_to_player="State manager not initialized."
        )

    # Parse command string: "@edit item bottle_mystery visible false"
    # parts = ["edit", "item", "bottle_mystery", "visible", "false"]
    action_str = command_data.get("action", "")
    parts = action_str.lstrip("@").split()

    if len(parts) < 5:
        return CommandResult(
            success=False,
            message_to_player="❌ Missing required parameters.\\n\\nFormat: @edit item <id> <property> <value>\\n\\nExamples:\\n- @edit item bottle_mystery visible false\\n- @edit item bottle_mystery state.glowing false\\n- @edit item bottle_mystery description \\\"New text\\\""
        )

    # parts[0] = "edit" (command)
    # parts[1] = "item" (target type)
    # parts[2] = "bottle_mystery" (item_id)
    # parts[3] = "visible" or "state.glowing" (property_path)
    # parts[4+] = "false" or multi-word value (new_value)
    item_id = parts[2]
    property_path = parts[3]
    new_value_str = " ".join(parts[4:])  # Handle multi-word values

    try:
        # Get world state
        world_state = await state_manager.get_world_state(experience_id)

        # Find item in world state
        item_data, world_path, location_context = await _find_item_in_world(
            world_state, item_id
        )

        if not item_data:
            return CommandResult(
                success=False,
                message_to_player=f"❌ Item '{item_id}' not found.\n\nUse @list-items to see available items.\nOr @where to see items near you."
            )

        # Resolve property path to get old value
        old_value = _resolve_nested_property(item_data, property_path)

        if old_value is None:
            return CommandResult(
                success=False,
                message_to_player=f"❌ Property '{property_path}' not found on item {item_id}.\n\nUse @examine item {item_id} to see available properties."
            )

        # Infer type from string input
        new_value = _infer_value_type(new_value_str)

        # Validate type compatibility
        try:
            _validate_type_match(old_value, new_value)
        except TypeError as e:
            return CommandResult(
                success=False,
                message_to_player=f"❌ Type mismatch for property '{property_path}'\n\nExpected: {type(old_value).__name__}\nGot: {type(new_value).__name__} ({json.dumps(new_value)})\nCurrent value: {json.dumps(old_value)} ({type(old_value).__name__})\n\nTry: @edit item {item_id} {property_path} <{type(old_value).__name__}>"
            )

        # Build nested update payload
        location_id = location_context.get("location")
        area_id = location_context.get("area")

        updates = _build_nested_update(
            item_id=item_id,
            property_path=property_path,
            new_value=new_value,
            location_id=location_id,
            area_id=area_id
        )

        # Apply update to world state (no user_id = no AOI rebuild for admin)
        await state_manager.update_world_state(
            experience=experience_id,
            updates=updates,
            user_id=None  # Admin operation, no player-specific rebuild
        )

        # Build confirmation message
        full_path = f"{world_path}.{property_path}"
        impact_msg = _get_property_impact_message(property_path, new_value)

        narrative = f"""🔄 Updating item: {item_id}

Property: {property_path}
Path: {full_path}
Old value: {json.dumps(old_value)}
New value: {json.dumps(new_value)}

✅ Update successful!

{impact_msg}

To verify: @examine item {item_id}
"""

        return CommandResult(
            success=True,
            message_to_player=narrative,
            state_changes={"world": updates},
            metadata={
                "command_type": "admin_edit_item",
                "item_id": item_id,
                "property_path": property_path,
                "world_path": world_path,
                "old_value": old_value,
                "new_value": new_value,
                "admin_command": True
            }
        )

    except Exception as e:
        logger.error(f"Failed to edit item property: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"Failed to edit item '{item_id}'."
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


def _resolve_nested_property(data: Dict, property_path: str) -> Any:
    """
    Resolve dot-notation property path to actual value.

    Examples:
        _resolve_nested_property({"state": {"glowing": True}}, "state.glowing") → True
        _resolve_nested_property({"visible": False}, "visible") → False
    """
    parts = property_path.split(".")
    current = data

    for part in parts:
        if not isinstance(current, dict):
            return None

        if part not in current:
            return None

        current = current[part]

    return current


def _infer_value_type(value_str: str) -> Any:
    """
    Intelligently infer type from string input.

    Examples:
        "true" → True (boolean)
        "false" → False (boolean)
        "123" → 123 (int)
        "45.67" → 45.67 (float)
        "hello" → "hello" (string)
        '{"key": "val"}' → {"key": "val"} (JSON object)
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


def _validate_type_match(old_value: Any, new_value: Any) -> None:
    """
    Validate that new value matches type of old value.

    Raises TypeError if types don't match.
    """
    old_type = type(old_value)
    new_type = type(new_value)

    # Special case: None can be replaced by any type
    if old_value is None:
        return

    # Type must match
    if old_type != new_type:
        raise TypeError(
            f"Type mismatch: property expects {old_type.__name__}, "
            f"got {new_type.__name__}"
        )


def _build_nested_update(
    item_id: str,
    property_path: str,
    new_value: Any,
    location_id: str,
    area_id: Optional[str]
) -> Dict:
    """
    Build nested update structure for UnifiedStateManager.

    Input:
        item_id: "bottle_mystery"
        property_path: "state.glowing"
        new_value: False
        location_id: "woander_store"
        area_id: "spawn_zone_1"

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
                                        "glowing": False
                                    }
                                }]
                            }
                        }
                    }
                }
            }
        }
    """
    # Parse property path
    property_parts = property_path.split(".")

    # Build nested property update
    property_update = new_value
    for part in reversed(property_parts):
        property_update = {part: property_update}

    # Build item update with instance_id
    item_update = {
        "instance_id": item_id,
        **property_update
    }

    # Build world path update
    if area_id:
        # Item is in area
        return {
            "locations": {
                location_id: {
                    "areas": {
                        area_id: {
                            "items": {
                                "$update": [item_update]
                            }
                        }
                    }
                }
            }
        }
    else:
        # Item is at top-level location
        return {
            "locations": {
                location_id: {
                    "items": {
                        "$update": [item_update]
                    }
                }
            }
        }


def _get_property_impact_message(property_path: str, new_value: Any) -> str:
    """
    Provide context about what this property change means.
    """
    if property_path == "visible":
        if new_value:
            return "The item is now visible to players. It will appear in AOI updates."
        else:
            return "The item is now hidden from players. It will not appear in AOI updates."

    if property_path == "collectible":
        if new_value:
            return "Players can now collect this item."
        else:
            return "Players cannot collect this item (it's scenery only)."

    if "glowing" in property_path:
        if new_value:
            return "The object is now glowing with magical energy."
        else:
            return "The object's magical glow has faded."

    if property_path == "description":
        return "Item description has been updated."

    if "dream_type" in property_path:
        return f"Dream type changed to '{new_value}'."

    return ""
