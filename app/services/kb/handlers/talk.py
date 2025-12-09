# ═══════════════════════════════════════════════════════════════════════════
# ⚠️  MVP KLUDGE WARNING - NPC TALK HANDLER
# ═══════════════════════════════════════════════════════════════════════════
#
# This file implements a TEMPORARY solution for NPC interactions for the
# Phase 1 demo. This is NOT the final architecture.
#
# CURRENT FLOW (MVP KLUDGE):
#   Unity → WebSocket → KB Service (this handler)
#                       ↓
#                       Makes HTTP call to Chat Service
#                       ↓
#                       Chat Service uses Louisa persona with KB tools
#                       ↓
#                       KB tools make HTTP calls BACK to KB service
#                       ↓
#   Unity ← WebSocket ← KB Service wraps response
#
# WHY THIS IS A KLUDGE:
#   1. HTTP call overhead between services (KB → Chat → KB)
#   2. Chat service coupled to game mechanics (knows about bottles, quests)
#   3. Louisa persona definition tightly coupled to KB state structure
#   4. Inefficient: Two HTTP calls per NPC interaction
#
# PROPER FUTURE ARCHITECTURE:
#   - Move LLM dialogue generation into KB service directly
#   - NPC templates stored in KB markdown (personality, situation, quests)
#   - KB service calls MultiProviderChatService internally (no HTTP)
#   - Trust system and conversation history managed in KB state
#   - See: docs/scratchpad/npc-llm-dialogue-system.md for full design
#
# TIMELINE:  Refactor after Phase 1 demo (estimated 1-2 days of work)
#
# ═══════════════════════════════════════════════════════════════════════════

"""
MVP KLUDGE: NPC Talk Command Handler

Routes talk actions to the Chat Service which uses the Louisa persona.
This is a temporary solution for the Phase 1 demo.
"""

import httpx
import logging
from typing import Any, Dict

from app.shared.models.command_result import CommandResult
from app.shared.config import settings

logger = logging.getLogger(__name__)

# Chat service URL
CHAT_SERVICE_URL = settings.CHAT_SERVICE_URL or "http://chat-service:8000"


async def handle_talk(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handle NPC talk action by routing to Chat Service.

    MVP KLUDGE: Makes HTTP call to chat service instead of handling
    dialogue generation in KB service directly.

    Args:
        user_id: Player talking to NPC
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data with npc_id and message

    Returns:
        CommandResult with NPC dialogue

    Example command_data:
        {
            "action": "talk",
            "npc_id": "louisa",
            "message": "Hello Louisa, can you help me?"
        }
    """
    npc_id = command_data.get("npc_id")
    player_message = command_data.get("message", "")

    if not npc_id:
        return CommandResult(
            success=False,
            message_to_player="Who do you want to talk to? (missing npc_id)"
        )

    logger.info(f"MVP KLUDGE: Routing talk action to Chat Service - user={user_id}, npc={npc_id}")

    try:
        # MVP KLUDGE: Make HTTP call to chat service
        # Future: Call MultiProviderChatService directly within KB
        async with httpx.AsyncClient() as client:
            # Use the chat/message endpoint with Louisa persona
            # The persona_id should match the Louisa persona in the database
            response = await client.post(
                f"{CHAT_SERVICE_URL}/chat/message",
                json={
                    "message": player_message,
                    "persona_id": "louisa",  # MVP: Hardcoded persona ID
                    "context": {
                        "experience": experience_id,
                        "npc_id": npc_id,
                        "user_id": user_id
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": settings.API_KEY  # Inter-service auth
                },
                timeout=30.0  # LLM can take time
            )

            if response.status_code == 200:
                chat_response = response.json()

                # Extract the NPC dialogue from chat response
                npc_dialogue = chat_response.get("response", "...")

                logger.info(f"MVP KLUDGE: Received NPC dialogue from Chat Service - length={len(npc_dialogue)}")

                return CommandResult(
                    success=True,
                    message_to_player=npc_dialogue,
                    metadata={
                        "npc_id": npc_id,
                        "dialogue_source": "chat_service_louisa_persona"  # For debugging
                    }
                )
            else:
                logger.error(f"Chat service error: HTTP {response.status_code}")
                return CommandResult(
                    success=False,
                    message_to_player=f"Sorry, I couldn't connect with {npc_id} right now."
                )

    except httpx.TimeoutException:
        logger.error(f"Chat service timeout talking to {npc_id}")
        return CommandResult(
            success=False,
            message_to_player=f"{npc_id} is taking too long to respond. Try again?"
        )
    except Exception as e:
        logger.error(f"Error routing talk to chat service: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"An error occurred while talking to {npc_id}."
        )
