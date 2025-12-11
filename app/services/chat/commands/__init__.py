"""
Slash Command System for GAIA Chat

This module provides user meta-commands (prefixed with `/`) that are intercepted
before LLM processing. Commands are instant (no token cost, <30ms response time).

Command Categories:
- User preferences: /persona, /settings
- Information: /help

Design Decisions:
- `/` prefix: Industry standard (IRC, Slack, Discord, MMOs, AI tools)
- `@` prefix: Reserved for existing game admin commands
- Interception point: unified_chat.py before any LLM calls
- Response format: CommandResponse with system message styling

See: docs/scratchpad/aeo-72-single-chat-design.md (Phase 2)
"""
from typing import Optional
from dataclasses import dataclass

from app.shared.logging import setup_service_logger

logger = setup_service_logger("chat_commands")


@dataclass
class CommandResponse:
    """Response from a slash command handler."""

    # The message to display to the user
    message: str

    # Response type for UI styling: 'success', 'error', 'info', 'list'
    response_type: str = "info"

    # Whether this command was handled (False = unknown command)
    handled: bool = True

    # Optional data payload (for commands that return structured data)
    data: Optional[dict] = None


# Import handlers AFTER CommandResponse is defined (to avoid circular import)
from .persona import handle_persona_command
from .help import handle_help_command

# Registry of available commands
COMMANDS = {
    'persona': handle_persona_command,
    'help': handle_help_command,
}


async def handle_command(
    message: str,
    user_id: str,
    user_email: Optional[str] = None,
    jwt_token: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> Optional[CommandResponse]:
    """
    Route slash commands to their handlers.

    Args:
        message: The full message text (must start with '/')
        user_id: User's unique identifier
        user_email: User's email address
        jwt_token: JWT token for authenticated requests
        conversation_id: Current conversation ID

    Returns:
        CommandResponse if message is a command, None otherwise.
        Returns error CommandResponse for unknown commands.
    """
    # Not a command
    if not message.startswith('/'):
        return None

    # Parse command and arguments
    parts = message[1:].split(' ', 1)
    command = parts[0].lower().strip()
    args = parts[1].strip() if len(parts) > 1 else ""

    logger.info(f"Processing command: /{command} (args: '{args}') for user {user_id}")

    # Look up handler
    handler = COMMANDS.get(command)
    if handler:
        try:
            return await handler(
                args=args,
                user_id=user_id,
                user_email=user_email,
                jwt_token=jwt_token,
                conversation_id=conversation_id
            )
        except Exception as e:
            logger.error(f"Error handling command /{command}: {e}")
            return CommandResponse(
                message=f"Error executing /{command}: {str(e)}",
                response_type="error",
                handled=True
            )

    # Unknown command
    available = ", ".join(f"/{cmd}" for cmd in sorted(COMMANDS.keys()))
    return CommandResponse(
        message=f"Unknown command: /{command}\n\nAvailable commands: {available}\n\nType /help for more information.",
        response_type="error",
        handled=True
    )
