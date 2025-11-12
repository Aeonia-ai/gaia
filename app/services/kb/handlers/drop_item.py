# app/services/kb/handlers/drop_item.py
"""
Fast command handler for dropping items in GAIA experiences.

Provides production-ready item dropping with world state synchronization,
validation, and real-time event publishing. Bypasses LLM for <20ms response time.

This is the inverse of collect_item - removes items from player inventory
and places them in the world at the player's current location/area.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from app.shared.models.command_result import CommandResult

logger = logging.getLogger(__name__)


async def handle_drop_item(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handles the 'drop_item' action directly for high performance.

    Production implementation:
    - Validates item exists in player inventory
    - Removes item from player inventory
    - Adds item to world state at current location/area
    - Publishes v0.4 WorldUpdate events (via update_player_view)

    Args:
        user_id: User ID performing the drop
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data containing 'instance_id' or 'item_id'

    Returns:
        CommandResult with success status, message, and state changes

    Response time: <20ms (1,250x faster than LLM path)

    Example:
        >>> await handle_drop_item(
        ...     user_id="user_123",
        ...     experience_id="wylding-woods",
        ...     command_data={"instance_id": "dream_bottle_1"}
        ... )
        CommandResult(success=True, message_to_player="You dropped peaceful dream bottle.")
    """
    from ..kb_agent import kb_agent

    state_manager = kb_agent.state_manager
    if not state_manager:
        return CommandResult(
            success=False,
            message_to_player="State manager not initialized."
        )

    # Extract instance_id (support both formats for compatibility)
    instance_id = command_data.get("instance_id") or command_data.get("item_id")

    if not instance_id:
        return CommandResult(
            success=False,
            message_to_player="Please specify which item to drop."
        )

    # Get player state
    try:
        player_view = await state_manager.get_player_view(experience_id, user_id)
    except Exception as e:
        logger.error(f"Failed to get player view: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player="Failed to access player state."
        )

    # Get player location
    current_location = player_view.get("player", {}).get("current_location")
    current_area = player_view.get("player", {}).get("current_area")

    if not current_location:
        return CommandResult(
            success=False,
            message_to_player="You must be in a location to drop items."
        )

    # Find item in inventory
    inventory = player_view.get("player", {}).get("inventory", [])
    item_data = None

    for item in inventory:
        if item.get("instance_id") == instance_id or item.get("id") == instance_id:
            item_data = item.copy()
            break

    if not item_data:
        return CommandResult(
            success=False,
            message_to_player=f"You don't have '{instance_id}' in your inventory."
        )

    # Get item name for response message
    item_name = item_data.get("semantic_name", item_data.get("name", "item"))

    # Check if item is droppable (some items might be quest items or bound)
    if item_data.get("droppable") is False:
        return CommandResult(
            success=False,
            message_to_player=f"You can't drop {item_name}."
        )

    # Remove from inventory
    inventory_updates = {
        "player": {
            "inventory": {
                "$remove": {"instance_id": instance_id}
            }
        }
    }

    # Add to world state at current location/area
    # Build nested dict structure for world update
    world_updates = _build_nested_add(item_data, current_location, current_area)

    try:
        # Update world state first (don't publish yet)
        await state_manager.update_world_state(
            experience=experience_id,
            updates=world_updates,
            user_id=None  # Don't publish here - let update_player_view handle it
        )

        # Update inventory (auto-publishes WorldUpdate event)
        await state_manager.update_player_view(
            experience=experience_id,
            user_id=user_id,
            updates=inventory_updates
        )

        return CommandResult(
            success=True,
            state_changes={
                "world": world_updates,
                "player": inventory_updates
            },
            message_to_player=f"You dropped {item_name}.",
            metadata={
                "instance_id": instance_id,
                "location": current_location,
                "area": current_area
            }
        )

    except Exception as e:
        logger.error(f"Failed to drop item: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"Failed to drop {item_name}."
        )


def _build_nested_add(
    item_data: Dict[str, Any],
    location_id: str,
    area_id: Optional[str]
) -> Dict[str, Any]:
    """
    Build nested dictionary structure for adding item to world state.

    CRITICAL: update_world_state() requires nested dicts, NOT dotted path strings.
    Uses $append operation to add item to items array at the specified location/area.

    Args:
        item_data: Complete item object with instance_id, template_id, state, etc.
        location_id: Location where item should be dropped (e.g., "woander_store")
        area_id: Optional area within location (e.g., "spawn_zone_1")

    Returns:
        Nested dict structure for world state update

    Example:
        >>> _build_nested_add(
        ...     {"instance_id": "bottle_1", "template_id": "dream_bottle"},
        ...     "woander_store",
        ...     "spawn_zone_1"
        ... )
        {
            'locations': {
                'woander_store': {
                    'areas': {
                        'spawn_zone_1': {
                            'items': {'$append': {...}}
                        }
                    }
                }
            }
        }
    """
    append_op = {"$append": item_data}

    if area_id:
        # Item dropped in an area - build 4-level nested structure
        return {
            "locations": {
                location_id: {
                    "areas": {
                        area_id: {
                            "items": append_op
                        }
                    }
                }
            }
        }
    else:
        # Item dropped at top-level location - build 3-level structure
        return {
            "locations": {
                location_id: {
                    "items": append_op
                }
            }
        }
