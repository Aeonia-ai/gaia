from typing import Dict, Any, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

async def execute_game_command(
    command: str,
    experience: str,
    user_context: Dict[str, Any],
    session_state: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    General-purpose game command processor for any game system.

    Processes natural language commands by:
    1. Applying code-enforced RBAC filtering
    2. Loading and filtering KB content by role
    3. Using LLM to interpret content rules
    4. Returning structured responses with actions and state changes

    Args:
        command: Natural language command ("examine crystal", "go north", "cast fireball")
        experience: Experience ID from KB ("west-of-house", "sanctuary", "rock-paper-scissors")
        user_context: Role and permission information
        session_state: Current game state (optional, managed by caller)

    Returns:
        A structured response dictionary.
    """
    # TEMPORARY: Route to KB Agent for natural language responses
    # TODO: Implement full structured processor with actions/state_changes

    try:
        # Get API key for inter-service communication
        from app.shared.config import settings
        api_key = settings.API_KEY

        # Call KB Agent endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://kb-service:8000/agent/interpret",
                json={
                    "query": command,
                    "context_path": f"/experiences/{experience}",
                    "mode": "decision"
                },
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": api_key
                },
                timeout=60.0
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("status") == "success":
                    agent_result = result.get("result", {})
                    narrative = agent_result.get("interpretation", "")

                    # Return in GameCommandResponse format
                    return {
                        "success": True,
                        "narrative": narrative,
                        "actions": [],  # Agent doesn't return structured actions
                        "state_changes": session_state or {},  # Preserve existing state
                        "next_suggestions": [],  # Could parse from narrative later
                        "metadata": {
                            "processing_time_ms": 0,
                            "kb_files_accessed": agent_result.get("context_files", 0),
                            "persona_used": "game_interpreter",
                            "user_role": user_context.get("role", "player"),
                            "experience": experience,
                            "model_used": agent_result.get("model_used", "unknown")
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": {
                            "code": "agent_error",
                            "message": "KB Agent failed to process command"
                        }
                    }
            else:
                return {
                    "success": False,
                    "error": {
                        "code": "http_error",
                        "message": f"HTTP {response.status_code}"
                    }
                }

    except Exception as e:
        logger.error(f"Game command execution error: {e}")
        return {
            "success": False,
            "error": {
                "code": "execution_error",
                "message": str(e)
            }
        }
