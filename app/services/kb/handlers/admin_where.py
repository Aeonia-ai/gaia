# app/services/kb/handlers/admin_where.py
"""
Admin command handler for showing current location context.

Provides technical view of admin's current location with all items and properties.
Bypasses LLM for <5ms response time.

This is a read-only operation - no state changes, no WorldUpdate events.
Shows admin view with technical IDs and property flags.
"""

import logging
from typing import Any, Dict, List

from app.shared.models.command_result import CommandResult

logger = logging.getLogger(__name__)


async def handle_admin_where(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handles the '@where' admin command for location context.

    Admin implementation:
    - Shows current location and area with technical IDs
    - Lists ALL items in area (visible + hidden)
    - Shows item properties (visible, collectible flags)
    - Lists NPCs in area
    - Shows all areas in location
    - Provides ready-to-use edit commands
    - Read-only: No state changes

    Args:
        user_id: Admin user ID
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data with action string "@where"

    Returns:
        CommandResult with location context and item details

    Response time: <5ms (read-only operation)

    Example:
        >>> await handle_admin_where(
        ...     user_id="admin@example.com",
        ...     experience_id="wylding-woods",
        ...     command_data={"action": "@where"}
        ... )
        CommandResult(success=True, message_to_player="📍 Current Location...")
    """
    from ..kb_agent import kb_agent

    state_manager = kb_agent.state_manager
    if not state_manager:
        return CommandResult(
            success=False,
            message_to_player="State manager not initialized."
        )

    # @where command has no parameters, just "@where"

    try:
        # Get player state to determine current location
        player_view = await state_manager.get_player_view(experience_id, user_id)
        current_location = player_view.get("player", {}).get("current_location")
        current_area = player_view.get("player", {}).get("current_area")

        if not current_location:
            return CommandResult(
                success=False,
                message_to_player="❌ Could not determine your current location.\n\nYour player state may not be initialized. Try:\n- look (to see player view)\n- go <location> (to move somewhere)"
            )

        # Get world state
        world_state = await state_manager.get_world_state(experience_id)
        locations = world_state.get("locations", {})
        location_data = locations.get(current_location)

        if not location_data:
            return CommandResult(
                success=False,
                message_to_player=f"❌ Location '{current_location}' not found in world state."
            )

        location_name = location_data.get("name", current_location)

        # Get area data if in area
        area_data = None
        area_name = None
        if current_area:
            areas = location_data.get("areas", {})
            area_data = areas.get(current_area)
            if area_data:
                area_name = area_data.get("name", current_area)

        # Build narrative
        if current_area and area_data:
            # Admin is in an area
            narrative = await _build_area_view(
                current_location,
                location_name,
                current_area,
                area_name,
                area_data,
                location_data
            )
        else:
            # Admin is at top-level location
            narrative = await _build_location_view(
                current_location,
                location_name,
                location_data
            )

        return CommandResult(
            success=True,
            message_to_player=narrative,
            metadata={
                "command_type": "admin_where",
                "current_location": current_location,
                "current_area": current_area,
                "items_count": len(area_data.get("items", [])) if area_data else len(location_data.get("items", [])),
                "admin_command": True
            }
        )

    except Exception as e:
        logger.error(f"Failed to get location context: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player="Failed to get location context."
        )


async def _build_area_view(
    location_id: str,
    location_name: str,
    area_id: str,
    area_name: str,
    area_data: Dict,
    location_data: Dict
) -> str:
    """Build admin view for when in an area."""
    description = area_data.get("description", "No description")

    # List items in this area
    items = area_data.get("items", [])
    items_str = _format_items_list(items)

    # List NPCs (placeholder - not yet implemented in world state)
    npcs_str = "None"

    # Build area summary for parent location
    areas = location_data.get("areas", {})
    areas_list = []
    for aid, adata in areas.items():
        # Count NPCs in area (placeholder)
        area_npcs = []  # TODO: Get from world state when NPCs implemented
        npc_suffix = f" - NPC: {', '.join(area_npcs)}" if area_npcs else ""
        marker = " ⬅️  YOU ARE HERE" if aid == area_id else ""
        areas_list.append(f"- {aid} ({adata.get('name', aid)}){npc_suffix}{marker}")

    areas_str = "\n".join(areas_list) if areas_list else "No areas"

    # Generate action suggestions
    actions = []
    if items:
        first_item = items[0].get("instance_id")
        actions.append(f"  @examine item {first_item}")
        actions.append(f"  @edit item {first_item} visible false")
    actions.append(f"  @list-items")
    actions.append(f"  @examine location {location_id}")

    actions_str = "\n".join(actions)

    narrative = f"""📍 Current Location: {location_id} ({location_name})
📍 Current Area: {area_id} ({area_name})

Description: {description}

Items in this area:
{items_str}

NPCs in this area: {npcs_str}

All areas in this location:
{areas_str}

Actions:
{actions_str}
"""

    return narrative


async def _build_location_view(
    location_id: str,
    location_name: str,
    location_data: Dict
) -> str:
    """Build admin view for when at top-level location."""
    description = location_data.get("description", "No description")

    # List items at this location
    items = location_data.get("items", [])
    items_str = _format_items_list(items)

    # List NPCs (placeholder)
    npcs_str = "None"

    # Check if location has areas
    areas = location_data.get("areas", {})
    if areas:
        areas_note = f"This location has {len(areas)} areas. Use 'go <area>' to enter an area."
    else:
        areas_note = "This location has no sublocations/areas."

    # Generate action suggestions
    actions = []
    if items:
        first_item = items[0].get("instance_id")
        actions.append(f"  @examine item {first_item}")
        actions.append(f"  @edit item {first_item} visible false")
    actions.append(f"  @examine location {location_id}")

    actions_str = "\n".join(actions)

    narrative = f"""📍 Current Location: {location_id} ({location_name})

Description: {description}

Items at this location:
{items_str}

NPCs at this location: {npcs_str}

{areas_note}

Actions:
{actions_str}
"""

    return narrative


def _format_items_list(items: List[Dict]) -> str:
    """Format items list with properties."""
    if not items:
        return "None"

    lines = []
    for idx, item in enumerate(items, 1):
        instance_id = item.get("instance_id", "?")
        semantic_name = item.get("semantic_name", instance_id)
        visible = item.get("visible", True)
        collectible = item.get("collectible", True)

        lines.append(f"{idx}. {instance_id} ({semantic_name}) - visible: {visible}, collectible: {collectible}")

    return "\n".join(lines)
