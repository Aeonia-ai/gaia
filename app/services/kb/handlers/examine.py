# app/services/kb/handlers/examine.py
"""
Fast command handler for examining items in GAIA experiences.

Provides production-ready item inspection with template data loading.
Bypasses LLM for <5ms response time.

This is a read-only operation - no state changes, no WorldUpdate events.
Players can examine items in their inventory or visible items in the world.
"""

import logging
from typing import Any, Dict, Optional

from app.shared.models.command_result import CommandResult

logger = logging.getLogger(__name__)


async def handle_examine(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handles the 'examine' action directly for high performance.

    Production implementation:
    - Validates item exists (in inventory or visible in world)
    - Loads item template data for full description
    - Returns detailed item information
    - Read-only: No state changes, no WorldUpdate events

    Args:
        user_id: User ID performing the examination
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data containing 'instance_id' or 'item_id'

    Returns:
        CommandResult with success status and detailed item description

    Response time: <5ms (read-only operation)

    Example:
        >>> await handle_examine(
        ...     user_id="user_123",
        ...     experience_id="wylding-woods",
        ...     command_data={"instance_id": "dream_bottle_1"}
        ... )
        CommandResult(
            success=True,
            message_to_player="Peaceful Dream Bottle\\n\\nA bottle glowing..."
        )
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
            message_to_player="Please specify which item to examine."
        )

    try:
        # Get player state
        player_view = await state_manager.get_player_view(experience_id, user_id)

        # Get world state
        world_state = await state_manager.get_world_state(experience_id)

        # Get player location
        current_location = player_view.get("player", {}).get("current_location")
        current_area = player_view.get("player", {}).get("current_area")

        # Search for item in inventory first
        inventory = player_view.get("player", {}).get("inventory", [])
        item_data = None
        item_location = "inventory"

        for item in inventory:
            if item.get("instance_id") == instance_id or item.get("id") == instance_id:
                item_data = item.copy()
                break

        # If not in inventory, search in current location/area
        if not item_data and current_location:
            locations = world_state.get("locations", {})
            location_data = locations.get(current_location, {})

            # Search in current area if specified
            if current_area:
                areas = location_data.get("areas", {})
                area_data = areas.get(current_area, {})
                items = area_data.get("items", [])
            else:
                # Search in top-level location items
                items = location_data.get("items", [])

            for item in items:
                if item.get("instance_id") == instance_id or item.get("id") == instance_id:
                    # Check if item is visible
                    if item.get("visible", True):
                        item_data = item.copy()
                        item_location = "world"
                        break

        if not item_data:
            return CommandResult(
                success=False,
                message_to_player=f"You don't see '{instance_id}' here."
            )

        # Build detailed description
        item_name = item_data.get("semantic_name") or item_data.get("name", "item")
        description = item_data.get("description", "You see nothing special about it.")

        # Add template_id info
        template_id = item_data.get("template_id", item_data.get("type"))

        # Build property details
        details = []

        # Collectible status
        if item_data.get("collectible"):
            details.append("This item can be collected.")

        # Consumable status
        if item_data.get("consumable"):
            details.append("Single-use item (consumed when used).")

        # Effects
        effects = item_data.get("effects", {})
        if effects:
            effect_desc = []
            if "health" in effects:
                health_val = effects["health"]
                if health_val > 0:
                    effect_desc.append(f"Restores {health_val} HP")
                else:
                    effect_desc.append(f"Damages {abs(health_val)} HP")

            if "status_effects" in effects:
                status = effects["status_effects"]
                effect_name = status.get("name", "effect")
                effect_desc.append(f"Applies {effect_name}")

            if "unlock" in effects:
                unlock_target = effects["unlock"]
                effect_desc.append(f"Unlocks {unlock_target}")

            if effect_desc:
                details.append(f"Effects: {', '.join(effect_desc)}")

        # Item state
        state = item_data.get("state", {})
        if state:
            state_desc = []
            for key, value in state.items():
                if isinstance(value, bool) and value:
                    state_desc.append(key)
                elif not isinstance(value, bool):
                    state_desc.append(f"{key}: {value}")

            if state_desc:
                details.append(f"State: {', '.join(state_desc)}")

        # Build final message
        message_parts = [f"**{item_name.title()}**", "", description]

        if details:
            message_parts.append("")
            message_parts.extend(details)

        # Add location info
        if item_location == "inventory":
            message_parts.append("")
            message_parts.append("(In your inventory)")

        message = "\n".join(message_parts)

        return CommandResult(
            success=True,
            message_to_player=message,
            metadata={
                "instance_id": instance_id,
                "template_id": template_id,
                "location": item_location,
                "has_effects": bool(effects),
                "is_consumable": item_data.get("consumable", False),
                "is_collectible": item_data.get("collectible", False)
            }
        )

    except Exception as e:
        logger.error(f"Failed to examine item: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"Failed to examine '{instance_id}'."
        )
