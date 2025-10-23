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
from app.shared.tools.game_commands import execute_game_command

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

        # Execute game command
        result = await execute_game_command(
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
