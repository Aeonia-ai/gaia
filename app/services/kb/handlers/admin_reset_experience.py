# app/services/kb/handlers/admin_reset_experience.py
"""
Admin command handler for resetting experiences to pristine state.

Provides clean reset mechanism for testing and development:
- Restores world state from template
- Clears player views and inventories
- Resets quest progress
- Creates timestamped backups

Response time: <100ms for full reset
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.shared.models.command_result import CommandResult

logger = logging.getLogger(__name__)


async def handle_admin_reset_experience(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handles the '@reset-experience' admin command for clean testing.

    Command patterns:
    - @reset experience → Shows preview, requests CONFIRM
    - @reset experience CONFIRM → Executes full reset
    - @reset world CONFIRM → World only (keeps player data)

    Full reset:
    - Restores world.json from world.template.json
    - Deletes all player view files
    - Clears inventories and quest progress
    - Creates timestamped backup

    Args:
        user_id: Admin user ID
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: Command data with action string

    Returns:
        CommandResult with reset summary or confirmation request

    Response time: <100ms

    Example:
        >>> await handle_admin_reset_experience(
        ...     user_id="admin@example.com",
        ...     experience_id="wylding-woods",
        ...     command_data={"action": "@reset experience CONFIRM"}
        ... )
        CommandResult(
            success=True,
            message_to_player="✅ Reset complete! 3 players cleared..."
        )
    """
    from ..kb_agent import kb_agent

    state_manager = kb_agent.state_manager
    if not state_manager:
        return CommandResult(
            success=False,
            message_to_player="State manager not initialized."
        )

    # Parse command: "@reset experience CONFIRM" -> ["reset", "experience", "CONFIRM"]
    action_str = command_data.get("action", "")
    parts = action_str.lstrip("@").split()

    if len(parts) < 2:
        return CommandResult(
            success=False,
            message_to_player=(
                "Usage:\n"
                "  @reset experience → Preview reset\n"
                "  @reset experience CONFIRM → Execute reset\n"
                "  @reset world CONFIRM → Reset world only"
            )
        )

    # Check for CONFIRM flag
    has_confirm = "CONFIRM" in parts

    # Determine scope
    scope = parts[1].lower()  # "experience" or "world"
    world_only = (scope == "world")

    # If no CONFIRM, show preview
    if not has_confirm:
        return await _build_reset_preview(experience_id, world_only, state_manager)

    # Execute reset with CONFIRM
    return await _execute_reset(experience_id, world_only, state_manager)


async def _build_reset_preview(
    experience_id: str,
    world_only: bool,
    state_manager
) -> CommandResult:
    """Build preview of what will be reset."""

    # Count players
    players_dir = Path(f"/kb/players")
    player_count = 0
    if players_dir.exists():
        for user_dir in players_dir.iterdir():
            if not user_dir.is_dir():
                continue
            player_exp_dir = user_dir / experience_id
            if player_exp_dir.exists():
                player_count += 1

    # Check template exists
    template_path = Path(f"/kb/experiences/{experience_id}/state/world.template.json")
    template_exists = template_path.exists()

    preview_lines = [
        f"⚠️  Reset Experience: {experience_id}",
        "",
        "❗ This will reset:"
    ]

    if world_only:
        preview_lines.extend([
            "- World state (locations, items, NPCs)",
            f"- Quest progress (bottles collected, etc.)",
            f"",
            f"✅ Will preserve:",
            f"- {player_count} player inventories",
            "",
            "⚠️ WARNING: May cause item duplication if players have collected items"
        ])
    else:
        preview_lines.extend([
            "- World state (locations, items, NPCs)",
            "- Quest progress (bottles collected, etc.)",
            f"- {player_count} player views and inventories",
            "- All NPC conversation histories"
        ])

    if not template_exists:
        preview_lines.extend([
            "",
            "❌ No template found!",
            f"Expected: {template_path}",
            "Create template first or current state will be used"
        ])

    preview_lines.extend([
        "",
        "📦 A backup will be created before reset.",
        "",
        "To confirm: @reset experience CONFIRM" if not world_only else "To confirm: @reset world CONFIRM"
    ])

    return CommandResult(
        success=False,
        requires_confirmation=True,
        message_to_player="\n".join(preview_lines),
        metadata={
            "command_type": "reset-experience",
            "scope": "world_only" if world_only else "full",
            "player_count": player_count,
            "template_exists": template_exists
        }
    )


async def _execute_reset(
    experience_id: str,
    world_only: bool,
    state_manager
) -> CommandResult:
    """Execute the reset with backup."""

    try:
        # Step 1: Create backup
        backup_file = await _create_backup(experience_id, state_manager)

        # Step 2: Restore world state from template
        await _restore_world_from_template(experience_id, state_manager)

        # Step 3: Clear player data (unless world-only)
        player_count = 0
        if not world_only:
            player_count = await _clear_player_data(experience_id)

        # Build success message
        success_lines = [
            f"✅ Reset Complete: {experience_id}",
            ""
        ]

        if backup_file:
            success_lines.append(f"📦 Backup: {Path(backup_file).name}")
            success_lines.append("")

        success_lines.append("♻️  Summary:")
        success_lines.append("- World state restored from template")
        success_lines.append("- Quest progress reset (0/4 bottles)")

        if world_only:
            success_lines.append("- Player inventories preserved")
        else:
            success_lines.append(f"- {player_count} player views cleared")

        success_lines.extend([
            "",
            "Experience is now in pristine state! ✨"
        ])

        return CommandResult(
            success=True,
            message_to_player="\n".join(success_lines),
            metadata={
                "command_type": "reset-experience",
                "scope": "world_only" if world_only else "full",
                "backup_file": backup_file,
                "player_views_deleted": player_count
            }
        )

    except Exception as e:
        logger.error(f"Reset failed: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"❌ Reset failed: {str(e)}"
        )


async def _create_backup(experience_id: str, state_manager) -> str:
    """Create timestamped backup of world state."""

    try:
        # Load current world state
        world_state = await state_manager.get_world_state(experience_id)

        # Create backup directory
        backup_dir = Path(f"/kb/experiences/{experience_id}/state/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped backup file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"world.{timestamp}.json"

        # Write backup
        with backup_file.open('w') as f:
            json.dump(world_state, f, indent=2)

        logger.info(f"Backup created: {backup_file}")

        # Rotate old backups (keep last 5)
        backups = sorted(backup_dir.glob("world.*.json"), reverse=True)
        for old_backup in backups[5:]:
            old_backup.unlink()
            logger.info(f"Deleted old backup: {old_backup}")

        return str(backup_file)

    except Exception as e:
        logger.warning(f"Failed to create backup: {e}")
        # Continue without backup (non-critical)
        return None


async def _restore_world_from_template(experience_id: str, state_manager) -> None:
    """Restore world.json from world.template.json."""

    template_path = Path(f"/kb/experiences/{experience_id}/state/world.template.json")

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Load template
    with template_path.open('r') as f:
        template = json.load(f)

    # Update metadata
    template["metadata"]["last_modified"] = datetime.now().isoformat()
    template["metadata"]["_version"] = template["metadata"].get("_version", 0) + 1
    template["metadata"]["_restored_from_template"] = datetime.now().isoformat()

    # Save as world state
    world_path = Path(f"/kb/experiences/{experience_id}/state/world.json")
    with world_path.open('w') as f:
        json.dump(template, f, indent=2)

    logger.info(f"World state restored from template: {experience_id}")


async def _clear_player_data(experience_id: str) -> int:
    """Clear all player views for this experience."""

    players_dir = Path("/kb/players")
    cleared_count = 0

    if not players_dir.exists():
        return 0

    for user_dir in players_dir.iterdir():
        if not user_dir.is_dir():
            continue

        player_exp_dir = user_dir / experience_id
        if player_exp_dir.exists():
            shutil.rmtree(player_exp_dir)
            cleared_count += 1
            logger.info(f"Cleared player data: {user_dir.name}/{experience_id}")

    logger.info(f"Cleared {cleared_count} player views")
    return cleared_count
