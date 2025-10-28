"""
Experience Interaction Endpoints

New stateful endpoints for game experiences using unified state model.
Replaces hardcoded /game/command with config-driven, markdown-based approach.
"""

import logging
import json
import re
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
    Interact with a game experience.

    This is the NEW stateful endpoint that:
    - Remembers player's current experience
    - Uses markdown hierarchical loading for game logic
    - Manages state through UnifiedStateManager
    - Supports both shared (multiplayer) and isolated (single-player) models

    Flow:
    1. Determine which experience (from request or player profile)
    2. If no experience selected, return experience selection prompt
    3. Load player view and world state
    4. Process message using markdown game logic
    5. Update state and return response

    Args:
        request: Interaction request with message and optional experience
        auth: Authentication info

    Returns:
        Response with narrative, state updates, and available actions
    """
    user_id = auth.get("user_id") or auth.get("email")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    state_manager = kb_agent.state_manager
    if not state_manager:
        raise HTTPException(status_code=500, detail="State manager not initialized")

    # Step 1: ALWAYS check if message contains experience selection first
    # This allows switching experiences mid-conversation
    available_experiences = state_manager.list_experiences()
    detected_exp = _detect_experience_selection(request.message, available_experiences)

    if detected_exp:
        # User is selecting/switching to an experience
        logger.info(f"Detected experience selection: '{detected_exp}' from message '{request.message}'")
        await state_manager.set_current_experience(user_id, detected_exp)

        # Get experience info for welcome message
        exp_info = state_manager.get_experience_info(detected_exp)

        narrative = (
            f"Great! You've selected **{exp_info['name']}**.\n\n"
            f"{exp_info.get('description', '')}\n\n"
            "What would you like to do?"
        )

        return InteractResponse(
            success=True,
            narrative=narrative,
            experience=detected_exp,
            available_actions=["look around", "check inventory", "explore"],
            metadata={"experience_selected": True}
        )

    # Step 2: No experience selection in message, use current/determined experience
    experience = await _determine_experience(
        state_manager,
        user_id,
        request.experience,
        request.force_experience_selection
    )

    if not experience:
        # Still no experience, return selection prompt
        return await _prompt_experience_selection(state_manager, user_id)

    # Step 3: Ensure player is bootstrapped
    try:
        player_view = await state_manager.get_player_view(experience, user_id)
        if not player_view:
            logger.info(f"Bootstrapping new player '{user_id}' for '{experience}'")
            player_view = await state_manager.bootstrap_player(experience, user_id)
    except Exception as e:
        logger.error(f"Error bootstrapping player: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize player: {e}")

    # Step 4: Get world state
    try:
        config = state_manager.load_config(experience)
        state_model = config["state"]["model"]

        if state_model == "shared":
            world_state = await state_manager.get_world_state(experience)
        else:  # isolated
            world_state = player_view  # In isolated model, player view IS the world state

    except Exception as e:
        logger.error(f"Error loading world state: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load world state: {e}")

    # Step 4: Process message using markdown game logic
    try:
        response = await _process_game_message(
            kb_agent,
            state_manager,
            request.message,
            experience,
            user_id,
            player_view,
            world_state,
            config
        )
    except Exception as e:
        logger.error(f"Error processing game message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process message: {e}")

    return response


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


async def _process_game_message(
    kb_agent_instance,
    state_manager,
    message: str,
    experience: str,
    user_id: str,
    player_view: Dict[str, Any],
    world_state: Dict[str, Any],
    config: Dict[str, Any]
) -> InteractResponse:
    """
    Process a game message using markdown game logic.

    This is where the magic happens:
    1. Detect which command the user is trying to execute
    2. Load game logic markdown for that command
    3. Use LLM to execute markdown instructions with state context
    4. Apply state changes if any
    5. Generate narrative response

    Args:
        kb_agent_instance: KB agent for LLM access
        state_manager: State manager for state operations
        message: Player's message
        experience: Experience ID
        user_id: User ID
        player_view: Player's view state
        world_state: World state
        config: Experience config

    Returns:
        Interaction response with narrative and state updates
    """
    logger.warning(f"[DIAGNOSTIC] _process_game_message called for exp={experience}, user={user_id}")

    try:
        # Step 1: Detect which command this is
        logger.warning(f"[DIAGNOSTIC] Starting command detection for: {message}")
        command_type = await _detect_command_type(
            kb_agent_instance,
            message,
            experience
        )

        logger.warning(f"[DIAGNOSTIC] Detected command type: {command_type}")

        # Step 2: Load markdown command file
        markdown_content = await _load_command_markdown(
            experience,
            command_type
        )

        if not markdown_content:
            # No markdown file found - return helpful error
            return InteractResponse(
                success=False,
                narrative=f"I don't understand the command '{command_type}'. Try 'look around', 'check inventory', or 'take [item]'.",
                experience=experience,
                available_actions=["look around", "check inventory"],
                metadata={"error": "command_not_found", "detected_command": command_type}
            )

        # Step 3: Execute command using LLM + markdown instructions
        # Write full state to file for debugging
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"/tmp/world_state_{timestamp}.json", "w") as f:
            f.write(json.dumps(world_state, indent=2))
        with open(f"/tmp/player_view_{timestamp}.json", "w") as f:
            f.write(json.dumps(player_view, indent=2))
        logger.warning(f"[DIAGNOSTIC] Wrote full state to /tmp/world_state_{timestamp}.json and player_view_{timestamp}.json")

        result = await _execute_markdown_command(
            kb_agent_instance,
            markdown_content,
            message,
            player_view,
            world_state,
            config,
            user_id
        )

        # Step 4: Apply state updates if any
        # Diagnostic logging for state persistence issue
        logger.info(f"Command result success: {result.get('success')}")
        logger.info(f"Has state_updates: {bool(result.get('state_updates'))}")
        if result.get("state_updates"):
            logger.info(f"Applying state updates: {json.dumps(result['state_updates'], indent=2)}")
        else:
            logger.warning(f"No state_updates in result for command: {command_type}")

        if result.get("state_updates"):
            await _apply_state_updates(
                state_manager,
                experience,
                user_id,
                result["state_updates"],
                config["state"]["model"]
            )

        # Step 5: Return response
        return InteractResponse(
            success=result.get("success", True),
            narrative=result.get("narrative", ""),
            experience=experience,
            state_updates=result.get("state_updates"),
            available_actions=result.get("available_actions", []),
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error processing game message: {e}", exc_info=True)
        return InteractResponse(
            success=False,
            narrative=f"Something went wrong: {str(e)}",
            experience=experience,
            available_actions=["look around", "check inventory"],
            metadata={"error": "execution_failed", "error_message": str(e)}
        )


async def _discover_available_commands(experience: str) -> dict[str, list[str]]:
    """
    Discover available commands by scanning game-logic directory for .md files.

    Args:
        experience: Experience ID

    Returns:
        Dictionary mapping command name to list of aliases/synonyms
    """
    kb_root = Path(settings.KB_PATH)
    game_logic_dir = kb_root / "experiences" / experience / "game-logic"

    commands = {}

    try:
        if not game_logic_dir.exists():
            logger.warning(f"Game logic directory not found: {game_logic_dir}")
            return {}

        # Scan for .md files
        for md_file in game_logic_dir.glob("*.md"):
            try:
                content = md_file.read_text()

                # Parse frontmatter to extract command name and aliases
                if content.startswith("---"):
                    frontmatter_end = content.find("---", 3)
                    if frontmatter_end != -1:
                        frontmatter = content[3:frontmatter_end].strip()

                        # Extract command name and aliases
                        command_name = None
                        aliases = []

                        for line in frontmatter.split("\n"):
                            line = line.strip()
                            if line.startswith("command:"):
                                command_name = line.split(":", 1)[1].strip()
                            elif line.startswith("aliases:"):
                                # Parse aliases list: [move, walk, travel]
                                aliases_str = line.split(":", 1)[1].strip()
                                if aliases_str.startswith("[") and aliases_str.endswith("]"):
                                    aliases_str = aliases_str[1:-1]
                                    aliases = [a.strip() for a in aliases_str.split(",")]

                        if command_name:
                            # Combine command name with aliases
                            all_keywords = [command_name] + aliases
                            commands[command_name] = all_keywords
                            logger.info(f"Discovered command '{command_name}' with aliases: {aliases}")

            except Exception as e:
                logger.error(f"Error parsing command file {md_file}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error discovering commands for {experience}: {e}")

    return commands


async def _detect_command_type(
    kb_agent_instance,
    message: str,
    experience: str
) -> str:
    """
    Use LLM to detect which command type the user is trying to execute.

    Args:
        kb_agent_instance: KB agent for LLM access
        message: User's message
        experience: Experience ID

    Returns:
        Command type (e.g., "look", "collect", "inventory", "talk")
    """
    # Discover available commands from markdown files
    command_mappings = await _discover_available_commands(experience)
    available_commands = list(command_mappings.keys())

    # Build command mapping text for LLM
    mapping_lines = []
    for cmd, keywords in command_mappings.items():
        mapping_lines.append(f"- {cmd}: {', '.join(keywords)}")

    detection_prompt = f"""You are a command parser for a text adventure game.

User message: "{message}"
Available commands: {", ".join(available_commands)}

Analyze the user's message and determine which command they're trying to execute.
Consider synonyms and natural language variations.

Command mappings:
{chr(10).join(mapping_lines)}

Respond with ONLY the command name (one word, lowercase).
If you're not sure, default to "look".

Command:"""

    try:
        # Use fast model for quick detection
        response = await kb_agent_instance.llm_service.chat_completion(
            messages=[
                {"role": "system", "content": "You are a command parser. Respond with ONLY the command name."},
                {"role": "user", "content": detection_prompt}
            ],
            model="claude-haiku-4-5",  # This model IS registered
            user_id="system",
            temperature=0.1
        )

        command_type = response["response"].strip().lower()

        # Validate it's a known command
        if command_type not in available_commands:
            logger.warning(f"Unknown command '{command_type}', defaulting to 'look'")
            command_type = "look"

        return command_type

    except Exception as e:
        logger.error(f"Error detecting command type: {e}")
        return "look"  # Safe default


async def _load_command_markdown(
    experience: str,
    command_type: str
) -> Optional[str]:
    """
    Load markdown file for a command.

    Args:
        experience: Experience ID
        command_type: Command type (e.g., "look", "collect")

    Returns:
        Markdown file content or None if not found
    """
    kb_root = Path(settings.KB_PATH)
    markdown_path = kb_root / "experiences" / experience / "game-logic" / f"{command_type}.md"

    try:
        if markdown_path.exists():
            return markdown_path.read_text()
        else:
            logger.warning(f"Markdown command file not found: {markdown_path}")
            return None
    except Exception as e:
        logger.error(f"Error loading markdown file {markdown_path}: {e}")
        return None


async def _execute_markdown_command(
    kb_agent_instance,
    markdown_content: str,
    user_message: str,
    player_view: Dict[str, Any],
    world_state: Dict[str, Any],
    config: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """
    Execute a command by having LLM follow markdown instructions.

    Args:
        kb_agent_instance: KB agent for LLM access
        markdown_content: Markdown command file content
        user_message: User's original message
        player_view: Player's view state
        world_state: World state
        config: Experience config
        user_id: User ID

    Returns:
        Dict with: success, narrative, state_updates, available_actions, metadata
    """
    print(f"[DIAGNOSTIC] Executing markdown command for user: {user_id}")  # Force output

    # Build execution prompt with all context
    execution_prompt = f"""You are a game command executor. You will execute a game command by following the instructions in a markdown file.

## Markdown Command Instructions:
{markdown_content}

## User's Message:
"{user_message}"

## Current Player State:
```json
{json.dumps(player_view, indent=2)}
```

## Current World State:
```json
{json.dumps(world_state, indent=2)}
```

## Experience Config:
State Model: {config["state"]["model"]}

## Your Task:
Follow the markdown instructions EXACTLY. Process each section in order:
1. "Input Parameters" - Extract what the user is asking for
2. "State Access" - Read player_view and world_state (above)
3. "Execution Logic" - Execute the command step-by-step
4. "State Updates" - **CRITICAL**: Determine state changes
5. "Response Format" - Use the EXACT format from the markdown

## IMPORTANT - State Updates:
- **IF SUCCESS**: MUST include "state_updates" with actual changes
- **IF FAILURE**: Set "state_updates": null
- Follow the Response Format section in the markdown EXACTLY

## Response Rules:
1. Return ONLY valid JSON (no markdown blocks, no explanations)
2. Use the Response Format examples from the markdown as your template
3. For successful state-modifying commands, state_updates is REQUIRED
4. Match the example response structure exactly

Example for successful collect:
{{
  "success": true,
  "narrative": "You take the brass lantern.",
  "state_updates": {{
    "world": {{"path": "locations.west_of_house.items", "operation": "remove", "item_id": "lantern_1"}},
    "player": {{"path": "player.inventory", "operation": "add", "item": {{...}}}}
  }},
  "available_actions": [...],
  "metadata": {{...}}
}}

Now execute the command following the markdown instructions."""

    try:
        response = await kb_agent_instance.llm_service.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "You are a game command executor. You MUST respond with ONLY a valid JSON object. NO markdown code blocks, NO explanations, NO commentary - ONLY the raw JSON object."
                },
                {"role": "user", "content": execution_prompt}
            ],
            model="claude-sonnet-4-5",  # Use smarter model for execution
            user_id=user_id,
            temperature=0.1  # Lower temperature for more deterministic JSON output
        )

        # Parse JSON response
        response_text = response["response"].strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        # Diagnostic logging for state persistence issue
        # Write raw response to file for debugging
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        debug_file = f"/tmp/llm_response_{timestamp}.json"
        with open(debug_file, "w") as f:
            f.write(response_text)
        logger.warning(f"[DIAGNOSTIC] Wrote LLM response to {debug_file}")

        result = json.loads(response_text)

        # Log the parsed result
        logger.warning(f"[DIAGNOSTIC] Parsed result keys: {list(result.keys())}")
        logger.warning(f"[DIAGNOSTIC] state_updates present: {'state_updates' in result}")
        if 'state_updates' in result:
            logger.warning(f"[DIAGNOSTIC] state_updates value: {result['state_updates']}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}\nResponse: {response_text}")
        return {
            "success": False,
            "narrative": "I had trouble understanding that command. Please try again.",
            "available_actions": ["look around", "check inventory"],
            "metadata": {"error": "json_parse_failed"}
        }
    except Exception as e:
        logger.error(f"Error executing markdown command: {e}", exc_info=True)
        return {
            "success": False,
            "narrative": f"Something went wrong: {str(e)}",
            "available_actions": ["look around"],
            "metadata": {"error": str(e)}
        }


async def _apply_state_updates(
    state_manager,
    experience: str,
    user_id: str,
    state_updates: Dict[str, Any],
    state_model: str
) -> None:
    """
    Apply state updates returned by command execution.

    Args:
        state_manager: UnifiedStateManager instance
        experience: Experience ID
        user_id: User ID
        state_updates: State updates dict from command execution
        state_model: "shared" or "isolated"
    """
    try:
        # Apply world state updates
        if "world" in state_updates:
            world_update = state_updates["world"]
            path = world_update.get("path", "")
            operation = world_update.get("operation", "update")

            # Accept multiple field names for data (flexible format)
            data = world_update.get("data") or world_update.get("item_id") or world_update.get("item") or {}

            # Convert path to nested dict update
            updates = _path_to_nested_dict(path, data, operation)

            await state_manager.update_world_state(
                experience,
                updates,
                user_id if state_model == "isolated" else None
            )
            logger.debug(f"Applied world state update: {operation} at {path}")

        # Apply player state updates
        if "player" in state_updates:
            player_update = state_updates["player"]
            path = player_update.get("path", "")
            operation = player_update.get("operation", "update")

            # Accept multiple field names for data (flexible format)
            data = player_update.get("data") or player_update.get("item_id") or player_update.get("item") or {}

            logger.warning(f"[APPLY] Player update - path='{path}', operation='{operation}', data type={type(data)}")
            updates = _path_to_nested_dict(path, data, operation)
            logger.warning(f"[APPLY] Nested dict result: {json.dumps(updates, indent=2)[:500]}")

            await state_manager.update_player_view(
                experience,
                user_id,
                updates
            )
            logger.debug(f"Applied player state update: {operation} at {path}")

        logger.info(f"Applied state updates for user {user_id} in {experience}")

    except Exception as e:
        logger.error(f"Error applying state updates: {e}", exc_info=True)
        raise


def _path_to_nested_dict(path: str, data: Any, operation: str) -> Dict[str, Any]:
    """
    Convert a dotted path like "locations.waypoint_28a.items" to nested dict.

    Args:
        path: Dotted path string
        data: Data to set at path
        operation: "add", "remove", "update"

    Returns:
        Nested dict structure
    """
    if not path:
        return data if isinstance(data, dict) else {}

    parts = path.split(".")
    result = {}
    current = result

    for i, part in enumerate(parts[:-1]):
        current[part] = {}
        current = current[part]

    # Handle operation
    last_part = parts[-1]
    if operation == "add":
        current[last_part] = {"$append": data}
    elif operation == "remove":
        current[last_part] = {"$remove": data}
    else:  # update
        current[last_part] = data

    return result
