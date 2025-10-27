"""
KB Intelligent Agent - Knowledge Interpretation and Decision Making

Embedded agent that interprets KB content as knowledge and rules for intelligent responses.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from app.services.llm.chat_service import MultiProviderChatService
from app.services.llm.base import ModelCapability, LLMProvider

logger = logging.getLogger(__name__)

class KBIntelligentAgent:
    """
    Embedded agent that interprets KB content as knowledge and rules.

    Key capabilities:
    - Interpret markdown as decision rules
    - Execute knowledge-driven workflows
    - Synthesize information across domains
    - Maintain context across queries
    """

    def __init__(self):
        self.llm_service = None  # Lazy init
        self.kb_storage = None   # Injected from main
        self.rule_cache: Dict[str, Any] = {}
        self.context_cache: Dict[str, List[str]] = {}

    async def initialize(self, kb_storage):
        """Initialize the agent with dependencies"""
        self.kb_storage = kb_storage
        self.llm_service = MultiProviderChatService()
        await self.llm_service.initialize()
        logger.info("KB Intelligent Agent initialized")

    async def interpret_knowledge(
        self,
        query: str,
        context_path: str,
        user_id: str,
        mode: str = "decision",  # decision, synthesis, validation
        model_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Interpret knowledge from KB and generate intelligent response.

        Args:
            query: User query or decision request
            context_path: Path in KB to search for relevant knowledge
            user_id: User identifier for context
            mode: Interpretation mode
            model_hint: Preferred model to use

        Returns:
            Response with interpretation, decision, or synthesis
        """

        # 1. Load relevant knowledge from KB
        knowledge_files = await self._load_context(context_path)

        # 2. Build prompt based on mode
        if mode == "decision":
            prompt = self._build_decision_prompt(query, knowledge_files)
            required_capabilities = [ModelCapability.CHAT]
        elif mode == "synthesis":
            prompt = self._build_synthesis_prompt(query, knowledge_files)
            required_capabilities = [ModelCapability.LONG_CONTEXT]
        elif mode == "validation":
            prompt = self._build_validation_prompt(query, knowledge_files)
            required_capabilities = [ModelCapability.CODE_GENERATION]
        else:
            raise ValueError(f"Unknown mode: {mode}")

        # 3. Select appropriate model based on complexity
        model = model_hint or self._select_model_for_query(query, mode)

        # 4. Get LLM response
        response = await self.llm_service.chat_completion(
            messages=[
                {"role": "system", "content": "You are a knowledge interpreter for the Gaia platform."},
                {"role": "user", "content": prompt}
            ],
            model=model,
            user_id=user_id,
            required_capabilities=required_capabilities,
            temperature=0.3 if mode == "validation" else 0.7
        )

        # 5. Cache successful interpretations
        cache_key = f"{context_path}:{query[:50]}"
        self.rule_cache[cache_key] = {
            "response": response["response"],
            "model": response["model"],
            "timestamp": time.time()
        }

        return {
            "interpretation": response["response"],
            "model_used": response["model"],
            "context_files": len(knowledge_files),
            "mode": mode,
            "cached": False
        }

    async def execute_game_command(
        self,
        command: str,
        experience: str,
        user_context: Dict[str, Any],
        session_state: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a game command by interpreting KB content as game mechanics.

        This is the core game command processor that:
        1. Loads game content from /kb/experiences/{experience}/
        2. Interprets player command against game rules
        3. Returns structured response with narrative, actions, and state changes

        Args:
            command: Player's natural language command
            experience: Experience identifier (e.g., "wylding-woods", "west-of-house")
            user_context: User context (user_id, auth info, etc.)
            session_state: Current player state/inventory

        Returns:
            {
                "success": bool,
                "narrative": str,  # What the player sees/reads
                "actions": List[Dict],  # Structured actions for client to execute
                "state_changes": Dict,  # Updated session state
                "model_used": str
            }
        """
        user_id = user_context.get("user_id", "unknown")

        # 1. Load game content from KB
        experience_path = f"/experiences/{experience}"
        game_content = await self._load_context(experience_path)

        if not game_content:
            return {
                "success": False,
                "error": {
                    "code": "experience_not_found",
                    "message": f"Experience '{experience}' not found in KB"
                }
            }

        # 2. Build game command prompt
        prompt = self._build_game_command_prompt(
            command=command,
            game_content=game_content,
            session_state=session_state or {}
        )

        # 3. Select model based on experience complexity
        model = self._select_model_for_experience(experience)

        # 4. Get LLM response with structured output
        try:
            response = await self.llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a game master interpreting player commands and game content."},
                    {"role": "user", "content": prompt}
                ],
                model=model,
                user_id=user_id,
                temperature=0.7  # Creative for narrative, but consistent
            )

            # 5. Parse LLM response into structured format
            result = self._parse_game_response(response["response"], session_state or {})
            result["model_used"] = response["model"]
            result["content_files"] = len(game_content)

            return result

        except Exception as e:
            logger.error(f"Game command execution failed: {e}")
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
kb_agent = KBIntelligentAgent()