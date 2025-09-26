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
            model="claude-3-5-sonnet-20241022",  # Use powerful model for workflows
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
            return "claude-3-5-sonnet-20241022"  # Powerful for complex tasks
        else:
            return "claude-3-5-haiku-20241022"  # Default fast model


# Global agent instance
kb_agent = KBIntelligentAgent()