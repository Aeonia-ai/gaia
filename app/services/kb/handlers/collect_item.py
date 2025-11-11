# app/services/kb/handlers/collect_item.py

import logging
from typing import Any, Dict
from datetime import datetime

from app.shared.models.command_result import CommandResult
from app.services.kb.kb_agent import kb_agent # To access the state manager

logger = logging.getLogger(__name__)

async def handle_collect_item(user_id: str, experience_id: str, command_data: Dict[str, Any]) -> CommandResult:
    """
    Handles the 'collect_item' action directly for high performance.
    Bypasses the LLM and interacts directly with the state manager.
    """
    # Accept instance_id (preferred) or item_id (legacy) during transition
    item_id = command_data.get("instance_id") or command_data.get("item_id")
    if not item_id:
        return CommandResult(
            success=False,
            message_to_player="Action 'collect_item' requires 'instance_id' or 'item_id' field."
        )

    try:
        state_manager = kb_agent.state_manager
        if not state_manager:
            raise Exception("State manager not initialized")

        # For now, we assume the item is collectible. 
        # A real implementation would check the world state to see if the item exists and is accessible.

        logger.info(f"User {user_id} is collecting item {item_id}")

        # Define the state changes
        state_changes = {
            "player.inventory": {
                "$append": {
                    "id": item_id,
                    "type": "collectible", # This could be dynamic in the future
                    "collected_at": datetime.utcnow().isoformat() + "Z"
                }
            }
            # In a full implementation, we would also add a change to remove the item from the world state.
        }

        # Apply the changes
        await state_manager.update_player_view(
            experience=experience_id,
            user_id=user_id,
            updates=state_changes
        )

        return CommandResult(
            success=True,
            state_changes=state_changes,
            message_to_player=f"You have collected {item_id}."
        )

    except Exception as e:
        logger.error(f"Error in handle_collect_item: {e}", exc_info=True)
        return CommandResult(success=False, message_to_player=f"Could not collect {item_id}.")
