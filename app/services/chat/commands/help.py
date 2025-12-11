"""
/help command - Display available commands

Usage:
    /help           - List all available commands
    /help <command> - Get help for a specific command (future)
"""
from typing import Optional

from . import CommandResponse
from app.shared.logging import setup_service_logger

logger = setup_service_logger("cmd_help")


# Help text for each command
COMMAND_HELP = {
    'persona': {
        'syntax': '/persona [name]',
        'description': 'List or switch AI personas',
        'examples': [
            '/persona        - List all available personas',
            '/persona Zoe    - Switch to Zoe persona',
        ]
    },
    'help': {
        'syntax': '/help [command]',
        'description': 'Show available commands and usage',
        'examples': [
            '/help          - List all commands',
        ]
    }
}


async def handle_help_command(
    args: str,
    user_id: str,
    user_email: Optional[str] = None,
    jwt_token: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> CommandResponse:
    """
    Handle the /help command.

    With no args: Lists all available commands.
    With args: Shows detailed help for specific command (future).
    """
    if args:
        # Help for specific command
        return _help_for_command(args.strip().lower())
    else:
        # List all commands
        return _list_all_commands()


def _list_all_commands() -> CommandResponse:
    """List all available commands."""
    lines = [
        "**Available Commands**\n",
    ]

    for cmd, info in sorted(COMMAND_HELP.items()):
        lines.append(f"**/{cmd}** - {info['description']}")

    lines.append("")
    lines.append("Type `/help <command>` for detailed usage.")

    return CommandResponse(
        message="\n".join(lines),
        response_type="info",
        data={"commands": list(COMMAND_HELP.keys())}
    )


def _help_for_command(command: str) -> CommandResponse:
    """Show detailed help for a specific command."""
    # Remove leading slash if present
    if command.startswith('/'):
        command = command[1:]

    info = COMMAND_HELP.get(command)
    if not info:
        available = ", ".join(f"/{cmd}" for cmd in sorted(COMMAND_HELP.keys()))
        return CommandResponse(
            message=f"Unknown command: /{command}\n\nAvailable commands: {available}",
            response_type="error"
        )

    lines = [
        f"**/{command}**\n",
        f"**Usage:** `{info['syntax']}`\n",
        info['description'],
        "",
        "**Examples:**"
    ]
    for example in info['examples']:
        lines.append(f"  `{example}`")

    return CommandResponse(
        message="\n".join(lines),
        response_type="info"
    )
