# app/services/kb/handlers/inventory.py
"""
Fast command handler for listing player inventory in GAIA experiences.

Provides production-ready inventory listing with item grouping and counts.
Bypasses LLM for <2ms response time.

This is a read-only operation - no state changes, no WorldUpdate events.
"""

import logging
from typing import Any, Dict
from collections import defaultdict

from app.shared.models.command_result import CommandResult

logger = logging.getLogger(__name__)


async def handle_inventory(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handles the 'inventory' action directly for high performance.

    Production implementation:
    - Retrieves player.inventory from player view
    - Groups items by template_id for cleaner display
    - Shows item counts for stackable items
    - Formats as human-readable list
    - Read-only: No state changes, no WorldUpdate events

    Args:
        user_id: User ID requesting inventory
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data (unused for inventory)

    Returns:
        CommandResult with success status and formatted inventory list

    Response time: <2ms (read-only operation)

    Example:
        >>> await handle_inventory(
        ...     user_id="user_123",
        ...     experience_id="wylding-woods",
        ...     command_data={}
        ... )
        CommandResult(
            success=True,
            message_to_player="Inventory:\\n- Health Potion x2\\n- Dream Bottle x1"
        )
    """
    from ..kb_agent import kb_agent

    state_manager = kb_agent.state_manager
    if not state_manager:
        return CommandResult(
            success=False,
            message_to_player="State manager not initialized."
        )

    try:
        # Get player state
        player_view = await state_manager.get_player_view(experience_id, user_id)
        inventory = player_view.get("player", {}).get("inventory", [])

        if not inventory:
            return CommandResult(
                success=True,
                message_to_player="Your inventory is empty.",
                metadata={
                    "item_count": 0,
                    "unique_items": 0
                }
            )

        # Group items by template_id for better display
        grouped_items = defaultdict(list)
        for item in inventory:
            template_id = item.get("template_id", item.get("type", "unknown"))
            grouped_items[template_id].append(item)

        # Build formatted inventory list
        inventory_lines = ["**Your Inventory:**", ""]

        for template_id, items in sorted(grouped_items.items()):
            count = len(items)
            # Get display name from first item
            first_item = items[0]
            item_name = first_item.get("semantic_name") or first_item.get("name", template_id)

            # Show count if multiple
            if count > 1:
                inventory_lines.append(f"- {item_name.title()} x{count}")
            else:
                inventory_lines.append(f"- {item_name.title()}")

            # Add effect summary for first item if available
            effects = first_item.get("effects", {})
            if effects:
                effect_parts = []
                if "health" in effects:
                    health_val = effects["health"]
                    if health_val > 0:
                        effect_parts.append(f"+{health_val} HP")
                    else:
                        effect_parts.append(f"{health_val} HP")

                if effect_parts:
                    inventory_lines.append(f"  └─ {', '.join(effect_parts)}")

        message = "\n".join(inventory_lines)

        return CommandResult(
            success=True,
            message_to_player=message,
            metadata={
                "item_count": len(inventory),
                "unique_items": len(grouped_items),
                "items": [
                    {
                        "template_id": template_id,
                        "count": len(items),
                        "name": items[0].get("semantic_name", template_id)
                    }
                    for template_id, items in grouped_items.items()
                ]
            }
        )

    except Exception as e:
        logger.error(f"Failed to get inventory: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player="Failed to retrieve inventory."
        )
