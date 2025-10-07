"""
Waypoints API for KB Service

Provides raw JSON access to waypoint markdown files.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import yaml
import logging
from pathlib import Path

from .kb_mcp_server import kb_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/waypoints", tags=["Waypoints"])


@router.get("/{experience}")
async def get_waypoints_for_experience(experience: str) -> Dict[str, Any]:
    """
    Get all waypoints for an experience as raw JSON.

    Args:
        experience: Experience name (e.g., "wylding-woods")

    Returns:
        {
            "success": True,
            "waypoints": [...],
            "count": int
        }
    """
    try:
        waypoints = []
        waypoints_path = f"experiences/{experience}/waypoints"

        # List waypoint files
        result = await kb_server.list_kb_directory(
            path=waypoints_path,
            pattern="*.md"
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=f"Experience not found: {experience}"
            )

        # Read and parse each waypoint file
        for file_info in result.get("files", []):
            file_path = file_info.get("path")

            # Skip index files
            if Path(file_path).name.startswith("+"):
                continue

            # Read file
            read_result = await kb_server.read_kb_file(
                path=file_path,
                parse_frontmatter=False
            )

            if not read_result.get("success"):
                logger.warning(f"Failed to read waypoint file: {file_path}")
                continue

            # Extract YAML from markdown
            content = read_result.get("content", "")
            yaml_content = _extract_yaml_block(content)

            if yaml_content:
                try:
                    waypoint = yaml.safe_load(yaml_content)
                    waypoints.append(waypoint)
                except yaml.YAMLError as e:
                    logger.error(f"YAML parse error in {file_path}: {e}")
                    continue

        logger.info(f"Loaded {len(waypoints)} waypoints for experience '{experience}'")

        return {
            "success": True,
            "waypoints": waypoints,
            "count": len(waypoints)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting waypoints for '{experience}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load waypoints: {str(e)}"
        )


def _extract_yaml_block(markdown_content: str) -> str:
    """Extract YAML code block from markdown content."""
    lines = markdown_content.split("\n")
    yaml_lines = []
    in_yaml_block = False

    for line in lines:
        if line.strip() == "```yaml":
            in_yaml_block = True
            continue
        elif line.strip() == "```" and in_yaml_block:
            break
        elif in_yaml_block:
            yaml_lines.append(line)

    return "\n".join(yaml_lines) if yaml_lines else ""
