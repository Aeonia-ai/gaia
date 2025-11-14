"""
Experience Interaction Endpoints

New stateful endpoints for game experiences using unified state model.
Replaces hardcoded /game/command with config-driven, markdown-based approach.
"""

import logging
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.shared import get_current_auth_legacy as get_current_auth
from app.shared.config import settings
from .kb_agent import kb_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/experience", tags=["experience"])


# ===== REQUEST/RESPONSE MODELS =====

class InteractRequest(BaseModel):
    """Request to interact with an experience."""
    message: str
    experience: Optional[str] = None  # If None, use player's current experience
    force_experience_selection: bool = False


class InteractResponse(BaseModel):
    """Response from experience interaction."""
    success: bool
    narrative: str
    experience: str
    state_updates: Optional[Dict[str, Any]] = None
    available_actions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ExperienceListResponse(BaseModel):
    """List of available experiences."""
    experiences: List[Dict[str, Any]]


# ===== ENDPOINTS =====

@router.post("/interact", response_model=InteractResponse)
async def interact_with_experience(
    request: InteractRequest,
    auth: dict = Depends(get_current_auth)
) -> InteractResponse:
    """
    Interact with a game experience through the unified command processor.
    """
    user_id = auth.get("user_id") or auth.get("email")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    state_manager = kb_agent.state_manager
    if not state_manager:
        raise HTTPException(status_code=500, detail="State manager not initialized")

    # Handle experience selection first
    available_experiences = state_manager.list_experiences()
    detected_exp = _detect_experience_selection(request.message, available_experiences)
    if detected_exp:
        await state_manager.set_current_experience(user_id, detected_exp)
        exp_info = state_manager.get_experience_info(detected_exp)
        narrative = f"Great! You've selected **{exp_info['name']}**.\n\n{exp_info.get('description', '')}\n\nWhat would you like to do?"
        return InteractResponse(success=True, narrative=narrative, experience=detected_exp, available_actions=["look around"])

    # Determine current experience
    experience = await _determine_experience(state_manager, user_id, request.experience, request.force_experience_selection)
    if not experience:
        return await _prompt_experience_selection(state_manager, user_id)

    # Ensure player is initialized
    await state_manager.ensure_player_initialized(experience, user_id)

    # DELEGATE TO COMMAND PROCESSOR
    from .command_processor import command_processor
    command_data = {"action": request.message, "message": request.message} # Use message for both action and message
    result = await command_processor.process_command(user_id, experience, command_data)

    return InteractResponse(
        success=result.success,
        narrative=result.message_to_player,
        experience=experience,
        state_updates=result.state_changes,
        metadata=result.metadata
    )


@router.get("/list", response_model=ExperienceListResponse)
async def list_experiences(
    auth: dict = Depends(get_current_auth)
) -> ExperienceListResponse:
    """
    List all available experiences.

    Returns:
        List of experiences with metadata
    """
    state_manager = kb_agent.state_manager
    if not state_manager:
        raise HTTPException(status_code=500, detail="State manager not initialized")

    try:
        experience_ids = state_manager.list_experiences()
        experiences = []

        for exp_id in experience_ids:
            info = state_manager.get_experience_info(exp_id)
            experiences.append(info)

        return ExperienceListResponse(experiences=experiences)

    except Exception as e:
        logger.error(f"Error listing experiences: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list experiences: {e}")


@router.get("/info/{experience_id}")
async def get_experience_info(
    experience_id: str,
    auth: dict = Depends(get_current_auth)
) -> Dict[str, Any]:
    """Get detailed info about a specific experience."""
    state_manager = kb_agent.state_manager
    if not state_manager:
        raise HTTPException(status_code=500, detail="State manager not initialized")

    try:
        info = state_manager.get_experience_info(experience_id)
        return info
    except Exception as e:
        logger.error(f"Error getting experience info: {e}")
        raise HTTPException(status_code=404, detail=f"Experience not found: {experience_id}")


# ===== HELPER FUNCTIONS =====

async def _determine_experience(
    state_manager,
    user_id: str,
    requested_experience: Optional[str],
    force_selection: bool
) -> Optional[str]:
    """
    Determine which experience the player is interacting with.

    Priority:
    1. Explicitly requested experience in request
    2. Player's current experience from profile
    3. None (trigger experience selection)

    Args:
        state_manager: UnifiedStateManager instance
        user_id: User ID
        requested_experience: Experience requested in this interaction
        force_selection: Force experience selection even if player has current

    Returns:
        Experience ID or None
    """
    if force_selection:
        return None

    if requested_experience:
        # Validate and save as current experience
        try:
            state_manager.load_config(requested_experience)
            await state_manager.set_current_experience(user_id, requested_experience)
            return requested_experience
        except Exception as e:
            logger.warning(f"Invalid experience '{requested_experience}': {e}")
            return None

    # Load player's current experience from profile
    current_experience = await state_manager.get_current_experience(user_id)
    if current_experience:
        logger.debug(f"User '{user_id}' continuing with experience '{current_experience}'")
        return current_experience

    # No experience selected yet
    return None


async def _prompt_experience_selection(
    state_manager,
    user_id: str
) -> InteractResponse:
    """
    Generate response prompting user to select an experience.

    Args:
        state_manager: UnifiedStateManager instance
        user_id: User ID

    Returns:
        Response with available experiences
    """
    experiences = state_manager.list_experiences()
    experience_list = []

    for exp_id in experiences:
        try:
            info = state_manager.get_experience_info(exp_id)
            experience_list.append(f"- **{info['name']}**: {info.get('description', 'No description')}")
        except Exception as e:
            logger.warning(f"Could not load info for experience '{exp_id}': {e}")

    narrative = (
        "Welcome! Please select an experience to begin:\n\n"
        + "\n".join(experience_list)
        + "\n\nTo select an experience, say: \"I want to play [experience name]\""
    )

    return InteractResponse(
        success=True,
        narrative=narrative,
        experience="",
        available_actions=[f"play {exp_id}" for exp_id in experiences],
        metadata={"requires_selection": True}
    )


def _detect_experience_selection(message: str, available_experiences: List[str]) -> Optional[str]:
    """
    Detect if message contains experience selection.

    Patterns:
    - "play [experience]"
    - "I want to play [experience]"
    - "select [experience]"
    - "choose [experience]"
    - "[experience]" (exact match)

    Args:
        message: User's message
        available_experiences: List of valid experience IDs

    Returns:
        Experience ID if detected, None otherwise
    """
    message_lower = message.lower().strip()

    # Try exact match first
    if message_lower in available_experiences:
        return message_lower

    # Try pattern matching
    selection_patterns = [
        r"play\s+([a-z0-9-]+)",
        r"select\s+([a-z0-9-]+)",
        r"choose\s+([a-z0-9-]+)",
        r"want\s+to\s+play\s+([a-z0-9-]+)",
    ]

    import re
    for pattern in selection_patterns:
        match = re.search(pattern, message_lower)
        if match:
            potential_exp = match.group(1)
            if potential_exp in available_experiences:
                return potential_exp

    return None


# ═══════════════════════════════════════════════════════════════════════════
# ⚠️  MVP KLUDGE WARNING - NPC INTERACTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════
#
# The following endpoints are a TEMPORARY solution for the Phase 1 demo.
# They support the chat-service-to-KB-service tool calling pattern.
#
# WHY THIS IS A KLUDGE:
#   - These endpoints are called BY the chat service's KB tools
#   - Creates circular dependency: KB → Chat → KB
#   - Inefficient: Extra HTTP overhead
#   - Tightly couples chat service to game mechanics
#
# PROPER FUTURE ARCHITECTURE:
#   - Remove these endpoints entirely
#   - Move NPC dialogue generation into KB service
#   - Handle quest/inventory/rewards as internal state operations
#   - See: docs/scratchpad/npc-llm-dialogue-system.md
#
# TIMELINE: Remove after Phase 1 demo refactor
#
# ═══════════════════════════════════════════════════════════════════════════


# Request/Response models for MVP kludge endpoints
class QuestStateRequest(BaseModel):
    """Request to check quest state."""
    quest_id: str
    user_id: str


class QuestStateResponse(BaseModel):
    """Quest state response."""
    success: bool
    quest_id: str
    status: str  # "not_started", "in_progress", "complete"
    progress: Optional[Dict[str, Any]] = None


class AcceptItemRequest(BaseModel):
    """Request to accept item from player."""
    item_id: str
    npc_id: str
    user_id: str


class AcceptItemResponse(BaseModel):
    """Accept item response."""
    success: bool
    message: str
    quest_updated: bool = False


class GrantRewardRequest(BaseModel):
    """Request to grant quest reward."""
    reward_type: str
    reward_data: Dict[str, Any]
    user_id: str


class GrantRewardResponse(BaseModel):
    """Grant reward response."""
    success: bool
    message: str
    reward: Optional[Dict[str, Any]] = None


class PlayerInventoryResponse(BaseModel):
    """Player inventory response."""
    success: bool
    inventory: List[Dict[str, Any]]


@router.post("/{experience}/quest/state")
async def check_quest_state(
    experience: str,
    request: QuestStateRequest,
    auth=Depends(get_current_auth)
):
    """
    MVP KLUDGE: Check player's quest state.

    Called by chat service KB tool when Louisa needs to know quest progress.
    Future: This will be handled internally when KB generates NPC dialogue.
    """
    try:
        state_manager = kb_agent.state_manager
        if not state_manager:
            raise HTTPException(status_code=500, detail="State manager not initialized")

        # Get player's current state
        player_view = await state_manager.get_player_view(experience, request.user_id)
        quests = player_view.get("player", {}).get("quests", {})

        # Check specific quest
        quest_state = quests.get(request.quest_id, {})

        return QuestStateResponse(
            success=True,
            quest_id=request.quest_id,
            status=quest_state.get("status", "not_started"),
            progress=quest_state.get("progress")
        )

    except Exception as e:
        logger.error(f"Error checking quest state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{experience}/npc/accept_item")
async def accept_item_from_player(
    experience: str,
    request: AcceptItemRequest,
    auth=Depends(get_current_auth)
):
    """
    MVP KLUDGE: Accept item from player when given to NPC.

    Called by chat service KB tool when Louisa accepts a bottle.
    Future: Use the existing give_item fast command handler.
    """
    try:
        # MVP: Just call the give_item handler directly
        from .handlers.give_item import handle_give_item

        result = await handle_give_item(
            request.user_id,
            experience,
            {
                "action": "give_item",
                "item_id": request.item_id,
                "recipient_id": request.npc_id
            }
        )

        return AcceptItemResponse(
            success=result.success,
            message=result.message_to_player,
            quest_updated=result.metadata.get("quest_updated", False) if result.metadata else False
        )

    except Exception as e:
        logger.error(f"Error accepting item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{experience}/quest/reward")
async def grant_quest_reward(
    experience: str,
    request: GrantRewardRequest,
    auth=Depends(get_current_auth)
):
    """
    MVP KLUDGE: Grant quest reward to player.

    Called by chat service KB tool when Louisa rewards the player.
    Future: Handle rewards as part of quest completion logic in KB.
    """
    try:
        state_manager = kb_agent.state_manager
        if not state_manager:
            raise HTTPException(status_code=500, detail="State manager not initialized")

        # MVP: Simple reward granting
        if request.reward_type == "trust":
            # Increase NPC trust
            trust_amount = request.reward_data.get("amount", 10)
            # Future: Update NPC trust in player state
            return GrantRewardResponse(
                success=True,
                message=f"Trust increased by {trust_amount}",
                reward={"type": "trust", "amount": trust_amount}
            )

        elif request.reward_type == "item":
            # Give item to player
            item_id = request.reward_data.get("item_id")
            # Future: Add item to inventory
            return GrantRewardResponse(
                success=True,
                message=f"Received {item_id}",
                reward={"type": "item", "item_id": item_id}
            )

        elif request.reward_type == "quest_complete":
            # Mark quest as complete
            return GrantRewardResponse(
                success=True,
                message="Quest completed!",
                reward={"type": "quest_complete"}
            )

        else:
            return GrantRewardResponse(
                success=False,
                message=f"Unknown reward type: {request.reward_type}"
            )

    except Exception as e:
        logger.error(f"Error granting reward: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{experience}/player/inventory")
async def get_player_inventory(
    experience: str,
    user_id: str,
    auth=Depends(get_current_auth)
):
    """
    MVP KLUDGE: Get player's inventory.

    Called by chat service KB tool when Louisa needs to check what player has.
    Future: Inventory will be included automatically in NPC dialogue context.
    """
    try:
        state_manager = kb_agent.state_manager
        if not state_manager:
            raise HTTPException(status_code=500, detail="State manager not initialized")

        player_view = await state_manager.get_player_view(experience, user_id)
        inventory = player_view.get("player", {}).get("inventory", [])

        return PlayerInventoryResponse(
            success=True,
            inventory=inventory
        )

    except Exception as e:
        logger.error(f"Error getting inventory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
