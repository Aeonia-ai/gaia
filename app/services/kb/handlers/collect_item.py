# app/services/kb/handlers/collect_item.py
"""
Fast command handler for item collection in GAIA experiences.

Provides production-ready item collection with world state synchronization,
validation, and real-time event publishing. Bypasses LLM for <100ms response time.
"""

import logging
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

from app.shared.models.command_result import CommandResult
from app.services.kb.kb_agent import kb_agent # To access the state manager

logger = logging.getLogger(__name__)

async def handle_collect_item(user_id: str, experience_id: str, command_data: Dict[str, Any]) -> CommandResult:
    """
    Handles the 'collect_item' action directly for high performance.
    Bypasses the LLM and interacts directly with the state manager.

    Production implementation:
    - Validates item exists and is accessible
    - Removes item from world state (using nested dict $remove operation)
    - Adds item to player inventory
    - Publishes v0.4 WorldUpdate events (via update_player_view)

    Args:
        user_id: User ID performing the collection
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data containing 'instance_id' or 'item_id'

    Returns:
        CommandResult with success status, message, and state changes

    Response time: <100ms (4,000x faster than LLM path)
    """
    # Accept instance_id (preferred) or item_id (legacy) during transition
    instance_id = command_data.get("instance_id") or command_data.get("item_id")
    if not instance_id:
        return CommandResult(
            success=False,
            message_to_player="Action 'collect_item' requires 'instance_id' or 'item_id' field."
        )

    try:
        state_manager = kb_agent.state_manager
        if not state_manager:
            raise Exception("State manager not initialized")

        # Get player state to determine current location
        player_view = await state_manager.get_player_view(experience_id, user_id)
        current_location = player_view.get("player", {}).get("current_location")
        current_area = player_view.get("player", {}).get("current_area")

        if not current_location:
            return CommandResult(
                success=False,
                message_to_player="You don't have a current location. Please update your GPS location first."
            )

        # Get world state to find and validate the item
        world_state = await state_manager.get_world_state(experience_id)

        # Find the item in world state
        item_data, item_path = await _find_item_in_world(
            world_state,
            instance_id,
            current_location,
            current_area
        )

        if not item_data:
            # Try to find item anywhere to provide helpful error message
            any_item, any_path = await _find_item_anywhere(world_state, instance_id)
            if any_item:
                return CommandResult(
                    success=False,
                    message_to_player=f"You don't see that item here. It's somewhere else in the world."
                )
            return CommandResult(
                success=False,
                message_to_player=f"Item '{instance_id}' not found anywhere in the world."
            )

        # Check if item is collectible
        if not item_data.get("collectible", True):
            return CommandResult(
                success=False,
                message_to_player=f"You can't collect {item_data.get('semantic_name', 'that item')}."
            )

        logger.info(f"User {user_id} collecting item {instance_id} from {item_path}")

        # Remove from world state first (this operation could fail)
        # Build nested dict update structure based on item_path
        # Extract spot_id from item_path if present (e.g., "locations.store.areas.main_room.spots.spot_1.items")
        spot_id = None
        if ".spots." in item_path:
            parts = item_path.split(".")
            spot_index = parts.index("spots")
            if spot_index + 1 < len(parts):
                spot_id = parts[spot_index + 1]

        world_updates = _build_nested_remove(item_path, instance_id, current_location, current_area, spot_id)

        # Update world state (now publishes event via _flatten_nested_changes)
        await state_manager.update_world_state(
            experience=experience_id,
            updates=world_updates,
            user_id=user_id  # Publish world_update event with proper changes
        )

        # Add to player inventory (this auto-publishes WorldUpdate event)
        # Use nested dict format for state merge
        inventory_updates = {
            "player": {
                "inventory": {
                    "$append": item_data
                }
            }
        }

        await state_manager.update_player_view(
            experience=experience_id,
            user_id=user_id,
            updates=inventory_updates
        )

        # Get item name for message
        item_name = item_data.get("semantic_name") or item_data.get("template_id") or instance_id

        return CommandResult(
            success=True,
            state_changes={
                "world": world_updates,
                "player": inventory_updates
            },
            message_to_player=f"You collected {item_name}.",
            metadata={
                "instance_id": instance_id,
                "location": current_location,
                "area": current_area
            }
        )

    except Exception as e:
        logger.error(f"Error in handle_collect_item: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"Could not collect {instance_id}. {str(e)}"
        )


async def _find_item_in_world(
    world_state: Dict[str, Any],
    instance_id: str,
    current_location: str,
    current_area: Optional[str]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Find item in world state at player's current location/area.

    NEW HIERARCHY: zone > area (room) > spot (position) > items

    Args:
        world_state: Full world state dictionary
        instance_id: Item instance ID to find (e.g., "bottle_mystery")
        current_location: Player's current location ID (zone)
        current_area: Player's current area ID (None = search entire zone)

    Returns:
        Tuple of (item_data, item_path) where:
        - item_data: Full item dictionary if found, None otherwise
        - item_path: Dotted path string (e.g., "locations.woander_store.areas.main_room.spots.spot_1.items")
    """
    location_data = world_state.get("locations", {}).get(current_location, {})

    # MVP Demo: If current_area is None, player can access entire zone
    # Search all areas and all spots within those areas
    if current_area is None:
        # Check top-level location items first (legacy support)
        items = location_data.get("items", [])
        for item in items:
            if item.get("instance_id") == instance_id:
                item_path = f"locations.{current_location}.items"
                return (item, item_path)

        # Search all areas in this location
        areas = location_data.get("areas", {})
        for area_id, area_data in areas.items():
            # Check area-level items (legacy structure support)
            items = area_data.get("items", [])
            for item in items:
                if item.get("instance_id") == instance_id:
                    item_path = f"locations.{current_location}.areas.{area_id}.items"
                    return (item, item_path)

            # Search all spots within this area (NEW hierarchy)
            spots = area_data.get("spots", {})
            for spot_id, spot_data in spots.items():
                items = spot_data.get("items", [])
                for item in items:
                    if item.get("instance_id") == instance_id:
                        item_path = f"locations.{current_location}.areas.{area_id}.spots.{spot_id}.items"
                        return (item, item_path)

        return (None, None)

    # Legacy: If current_area is specified, only search that specific area
    else:
        area_data = location_data.get("areas", {}).get(current_area, {})

        # Check area-level items first (legacy support)
        items = area_data.get("items", [])
        for item in items:
            if item.get("instance_id") == instance_id:
                item_path = f"locations.{current_location}.areas.{current_area}.items"
                return (item, item_path)

        # Search all spots within this area (NEW hierarchy)
        spots = area_data.get("spots", {})
        for spot_id, spot_data in spots.items():
            items = spot_data.get("items", [])
            for item in items:
                if item.get("instance_id") == instance_id:
                    item_path = f"locations.{current_location}.areas.{current_area}.spots.{spot_id}.items"
                    return (item, item_path)

        # Fall back to top-level location items
        items = location_data.get("items", [])
        for item in items:
            if item.get("instance_id") == instance_id:
                item_path = f"locations.{current_location}.items"
                return (item, item_path)

        return (None, None)


async def _find_item_anywhere(
    world_state: Dict[str, Any],
    instance_id: str
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Find item anywhere in world state (used for helpful error messages).

    NEW HIERARCHY: Searches zone > area > spot > items

    Args:
        world_state: Full world state dictionary
        instance_id: Item instance ID to find

    Returns:
        Tuple of (item_data, item_path) if found anywhere, else (None, None)
    """
    locations = world_state.get("locations", {})

    for location_id, location_data in locations.items():
        # Check top-level items (legacy support)
        for item in location_data.get("items", []):
            if item.get("instance_id") == instance_id:
                return (item, f"locations.{location_id}.items")

        # Check all areas
        areas = location_data.get("areas", {})
        for area_id, area_data in areas.items():
            # Check area-level items (legacy support)
            for item in area_data.get("items", []):
                if item.get("instance_id") == instance_id:
                    return (item, f"locations.{location_id}.areas.{area_id}.items")

            # Check all spots within this area (NEW hierarchy)
            spots = area_data.get("spots", {})
            for spot_id, spot_data in spots.items():
                for item in spot_data.get("items", []):
                    if item.get("instance_id") == instance_id:
                        return (item, f"locations.{location_id}.areas.{area_id}.spots.{spot_id}.items")

    return (None, None)


def _build_nested_remove(
    item_path: str,
    instance_id: str,
    location_id: str,
    area_id: Optional[str],
    spot_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build nested dictionary structure for removing item from world state.

    NEW HIERARCHY: Supports zone > area > spot > items structure

    Note: update_world_state() merges nested dicts for state updates, then
    _flatten_nested_changes() converts them to flattened paths for v0.4 events.

    Args:
        item_path: Dotted path string (e.g., "locations.store.areas.main_room.spots.spot_1.items")
        instance_id: Item instance ID to remove
        location_id: Location ID (e.g., "woander_store")
        area_id: Area ID (e.g., "main_room"), required if spot_id is provided, None for top-level items
        spot_id: Spot ID (e.g., "spot_1"), None for area-level items

    Returns:
        Nested dict structure with $remove operation, e.g.:
        {"locations": {"woander_store": {"areas": {"main_room": {"spots": {"spot_1": {"items": {"$remove": {...}}}}}}}}}

    Example:
        >>> _build_nested_remove("...", "bottle_mystery", "woander_store", "main_room", "spot_1")
        {'locations': {'woander_store': {'areas': {'main_room': {'spots': {'spot_1': {'items': {'$remove': {'instance_id': 'bottle_mystery'}}}}}}}}}
    """
    remove_op = {"$remove": {"instance_id": instance_id}}

    if spot_id:
        # NEW HIERARCHY: Item is in a spot within an area
        # Must have area_id to build proper path
        if not area_id:
            raise ValueError(f"spot_id provided ({spot_id}) but area_id is None - cannot build nested path")
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
    elif area_id:
        # Legacy: Item is in an area (no spots)
        return {
            "locations": {
                location_id: {
                    "areas": {
                        area_id: {
                            "items": remove_op
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
                    "items": remove_op
                }
            }
        }
