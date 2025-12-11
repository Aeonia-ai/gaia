"""
/persona command - Switch or list AI personas

Usage:
    /persona          - List all available personas with current selection marked
    /persona <name>   - Switch to the specified persona

Examples:
    /persona
    /persona Zoe
    /persona default
"""
from typing import Optional

from . import CommandResponse
from app.shared.logging import setup_service_logger
from app.services.persona_service import persona_service

logger = setup_service_logger("cmd_persona")


async def handle_persona_command(
    args: str,
    user_id: str,
    user_email: Optional[str] = None,
    jwt_token: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> CommandResponse:
    """
    Handle the /persona command.

    With no args: Lists all available personas with current marked.
    With args: Switches to the specified persona.
    """
    if not args:
        # List all personas
        return await _list_personas(user_id)
    else:
        # Switch to specified persona
        return await _switch_persona(args.strip(), user_id)


async def _list_personas(user_id: str) -> CommandResponse:
    """List all available personas with current selection marked."""
    try:
        # Get all active personas
        personas = await persona_service.list_personas(active_only=True)

        if not personas:
            return CommandResponse(
                message="No personas available.",
                response_type="info"
            )

        # Get current persona for this user
        current_persona = await persona_service.get_user_persona(user_id)
        current_name = current_persona.name.lower() if current_persona else "default"

        # Build list
        lines = ["**Available Personas:**\n"]
        for persona in personas:
            is_current = persona.name.lower() == current_name
            marker = " ✓ (current)" if is_current else ""
            lines.append(f"• **{persona.name}**{marker}")
            if persona.description:
                lines.append(f"  {persona.description}")
            lines.append("")  # Blank line between personas

        lines.append("Use `/persona <name>` to switch personas.")

        return CommandResponse(
            message="\n".join(lines),
            response_type="list",
            data={"personas": [p.name for p in personas], "current": current_name}
        )

    except Exception as e:
        logger.error(f"Error listing personas: {e}")
        return CommandResponse(
            message=f"Error listing personas: {str(e)}",
            response_type="error"
        )


async def _switch_persona(persona_name: str, user_id: str) -> CommandResponse:
    """Switch to the specified persona."""
    try:
        # Find the persona (case-insensitive)
        personas = await persona_service.list_personas(active_only=True)
        target_persona = None

        for persona in personas:
            if persona.name.lower() == persona_name.lower():
                target_persona = persona
                break

        if not target_persona:
            # Persona not found - list available options
            available = ", ".join(p.name for p in personas)
            return CommandResponse(
                message=f"Persona '{persona_name}' not found.\n\nAvailable personas: {available}",
                response_type="error"
            )

        # Set the user's persona preference
        await persona_service.set_user_persona(user_id, str(target_persona.id))

        return CommandResponse(
            message=f"✓ Switched to **{target_persona.name}**\n\n{target_persona.description or ''}",
            response_type="success",
            data={"persona_id": str(target_persona.id), "persona_name": target_persona.name}
        )

    except Exception as e:
        logger.error(f"Error switching persona: {e}")
        return CommandResponse(
            message=f"Error switching persona: {str(e)}",
            response_type="error"
        )
