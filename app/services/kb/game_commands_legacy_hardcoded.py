"""
Legacy Hardcoded Game Command System (ARCHIVED)

This module contains the ORIGINAL hardcoded implementation of the game command
system used in wylding-woods and west-of-house experiences.

## Why This Exists

This code is archived before migrating to markdown-driven command execution.
It represents the working, production-tested system that:

1. Parses natural language commands with Haiku 4.5 LLM
2. Routes to hardcoded Python methods (look, collect, return, inventory, talk)
3. Manages JSON state files (manifest.json, player progress, item instances)
4. Returns hardcoded narrative strings

## Migration Context

**Before Migration** (this file):
- Command logic: Hardcoded in Python
- Narratives: Hardcoded strings
- State: JSON files (this part stays the same)
- Response time: 1-2 seconds
- Content updates: Require code deploy

**After Migration** (new implementation):
- Command logic: Defined in markdown files
- Narratives: Generated from templates
- State: JSON files (no change)
- Response time: 2-4 seconds
- Content updates: Edit markdown, instant

## Usage

This file should NOT be imported or used directly. It exists for:
1. **Reference** - Understanding how the original system worked
2. **Comparison** - Validating new implementation matches behavior
3. **Rollback** - Emergency fallback if migration fails
4. **Documentation** - Showing what we're migrating away from

## Key Methods Archived

### Main Entry Point
- `execute_game_command()` - Parse and route player/admin commands

### Player Command Handlers
- `_find_instances_at_location()` - Look/observe command
- `_collect_item()` - Pick up items
- `_return_item()` - Return items to NPCs/destinations
- `_talk_to_npc()` - NPC conversations

### State Management
- `_load_player_state()` - Load player inventory/progress
- `_save_player_state_atomic()` - Save player state
- `_save_instance_atomic()` - Atomic file writes

### Admin Commands
- `_execute_admin_command()` - Route admin commands (@list, @create, etc.)
- ~20 admin command handlers (_admin_list, _admin_create, etc.)

## File Organization

Lines 1-3211 extracted from app/services/kb/kb_agent.py:
- Lines 113-330: execute_game_command() - Main entry point
- Lines 700-796: Player state management helpers
- Lines 797-1023: Instance operation methods
- Lines 1028-3041: Admin command system (23+ commands)
- Lines 3042-3323: NPC conversation system

## Date Archived

2025-10-27 (before markdown migration)

## Related Documentation

- /tmp/markdown_migration_plan.md - Complete migration plan
- /tmp/markdown_command_execution_flow.md - New vs old architecture
- docs/kb/game-command-systems.md - System comparison

## DO NOT MODIFY

This file is READ-ONLY. It represents the snapshot at the time of
migration and should be preserved for historical reference.

If you need to reference this code, copy specific methods to the new
implementation rather than importing from here.
"""

import json
import logging
import os
import time
import tempfile
from typing import Dict, Any, List, Optional

from app.shared.config import settings

logger = logging.getLogger(__name__)


class LegacyGameCommandHandler:
    """
    ARCHIVED: Original hardcoded game command handler.

    This class contains the complete original implementation.
    DO NOT use this in production - it's archived for reference only.
    """

    def __init__(self, llm_service, kb_server):
        """Initialize with required dependencies."""
        self.llm_service = llm_service
        self.kb_server = kb_server

    # ========== ARCHIVED METHOD: Main Entry Point ==========

    async def execute_game_command(
        self,
        command: str,
        experience: str,
        user_context: Dict[str, Any],
        session_state: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a game command using LLM to parse natural language → instance operations.

        Supports both player commands and admin commands (prefixed with @).

        This bridges natural language with instance management:
        1. Use LLM to parse command into structured action (player)
           OR parse admin command directly (admin)
        2. Execute corresponding instance management method
        3. Generate narrative from results

        Args:
            command: Player's natural language command or admin command (@list, @create, etc.)
            experience: Experience identifier (e.g., "wylding-woods", "west-of-house")
            user_context: User context (waypoint, sublocation, user_id, role, etc.)
            session_state: Current player state/inventory

        Returns:
            {
                "success": bool,
                "narrative": str,
                "actions": List[Dict],
                "state_changes": Dict,
                "model_used": str
            }
        """
        user_id = user_context.get("user_id", "unknown")
        role = user_context.get("role", "player")

        # Check if this is an admin command
        if command.strip().startswith("@"):
            if role != "admin":
                return {
                    "success": False,
                    "error": {
                        "code": "unauthorized",
                        "message": "Admin commands require admin role"
                    },
                    "narrative": "🚫 You don't have permission to use admin commands."
                }

            return await self._execute_admin_command(command.strip(), experience, user_context)

        # Player command processing (existing logic)
        waypoint = user_context.get("waypoint", "unknown")
        sublocation = user_context.get("sublocation")

        # Step 1: Use LLM to parse command into structured action
        parse_prompt = f"""Parse this player command into a structured action:

Command: "{command}"

Experience: {experience}
Current location context (may be unknown):
- Waypoint: {waypoint}
- Sublocation: {sublocation or 'not specified'}

Extract location FROM the command if mentioned, otherwise use current context.

Respond with ONLY a JSON object (no markdown, no explanation):
{{
  "action": "look" | "collect" | "return" | "inventory" | "talk" | "unknown",
  "target": "item_name or npc_name (if applicable)",
  "destination": "destination_name (for return action)",
  "waypoint": "waypoint_id (if mentioned in command, else use current)",
  "sublocation": "sublocation_name (if mentioned in command, else use current)",
  "confidence": 0.0-1.0
}}

Examples:
- "look at shelf_1" → {{"action": "look", "sublocation": "shelf_1", "target": null}}
- "look around at shelf_1 in waypoint_28a" → {{"action": "look", "waypoint": "waypoint_28a", "sublocation": "shelf_1"}}
- "pick up the dream bottle" → {{"action": "collect", "target": "dream_bottle"}}
- "return bottle to fairy_door_1" → {{"action": "return", "target": "dream_bottle", "destination": "fairy_door_1", "sublocation": "fairy_door_1"}}
- "check inventory" → {{"action": "inventory"}}
- "talk to louisa" → {{"action": "talk", "target": "louisa"}}
- "ask louisa about the dream bottles" → {{"action": "talk", "target": "louisa"}}
- "hello louisa" → {{"action": "talk", "target": "louisa"}}
"""

        try:
            # Parse command with LLM
            parse_response = await self.llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a command parser. Respond ONLY with valid JSON."},
                    {"role": "user", "content": parse_prompt}
                ],
                model="claude-haiku-4-5",  # Fast model for parsing
                user_id=user_id,
                temperature=0.1  # Low temp for consistent parsing
            )

            # Extract JSON from response
            response_text = parse_response["response"].strip()
            if response_text.startswith("```"):
                # Remove markdown code blocks if present
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            parsed_action = json.loads(response_text.strip())

            # Step 2: Execute corresponding instance management method
            action_type = parsed_action.get("action")
            target = parsed_action.get("target")
            destination = parsed_action.get("destination")

            # Use extracted location from command, fallback to context
            command_waypoint = parsed_action.get("waypoint", waypoint)
            command_sublocation = parsed_action.get("sublocation", sublocation)

            if action_type == "look":
                result = await self._find_instances_at_location(experience, command_waypoint, command_sublocation)
                if len(result) == 0:
                    return {
                        "success": True,
                        "narrative": f"You don't see anything interesting here.",
                        "actions": [],
                        "state_changes": {},
                        "model_used": parse_response["model"]
                    }
                else:
                    items_list = [f"- {inst['semantic_name']}: {inst.get('description', 'No description')}"
                                 for inst in result]
                    narrative = f"You see:\n" + "\n".join(items_list)
                    return {
                        "success": True,
                        "narrative": narrative,
                        "actions": [],
                        "state_changes": {"visible_instances": result},
                        "model_used": parse_response["model"]
                    }

            elif action_type == "collect":
                if not target:
                    return {"success": False, "error": {"code": "no_target", "message": "What do you want to collect?"}}

                result = await self._collect_item(experience, target, user_id, command_waypoint, command_sublocation)
                return {**result, "model_used": parse_response["model"]}

            elif action_type == "return":
                if not target or not destination:
                    return {"success": False, "error": {"code": "incomplete_action", "message": "What do you want to return and where?"}}

                result = await self._return_item(experience, target, destination, user_id, command_waypoint, command_sublocation)
                return {**result, "model_used": parse_response["model"]}

            elif action_type == "inventory":
                player_state = await self._load_player_state(user_id, experience)
                inventory = player_state.get("inventory", [])

                if len(inventory) == 0:
                    narrative = "You're not carrying anything."
                else:
                    items_list = [f"- {item['semantic_name']}" + (f" ({item.get('symbol')} symbol)" if item.get('symbol') else "")
                                 for item in inventory]
                    narrative = f"You're carrying:\n" + "\n".join(items_list)

                return {
                    "success": True,
                    "narrative": narrative,
                    "actions": [],
                    "state_changes": {"inventory": inventory, "quest_progress": player_state.get("quest_progress", {})},
                    "model_used": parse_response["model"]
                }

            elif action_type == "talk":
                if not target:
                    return {"success": False, "error": {"code": "no_target", "message": "Who do you want to talk to?"}}

                # Extract the actual message from the original command
                # For now, use the full command as the message (LLM will extract intent)
                result = await self._talk_to_npc(
                    experience=experience,
                    npc_semantic_name=target,
                    message=command,
                    user_id=user_id,
                    waypoint=command_waypoint,
                    sublocation=command_sublocation
                )
                return {**result, "model_used": parse_response["model"]}

            else:
                return {
                    "success": False,
                    "error": {
                        "code": "unknown_action",
                        "message": f"I don't understand that command. Try: look, collect, return, inventory, or talk to NPCs."
                    },
                    "model_used": parse_response["model"]
                }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return {
                "success": False,
                "error": {
                    "code": "parse_error",
                    "message": "Failed to understand command. Please try rephrasing."
                }
            }
        except Exception as e:
            logger.error(f"Game command execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": {
                    "code": "execution_failed",
                    "message": str(e)
                }
            }

    async def execute_knowledge_workflow(
        self,
        workflow_path: str,
        parameters: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute a workflow defined in markdown.

        Example workflow in KB:
        ```markdown
        # Player Combat Workflow
        1. Check player stats
        2. Calculate damage based on weapon
        3. Apply environmental modifiers
        4. Update creature health
        ```
        """
        # Load workflow definition using KB server
        from .kb_mcp_server import kb_server
        workflow_content = await kb_server.read_kb_file(workflow_path)

        if not workflow_content.get("success"):
            raise ValueError(f"Could not load workflow: {workflow_path}")

        # Use LLM to interpret and execute workflow steps
        prompt = f"""
        Execute this workflow with parameters {parameters}:

        {workflow_content["content"]}

        Return the result of each step and final outcome.
        """

        response = await self.llm_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="claude-sonnet-4-5",  # Use powerful model for workflows
            user_id=user_id
        )

        return {
            "workflow": workflow_path,
            "parameters": parameters,
            "execution_result": response["response"],
            "model_used": response["model"]
        }

    async def validate_against_rules(
        self,
        action: str,
        rules_path: str,
        context: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Validate an action against rules defined in KB.
        """
        # Load rules - handle both files and directories
        if rules_path.endswith('.md'):
            # Single file
            from .kb_mcp_server import kb_server
            file_result = await kb_server.read_kb_file(rules_path)
            if file_result.get("success"):
                rules = {rules_path: file_result["content"]}
            else:
                rules = {}
        else:
            # Directory
            rules = await self._load_context(rules_path)

        prompt = f"""
        Validate this action against the rules:

        Action: {action}
        Context: {context}

        Rules:
        {chr(10).join(rules.values())}

        Return: valid/invalid and explanation
        """

        response = await self.llm_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="claude-3-5-haiku-20241022",  # Fast model for validation
            user_id=user_id,
            temperature=0.1  # Low temperature for consistency
        )

        return {
            "action": action,
            "validation_result": response["response"],
            "rules_checked": len(rules),
            "model_used": response["model"]
        }

    async def _load_context(self, context_path: str) -> Dict[str, str]:
        """Load knowledge files from specified path"""
        # Use existing KB MCP server functionality
        from .kb_mcp_server import kb_server

        try:
            # Use list_kb_directory to directly find markdown files in the path
            list_result = await kb_server.list_kb_directory(
                path=context_path,
                pattern="*.md"
            )

            files = {}
            if list_result.get("success"):
                # Load content from discovered files
                for file_info in list_result.get("files", []):
                    file_path = file_info["path"]
                    try:
                        file_result = await kb_server.read_kb_file(file_path)
                        if file_result.get("success"):
                            files[file_path] = file_result["content"]
                    except Exception as e:
                        logger.warning(f"Could not read file {file_path}: {e}")

                # Also check subdirectories recursively
                for dir_info in list_result.get("directories", []):
                    subdir_files = await self._load_context(dir_info["path"])
                    files.update(subdir_files)

            return files
        except Exception as e:
            logger.error(f"Failed to load context from {context_path}: {e}")
            return {}

    async def _collect_files_recursive(self, nav_node: Dict, files: Dict[str, str]):
        """Recursively collect file contents from navigation tree"""
        if nav_node.get("type") == "file":
            file_path = nav_node["path"]
            try:
                from .kb_mcp_server import kb_server
                file_result = await kb_server.read_kb_file(file_path)
                if file_result.get("success"):
                    files[file_path] = file_result["content"]
            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")

        # Process children
        for child in nav_node.get("children", []):
            await self._collect_files_recursive(child, files)

    def _build_decision_prompt(self, query: str, knowledge_files: Dict[str, str]) -> str:
        """Build prompt for decision-making mode"""
        knowledge_text = "\n\n".join([
            f"## {path}\n{content}" for path, content in knowledge_files.items()
        ])

        return f"""
        Based on the following knowledge base content, make a decision or provide guidance for this query:

        **Query:** {query}

        **Available Knowledge:**
        {knowledge_text}

        Please provide a clear decision or recommendation based on the available knowledge.
        """

    def _build_synthesis_prompt(self, query: str, knowledge_files: Dict[str, str]) -> str:
        """Build prompt for synthesis mode"""
        knowledge_text = "\n\n".join([
            f"## {path}\n{content}" for path, content in knowledge_files.items()
        ])

        return f"""
        Synthesize information from multiple knowledge sources to answer this query:

        **Query:** {query}

        **Knowledge Sources:**
        {knowledge_text}

        Please synthesize insights from across these sources to provide a comprehensive answer.
        """

    def _build_validation_prompt(self, query: str, knowledge_files: Dict[str, str]) -> str:
        """Build prompt for validation mode"""
        knowledge_text = "\n\n".join([
            f"## {path}\n{content}" for path, content in knowledge_files.items()
        ])

        return f"""
        Validate this query against the established rules and guidelines:

        **Query to Validate:** {query}

        **Rules and Guidelines:**
        {knowledge_text}

        Please return "VALID" or "INVALID" followed by a detailed explanation.
        """

    def _select_model_for_query(self, query: str, mode: str) -> str:
        """Select appropriate model based on query complexity and mode"""
        if mode == "validation":
            return "claude-3-5-haiku-20241022"  # Fast for validation
        elif len(query) > 1000 or mode == "synthesis":
            return "claude-sonnet-4-5"  # Powerful for complex tasks
        else:
            return "claude-3-5-haiku-20241022"  # Default fast model

    def _build_game_command_prompt(
        self,
        command: str,
        game_content: Dict[str, str],
        session_state: Dict[str, Any]
    ) -> str:
        """
        Build prompt for game command execution.

        The prompt instructs the LLM to:
        1. Load universal command vocabulary from KB
        2. Interpret the command against game content
        3. Generate narrative response
        4. Return structured actions following response-format.md
        """
        # Combine all game content
        content_text = "\n\n".join([
            f"## {path}\n{content}" for path, content in game_content.items()
        ])

        return f"""
You are a game master interpreting player commands for an interactive experience.

**Command System Reference**:
Follow the command vocabulary and response format defined in:
- `/shared/mmoirl-platform/commands/+commands.md` (command system overview)
- `/shared/mmoirl-platform/commands/universal-actions.md` (action vocabulary)
- `/shared/mmoirl-platform/commands/response-format.md` (JSON response structure)

**Key Principles**:
- Commands are SEMANTIC - describe WHAT happens, not HOW to render it
- Actions come from universal vocabulary (talk, examine, collect, etc.)
- Targets come from game content below (NPCs, items, locations)
- Return structured JSON following response-format.md

**Game Content (NPCs, Items, Locations, Quests):**
{content_text}

**Current Player State:**
{session_state}

**Player Command:**
{command}

**Processing Instructions**:
1. Parse command to identify semantic action and target
2. Validate action exists in universal-actions.md vocabulary
3. Validate target exists in game content above
4. Check if player state allows this action
5. Generate narrative appropriate to experience genre
6. Determine client actions (audio, visual, state updates)
7. Calculate state changes (inventory, quests, relationships)

**Required Response Format (from response-format.md)**:
```json
{{
  "success": true,
  "narrative": "Descriptive narrative of what happens (adapt style to experience genre)",
  "actions": [
    {{"action": "add_to_inventory", "item": "item_id"}},
    {{"action": "play_sound", "sound": "effect.mp3", "volume": 0.7}},
    {{"action": "trigger_ar_effect", "effect": "sparkles", "duration_ms": 2000}},
    {{"action": "update_dialogue_state", "npc": "npc_id", "dialogue_node": "greeting"}}
  ],
  "state_changes": {{
    "inventory": ["item1", "item2"],
    "current_location": "waypoint_id",
    "quest_progress": {{"quest_id": {{"status": "active"}}}},
    "npc_relationships": {{"npc_id": {{"trust_level": 0.7}}}}
  }}
}}
```

If action invalid or target not found, return:
```json
{{
  "success": false,
  "error": {{
    "code": "invalid_action" | "target_not_found" | "state_invalid",
    "message": "Human-readable error message",
    "recoverable": true
  }},
  "suggestions": [
    {{"action": "examine", "target": "entity", "description": "Suggested next action"}}
  ]
}}
```

**Important**: Respond ONLY with the JSON object. No markdown code blocks, no explanatory text.
"""

    def _parse_game_response(
        self,
        llm_response: str,
        current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse LLM response into structured game command result.

        Handles both JSON responses and natural language fallback.
        """
        import json
        import re

        try:
            # Try to extract JSON from response
            # Look for JSON block in markdown or raw JSON
            json_match = re.search(r'```json\s*(\{.*\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to parse entire response as JSON
                json_str = llm_response.strip()

            parsed = json.loads(json_str)

            return {
                "success": True,
                "narrative": parsed.get("narrative", ""),
                "actions": parsed.get("actions", []),
                "state_changes": {**current_state, **parsed.get("state_changes", {})}
            }

        except (json.JSONDecodeError, AttributeError) as e:
            # Fallback: treat entire response as narrative
            logger.warning(f"Could not parse JSON from LLM response: {e}")
            return {
                "success": True,
                "narrative": llm_response,
                "actions": [],
                "state_changes": current_state
            }

    # ========== Instance Management Methods ==========

    async def _load_manifest(self, experience: str) -> Dict[str, Any]:
        """
        Load the instance manifest for an experience.

        Args:
            experience: Experience identifier (e.g., "wylding-woods")

        Returns:
            Manifest dictionary with instances list
        """
        import json
        import os

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        manifest_path = f"{kb_path}/experiences/{experience}/instances/manifest.json"

        if not os.path.exists(manifest_path):
            logger.warning(f"Manifest not found for experience '{experience}' at {manifest_path}")
            return {"experience": experience, "instances": []}

        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            return manifest
        except Exception as e:
            logger.error(f"Failed to load manifest for '{experience}': {e}")
            return {"experience": experience, "instances": []}

    async def _load_player_state(self, user_id: str, experience: str) -> Dict[str, Any]:
        """
        Load player state for an experience.

        Args:
            user_id: Player identifier
            experience: Experience identifier

        Returns:
            Player state dictionary
        """
        import json
        import os

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        player_state_path = f"{kb_path}/players/{user_id}/{experience}/progress.json"

        if not os.path.exists(player_state_path):
            # Initialize new player state
            return {
                "user_id": user_id,
                "experience": experience,
                "inventory": [],
                "current_location": None,
                "current_sublocation": None,
                "quest_progress": {},
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "last_modified": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

        try:
            with open(player_state_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load player state for {user_id}/{experience}: {e}")
            return {"user_id": user_id, "experience": experience, "inventory": []}

    async def _save_instance_atomic(self, file_path: str, data: Dict[str, Any]) -> bool:
        """
        Atomically save instance data to file.

        Uses os.replace() for POSIX atomic write operation.

        Args:
            file_path: Path to instance file
            data: Instance data to save

        Returns:
            True if successful, False otherwise
        """
        import json
        import os
        import tempfile

        try:
            # Write to temporary file first
            dir_path = os.path.dirname(file_path)
            os.makedirs(dir_path, exist_ok=True)

            with tempfile.NamedTemporaryFile(mode='w', dir=dir_path, delete=False, suffix='.tmp') as tmp_file:
                json.dump(data, tmp_file, indent=2)
                tmp_path = tmp_file.name

            # Atomic replace
            os.replace(tmp_path, file_path)
            return True

        except Exception as e:
            logger.error(f"Failed to save instance atomically to {file_path}: {e}")
            # Clean up temp file if it exists
            if 'tmp_path' in locals():
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            return False

    async def _save_player_state_atomic(self, user_id: str, experience: str, state: Dict[str, Any]) -> bool:
        """
        Atomically save player state.

        Args:
            user_id: Player identifier
            experience: Experience identifier
            state: Player state to save

        Returns:
            True if successful, False otherwise
        """
        kb_path = getattr(settings, 'KB_PATH', '/kb')
        player_state_path = f"{kb_path}/players/{user_id}/{experience}/progress.json"

        # Update last_modified timestamp
        state["last_modified"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        return await self._save_instance_atomic(player_state_path, state)

    async def _find_instances_at_location(
        self,
        experience: str,
        waypoint: str,
        sublocation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all instances at a specific location.

        Args:
            experience: Experience identifier
            waypoint: Waypoint ID (e.g., "waypoint_28a")
            sublocation: Optional sublocation ID (e.g., "shelf_1")

        Returns:
            List of instance dictionaries from manifest
        """
        manifest = await self._load_manifest(experience)

        instances = []
        for instance in manifest.get("instances", []):
            # Match waypoint
            if instance.get("location") != waypoint:
                continue

            # Match sublocation if specified
            if sublocation is not None and instance.get("sublocation") != sublocation:
                continue

            instances.append(instance)

        return instances

    async def _collect_item(
        self,
        experience: str,
        item_semantic_name: str,
        user_id: str,
        waypoint: str,
        sublocation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect an item and add to player inventory.

        Args:
            experience: Experience identifier
            item_semantic_name: Semantic name of item (e.g., "dream_bottle")
            user_id: Player identifier
            waypoint: Player's waypoint
            sublocation: Player's sublocation

        Returns:
            Result dictionary with success status and narrative
        """
        import json

        # 1. Find item instances at player's location
        candidates = await self._find_instances_at_location(experience, waypoint, sublocation)

        # Filter by semantic name and not already collected
        available_items = []
        kb_path = getattr(settings, 'KB_PATH', '/kb')
        for inst in candidates:
            if inst.get("semantic_name") == item_semantic_name:
                # Load instance file to check state
                instance_file_path = f"{kb_path}/experiences/{experience}/instances/{inst['instance_file']}"
                try:
                    with open(instance_file_path, 'r') as f:
                        instance_data = json.load(f)

                    # Check if already collected
                    if instance_data["state"].get("collected_by") is None:
                        available_items.append({"manifest_entry": inst, "instance_data": instance_data, "file_path": instance_file_path})
                except Exception as e:
                    logger.error(f"Failed to load instance file {instance_file_path}: {e}")

        if len(available_items) == 0:
            return {
                "success": False,
                "error": {"code": "item_not_found", "message": f"No {item_semantic_name} found here."}
            }

        # 2. Take the first available item (DD-007: location-based disambiguation)
        item = available_items[0]

        # 3. Update instance state (mark as collected)
        item["instance_data"]["state"]["collected_by"] = user_id
        item["instance_data"]["metadata"]["last_modified"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        item["instance_data"]["metadata"]["_version"] += 1

        success = await self._save_instance_atomic(item["file_path"], item["instance_data"])

        if not success:
            return {
                "success": False,
                "error": {"code": "save_failed", "message": "Failed to save item state."}
            }

        # 4. Update player inventory
        player_state = await self._load_player_state(user_id, experience)
        if "inventory" not in player_state:
            player_state["inventory"] = []

        player_state["inventory"].append({
            "instance_id": item["manifest_entry"]["id"],
            "semantic_name": item_semantic_name,
            "template": item["manifest_entry"]["template"],
            "symbol": item["instance_data"]["state"].get("symbol"),  # For dream bottles
            "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })

        await self._save_player_state_atomic(user_id, experience, player_state)

        # 5. Return success with narrative
        return {
            "success": True,
            "narrative": f"You carefully lift the {item_semantic_name}. {item['manifest_entry'].get('description', '')}",
            "actions": [{
                "type": "collect_item",
                "instance_id": item["manifest_entry"]["id"],
                "semantic_name": item_semantic_name,
                "sublocation": sublocation
            }],
            "state_changes": {
                "inventory": player_state["inventory"]
            }
        }

    async def _return_item(
        self,
        experience: str,
        item_semantic_name: str,
        destination_name: str,
        user_id: str,
        waypoint: str,
        sublocation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Return an item from inventory to a destination (e.g., fairy house).

        Validates symbol matching for dream bottles.

        Args:
            experience: Experience identifier
            item_semantic_name: Item to return (e.g., "dream_bottle")
            destination_name: Destination semantic name (e.g., "fairy_door_1")
            user_id: Player identifier
            waypoint: Player's waypoint
            sublocation: Player's sublocation

        Returns:
            Result dictionary with success status and narrative
        """
        # 1. Check player has item in inventory
        player_state = await self._load_player_state(user_id, experience)
        inventory = player_state.get("inventory", [])

        # Find item in inventory
        item_in_inventory = None
        for idx, inv_item in enumerate(inventory):
            if inv_item["semantic_name"] == item_semantic_name:
                item_in_inventory = (idx, inv_item)
                break

        if item_in_inventory is None:
            return {
                "success": False,
                "error": {"code": "item_not_in_inventory", "message": f"You don't have a {item_semantic_name}."}
            }

        item_idx, item_data = item_in_inventory

        # 2. Validate destination (for dream bottles, check symbol matching)
        # Parse destination_name to extract symbol (e.g., "fairy_door_1" → "spiral")
        # This is a simple demo - in production, load destination metadata from KB
        symbol_map = {
            "fairy_door_1": "spiral",
            "fairy_door_2": "star",
            "fairy_door_3": "moon",
            "fairy_door_4": "sun"
        }

        if destination_name in symbol_map:
            expected_symbol = symbol_map[destination_name]
            item_symbol = item_data.get("symbol")

            if item_symbol != expected_symbol:
                return {
                    "success": False,
                    "error": {
                        "code": "symbol_mismatch",
                        "message": f"The bottle's symbol doesn't match this house. Perhaps there's another house nearby with the matching symbol?"
                    }
                }

        # 3. Remove item from inventory
        player_state["inventory"].pop(item_idx)

        # 4. Update quest progress
        if "quest_progress" not in player_state:
            player_state["quest_progress"] = {}

        if "dream_bottle_quest" not in player_state["quest_progress"]:
            player_state["quest_progress"]["dream_bottle_quest"] = {"bottles_returned": 0}

        player_state["quest_progress"]["dream_bottle_quest"]["bottles_returned"] += 1

        await self._save_player_state_atomic(user_id, experience, player_state)

        # 5. Return success with narrative
        bottles_returned = player_state["quest_progress"]["dream_bottle_quest"]["bottles_returned"]

        return {
            "success": True,
            "narrative": f"The bottle dissolves into streams of light that flow into the fairy house. You hear distant, joyful music as the house glows brighter. ({bottles_returned}/4 bottles returned)",
            "actions": [{
                "type": "return_item",
                "item": item_semantic_name,
                "destination": destination_name,
                "sublocation": sublocation
            }],
            "state_changes": {
                "inventory": player_state["inventory"],
                "quest_progress": player_state["quest_progress"]
            }
        }

    # ========== End Instance Management Methods ==========

    # ========== Admin Command Methods ==========

    async def _execute_admin_command(
        self,
        command: str,
        experience: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute admin command (@list, @create, @edit, etc.).

        Admin commands use structured syntax, not natural language.

        Args:
            command: Admin command string (starting with @)
            experience: Experience identifier
            user_context: User context with user_id, role, etc.

        Returns:
            Result dictionary with success, narrative, and data
        """
        import re
        import os

        # Parse command structure: @action target [args...]
        # Examples:
        #   @list waypoints
        #   @list locations waypoint_28a
        #   @list items at waypoint_28a clearing shelf_1
        #   @create location waypoint_28a forest_path
        #   @inspect item dream_bottle_1

        parts = command[1:].split()  # Remove @ and split
        if len(parts) == 0:
            return {
                "success": False,
                "error": {"code": "invalid_command", "message": "Empty admin command"},
                "narrative": "❌ Invalid command. Try: @list waypoints"
            }

        action = parts[0].lower()
        target_type = parts[1].lower() if len(parts) > 1 else None

        try:
            # Route to appropriate handler
            if action == "list":
                return await self._admin_list(target_type, parts[2:], experience)
            elif action == "inspect":
                return await self._admin_inspect(target_type, parts[2:], experience)
            elif action == "create":
                return await self._admin_create(target_type, parts[2:], experience, user_context)
            elif action == "edit":
                return await self._admin_edit(target_type, parts[2:], experience, user_context)
            elif action == "delete":
                return await self._admin_delete(target_type, parts[2:], experience, user_context)
            elif action == "spawn":
                return await self._admin_spawn(target_type, parts[2:], experience, user_context)
            elif action == "where":
                return await self._admin_where(target_type, parts[1:], experience)
            elif action == "find":
                return await self._admin_find(parts[1:], experience)
            elif action == "stats":
                return await self._admin_stats(experience)
            elif action == "connect":
                return await self._admin_connect(parts[1:], experience, user_context)
            elif action == "disconnect":
                return await self._admin_disconnect(parts[1:], experience, user_context)
            elif action == "reset":
                return await self._admin_reset(target_type, parts[2:], experience, user_context)
            else:
                return {
                    "success": False,
                    "error": {"code": "unknown_command", "message": f"Unknown admin command: @{action}"},
                    "narrative": f"❌ Unknown command '@{action}'. Available: @list, @inspect, @create, @edit, @delete, @spawn, @where, @find, @stats, @connect, @disconnect, @reset"
                }

        except Exception as e:
            logger.error(f"Admin command failed: {command} - {e}", exc_info=True)
            return {
                "success": False,
                "error": {"code": "execution_failed", "message": str(e)},
                "narrative": f"❌ Command failed: {str(e)}"
            }

    async def _admin_list(
        self,
        target_type: Optional[str],
        args: List[str],
        experience: str
    ) -> Dict[str, Any]:
        """
        Handle @list commands.

        Supported:
        - @list waypoints
        - @list locations <waypoint>
        - @list sublocations <waypoint> <location>
        - @list items [at <waypoint> <location> <sublocation>]
        - @list templates [<type>]
        """
        kb_path = getattr(settings, 'KB_PATH', '/kb')

        if target_type == "waypoints":
            return await self._admin_list_waypoints(experience)

        elif target_type == "locations":
            if len(args) < 1:
                return {"success": False, "error": {"code": "missing_arg", "message": "Missing waypoint ID"}, "narrative": "❌ Usage: @list locations <waypoint>"}
            waypoint = args[0]
            return await self._admin_list_locations(experience, waypoint)

        elif target_type == "sublocations":
            if len(args) < 2:
                return {"success": False, "error": {"code": "missing_arg", "message": "Missing waypoint and location"}, "narrative": "❌ Usage: @list sublocations <waypoint> <location>"}
            waypoint, location = args[0], args[1]
            return await self._admin_list_sublocations(experience, waypoint, location)

        elif target_type == "items":
            # @list items [at waypoint location sublocation]
            if len(args) >= 4 and args[0] == "at":
                waypoint, location, sublocation = args[1], args[2], args[3]
                return await self._admin_list_items_at(experience, waypoint, location, sublocation)
            else:
                # List all items in experience
                return await self._admin_list_all_items(experience)

        elif target_type == "templates":
            # @list templates [item|npc]
            filter_type = args[0] if len(args) > 0 else None
            return await self._admin_list_templates(experience, filter_type)

        else:
            return {
                "success": False,
                "error": {"code": "invalid_target", "message": f"Unknown list target: {target_type}"},
                "narrative": f"❌ Unknown target '{target_type}'. Try: waypoints, locations, sublocations, items, templates"
            }

    async def _admin_list_waypoints(self, experience: str) -> Dict[str, Any]:
        """List all waypoints in experience."""
        import os
        import json

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

        if not os.path.exists(locations_file):
            return {
                "success": False,
                "error": {"code": "not_found", "message": "locations.json not found"},
                "narrative": "❌ No locations.json file found for this experience."
            }

        try:
            with open(locations_file, 'r') as f:
                locations_data = json.load(f)

            waypoints = []
            for waypoint_id, waypoint_data in locations_data.items():
                waypoints.append({
                    "id": waypoint_id,
                    "name": waypoint_data.get("name", "Unnamed"),
                    "location_count": len(waypoint_data.get("locations", {}))
                })

            if len(waypoints) == 0:
                narrative = "No waypoints found."
            else:
                lines = ["Waypoints:"]
                for i, wp in enumerate(waypoints, 1):
                    lines.append(f"  {i}. {wp['id']} - {wp['name']} ({wp['location_count']} locations)")
                narrative = "\n".join(lines)

            return {
                "success": True,
                "narrative": narrative,
                "data": {"waypoints": waypoints},
                "actions": []
            }

        except Exception as e:
            logger.error(f"Failed to list waypoints: {e}")
            return {
                "success": False,
                "error": {"code": "read_failed", "message": str(e)},
                "narrative": f"❌ Failed to read waypoints: {str(e)}"
            }

    async def _admin_list_locations(self, experience: str, waypoint: str) -> Dict[str, Any]:
        """List all locations in a waypoint."""
        import os
        import json

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

        if not os.path.exists(locations_file):
            return {
                "success": False,
                "error": {"code": "not_found", "message": "locations.json not found"},
                "narrative": "❌ No locations.json file found."
            }

        try:
            with open(locations_file, 'r') as f:
                locations_data = json.load(f)

            if waypoint not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "waypoint_not_found", "message": f"Waypoint '{waypoint}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint}' not found."
                }

            waypoint_data = locations_data[waypoint]
            locations = []

            for location_id, location_data in waypoint_data.get("locations", {}).items():
                locations.append({
                    "id": location_id,
                    "name": location_data.get("name", "Unnamed"),
                    "sublocation_count": len(location_data.get("sublocations", {}))
                })

            if len(locations) == 0:
                narrative = f"No locations in waypoint '{waypoint}'."
            else:
                lines = [f"Locations in {waypoint}:"]
                for i, loc in enumerate(locations, 1):
                    lines.append(f"  {i}. {loc['id']} - {loc['name']} ({loc['sublocation_count']} sublocations)")
                narrative = "\n".join(lines)

            return {
                "success": True,
                "narrative": narrative,
                "data": {"waypoint": waypoint, "locations": locations},
                "actions": []
            }

        except Exception as e:
            logger.error(f"Failed to list locations: {e}")
            return {
                "success": False,
                "error": {"code": "read_failed", "message": str(e)},
                "narrative": f"❌ Failed to read locations: {str(e)}"
            }

    async def _admin_list_sublocations(self, experience: str, waypoint: str, location: str) -> Dict[str, Any]:
        """List all sublocations in a location."""
        import os
        import json

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

        if not os.path.exists(locations_file):
            return {
                "success": False,
                "error": {"code": "not_found", "message": "locations.json not found"},
                "narrative": "❌ No locations.json file found."
            }

        try:
            with open(locations_file, 'r') as f:
                locations_data = json.load(f)

            if waypoint not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "waypoint_not_found", "message": f"Waypoint '{waypoint}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint}' not found."
                }

            waypoint_data = locations_data[waypoint]

            if location not in waypoint_data.get("locations", {}):
                return {
                    "success": False,
                    "error": {"code": "location_not_found", "message": f"Location '{location}' not found in waypoint '{waypoint}'"},
                    "narrative": f"❌ Location '{location}' not found in waypoint '{waypoint}'."
                }

            location_data = waypoint_data["locations"][location]
            sublocations = []

            for subloc_id, subloc_data in location_data.get("sublocations", {}).items():
                exits = subloc_data.get("exits", [])
                sublocations.append({
                    "id": subloc_id,
                    "name": subloc_data.get("name", "Unnamed"),
                    "exits": exits,
                    "interactable": subloc_data.get("interactable", False)
                })

            if len(sublocations) == 0:
                narrative = f"No sublocations in {waypoint} → {location}."
            else:
                lines = [f"Sublocations in {waypoint} → {location}:"]
                for i, subloc in enumerate(sublocations, 1):
                    exits_str = ", ".join(subloc['exits']) if subloc['exits'] else "none"
                    lines.append(f"  {i}. {subloc['id']} - {subloc['name']} (exits: {exits_str})")
                narrative = "\n".join(lines)

            return {
                "success": True,
                "narrative": narrative,
                "data": {"waypoint": waypoint, "location": location, "sublocations": sublocations},
                "actions": []
            }

        except Exception as e:
            logger.error(f"Failed to list sublocations: {e}")
            return {
                "success": False,
                "error": {"code": "read_failed", "message": str(e)},
                "narrative": f"❌ Failed to read sublocations: {str(e)}"
            }

    async def _admin_list_items_at(self, experience: str, waypoint: str, location: str, sublocation: str) -> Dict[str, Any]:
        """List items at a specific sublocation."""
        # Use existing instance finding method
        instances = await self._find_instances_at_location(experience, waypoint, sublocation)

        if len(instances) == 0:
            narrative = f"No items at {waypoint} → {location} → {sublocation}."
        else:
            lines = [f"Items at {waypoint} → {location} → {sublocation}:"]
            for i, inst in enumerate(instances, 1):
                lines.append(f"  {i}. {inst['semantic_name']} (instance #{inst['id']}, template: {inst['template']})")
            narrative = "\n".join(lines)

        return {
            "success": True,
            "narrative": narrative,
            "data": {"items": instances},
            "actions": []
        }

    async def _admin_list_all_items(self, experience: str) -> Dict[str, Any]:
        """List all item instances in experience."""
        manifest = await self._load_manifest(experience)
        instances = manifest.get("instances", [])

        if len(instances) == 0:
            narrative = "No item instances in this experience."
        else:
            lines = [f"All items in {experience}:"]
            for i, inst in enumerate(instances, 1):
                location_str = f"{inst.get('location', 'unknown')}/{inst.get('sublocation', 'unknown')}"
                lines.append(f"  {i}. {inst['semantic_name']} at {location_str} (instance #{inst['id']})")
            narrative = "\n".join(lines)

        return {
            "success": True,
            "narrative": narrative,
            "data": {"items": instances},
            "actions": []
        }

    async def _admin_list_templates(self, experience: str, filter_type: Optional[str]) -> Dict[str, Any]:
        """List templates (items, NPCs, etc.)."""
        import os

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        templates_dir = f"{kb_path}/experiences/{experience}/templates"

        if not os.path.exists(templates_dir):
            return {
                "success": False,
                "error": {"code": "not_found", "message": "Templates directory not found"},
                "narrative": "❌ No templates directory found."
            }

        templates = []

        # Scan for template files
        for root, dirs, files in os.walk(templates_dir):
            for file in files:
                if file.endswith('.md'):
                    rel_path = os.path.relpath(os.path.join(root, file), templates_dir)
                    template_type = os.path.dirname(rel_path) if os.path.dirname(rel_path) else "unknown"
                    template_name = os.path.splitext(file)[0]

                    # Filter by type if specified
                    if filter_type and template_type != filter_type:
                        continue

                    templates.append({
                        "name": template_name,
                        "type": template_type,
                        "path": rel_path
                    })

        if len(templates) == 0:
            narrative = f"No templates found{f' of type {filter_type}' if filter_type else ''}."
        else:
            lines = [f"Templates{f' ({filter_type})' if filter_type else ''}:"]
            for i, tmpl in enumerate(templates, 1):
                lines.append(f"  {i}. {tmpl['name']} ({tmpl['type']})")
            narrative = "\n".join(lines)

        return {
            "success": True,
            "narrative": narrative,
            "data": {"templates": templates},
            "actions": []
        }

    async def _admin_inspect(self, target_type: Optional[str], args: List[str], experience: str) -> Dict[str, Any]:
        """
        Handle @inspect command - detailed inspection of game objects.

        Supported:
        - @inspect waypoint <id>
        - @inspect location <waypoint> <id>
        - @inspect sublocation <waypoint> <location> <id>
        - @inspect item <instance_id>
        """
        import os
        import json

        kb_path = getattr(settings, 'KB_PATH', '/kb')

        if target_type == "waypoint":
            if len(args) < 1:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing waypoint ID"},
                    "narrative": "❌ Usage: @inspect waypoint <id>"
                }

            waypoint_id = args[0]
            locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

            if not os.path.exists(locations_file):
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": "locations.json not found"},
                    "narrative": "❌ No locations.json found."
                }

            with open(locations_file, 'r') as f:
                locations_data = json.load(f)

            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            waypoint = locations_data[waypoint_id]
            location_count = len(waypoint.get("locations", {}))

            # Count total sublocations
            subloc_count = 0
            for loc in waypoint.get("locations", {}).values():
                subloc_count += len(loc.get("sublocations", {}))

            lines = [
                f"Waypoint: {waypoint_id}",
                f"  Name: {waypoint.get('name', 'Unnamed')}",
                f"  Description: {waypoint.get('description', 'No description')}",
                f"  Locations: {location_count}",
                f"  Total Sublocations: {subloc_count}",
                ""
            ]

            if waypoint.get("metadata"):
                lines.append("  Metadata:")
                for key, value in waypoint["metadata"].items():
                    lines.append(f"    {key}: {value}")

            if location_count > 0:
                lines.append("\n  Locations:")
                for loc_id, loc_data in waypoint["locations"].items():
                    subloc_count = len(loc_data.get("sublocations", {}))
                    lines.append(f"    • {loc_id} - {loc_data.get('name')} ({subloc_count} sublocations)")

            return {
                "success": True,
                "narrative": "\n".join(lines),
                "data": {"waypoint": waypoint},
                "actions": []
            }

        elif target_type == "location":
            if len(args) < 2:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing waypoint and location ID"},
                    "narrative": "❌ Usage: @inspect location <waypoint> <id>"
                }

            waypoint_id = args[0]
            location_id = args[1]
            locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

            if not os.path.exists(locations_file):
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": "locations.json not found"},
                    "narrative": "❌ No locations.json found."
                }

            with open(locations_file, 'r') as f:
                locations_data = json.load(f)

            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            if location_id not in locations_data[waypoint_id]["locations"]:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Location '{location_id}' not found"},
                    "narrative": f"❌ Location '{location_id}' does not exist."
                }

            location = locations_data[waypoint_id]["locations"][location_id]
            subloc_count = len(location.get("sublocations", {}))

            lines = [
                f"Location: {waypoint_id}/{location_id}",
                f"  Name: {location.get('name', 'Unnamed')}",
                f"  Description: {location.get('description', 'No description')}",
                f"  Default Sublocation: {location.get('default_sublocation', 'none')}",
                f"  Sublocations: {subloc_count}",
                ""
            ]

            if location.get("metadata"):
                lines.append("  Metadata:")
                for key, value in location["metadata"].items():
                    lines.append(f"    {key}: {value}")

            if subloc_count > 0:
                lines.append("\n  Sublocations:")
                for subloc_id, subloc_data in location["sublocations"].items():
                    exits_count = len(subloc_data.get("exits", []))
                    lines.append(f"    • {subloc_id} - {subloc_data.get('name')} ({exits_count} exits)")

            return {
                "success": True,
                "narrative": "\n".join(lines),
                "data": {"location": location},
                "actions": []
            }

        elif target_type == "sublocation":
            if len(args) < 3:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing waypoint, location, and sublocation ID"},
                    "narrative": "❌ Usage: @inspect sublocation <waypoint> <location> <id>"
                }

            waypoint_id = args[0]
            location_id = args[1]
            sublocation_id = args[2]
            locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

            if not os.path.exists(locations_file):
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": "locations.json not found"},
                    "narrative": "❌ No locations.json found."
                }

            with open(locations_file, 'r') as f:
                locations_data = json.load(f)

            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            if location_id not in locations_data[waypoint_id]["locations"]:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Location '{location_id}' not found"},
                    "narrative": f"❌ Location '{location_id}' does not exist."
                }

            location = locations_data[waypoint_id]["locations"][location_id]

            if sublocation_id not in location["sublocations"]:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Sublocation '{sublocation_id}' not found"},
                    "narrative": f"❌ Sublocation '{sublocation_id}' does not exist."
                }

            subloc = location["sublocations"][sublocation_id]

            lines = [
                f"Sublocation: {waypoint_id}/{location_id}/{sublocation_id}",
                f"  Name: {subloc.get('name', 'Unnamed')}",
                f"  Description: {subloc.get('description', 'No description')}",
                f"  Interactable: {subloc.get('interactable', False)}",
                ""
            ]

            # Show exits
            exits = subloc.get("exits", [])
            if exits:
                lines.append(f"  Exits ({len(exits)}):")
                for exit_id in exits:
                    lines.append(f"    • {exit_id}")
            else:
                lines.append("  Exits: none")

            # Show cardinal exits
            cardinal = subloc.get("cardinal_exits", {})
            if cardinal:
                lines.append(f"\n  Cardinal Directions:")
                for direction, target in cardinal.items():
                    lines.append(f"    {direction} → {target}")

            # Show metadata
            if subloc.get("metadata"):
                lines.append("\n  Metadata:")
                for key, value in subloc["metadata"].items():
                    lines.append(f"    {key}: {value}")

            return {
                "success": True,
                "narrative": "\n".join(lines),
                "data": {"sublocation": subloc},
                "actions": []
            }

        elif target_type == "item":
            if len(args) < 1:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing instance ID"},
                    "narrative": "❌ Usage: @inspect item <instance_id>"
                }

            instance_id = int(args[0])
            manifest = await self._load_manifest(experience)

            # Find item in manifest
            item = None
            for inst in manifest.get("instances", []):
                if inst.get("id") == instance_id:
                    item = inst
                    break

            if not item:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Item instance #{instance_id} not found"},
                    "narrative": f"❌ Item instance #{instance_id} does not exist."
                }

            lines = [
                f"Item Instance: #{instance_id}",
                f"  Template: {item.get('template', 'unknown')}",
                f"  Semantic Name: {item.get('semantic_name', 'unknown')}",
                f"  Location: {item.get('location', 'unknown')}/{item.get('sublocation', 'unknown')}",
                f"  Instance File: {item.get('instance_file', 'unknown')}",
                ""
            ]

            if item.get("description"):
                lines.append(f"  Description: {item['description']}")
                lines.append("")

            if item.get("state"):
                lines.append("  State:")
                for key, value in item["state"].items():
                    lines.append(f"    {key}: {value}")
                lines.append("")

            if item.get("created_at"):
                lines.append(f"  Created: {item['created_at']}")

            return {
                "success": True,
                "narrative": "\n".join(lines),
                "data": {"item": item},
                "actions": []
            }

        else:
            return {
                "success": False,
                "error": {"code": "invalid_target", "message": f"Unknown inspect target: {target_type}"},
                "narrative": f"❌ Unknown target '{target_type}'. Try: waypoint, location, sublocation, item"
            }

    async def _admin_create(self, target_type: Optional[str], args: List[str], experience: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle @create command.

        Supported:
        - @create waypoint <id> <name>
        - @create location <waypoint> <id> <name>
        - @create sublocation <waypoint> <location> <id> <name>
        """
        import os
        import json
        import tempfile
        from datetime import datetime

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

        if target_type == "waypoint":
            if len(args) < 2:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing waypoint ID and name"},
                    "narrative": "❌ Usage: @create waypoint <id> <name>"
                }

            waypoint_id = args[0]
            waypoint_name = " ".join(args[1:])

            # Load existing locations
            if os.path.exists(locations_file):
                with open(locations_file, 'r') as f:
                    locations_data = json.load(f)
            else:
                locations_data = {}

            # Check if waypoint already exists
            if waypoint_id in locations_data:
                return {
                    "success": False,
                    "error": {"code": "already_exists", "message": f"Waypoint '{waypoint_id}' already exists"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' already exists. Use @edit to modify."
                }

            # Create new waypoint
            locations_data[waypoint_id] = {
                "waypoint_id": waypoint_id,
                "name": waypoint_name,
                "description": f"Waypoint: {waypoint_name}",
                "locations": {},
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "created_by": user_context.get("user_id", "unknown")
                }
            }

            # Save atomically
            await self._save_locations_atomic(locations_file, locations_data)

            return {
                "success": True,
                "narrative": f"✅ Created waypoint '{waypoint_id}' - {waypoint_name}",
                "data": {"waypoint": locations_data[waypoint_id]},
                "actions": []
            }

        elif target_type == "location":
            if len(args) < 3:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing waypoint, location ID, and name"},
                    "narrative": "❌ Usage: @create location <waypoint> <id> <name>"
                }

            waypoint_id = args[0]
            location_id = args[1]
            location_name = " ".join(args[2:])

            # Load existing locations
            if not os.path.exists(locations_file):
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": "locations.json not found"},
                    "narrative": "❌ No locations.json found. Create a waypoint first."
                }

            with open(locations_file, 'r') as f:
                locations_data = json.load(f)

            # Check waypoint exists
            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            # Check if location already exists
            if location_id in locations_data[waypoint_id]["locations"]:
                return {
                    "success": False,
                    "error": {"code": "already_exists", "message": f"Location '{location_id}' already exists"},
                    "narrative": f"❌ Location '{location_id}' already exists in '{waypoint_id}'."
                }

            # Create new location
            locations_data[waypoint_id]["locations"][location_id] = {
                "location_id": location_id,
                "name": location_name,
                "description": f"Location: {location_name}",
                "default_sublocation": "center",
                "sublocations": {},
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "created_by": user_context.get("user_id", "unknown")
                }
            }

            # Save atomically
            await self._save_locations_atomic(locations_file, locations_data)

            return {
                "success": True,
                "narrative": f"✅ Created location '{location_id}' - {location_name} in '{waypoint_id}'",
                "data": {"location": locations_data[waypoint_id]["locations"][location_id]},
                "actions": []
            }

        elif target_type == "sublocation":
            if len(args) < 4:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing waypoint, location, sublocation ID, and name"},
                    "narrative": "❌ Usage: @create sublocation <waypoint> <location> <id> <name>"
                }

            waypoint_id = args[0]
            location_id = args[1]
            sublocation_id = args[2]
            sublocation_name = " ".join(args[3:])

            # Load existing locations
            if not os.path.exists(locations_file):
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": "locations.json not found"},
                    "narrative": "❌ No locations.json found. Create a waypoint and location first."
                }

            with open(locations_file, 'r') as f:
                locations_data = json.load(f)

            # Check waypoint exists
            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            # Check location exists
            if location_id not in locations_data[waypoint_id]["locations"]:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Location '{location_id}' not found"},
                    "narrative": f"❌ Location '{location_id}' does not exist in '{waypoint_id}'."
                }

            location_data = locations_data[waypoint_id]["locations"][location_id]

            # Check if sublocation already exists
            if sublocation_id in location_data["sublocations"]:
                return {
                    "success": False,
                    "error": {"code": "already_exists", "message": f"Sublocation '{sublocation_id}' already exists"},
                    "narrative": f"❌ Sublocation '{sublocation_id}' already exists in '{waypoint_id}/{location_id}'."
                }

            # Create new sublocation
            location_data["sublocations"][sublocation_id] = {
                "sublocation_id": sublocation_id,
                "name": sublocation_name,
                "description": f"Sublocation: {sublocation_name}",
                "interactable": True,
                "exits": [],
                "cardinal_exits": {},
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "created_by": user_context.get("user_id", "unknown")
                }
            }

            # Save atomically
            await self._save_locations_atomic(locations_file, locations_data)

            return {
                "success": True,
                "narrative": f"✅ Created sublocation '{sublocation_id}' - {sublocation_name} in '{waypoint_id}/{location_id}'",
                "data": {"sublocation": location_data["sublocations"][sublocation_id]},
                "actions": []
            }

        else:
            return {
                "success": False,
                "error": {"code": "invalid_target", "message": f"Unknown create target: {target_type}"},
                "narrative": f"❌ Unknown target '{target_type}'. Try: waypoint, location, sublocation"
            }

    async def _save_locations_atomic(self, file_path: str, data: Dict[str, Any]) -> None:
        """Save locations.json atomically using temp file + rename."""
        import os
        import json
        import tempfile

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write to temp file in same directory
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(file_path), suffix='.json')
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(data, f, indent=2)

            # Atomic rename
            os.replace(temp_path, file_path)
        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e

    async def _admin_edit(self, target_type: Optional[str], args: List[str], experience: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle @edit command - modify properties of waypoint/location/sublocation.

        Supported:
        - @edit waypoint <id> name <new_name>
        - @edit waypoint <id> description <new_description>
        - @edit location <waypoint> <id> name <new_name>
        - @edit location <waypoint> <id> description <new_description>
        - @edit sublocation <waypoint> <location> <id> name <new_name>
        - @edit sublocation <waypoint> <location> <id> description <new_description>
        - @edit sublocation <waypoint> <location> <id> interactable <true|false>
        """
        import os
        import json
        from datetime import datetime

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

        if not os.path.exists(locations_file):
            return {
                "success": False,
                "error": {"code": "not_found", "message": "locations.json not found"},
                "narrative": "❌ No locations.json found."
            }

        with open(locations_file, 'r') as f:
            locations_data = json.load(f)

        if target_type == "waypoint":
            if len(args) < 3:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing arguments"},
                    "narrative": "❌ Usage: @edit waypoint <id> <field> <value>"
                }

            waypoint_id = args[0]
            field = args[1].lower()
            value = " ".join(args[2:])

            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            waypoint = locations_data[waypoint_id]

            if field == "name":
                old_value = waypoint.get("name", "")
                waypoint["name"] = value
            elif field == "description":
                old_value = waypoint.get("description", "")
                waypoint["description"] = value
            else:
                return {
                    "success": False,
                    "error": {"code": "invalid_field", "message": f"Unknown field: {field}"},
                    "narrative": f"❌ Unknown field '{field}'. Available: name, description"
                }

            # Update metadata
            if "metadata" not in waypoint:
                waypoint["metadata"] = {}
            waypoint["metadata"]["last_modified"] = datetime.now().isoformat()
            waypoint["metadata"]["last_modified_by"] = user_context.get("user_id", "unknown")

            await self._save_locations_atomic(locations_file, locations_data)

            return {
                "success": True,
                "narrative": f"✅ Updated waypoint '{waypoint_id}' {field}: '{old_value}' → '{value}'",
                "data": {"waypoint": waypoint},
                "actions": []
            }

        elif target_type == "location":
            if len(args) < 4:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing arguments"},
                    "narrative": "❌ Usage: @edit location <waypoint> <id> <field> <value>"
                }

            waypoint_id = args[0]
            location_id = args[1]
            field = args[2].lower()
            value = " ".join(args[3:])

            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            if location_id not in locations_data[waypoint_id]["locations"]:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Location '{location_id}' not found"},
                    "narrative": f"❌ Location '{location_id}' does not exist."
                }

            location = locations_data[waypoint_id]["locations"][location_id]

            if field == "name":
                old_value = location.get("name", "")
                location["name"] = value
            elif field == "description":
                old_value = location.get("description", "")
                location["description"] = value
            elif field == "default_sublocation":
                old_value = location.get("default_sublocation", "")
                # Validate sublocation exists
                if value not in location.get("sublocations", {}):
                    return {
                        "success": False,
                        "error": {"code": "not_found", "message": f"Sublocation '{value}' not found"},
                        "narrative": f"❌ Sublocation '{value}' does not exist in this location."
                    }
                location["default_sublocation"] = value
            else:
                return {
                    "success": False,
                    "error": {"code": "invalid_field", "message": f"Unknown field: {field}"},
                    "narrative": f"❌ Unknown field '{field}'. Available: name, description, default_sublocation"
                }

            # Update metadata
            if "metadata" not in location:
                location["metadata"] = {}
            location["metadata"]["last_modified"] = datetime.now().isoformat()
            location["metadata"]["last_modified_by"] = user_context.get("user_id", "unknown")

            await self._save_locations_atomic(locations_file, locations_data)

            return {
                "success": True,
                "narrative": f"✅ Updated location '{waypoint_id}/{location_id}' {field}: '{old_value}' → '{value}'",
                "data": {"location": location},
                "actions": []
            }

        elif target_type == "sublocation":
            if len(args) < 5:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing arguments"},
                    "narrative": "❌ Usage: @edit sublocation <waypoint> <location> <id> <field> <value>"
                }

            waypoint_id = args[0]
            location_id = args[1]
            sublocation_id = args[2]
            field = args[3].lower()
            value = " ".join(args[4:])

            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            if location_id not in locations_data[waypoint_id]["locations"]:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Location '{location_id}' not found"},
                    "narrative": f"❌ Location '{location_id}' does not exist."
                }

            location = locations_data[waypoint_id]["locations"][location_id]

            if sublocation_id not in location["sublocations"]:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Sublocation '{sublocation_id}' not found"},
                    "narrative": f"❌ Sublocation '{sublocation_id}' does not exist."
                }

            subloc = location["sublocations"][sublocation_id]

            if field == "name":
                old_value = subloc.get("name", "")
                subloc["name"] = value
            elif field == "description":
                old_value = subloc.get("description", "")
                subloc["description"] = value
            elif field == "interactable":
                old_value = subloc.get("interactable", False)
                if value.lower() in ["true", "yes", "1"]:
                    subloc["interactable"] = True
                    value = "true"
                else:
                    subloc["interactable"] = False
                    value = "false"
                old_value = str(old_value).lower()
            else:
                return {
                    "success": False,
                    "error": {"code": "invalid_field", "message": f"Unknown field: {field}"},
                    "narrative": f"❌ Unknown field '{field}'. Available: name, description, interactable"
                }

            # Update metadata
            if "metadata" not in subloc:
                subloc["metadata"] = {}
            subloc["metadata"]["last_modified"] = datetime.now().isoformat()
            subloc["metadata"]["last_modified_by"] = user_context.get("user_id", "unknown")

            await self._save_locations_atomic(locations_file, locations_data)

            return {
                "success": True,
                "narrative": f"✅ Updated sublocation '{waypoint_id}/{location_id}/{sublocation_id}' {field}: '{old_value}' → '{value}'",
                "data": {"sublocation": subloc},
                "actions": []
            }

        else:
            return {
                "success": False,
                "error": {"code": "invalid_target", "message": f"Unknown edit target: {target_type}"},
                "narrative": f"❌ Unknown target '{target_type}'. Try: waypoint, location, sublocation"
            }

    async def _admin_delete(self, target_type: Optional[str], args: List[str], experience: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle @delete command - remove waypoint/location/sublocation.

        Supported:
        - @delete waypoint <id> CONFIRM
        - @delete location <waypoint> <id> CONFIRM
        - @delete sublocation <waypoint> <location> <id> CONFIRM

        Requires CONFIRM to prevent accidental deletion.
        """
        import os
        import json

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

        if not os.path.exists(locations_file):
            return {
                "success": False,
                "error": {"code": "not_found", "message": "locations.json not found"},
                "narrative": "❌ No locations.json found."
            }

        with open(locations_file, 'r') as f:
            locations_data = json.load(f)

        if target_type == "waypoint":
            if len(args) < 2:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing waypoint ID and CONFIRM"},
                    "narrative": "❌ Usage: @delete waypoint <id> CONFIRM"
                }

            waypoint_id = args[0]
            confirm = args[1].upper() if len(args) > 1 else ""

            if confirm != "CONFIRM":
                return {
                    "success": False,
                    "error": {"code": "not_confirmed", "message": "Deletion not confirmed"},
                    "narrative": f"⚠️  Deleting waypoint '{waypoint_id}' will remove ALL locations and sublocations.\n   Add CONFIRM to proceed: @delete waypoint {waypoint_id} CONFIRM"
                }

            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            # Count what's being deleted
            location_count = len(locations_data[waypoint_id].get("locations", {}))
            subloc_count = sum(len(loc.get("sublocations", {})) for loc in locations_data[waypoint_id].get("locations", {}).values())

            del locations_data[waypoint_id]

            await self._save_locations_atomic(locations_file, locations_data)

            return {
                "success": True,
                "narrative": f"✅ Deleted waypoint '{waypoint_id}' ({location_count} locations, {subloc_count} sublocations removed)",
                "data": {"deleted": waypoint_id, "location_count": location_count, "subloc_count": subloc_count},
                "actions": []
            }

        elif target_type == "location":
            if len(args) < 3:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing waypoint, location ID, and CONFIRM"},
                    "narrative": "❌ Usage: @delete location <waypoint> <id> CONFIRM"
                }

            waypoint_id = args[0]
            location_id = args[1]
            confirm = args[2].upper() if len(args) > 2 else ""

            if confirm != "CONFIRM":
                return {
                    "success": False,
                    "error": {"code": "not_confirmed", "message": "Deletion not confirmed"},
                    "narrative": f"⚠️  Deleting location '{location_id}' will remove ALL sublocations.\n   Add CONFIRM to proceed: @delete location {waypoint_id} {location_id} CONFIRM"
                }

            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            if location_id not in locations_data[waypoint_id]["locations"]:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Location '{location_id}' not found"},
                    "narrative": f"❌ Location '{location_id}' does not exist."
                }

            # Count sublocations being deleted
            subloc_count = len(locations_data[waypoint_id]["locations"][location_id].get("sublocations", {}))

            del locations_data[waypoint_id]["locations"][location_id]

            await self._save_locations_atomic(locations_file, locations_data)

            return {
                "success": True,
                "narrative": f"✅ Deleted location '{waypoint_id}/{location_id}' ({subloc_count} sublocations removed)",
                "data": {"deleted": f"{waypoint_id}/{location_id}", "subloc_count": subloc_count},
                "actions": []
            }

        elif target_type == "sublocation":
            if len(args) < 4:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing waypoint, location, sublocation ID, and CONFIRM"},
                    "narrative": "❌ Usage: @delete sublocation <waypoint> <location> <id> CONFIRM"
                }

            waypoint_id = args[0]
            location_id = args[1]
            sublocation_id = args[2]
            confirm = args[3].upper() if len(args) > 3 else ""

            if confirm != "CONFIRM":
                return {
                    "success": False,
                    "error": {"code": "not_confirmed", "message": "Deletion not confirmed"},
                    "narrative": f"⚠️  This will delete sublocation '{sublocation_id}' and break any connections to it.\n   Add CONFIRM to proceed: @delete sublocation {waypoint_id} {location_id} {sublocation_id} CONFIRM"
                }

            if waypoint_id not in locations_data:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                    "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
                }

            if location_id not in locations_data[waypoint_id]["locations"]:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Location '{location_id}' not found"},
                    "narrative": f"❌ Location '{location_id}' does not exist."
                }

            location = locations_data[waypoint_id]["locations"][location_id]

            if sublocation_id not in location["sublocations"]:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Sublocation '{sublocation_id}' not found"},
                    "narrative": f"❌ Sublocation '{sublocation_id}' does not exist."
                }

            # Remove references from other sublocations' exits
            orphaned_connections = []
            for other_id, other_subloc in location["sublocations"].items():
                if other_id != sublocation_id:
                    if sublocation_id in other_subloc.get("exits", []):
                        other_subloc["exits"].remove(sublocation_id)
                        orphaned_connections.append(other_id)
                    # Remove cardinal exits
                    cardinal_to_remove = []
                    for direction, target in other_subloc.get("cardinal_exits", {}).items():
                        if target == sublocation_id:
                            cardinal_to_remove.append(direction)
                    for direction in cardinal_to_remove:
                        del other_subloc["cardinal_exits"][direction]

            del location["sublocations"][sublocation_id]

            await self._save_locations_atomic(locations_file, locations_data)

            narrative = f"✅ Deleted sublocation '{waypoint_id}/{location_id}/{sublocation_id}'"
            if orphaned_connections:
                narrative += f"\n   ⚠️  Removed connections from: {', '.join(orphaned_connections)}"

            return {
                "success": True,
                "narrative": narrative,
                "data": {"deleted": f"{waypoint_id}/{location_id}/{sublocation_id}", "orphaned": orphaned_connections},
                "actions": []
            }

        else:
            return {
                "success": False,
                "error": {"code": "invalid_target", "message": f"Unknown delete target: {target_type}"},
                "narrative": f"❌ Unknown target '{target_type}'. Try: waypoint, location, sublocation"
            }

    async def _admin_spawn(self, target_type: Optional[str], args: List[str], experience: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle @spawn command (placeholder)."""
        return {
            "success": False,
            "error": {"code": "not_implemented", "message": "@spawn not yet implemented"},
            "narrative": "❌ @spawn command coming soon."
        }

    async def _admin_where(self, target_type: Optional[str], args: List[str], experience: str) -> Dict[str, Any]:
        """
        Handle @where command - find item/NPC location by instance ID or name.

        Supported:
        - @where item <instance_id>
        - @where npc <instance_id>
        - @where <semantic_name>
        """
        if not args or len(args) < 1:
            return {
                "success": False,
                "error": {"code": "missing_arg", "message": "Missing search term"},
                "narrative": "❌ Usage: @where <instance_id> or @where item <instance_id>"
            }

        manifest = await self._load_manifest(experience)

        # Handle routing quirk: target_type might be the search term itself
        # If target_type is "item" or "npc", then args[0] is the search term
        # Otherwise, target_type IS the search term (for "@where louisa" case)
        if target_type in ["item", "npc"]:
            # Command was "@where item 1" -> target_type="item", args=["item", "1"]
            # Use args[1] as search term (skip the duplicate target_type in args[0])
            search_term = args[1] if len(args) > 1 else args[0]
        else:
            # Command was "@where louisa" -> target_type="louisa", args=["louisa"]
            # target_type IS the search term
            search_term = target_type if target_type else args[0]

        instance_id = None

        try:
            instance_id = int(search_term)
        except ValueError:
            # Not a number, treat as semantic name
            pass

        # Search in manifest
        found_items = []

        for inst in manifest.get("instances", []):
            # Match by instance ID or semantic name
            if instance_id is not None:
                if inst.get("id") == instance_id:
                    found_items.append(inst)
            else:
                if inst.get("semantic_name") == search_term or inst.get("template") == search_term:
                    found_items.append(inst)

        if len(found_items) == 0:
            return {
                "success": False,
                "error": {"code": "not_found", "message": f"No items found matching '{search_term}'"},
                "narrative": f"❌ No items found matching '{search_term}'."
            }

        lines = []
        if len(found_items) == 1:
            item = found_items[0]
            lines.append(f"Location of {item.get('semantic_name', 'item')} (instance #{item.get('id')}):")
            lines.append(f"  Waypoint: {item.get('location', 'unknown')}")
            lines.append(f"  Sublocation: {item.get('sublocation', 'unknown')}")
            lines.append(f"  Template: {item.get('template', 'unknown')}")
            if item.get("description"):
                lines.append(f"  Description: {item.get('description')}")
        else:
            lines.append(f"Found {len(found_items)} items matching '{search_term}':")
            for item in found_items:
                location_str = f"{item.get('location', '?')}/{item.get('sublocation', '?')}"
                lines.append(f"  • Instance #{item.get('id')} at {location_str}")

        return {
            "success": True,
            "narrative": "\n".join(lines),
            "data": {"items": found_items},
            "actions": []
        }

    async def _admin_find(self, args: List[str], experience: str) -> Dict[str, Any]:
        """
        Handle @find command - find all instances of a template.

        Syntax: @find <template_name>
        """
        if len(args) < 1:
            return {
                "success": False,
                "error": {"code": "missing_arg", "message": "Missing template name"},
                "narrative": "❌ Usage: @find <template_name>"
            }

        template_name = args[0]
        manifest = await self._load_manifest(experience)

        # Find all instances matching template
        found_items = []
        for inst in manifest.get("instances", []):
            if inst.get("template") == template_name:
                found_items.append(inst)

        if len(found_items) == 0:
            return {
                "success": False,
                "error": {"code": "not_found", "message": f"No instances of template '{template_name}' found"},
                "narrative": f"❌ No instances of template '{template_name}' found."
            }

        # Group by location
        by_location = {}
        for item in found_items:
            location_key = f"{item.get('location', 'unknown')}/{item.get('sublocation', 'unknown')}"
            if location_key not in by_location:
                by_location[location_key] = []
            by_location[location_key].append(item)

        lines = [f"Found {len(found_items)} instances of '{template_name}':"]
        lines.append("")

        for location_key, items in sorted(by_location.items()):
            lines.append(f"  {location_key}:")
            for item in items:
                desc = item.get('description', 'no description')
                lines.append(f"    • Instance #{item.get('id')} - {desc}")

        return {
            "success": True,
            "narrative": "\n".join(lines),
            "data": {
                "template": template_name,
                "count": len(found_items),
                "items": found_items,
                "by_location": by_location
            },
            "actions": []
        }

    async def _admin_connect(self, args: List[str], experience: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle @connect command - add bidirectional edge between sublocations.

        Syntax: @connect <waypoint> <location> <from_subloc> <to_subloc> [direction]

        Creates exits from both sublocations:
        - from_subloc.exits includes to_subloc
        - to_subloc.exits includes from_subloc

        Optional direction (north/south/east/west) adds cardinal shortcuts.
        """
        import os
        import json

        if len(args) < 4:
            return {
                "success": False,
                "error": {"code": "missing_arg", "message": "Missing required arguments"},
                "narrative": "❌ Usage: @connect <waypoint> <location> <from_subloc> <to_subloc> [direction]"
            }

        waypoint_id = args[0]
        location_id = args[1]
        from_subloc = args[2]
        to_subloc = args[3]
        direction = args[4].lower() if len(args) > 4 else None

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

        # Load locations
        if not os.path.exists(locations_file):
            return {
                "success": False,
                "error": {"code": "not_found", "message": "locations.json not found"},
                "narrative": "❌ No locations.json found."
            }

        with open(locations_file, 'r') as f:
            locations_data = json.load(f)

        # Validate hierarchy
        if waypoint_id not in locations_data:
            return {
                "success": False,
                "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
            }

        if location_id not in locations_data[waypoint_id]["locations"]:
            return {
                "success": False,
                "error": {"code": "not_found", "message": f"Location '{location_id}' not found"},
                "narrative": f"❌ Location '{location_id}' does not exist in '{waypoint_id}'."
            }

        location_data = locations_data[waypoint_id]["locations"][location_id]

        # Check both sublocations exist
        if from_subloc not in location_data["sublocations"]:
            return {
                "success": False,
                "error": {"code": "not_found", "message": f"Sublocation '{from_subloc}' not found"},
                "narrative": f"❌ Sublocation '{from_subloc}' does not exist."
            }

        if to_subloc not in location_data["sublocations"]:
            return {
                "success": False,
                "error": {"code": "not_found", "message": f"Sublocation '{to_subloc}' not found"},
                "narrative": f"❌ Sublocation '{to_subloc}' does not exist."
            }

        from_data = location_data["sublocations"][from_subloc]
        to_data = location_data["sublocations"][to_subloc]

        # Add bidirectional exits
        if to_subloc not in from_data["exits"]:
            from_data["exits"].append(to_subloc)

        if from_subloc not in to_data["exits"]:
            to_data["exits"].append(from_subloc)

        # Add cardinal directions if specified
        opposite_directions = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east"
        }

        if direction and direction in opposite_directions:
            from_data["cardinal_exits"][direction] = to_subloc
            to_data["cardinal_exits"][opposite_directions[direction]] = from_subloc

        # Save atomically
        await self._save_locations_atomic(locations_file, locations_data)

        narrative_parts = [f"✅ Connected {from_subloc} ↔ {to_subloc}"]
        if direction:
            narrative_parts.append(f"   ({from_subloc} {direction}→ {to_subloc})")

        return {
            "success": True,
            "narrative": "\n".join(narrative_parts),
            "data": {
                "from": from_subloc,
                "to": to_subloc,
                "direction": direction,
                "from_exits": from_data["exits"],
                "to_exits": to_data["exits"]
            },
            "actions": []
        }

    async def _admin_disconnect(self, args: List[str], experience: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle @disconnect command - remove bidirectional edge between sublocations.

        Syntax: @disconnect <waypoint> <location> <from_subloc> <to_subloc>

        Removes exits from both sublocations and cardinal directions.
        """
        import os
        import json

        if len(args) < 4:
            return {
                "success": False,
                "error": {"code": "missing_arg", "message": "Missing required arguments"},
                "narrative": "❌ Usage: @disconnect <waypoint> <location> <from_subloc> <to_subloc>"
            }

        waypoint_id = args[0]
        location_id = args[1]
        from_subloc = args[2]
        to_subloc = args[3]

        kb_path = getattr(settings, 'KB_PATH', '/kb')
        locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"

        # Load locations
        if not os.path.exists(locations_file):
            return {
                "success": False,
                "error": {"code": "not_found", "message": "locations.json not found"},
                "narrative": "❌ No locations.json found."
            }

        with open(locations_file, 'r') as f:
            locations_data = json.load(f)

        # Validate hierarchy
        if waypoint_id not in locations_data:
            return {
                "success": False,
                "error": {"code": "not_found", "message": f"Waypoint '{waypoint_id}' not found"},
                "narrative": f"❌ Waypoint '{waypoint_id}' does not exist."
            }

        if location_id not in locations_data[waypoint_id]["locations"]:
            return {
                "success": False,
                "error": {"code": "not_found", "message": f"Location '{location_id}' not found"},
                "narrative": f"❌ Location '{location_id}' does not exist in '{waypoint_id}'."
            }

        location_data = locations_data[waypoint_id]["locations"][location_id]

        # Check both sublocations exist
        if from_subloc not in location_data["sublocations"]:
            return {
                "success": False,
                "error": {"code": "not_found", "message": f"Sublocation '{from_subloc}' not found"},
                "narrative": f"❌ Sublocation '{from_subloc}' does not exist."
            }

        if to_subloc not in location_data["sublocations"]:
            return {
                "success": False,
                "error": {"code": "not_found", "message": f"Sublocation '{to_subloc}' not found"},
                "narrative": f"❌ Sublocation '{to_subloc}' does not exist."
            }

        from_data = location_data["sublocations"][from_subloc]
        to_data = location_data["sublocations"][to_subloc]

        # Remove bidirectional exits
        if to_subloc in from_data["exits"]:
            from_data["exits"].remove(to_subloc)

        if from_subloc in to_data["exits"]:
            to_data["exits"].remove(from_subloc)

        # Remove cardinal directions
        cardinal_to_remove = []
        for direction, target in from_data.get("cardinal_exits", {}).items():
            if target == to_subloc:
                cardinal_to_remove.append(direction)

        for direction in cardinal_to_remove:
            del from_data["cardinal_exits"][direction]

        cardinal_to_remove = []
        for direction, target in to_data.get("cardinal_exits", {}).items():
            if target == from_subloc:
                cardinal_to_remove.append(direction)

        for direction in cardinal_to_remove:
            del to_data["cardinal_exits"][direction]

        # Save atomically
        await self._save_locations_atomic(locations_file, locations_data)

        return {
            "success": True,
            "narrative": f"✅ Disconnected {from_subloc} ↮ {to_subloc}",
            "data": {
                "from": from_subloc,
                "to": to_subloc,
                "from_exits": from_data["exits"],
                "to_exits": to_data["exits"]
            },
            "actions": []
        }

    async def _admin_reset(
        self,
        target_type: Optional[str],
        args: List[str],
        experience: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle @reset command - reset instances or player progress.

        Supported:
        - @reset instance <instance_id> CONFIRM
        - @reset player <user_id> CONFIRM
        - @reset experience <experience> CONFIRM
        """
        import os
        import json
        from datetime import datetime

        if target_type == "instance":
            # Reset single instance
            if len(args) < 2:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing arguments"},
                    "narrative": "❌ Usage: @reset instance <instance_id> CONFIRM"
                }

            instance_id = int(args[0])
            confirm = args[1].upper() if len(args) > 1 else ""

            if confirm != "CONFIRM":
                return {
                    "success": False,
                    "error": {"code": "missing_confirm", "message": "CONFIRM required"},
                    "narrative": f"⚠️  Resetting instance #{instance_id} will clear collection state.\n   Add CONFIRM to proceed: @reset instance {instance_id} CONFIRM"
                }

            # Load manifest to find instance
            manifest = await self._load_manifest(experience)
            instance_entry = None
            for inst in manifest.get("instances", []):
                if inst["id"] == instance_id:
                    instance_entry = inst
                    break

            if not instance_entry:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": f"Instance #{instance_id} not found"},
                    "narrative": f"❌ Instance #{instance_id} does not exist."
                }

            # Load instance file
            kb_path = getattr(settings, 'KB_PATH', '/kb')
            instance_file = f"{kb_path}/experiences/{experience}/instances/{instance_entry['instance_file']}"

            if not os.path.exists(instance_file):
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": "Instance file not found"},
                    "narrative": f"❌ Instance file not found: {instance_entry['instance_file']}"
                }

            with open(instance_file, 'r') as f:
                instance_data = json.load(f)

            # Reset state
            old_collected_by = instance_data["state"].get("collected_by")
            instance_data["state"]["collected_by"] = None
            instance_data["metadata"]["last_modified"] = datetime.now().isoformat()
            instance_data["metadata"]["_version"] = instance_data["metadata"].get("_version", 1) + 1

            # Save atomically
            success = await self._save_instance_atomic(instance_file, instance_data)

            if not success:
                return {
                    "success": False,
                    "error": {"code": "save_failed", "message": "Failed to save instance"},
                    "narrative": "❌ Failed to save instance state."
                }

            location_str = f"{instance_entry['location']}/{instance_entry.get('sublocation', 'N/A')}"
            reset_msg = f"✅ Reset instance #{instance_id} ({instance_entry['semantic_name']} at {location_str})"
            if old_collected_by:
                reset_msg += f"\n   - Cleared collected_by (was: {old_collected_by})"
            reset_msg += "\n   - Instance returned to uncollected state"

            return {
                "success": True,
                "narrative": reset_msg,
                "data": {"instance": instance_data},
                "actions": []
            }

        elif target_type == "player":
            # Reset player progress
            if len(args) < 2:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing arguments"},
                    "narrative": "❌ Usage: @reset player <user_id> CONFIRM"
                }

            player_user_id = args[0]
            confirm = args[1].upper() if len(args) > 1 else ""

            if confirm != "CONFIRM":
                return {
                    "success": False,
                    "error": {"code": "missing_confirm", "message": "CONFIRM required"},
                    "narrative": f"⚠️  Resetting player '{player_user_id}' will delete all progress.\n   Add CONFIRM to proceed: @reset player {player_user_id} CONFIRM"
                }

            # Load player state to see what we're deleting
            player_state = await self._load_player_state(player_user_id, experience)
            inventory_count = len(player_state.get("inventory", []))

            # Delete player progress file
            kb_path = getattr(settings, 'KB_PATH', '/kb')
            player_file = f"{kb_path}/players/{player_user_id}/{experience}/progress.json"

            if os.path.exists(player_file):
                os.remove(player_file)

                return {
                    "success": True,
                    "narrative": f"✅ Reset progress for {player_user_id} in {experience}\n   - Cleared inventory ({inventory_count} items removed)\n   - Reset quest progress\n   - Player progress file deleted",
                    "data": {"player_id": player_user_id, "items_removed": inventory_count},
                    "actions": []
                }
            else:
                return {
                    "success": True,
                    "narrative": f"✅ Player {player_user_id} had no progress in {experience} (already reset)",
                    "data": {"player_id": player_user_id},
                    "actions": []
                }

        elif target_type == "experience":
            # Reset entire experience (nuclear option)
            if len(args) < 1:
                return {
                    "success": False,
                    "error": {"code": "missing_arg", "message": "Missing CONFIRM"},
                    "narrative": "❌ Usage: @reset experience CONFIRM"
                }

            confirm = args[0].upper()

            if confirm != "CONFIRM":
                # Count what will be reset
                manifest = await self._load_manifest(experience)
                instance_count = len(manifest.get("instances", []))

                kb_path = getattr(settings, 'KB_PATH', '/kb')
                players_dir = f"{kb_path}/players"
                player_count = 0
                if os.path.exists(players_dir):
                    for user_dir in os.listdir(players_dir):
                        player_progress_file = f"{players_dir}/{user_dir}/{experience}/progress.json"
                        if os.path.exists(player_progress_file):
                            player_count += 1

                return {
                    "success": False,
                    "error": {"code": "missing_confirm", "message": "CONFIRM required"},
                    "narrative": f"⚠️  This will reset:\n   - {instance_count} instances (all set to uncollected)\n   - {player_count} player progress files (all deleted)\n\n   Add CONFIRM to proceed: @reset experience CONFIRM"
                }

            # Reset all instances
            manifest = await self._load_manifest(experience)
            kb_path = getattr(settings, 'KB_PATH', '/kb')
            instances_reset = 0

            for inst in manifest.get("instances", []):
                instance_file = f"{kb_path}/experiences/{experience}/instances/{inst['instance_file']}"

                if os.path.exists(instance_file):
                    with open(instance_file, 'r') as f:
                        instance_data = json.load(f)

                    # Reset state
                    if instance_data["state"].get("collected_by") is not None:
                        instance_data["state"]["collected_by"] = None
                        instance_data["metadata"]["last_modified"] = datetime.now().isoformat()
                        instance_data["metadata"]["_version"] = instance_data["metadata"].get("_version", 1) + 1
                        await self._save_instance_atomic(instance_file, instance_data)
                        instances_reset += 1

            # Delete all player progress files
            players_dir = f"{kb_path}/players"
            players_reset = 0
            if os.path.exists(players_dir):
                for user_dir in os.listdir(players_dir):
                    player_progress_file = f"{players_dir}/{user_dir}/{experience}/progress.json"
                    if os.path.exists(player_progress_file):
                        os.remove(player_progress_file)
                        players_reset += 1

            return {
                "success": True,
                "narrative": f"✅ Experience '{experience}' reset to initial state\n   - {instances_reset} instances reset to uncollected\n   - {players_reset} player progress files deleted",
                "data": {"instances_reset": instances_reset, "players_reset": players_reset},
                "actions": []
            }

        else:
            return {
                "success": False,
                "error": {"code": "invalid_target", "message": f"Unknown target type: {target_type}"},
                "narrative": f"❌ Unknown target '{target_type}'. Available: instance, player, experience"
            }

    async def _admin_stats(self, experience: str) -> Dict[str, Any]:
        """
        Handle @stats command - show world statistics.

        Returns counts of waypoints, locations, sublocations, items, NPCs, players.
        """
        import os
        import json

        kb_path = getattr(settings, 'KB_PATH', '/kb')

        stats = {
            "waypoints": 0,
            "locations": 0,
            "sublocations": 0,
            "item_instances": 0,
            "npc_instances": 0,
            "active_players": 0
        }

        try:
            # Count waypoints/locations/sublocations
            locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"
            if os.path.exists(locations_file):
                with open(locations_file, 'r') as f:
                    locations_data = json.load(f)

                stats["waypoints"] = len(locations_data)

                for waypoint_data in locations_data.values():
                    for location_data in waypoint_data.get("locations", {}).values():
                        stats["locations"] += 1
                        stats["sublocations"] += len(location_data.get("sublocations", {}))

            # Count instances
            manifest = await self._load_manifest(experience)
            stats["item_instances"] = len(manifest.get("instances", []))

            # Count players (rough estimate from session files)
            players_dir = f"{kb_path}/players"
            if os.path.exists(players_dir):
                for user_dir in os.listdir(players_dir):
                    user_exp_dir = os.path.join(players_dir, user_dir, experience)
                    if os.path.exists(user_exp_dir):
                        stats["active_players"] += 1

            lines = [
                f"World Statistics for '{experience}':",
                f"  - Waypoints: {stats['waypoints']}",
                f"  - Locations: {stats['locations']}",
                f"  - Sublocations: {stats['sublocations']}",
                f"  - Item Instances: {stats['item_instances']}",
                f"  - NPC Instances: {stats['npc_instances']}",
                f"  - Active Players: {stats['active_players']}"
            ]

            return {
                "success": True,
                "narrative": "\n".join(lines),
                "data": stats,
                "actions": []
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "success": False,
                "error": {"code": "stats_failed", "message": str(e)},
                "narrative": f"❌ Failed to get stats: {str(e)}"
            }

    # ========== End Admin Command Methods ==========

    # ========== NPC Communication Methods ==========

    async def _talk_to_npc(
        self,
        experience: str,
        npc_semantic_name: str,
        message: str,
        user_id: str,
        waypoint: str,
        sublocation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle NPC conversation with memory-aware dialogue.

        Uses three-layer memory system:
        1. Template (markdown) - personality, knowledge, voice
        2. Instance (JSON) - current world state, quest status
        3. Relationship (JSON) - per-player conversation history

        Args:
            experience: Experience ID
            npc_semantic_name: NPC semantic name (e.g., "louisa")
            message: Player's message
            user_id: Player user ID
            waypoint: Current waypoint
            sublocation: Current sublocation

        Returns:
            Response with narrative, actions, state changes
        """
        try:
            # 1. Find NPC instance at player's location
            manifest = await self._load_manifest(experience)
            npc_instance = None

            for inst in manifest["instances"]:
                if (inst["semantic_name"] == npc_semantic_name and
                    inst["location"] == waypoint):
                    if sublocation is None or inst.get("sublocation") == sublocation:
                        npc_instance = inst
                        break

            if not npc_instance:
                return {
                    "success": False,
                    "error": {"code": "npc_not_found", "message": f"No {npc_semantic_name} here"},
                    "narrative": f"You don't see {npc_semantic_name} nearby."
                }

            # 2. Load three layers of memory
            template_text = await self._load_npc_template_text(experience, npc_instance["template"])
            instance_state = await self._load_npc_instance_state(experience, npc_instance["instance_file"])
            relationship = await self._load_npc_relationship(experience, user_id, npc_instance["template"])

            # 3. Build conversation context for LLM
            context = self._build_npc_context(
                template_text=template_text,
                instance_state=instance_state,
                relationship=relationship,
                message=message
            )

            # 4. Generate response with LLM
            llm_response = await self.llm_service.chat_completion(
                messages=[{"role": "user", "content": context}],
                model="claude-3-5-haiku-20241022",
                user_id=user_id,
                temperature=0.7  # Natural conversation
            )
            response_text = llm_response["response"]

            # 5. Update conversation history
            timestamp = datetime.utcnow().isoformat() + "Z"
            conversation_entry = {
                "timestamp": timestamp,
                "player": message,
                "npc": response_text,
                "mood": instance_state["state"].get("emotional_state", "neutral")
            }

            relationship["conversation_history"].append(conversation_entry)

            # Keep only last 20 conversations
            if len(relationship["conversation_history"]) > 20:
                relationship["conversation_history"] = relationship["conversation_history"][-20:]

            # 6. Update relationship metrics
            relationship["total_conversations"] += 1
            relationship["last_interaction"] = timestamp

            # Simple trust increase for any positive interaction
            if len(message) > 5:  # Not just "hi"
                relationship["trust_level"] = min(100, relationship["trust_level"] + 2)

            # 7. Save updated relationship
            await self._save_npc_relationship_atomic(experience, user_id, npc_instance["template"], relationship)

            return {
                "success": True,
                "narrative": response_text,
                "actions": [{
                    "type": "npc_dialogue",
                    "npc": npc_semantic_name,
                    "mood": instance_state["state"].get("emotional_state", "neutral")
                }],
                "state_changes": {
                    "relationship": {
                        "npc": npc_semantic_name,
                        "trust": relationship["trust_level"],
                        "conversations": relationship["total_conversations"]
                    }
                }
            }

        except Exception as e:
            logger.error(f"NPC conversation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": {"code": "npc_talk_failed", "message": str(e)},
                "narrative": f"Something went wrong while talking to {npc_semantic_name}."
            }

    async def _load_npc_template_text(self, experience: str, template_name: str) -> str:
        """Load NPC template markdown file as text."""
        kb_path = getattr(settings, 'KB_PATH', '/kb')
        template_path = os.path.join(kb_path, "experiences", experience, "templates", "npcs", f"{template_name}.md")

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"NPC template not found: {template_path}")

        with open(template_path, 'r') as f:
            return f.read()

    async def _load_npc_instance_state(self, experience: str, instance_file: str) -> Dict[str, Any]:
        """Load NPC instance state JSON."""
        kb_path = getattr(settings, 'KB_PATH', '/kb')
        instance_path = os.path.join(kb_path, "experiences", experience, "instances", instance_file)

        if not os.path.exists(instance_path):
            raise FileNotFoundError(f"NPC instance not found: {instance_path}")

        with open(instance_path, 'r') as f:
            return json.load(f)

    async def _load_npc_relationship(self, experience: str, user_id: str, npc_template: str) -> Dict[str, Any]:
        """
        Load player-NPC relationship data.

        Creates new relationship file if it doesn't exist.
        Stored in: /kb/experiences/{experience}/players/{user_id}/npcs/{npc_template}.json
        """
        kb_path = getattr(settings, 'KB_PATH', '/kb')
        rel_path = os.path.join(kb_path, "experiences", experience, "players", user_id, "npcs", f"{npc_template}.json")

        if os.path.exists(rel_path):
            with open(rel_path, 'r') as f:
                return json.load(f)
        else:
            # Create new relationship
            timestamp = datetime.utcnow().isoformat() + "Z"
            new_relationship = {
                "npc_template": npc_template,
                "player_id": user_id,
                "first_met": timestamp,
                "last_interaction": timestamp,
                "total_conversations": 0,
                "trust_level": 50,  # Neutral starting trust
                "conversation_history": [],
                "facts_learned": [],
                "promises": [],
                "metadata": {
                    "created_at": timestamp,
                    "last_modified": timestamp,
                    "_version": 1
                }
            }

            # Ensure directory exists
            os.makedirs(os.path.dirname(rel_path), exist_ok=True)

            # Save initial relationship
            with open(rel_path, 'w') as f:
                json.dump(new_relationship, f, indent=2)

            return new_relationship

    async def _save_npc_relationship_atomic(
        self,
        experience: str,
        user_id: str,
        npc_template: str,
        relationship: Dict[str, Any]
    ) -> bool:
        """Save NPC relationship atomically."""
        kb_path = getattr(settings, 'KB_PATH', '/kb')
        rel_path = os.path.join(kb_path, "experiences", experience, "players", user_id, "npcs", f"{npc_template}.json")

        # Update metadata
        relationship["metadata"]["last_modified"] = datetime.utcnow().isoformat() + "Z"
        relationship["metadata"]["_version"] = relationship["metadata"].get("_version", 0) + 1

        # Atomic write
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(rel_path), suffix='.json')
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(relationship, f, indent=2)
            os.replace(temp_path, rel_path)
            return True
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def _build_npc_context(
        self,
        template_text: str,
        instance_state: Dict[str, Any],
        relationship: Dict[str, Any],
        message: str
    ) -> str:
        """Build conversation context for LLM."""

        # Format recent conversation history
        recent_history = ""
        if relationship["conversation_history"]:
            recent_convos = relationship["conversation_history"][-3:]  # Last 3
            recent_history = "\n".join([
                f"  Player: {c['player']}\n  NPC: {c['npc']}"
                for c in recent_convos
            ])

        # Build prompt
        prompt = f"""You are an NPC in a fantasy game. Use this information to respond naturally:

=== NPC TEMPLATE ===
{template_text}

=== CURRENT STATE ===
Emotional State: {instance_state['state'].get('emotional_state', 'neutral')}
Quest Given: {instance_state['state'].get('quest_given', False)}
Bottles Returned: {instance_state['state'].get('bottles_returned', 0)}/4

=== RELATIONSHIP WITH PLAYER ===
Trust Level: {relationship['trust_level']}/100
Total Conversations: {relationship['total_conversations']}
First Met: {relationship['first_met']}

Recent Conversation History:
{recent_history if recent_history else "(This is your first conversation)"}

=== PLAYER SAYS ===
"{message}"

=== INSTRUCTIONS ===
- Respond in character based on your personality and interaction guidelines
- Remember your current situation and emotional state
- Consider your relationship with the player (trust level and history)
- Keep response under 3 sentences unless providing important quest information
- Be natural and authentic, not scripted
- If they ask for help and you haven't given the quest yet, explain the dream bottle situation

Respond as the NPC (only the dialogue, no narration or actions):"""

        return prompt

    # ========== End NPC Communication Methods ==========

    def _select_model_for_experience(self, experience: str) -> str:
        """
        Select appropriate model based on experience type.

        Complex AR experiences like Wylding Woods use more powerful models.
        Simple text adventures can use faster models.
        """
        # Map experiences to model complexity
        complex_experiences = ["wylding-woods", "dragon-quest", "space-odyssey"]

        if experience in complex_experiences:
            return "claude-sonnet-4-5"  # Powerful for complex games
        else:
            return "claude-3-5-haiku-20241022"  # Fast for simpler games


# Global agent instance
