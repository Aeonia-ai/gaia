# app/services/kb/handlers/go.py

import logging
from typing import Any, Dict
from datetime import datetime

from app.shared.models.command_result import CommandResult
from app.services.kb.kb_agent import kb_agent

logger = logging.getLogger(__name__)

async def handle_go(user_id: str, experience_id: str, command_data: Dict[str, Any]) -> CommandResult:
    """
    Handles the 'go' action directly for high performance.
    Bypasses the LLM and interacts directly with the state manager.

    Args:
        user_id: User ID performing the action
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data containing destination

    Returns:
        CommandResult with success status and message
    """
    # Extract destination from command data
    # Support multiple parameter names for flexibility
    destination = command_data.get("destination") or command_data.get("target") or command_data.get("area")

    if not destination:
        return CommandResult(
            success=False,
            message_to_player="Action 'go' requires 'destination', 'target', or 'area' field."
        )

    try:
        state_manager = kb_agent.state_manager
        if not state_manager:
            raise Exception("State manager not initialized")

        # Get player view to check current location
        player_view = await state_manager.get_player_view(experience_id, user_id)
        current_location = player_view.get("player", {}).get("current_location")

        if not current_location:
            return CommandResult(
                success=False,
                message_to_player="You don't have a current location. Please update your GPS location first."
            )

        # Get world state to validate destination exists
        world_state = await state_manager.get_world_state(experience_id)
        location_data = world_state.get("locations", {}).get(current_location, {})
        areas = location_data.get("areas", {})

        # Validate destination exists
        if destination not in areas:
            available = ", ".join(areas.keys()) if areas else "none"
            return CommandResult(
                success=False,
                message_to_player=f"You don't see a way to '{destination}'. Available areas: {available}"
            )

        logger.info(f"User {user_id} navigating from {current_location} to {destination}")

        # Update player's current area
        state_changes = {
            "player": {
                "current_area": destination
            }
        }

        # Apply the changes
        await state_manager.update_player_view(
            experience=experience_id,
            user_id=user_id,
            updates=state_changes
        )

        # Get area description for narrative
        area_data = areas.get(destination, {})
        area_name = area_data.get("name", destination)
        area_description = area_data.get("description", "")

        message = f"You move to {area_name}."
        if area_description:
            message += f" {area_description}"

        return CommandResult(
            success=True,
            state_changes=state_changes,
            message_to_player=message,
            metadata={
                "destination": destination,
                "location": current_location
            }
        )

    except Exception as e:
        logger.error(f"Error in handle_go: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"Could not move to {destination}. {str(e)}"
        )
