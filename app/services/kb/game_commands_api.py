"""
Game Commands API Endpoints

RESTful API endpoint for KB-driven game command processing.
Processes natural language game commands with structured responses.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.shared.security import get_current_auth_legacy as get_current_auth
from .kb_agent import kb_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/game", tags=["Game Commands"])


class GameCommandRequest(BaseModel):
    """Request model for game command execution."""
    command: str
    experience: str
    user_context: Dict[str, Any]
    session_state: Optional[Dict[str, Any]] = None


@router.post("/command")
async def process_game_command(
    request: GameCommandRequest,
    auth: dict = Depends(get_current_auth)
) -> Dict[str, Any]:
    """
    Process a natural language game command through the KB system.

    This endpoint:
    1. Validates user permissions via RBAC
    2. Loads game content from KB based on experience ID
    3. Uses LLM to interpret command against game rules
    4. Returns structured response with narrative, actions, and state changes

    Args:
        request: Game command details (command, experience, user_context, session_state)
        auth: Authentication context from middleware

    Returns:
        GameCommandResponse with success, narrative, actions, state_changes, etc.

    Raises:
        HTTPException: For permission errors, invalid experiences, or processing failures
    """
    try:
        # Extract user ID from auth
        user_id = auth.get("email", auth.get("user_id", "unknown"))

        # Merge auth context with provided user_context
        merged_context = {
            **request.user_context,
            "user_id": user_id,
            "auth_email": auth.get("email"),
            "auth_type": auth.get("auth_type", "api_key")
        }

        # Execute game command via KB agent (direct call, no HTTP)
        # NOTE: execute_game_command() currently delegates to legacy version
        #       Once markdown migration complete, it will use content-driven system
        result = await kb_agent.execute_game_command(
            command=request.command,
            experience=request.experience,
            user_context=merged_context,
            session_state=request.session_state
        )

        logger.info(
            f"Game command executed for user {user_id}: "
            f"experience={request.experience}, command='{request.command}', "
            f"success={result.get('success', False)}"
        )

        # Return result directly (already in GameCommandResponse format)
        return result

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Game command processing failed: {e}", exc_info=True)
        # Return error in GameCommandResponse format
        return {
            "success": False,
            "error": {
                "code": "processing_error",
                "message": str(e)
            },
            "metadata": {
                "processing_time_ms": 0,
                "kb_files_accessed": [],
                "persona_used": "unknown",
                "user_role": request.user_context.get("role", "unknown"),
                "experience": request.experience
            }
        }


class SimpleCommandRequest(BaseModel):
    """Simplified request model for direct instance management testing."""
    action: str  # "collect", "return", "look", "inventory"
    target: Optional[str] = None  # "dream_bottle", "louisa", etc.
    destination: Optional[str] = None  # For "return" action
    experience: str = "wylding-woods"
    waypoint: str = "waypoint_28a"
    sublocation: Optional[str] = None  # "shelf_1", "fairy_door_1", etc.


@router.post("/test/simple-command")
async def process_simple_command(
    request: SimpleCommandRequest,
    auth: dict = Depends(get_current_auth)
) -> Dict[str, Any]:
    """
    Simple test endpoint for instance management without LLM overhead.

    Directly calls instance management methods for faster testing.

    Examples:
        {"action": "collect", "target": "dream_bottle", "sublocation": "shelf_1"}
        {"action": "return", "target": "dream_bottle", "destination": "fairy_door_1"}
        {"action": "inventory"}
        {"action": "look", "sublocation": "shelf_1"}

    Returns:
        Result with narrative, actions, and state changes
    """
    try:
        user_id = auth.get("email", auth.get("user_id", "test_user"))

        # Route to appropriate handler based on action
        if request.action == "collect":
            if not request.target:
                raise HTTPException(status_code=400, detail="'target' required for collect action")
            if not request.sublocation:
                raise HTTPException(status_code=400, detail="'sublocation' required for collect action")

            result = await kb_agent._collect_item(
                experience=request.experience,
                item_semantic_name=request.target,
                user_id=user_id,
                waypoint=request.waypoint,
                sublocation=request.sublocation
            )

        elif request.action == "return":
            if not request.target or not request.destination:
                raise HTTPException(status_code=400, detail="'target' and 'destination' required for return action")

            result = await kb_agent._return_item(
                experience=request.experience,
                item_semantic_name=request.target,
                destination_name=request.destination,
                user_id=user_id,
                waypoint=request.waypoint,
                sublocation=request.sublocation
            )

        elif request.action == "inventory":
            # Load player state and return inventory
            player_state = await kb_agent._load_player_state(user_id, request.experience)
            inventory = player_state.get("inventory", [])

            if len(inventory) == 0:
                narrative = "You're not carrying anything."
            else:
                items_list = [f"- {item['semantic_name']}" + (f" ({item.get('symbol')} symbol)" if item.get('symbol') else "")
                             for item in inventory]
                narrative = f"You're carrying:\n" + "\n".join(items_list)

            result = {
                "success": True,
                "narrative": narrative,
                "state_changes": {
                    "inventory": inventory,
                    "quest_progress": player_state.get("quest_progress", {})
                }
            }

        elif request.action == "look":
            # Find instances at location
            instances = await kb_agent._find_instances_at_location(
                experience=request.experience,
                waypoint=request.waypoint,
                sublocation=request.sublocation
            )

            if len(instances) == 0:
                narrative = f"You don't see anything interesting at {request.sublocation or request.waypoint}."
            else:
                items_list = [f"- {inst['semantic_name']}: {inst.get('description', 'No description')}"
                             for inst in instances]
                location_name = request.sublocation or request.waypoint
                narrative = f"At {location_name}, you see:\n" + "\n".join(items_list)

            result = {
                "success": True,
                "narrative": narrative,
                "instances": instances
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

        logger.info(
            f"Simple command executed: user={user_id}, action={request.action}, "
            f"success={result.get('success', False)}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Simple command processing failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "processing_error",
                "message": str(e)
            }
        }


@router.get("/experiences")
async def list_game_experiences(
    auth: dict = Depends(get_current_auth)
) -> Dict[str, Any]:
    """
    List available game experiences from the KB.

    Returns:
        List of game experiences with metadata (IDs, names, descriptions)
    """
    try:
        # TODO: Implement KB experience listing
        # For now, return placeholder
        return {
            "success": True,
            "experiences": [
                {
                    "id": "west-of-house",
                    "name": "West of House",
                    "type": "text-adventure",
                    "description": "Classic text adventure game"
                },
                {
                    "id": "wylding-woods",
                    "name": "Wylding Woods",
                    "type": "ar-location",
                    "description": "AR location-based adventure"
                },
                {
                    "id": "rock-paper-scissors",
                    "name": "Rock Paper Scissors",
                    "type": "turn-based",
                    "description": "Simple turn-based game"
                }
            ]
        }
    except Exception as e:
        logger.error(f"Experience listing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list experiences: {str(e)}"
        )
