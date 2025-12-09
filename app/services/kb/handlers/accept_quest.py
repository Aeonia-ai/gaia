# app/services/kb/handlers/accept_quest.py
"""
Fast command handler for quest acceptance with visibility toggle.

Phase 1 Implementation: Visibility Toggle
- Accepts quest from NPC (e.g., Louisa's dream_bottle_recovery)
- Toggles visibility of quest-related items from false → true
- Updates player quest state to "active"
- Publishes v0.4 WorldUpdate event to spawn items in Unity

Response time: <50ms (vs 1-3s for LLM path)
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from app.shared.models.command_result import CommandResult
from app.services.kb.kb_agent import kb_agent

logger = logging.getLogger(__name__)

# Quest-to-items mapping: Which items should become visible when quest is accepted
QUEST_VISIBILITY_MAP = {
    "dream_bottle_recovery": {
        "items_to_show": [
            "bottle_mystery",  # Turquoise glow, spiral symbol - spawn_zone_1
            "bottle_energy",   # Amber glow, star symbol - spawn_zone_2
            "bottle_joy",      # Golden glow, moon symbol - spawn_zone_3
            "bottle_nature",   # Emerald glow, leaf symbol - spawn_zone_4
        ],
        "required_npc": "louisa",
        "min_trust_level": 60
    }
}


async def handle_accept_quest(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handles quest acceptance with automatic item visibility toggle.

    Phase 1 Implementation:
    - Validates quest exists and prerequisites are met
    - Updates player quest status from "offered" → "active"
    - Toggles visibility of quest items from false → true
    - Rebuilds AOI with newly visible items
    - Publishes WorldUpdate event to Unity

    Args:
        user_id: Player accepting quest
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: { "quest_id": "dream_bottle_recovery", "npc_id": "louisa" }

    Returns:
        CommandResult with quest acceptance narrative and state updates

    Example:
        > accept quest dream_bottle_recovery

        Louisa's wings flutter with excitement!

        "Thank you, dear friend! The dream bottles are scattered throughout
        the shop. I can sense them now - look for the glowing bottles with
        special symbols..."

        [Quest Accepted: Dream Bottle Recovery]
        [4 dream bottles are now visible in the shop]
    """
    quest_id = command_data.get("quest_id")
    npc_id = command_data.get("npc_id")

    if not quest_id:
        return CommandResult(
            success=False,
            message_to_player="Which quest do you want to accept? Try: accept quest <quest_name>"
        )

    try:
        state_manager = kb_agent.state_manager
        if not state_manager:
            raise Exception("State manager not initialized")

        # Get player state to check quest status and NPC relationships
        player_view = await state_manager.get_player_view(experience_id, user_id)
        player_quests = player_view.get("player", {}).get("quests", {})
        npc_relationships = player_view.get("player", {}).get("npcs", {})

        # Validate quest exists and is in "offered" state
        if quest_id not in player_quests:
            return CommandResult(
                success=False,
                message_to_player=f"Quest '{quest_id}' has not been offered to you yet. Try talking to NPCs to discover quests."
            )

        quest_data = player_quests[quest_id]

        if quest_data.get("status") == "active":
            return CommandResult(
                success=False,
                message_to_player=f"You've already accepted this quest. Check progress with: quests"
            )

        if quest_data.get("status") == "completed":
            return CommandResult(
                success=False,
                message_to_player=f"You've already completed this quest!"
            )

        if quest_data.get("status") != "offered":
            return CommandResult(
                success=False,
                message_to_player=f"Quest '{quest_id}' is not available to accept."
            )

        # Check prerequisites if quest has visibility toggle behavior
        if quest_id in QUEST_VISIBILITY_MAP:
            quest_config = QUEST_VISIBILITY_MAP[quest_id]

            # Validate NPC requirement
            required_npc = quest_config.get("required_npc")
            if npc_id and npc_id != required_npc:
                return CommandResult(
                    success=False,
                    message_to_player=f"This quest must be accepted from {required_npc}, not {npc_id}."
                )

            # Check trust level requirement
            min_trust = quest_config.get("min_trust_level", 0)
            npc_data = npc_relationships.get(required_npc, {})
            current_trust = npc_data.get("trust_level", 0)

            if current_trust < min_trust:
                return CommandResult(
                    success=False,
                    message_to_player=f"You need more trust with {required_npc} to accept this quest. (Current: {current_trust}, Required: {min_trust})"
                )

        logger.info(f"User {user_id} accepting quest {quest_id}")

        # Update player quest status to "active"
        quest_updates = {
            "player": {
                "quests": {
                    quest_id: {
                        "status": "active",
                        "accepted_at": datetime.utcnow().isoformat()
                    }
                }
            }
        }

        await state_manager.update_player_view(
            experience=experience_id,
            user_id=user_id,
            updates=quest_updates
        )

        # PHASE 1: Toggle item visibility if quest has associated items
        world_updates = {}
        items_shown_count = 0

        if quest_id in QUEST_VISIBILITY_MAP:
            quest_config = QUEST_VISIBILITY_MAP[quest_id]
            items_to_show = quest_config.get("items_to_show", [])

            if items_to_show:
                # Get world state to find and update items
                world_state = await state_manager.get_world_state(experience_id)

                # Build visibility toggle updates
                world_updates = await _build_visibility_updates(
                    world_state,
                    items_to_show,
                    visible=True
                )

                if world_updates:
                    # Update world state and publish WorldUpdate event
                    await state_manager.update_world_state(
                        experience=experience_id,
                        updates=world_updates,
                        user_id=user_id  # Publish event to trigger AOI rebuild
                    )
                    items_shown_count = len(items_to_show)

        # Generate acceptance narrative
        quest_title = quest_data.get("title", quest_id)
        narrative = f"✅ **Quest Accepted: {quest_title}**\n\n"

        if items_shown_count > 0:
            narrative += f"🔮 {items_shown_count} quest items are now visible in the world.\n\n"

        narrative += "Check your quest progress with: **quests**"

        return CommandResult(
            success=True,
            state_changes={
                "player": quest_updates,
                "world": world_updates
            },
            message_to_player=narrative,
            metadata={
                "quest_id": quest_id,
                "items_shown": items_shown_count,
                "quest_status": "active"
            }
        )

    except Exception as e:
        logger.error(f"Error in handle_accept_quest: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"Could not accept quest. {str(e)}"
        )


async def _build_visibility_updates(
    world_state: Dict[str, Any],
    instance_ids: list[str],
    visible: bool
) -> Dict[str, Any]:
    """
    Build nested dict updates to toggle item visibility.

    Searches world state for items by instance_id and builds update structure
    to set their "visible" field.

    Args:
        world_state: Full world state dictionary
        instance_ids: List of instance IDs to update (e.g., ["dream_bottle_1", ...])
        visible: True to show items, False to hide them

    Returns:
        Nested dict structure for update_world_state(), e.g.:
        {
            "locations": {
                "woander_store": {
                    "areas": {
                        "spawn_zone_1": {
                            "items": {
                                "$update": {
                                    "instance_id": "dream_bottle_1",
                                    "visible": true
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    updates = {}
    locations = world_state.get("locations", {})

    for location_id, location_data in locations.items():
        location_updates = {}

        # Check top-level location items
        items = location_data.get("items", [])
        for item in items:
            if item.get("instance_id") in instance_ids:
                if "items" not in location_updates:
                    location_updates["items"] = {"$update": []}

                location_updates["items"]["$update"].append({
                    "instance_id": item.get("instance_id"),
                    "visible": visible
                })

        # Check area items
        areas = location_data.get("areas", {})
        area_updates = {}

        for area_id, area_data in areas.items():
            items = area_data.get("items", [])

            for item in items:
                if item.get("instance_id") in instance_ids:
                    if area_id not in area_updates:
                        area_updates[area_id] = {"items": {"$update": []}}

                    area_updates[area_id]["items"]["$update"].append({
                        "instance_id": item.get("instance_id"),
                        "visible": visible
                    })

        if area_updates:
            location_updates["areas"] = area_updates

        if location_updates:
            if "locations" not in updates:
                updates["locations"] = {}
            updates["locations"][location_id] = location_updates

    return updates
