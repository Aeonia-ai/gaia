# app/services/kb/handlers/admin_command_router.py
"""
Admin Command Router

Routes all admin commands (@ prefix) to their specific handlers.
Parses command syntax and dispatches to the appropriate handler.

This acts as an intermediary between the command_processor's exact-match
registration and the admin handlers that need parsed parameters.
"""

import logging
from typing import Any, Dict

from app.shared.models.command_result import CommandResult

logger = logging.getLogger(__name__)


async def route_admin_command(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Route admin commands to their specific handlers.

    Parses command string like "@examine item bottle_mystery" and
    routes to the appropriate handler function.

    Args:
        user_id: User ID
        experience_id: Experience ID
        command_data: Command data with 'action' field containing full command

    Returns:
        CommandResult from the specific handler

    Example:
        "@examine item bottle_mystery" → handle_admin_examine()
        "@where" → handle_admin_where()
        "@edit item bottle_mystery visible false" → handle_admin_edit_item()
    """
    action_str = command_data.get("action", "")

    if not action_str.startswith("@"):
        return CommandResult(
            success=False,
            message_to_player="❌ Admin commands must start with @"
        )

    # Parse: "@examine item bottle_mystery" → ["examine", "item", "bottle_mystery"]
    parts = action_str.lstrip("@").split()

    if len(parts) == 0:
        return CommandResult(
            success=False,
            message_to_player="❌ Empty admin command"
        )

    command = parts[0].lower()

    try:
        # Route to specific handler based on command
        if command == "examine":
            from .admin_examine import handle_admin_examine
            return await handle_admin_examine(user_id, experience_id, command_data)

        elif command == "where":
            from .admin_where import handle_admin_where
            return await handle_admin_where(user_id, experience_id, command_data)

        elif command == "edit":
            # Check if it's "@edit item" or "@edit-item"
            from .admin_edit_item import handle_admin_edit_item
            return await handle_admin_edit_item(user_id, experience_id, command_data)

        elif command in ["reset-experience", "reset"]:
            from .admin_reset_experience import handle_admin_reset_experience
            return await handle_admin_reset_experience(user_id, experience_id, command_data)

        else:
            # Command not recognized by new admin system, let it fall through
            # to legacy admin command system in kb_agent
            return CommandResult(
                success=False,
                message_to_player=f"❌ Unknown admin command '@{command}'. Try: @examine, @where, @edit, @reset"
            )

    except Exception as e:
        logger.error(f"Admin command routing failed: {command} - {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"❌ Admin command failed: {str(e)}"
        )
