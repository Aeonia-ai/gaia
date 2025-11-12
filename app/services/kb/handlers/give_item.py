# app/services/kb/handlers/give_item.py
"""
Fast command handler for giving items to NPCs or players in GAIA experiences.

Provides production-ready item transfer with proximity validation and
extensible hooks for quest/reward systems. Bypasses LLM for <10ms response time.

Current implementation: NPC item delivery only (player transfer deferred)
"""

import logging
from typing import Any, Dict

from app.shared.models.command_result import CommandResult

logger = logging.getLogger(__name__)


async def handle_give_item(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handles the 'give_item' action directly for high performance.

    Production implementation:
    - Validates item exists in player inventory
    - Validates proximity to target (same location/area)
    - Removes item from player inventory
    - For NPCs: Calls hook for future quest/reward logic
    - For Players: Deferred to future implementation

    Args:
        user_id: User ID giving the item
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data containing:
            - instance_id: Item to give
            - target_npc_id: NPC to give to (optional)
            - target_player_id: Player to give to (optional, not implemented)

    Returns:
        CommandResult with success status, NPC dialogue, and metadata

    Response time: <10ms

    Example:
        >>> await handle_give_item(
        ...     user_id="user_123",
        ...     experience_id="wylding-woods",
        ...     command_data={
        ...         "instance_id": "dream_bottle_1",
        ...         "target_npc_id": "louisa"
        ...     }
        ... )
        CommandResult(
            success=True,
            message_to_player="Louisa: Thank you for the peaceful dream bottle."
        )
    """
    from ..kb_agent import kb_agent

    state_manager = kb_agent.state_manager
    if not state_manager:
        return CommandResult(
            success=False,
            message_to_player="State manager not initialized."
        )

    # Extract parameters
    instance_id = command_data.get("instance_id") or command_data.get("item_id")
    target_npc_id = command_data.get("target_npc_id")
    target_player_id = command_data.get("target_player_id")

    if not instance_id:
        return CommandResult(
            success=False,
            message_to_player="Please specify which item to give."
        )

    if not target_npc_id and not target_player_id:
        return CommandResult(
            success=False,
            message_to_player="Please specify who to give the item to."
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

    current_location = player_view.get("player", {}).get("current_location")
    current_area = player_view.get("player", {}).get("current_area")

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

    item_name = item_data.get("semantic_name", item_data.get("name", "item"))

    # Route to appropriate handler
    if target_npc_id:
        return await _handle_npc_delivery(
            user_id=user_id,
            experience_id=experience_id,
            npc_id=target_npc_id,
            item_data=item_data,
            item_name=item_name,
            current_location=current_location,
            current_area=current_area,
            state_manager=state_manager
        )

    elif target_player_id:
        # Player-to-player transfer deferred to Phase 2
        return CommandResult(
            success=False,
            message_to_player="Player-to-player trading is not yet implemented."
        )


async def _handle_npc_delivery(
    user_id: str,
    experience_id: str,
    npc_id: str,
    item_data: Dict[str, Any],
    item_name: str,
    current_location: str,
    current_area: str,
    state_manager
) -> CommandResult:
    """
    Handle item delivery to NPC.

    Validates proximity, removes item, calls quest hook.
    """
    # Get world state to find NPC location
    try:
        world_state = await state_manager.get_world_state(experience_id)
    except Exception as e:
        logger.error(f"Failed to get world state: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player="Failed to access world state."
        )

    # Find NPC in world
    npc_location = None
    npc_area = None
    npc_name = npc_id.replace("_", " ").title()

    locations = world_state.get("locations", {})
    for loc_id, loc_data in locations.items():
        # Check top-level location
        if loc_data.get("npc") == npc_id:
            npc_location = loc_id
            npc_name = loc_data.get("npc_name", npc_name)
            break

        # Check areas
        areas = loc_data.get("areas", {})
        for area_id, area_data in areas.items():
            if area_data.get("npc") == npc_id:
                npc_location = loc_id
                npc_area = area_id
                npc_name = area_data.get("npc_name", npc_name)
                break

        if npc_location:
            break

    if not npc_location:
        return CommandResult(
            success=False,
            message_to_player=f"NPC '{npc_id}' not found in this experience."
        )

    # Validate proximity
    if current_location != npc_location:
        return CommandResult(
            success=False,
            message_to_player=f"You must be in the same location as {npc_name}."
        )

    if npc_area and current_area != npc_area:
        return CommandResult(
            success=False,
            message_to_player=f"You must be near {npc_name} to give items."
        )

    # Remove item from player inventory
    try:
        await state_manager.update_player_view(
            experience=experience_id,
            user_id=user_id,
            updates={
                "player": {
                    "inventory": {
                        "$remove": {"instance_id": item_data["instance_id"]}
                    }
                }
            }
        )
    except Exception as e:
        logger.error(f"Failed to remove item from inventory: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"Failed to give {item_name} to {npc_name}."
        )

    # Call quest/reward hook (extensible for future implementation)
    hook_result = await _process_npc_item(
        experience_id=experience_id,
        npc_id=npc_id,
        npc_name=npc_name,
        item_data=item_data,
        user_id=user_id
    )

    # Build response message
    dialogue = hook_result.get("dialogue", f"{npc_name}: Thank you for the {item_name}.")

    return CommandResult(
        success=True,
        message_to_player=dialogue,
        metadata={
            "npc_id": npc_id,
            "item_delivered": True,
            "item_instance_id": item_data["instance_id"],
            "item_template_id": item_data.get("template_id"),
            "hook_result": hook_result
        }
    )


async def _process_npc_item(
    experience_id: str,
    npc_id: str,
    npc_name: str,
    item_data: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """
    Hook for future quest/reward system integration.

    This is called after item is removed from player inventory.
    Future implementations can:
    - Validate item requirements
    - Award XP, reputation, items
    - Update quest progress
    - Return item if validation fails
    - Trigger NPC dialogue sequences

    Args:
        experience_id: Experience ID
        npc_id: NPC receiving the item
        npc_name: NPC display name
        item_data: Complete item data with instance_id, template_id, state
        user_id: Player giving the item

    Returns:
        {
            "accepted": bool,
            "dialogue": str,
            "rewards": dict,  # Future: XP, items, reputation
            "quest_updates": dict  # Future: Quest progress
        }
    """
    # MVP: Accept all items with generic dialogue
    item_name = item_data.get("semantic_name", item_data.get("name", "item"))

    return {
        "accepted": True,
        "dialogue": f"{npc_name}: Thank you for the {item_name}.",
        "rewards": {},
        "quest_updates": {}
    }
