"""
KB Tools for LLM Integration

Provides direct KB service tools that can be used by the LLM during chat.
These tools make HTTP calls to the KB service endpoints.
"""

import httpx
import json
import logging
from typing import Dict, Any, List, Optional
from app.shared.config import settings

logger = logging.getLogger(__name__)

# KB service URL
KB_SERVICE_URL = settings.KB_SERVICE_URL or "http://kb-service:8000"


# Tool definitions for LLM
KB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "FIRST CHOICE for KB queries: Real-time search of user's personal knowledge base for their stored information, notes, documents, and past work. Finds all content including recently added files. Use when user asks: 'what do I know about', 'find my notes on', 'search my knowledge', 'what's in my KB', 'analyze my knowledge base content', or references their personal knowledge/information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find in the knowledge base"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "load_kos_context",
            "description": "Load KOS context when user wants to: continue previous work ('continue where we left off', 'what was I working on'), manage threads ('show active threads', 'load thread'), or switch contexts ('load consciousness context', 'transition to technical work').",
            "parameters": {
                "type": "object",
                "properties": {
                    "context_type": {
                        "type": "string",
                        "enum": ["current-session", "active-threads", "daily-plan", "chat-instructions", "project-context"],
                        "description": "Type of KOS context to load"
                    },
                    "project": {
                        "type": "string",
                        "description": "Optional project name for project-specific context"
                    }
                },
                "required": ["context_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_kb_file",
            "description": "Read the contents of a specific file from the knowledge base. Use this after searching to get the full content of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file in the knowledge base"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_kb_directory",
            "description": "List files and directories in a specific path of the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to list (use '/' for root)",
                        "default": "/"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "load_kb_context",
            "description": "Load context around a specific topic or file in the knowledge base. This provides related information and connections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic or file path to load context for"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "How many levels of related content to include",
                        "default": 2
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "synthesize_kb_information",
            "description": "Use when user asks to connect or synthesize across domains: 'how does X relate to Y', 'connect A with B', 'find patterns across', 'synthesize insights from'. Matches Jason's cross-pollination workflow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths or topics to synthesize"
                    },
                    "focus": {
                        "type": "string",
                        "description": "What aspect to focus the synthesis on"
                    }
                },
                "required": ["sources"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "interpret_knowledge",
            "description": "PRIORITY TOOL: Use when user explicitly mentions 'KB Agent', 'analyze my knowledge base', 'intelligent decisions', 'understand my knowledge', 'interpret my content', or asks for analysis/guidance based on their personal knowledge base. This tool uses advanced AI to interpret and analyze knowledge base content intelligently.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question, decision request, or topic to analyze"
                    },
                    "context_path": {
                        "type": "string",
                        "description": "KB path to focus the analysis on (default: all KB content)",
                        "default": "/"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["decision", "synthesis", "validation"],
                        "description": "Type of interpretation: decision (make choices), synthesis (combine info), validation (check against rules)",
                        "default": "decision"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_knowledge_workflow",
            "description": "Execute a workflow or procedure defined in the knowledge base. Use when user wants to run a specific process, follow documented procedures, or execute step-by-step workflows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_path": {
                        "type": "string",
                        "description": "Path to the workflow markdown file in the KB"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameters to pass to the workflow execution",
                        "default": {}
                    }
                },
                "required": ["workflow_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_against_rules",
            "description": "Validate an action, decision, or proposal against rules and guidelines defined in the knowledge base. Use when user wants to check compliance, verify if something is allowed, or ensure adherence to established policies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action, decision, or proposal to validate"
                    },
                    "rules_path": {
                        "type": "string",
                        "description": "Path to the rules/guidelines in the KB to validate against"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context information for the validation",
                        "default": {}
                    }
                },
                "required": ["action", "rules_path"]
            }
        }
    }
]


class KBToolExecutor:
    """Executes KB tool calls by making HTTP requests to the KB service."""

    def __init__(self, auth_principal: Dict[str, Any], progressive_mode: bool = False, conversation_id: Optional[str] = None):
        self.auth_principal = auth_principal
        self.progressive_mode = progressive_mode
        self.conversation_id = conversation_id

        # For inter-service communication, we need to use the system API key
        # When auth_type is 'jwt', the auth_principal won't have a 'key' field
        api_key = auth_principal.get("key", "")

        # If no API key in auth_principal (JWT auth), use system API key from settings
        if not api_key and auth_principal.get("auth_type") == "jwt":
            api_key = settings.API_KEY  # Use the system's API_KEY for inter-service calls
            logger.info(f"Using system API_KEY for KB service call (JWT auth detected)")

        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Execute a KB tool and return the result or yield progressive events."""

        # Debug: Always log what we receive
        logger.warning(f"[EXECUTE_TOOL] Called with tool_name='{tool_name}', progressive_mode={getattr(self, 'progressive_mode', False)}")
        logger.warning(f"[EXECUTE_TOOL] Arguments received: {arguments}")

        # Handle special progressive case for interpret_knowledge
        if tool_name == "interpret_knowledge" and hasattr(self, 'progressive_mode') and self.progressive_mode:
            # Import progressive response system
            from app.services.kb_progressive_integration import progressive_interpret_knowledge

            # Debug: Log the arguments being passed
            query = arguments.get("query")
            logger.warning(f"[DEBUG] interpret_knowledge called with arguments: {arguments}")
            logger.warning(f"[DEBUG] extracted query: '{query}'")

            # If query is None or empty, use a fallback
            if not query:
                logger.warning(f"[DEBUG] No query provided, using fallback")
                query = "general knowledge base analysis"

            # Yield progressive events
            async for event in progressive_interpret_knowledge(
                query=query,
                context_path=arguments.get("context_path", "/"),
                operation_mode=arguments.get("mode", "decision"),
                conversation_id=getattr(self, 'conversation_id', None),
                auth_header=self.headers.get("X-API-Key")
            ):
                yield event
            return  # End generator without value

        # For all other cases, delegate to synchronous execution
        result = await self._execute_tool_sync(tool_name, arguments)
        yield result

    async def _execute_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a KB tool synchronously and return the result."""

        if tool_name == "search_knowledge_base":
            return await self._search_kb(arguments.get("query"), arguments.get("limit", 10))

        elif tool_name == "load_kos_context":
            return await self._load_kos_context(arguments.get("context_type"), arguments.get("project"))

        elif tool_name == "read_kb_file":
            return await self._read_file(arguments.get("path"))

        elif tool_name == "list_kb_directory":
            return await self._list_directory(arguments.get("path", "/"))

        elif tool_name == "load_kb_context":
            return await self._load_context(arguments.get("topic"), arguments.get("depth", 2))

        elif tool_name == "synthesize_kb_information":
            return await self._synthesize(arguments.get("sources"), arguments.get("focus"))

        elif tool_name == "interpret_knowledge":
            # Fallback to synchronous delivery
            return await self._interpret_knowledge(
                arguments.get("query"),
                arguments.get("context_path", "/"),
                arguments.get("mode", "decision")
            )

        elif tool_name == "execute_knowledge_workflow":
            return await self._execute_workflow(
                arguments.get("workflow_path"),
                arguments.get("parameters", {})
            )

        elif tool_name == "validate_against_rules":
            return await self._validate_rules(
                arguments.get("action"),
                arguments.get("rules_path"),
                arguments.get("context", {})
            )

        else:
            return {"error": f"Unknown KB tool: {tool_name}"}
    
    async def _search_kb(self, query: str, limit: int) -> Dict[str, Any]:
        """Search the knowledge base."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/search",
                    json={"message": query},
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # KB service returns {status, response, metadata} format
                    logger.info(f"KB search response for '{query}': status={result.get('status')}, has_response={bool(result.get('response'))}, metadata={result.get('metadata')}")
                    if result.get("status") == "success":
                        content = result.get("response", "No results found")
                        return {"success": True, "content": content}
                    else:
                        return {"success": False, "error": result.get("response", "Unknown error")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"KB search error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _read_file(self, path: str) -> Dict[str, Any]:
        """Read a file from the knowledge base."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/read",
                    json={"message": path},
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        content = result.get("response", "File not found")
                        return {"success": True, "content": content}
                    else:
                        return {"success": False, "error": result.get("response", "Unknown error")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"KB read error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _list_directory(self, path: str) -> Dict[str, Any]:
        """List directory contents in the knowledge base."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/list",
                    json={"message": path},
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        content = result.get("response", "Directory not found")
                        return {"success": True, "content": content}
                    else:
                        return {"success": False, "error": result.get("response", "Unknown error")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"KB list error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _load_context(self, topic: str, depth: int) -> Dict[str, Any]:
        """Load context around a topic."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/context",
                    json={"message": f"{topic} (depth: {depth})"},
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        content = result.get("response", "Context not found")
                        return {"success": True, "content": content}
                    else:
                        return {"success": False, "error": result.get("response", "Unknown error")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"KB context error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _synthesize(self, sources: List[str], focus: Optional[str]) -> Dict[str, Any]:
        """Synthesize information from multiple sources."""
        try:
            message = f"Synthesize from: {', '.join(sources)}"
            if focus:
                message += f" focusing on: {focus}"
                
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/synthesize",
                    json={"message": message},
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        content = result.get("response", "Synthesis failed")
                        return {"success": True, "content": content}
                    else:
                        return {"success": False, "error": result.get("response", "Unknown error")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"KB synthesize error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _load_kos_context(self, context_type: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Load specific KOS context files like current-session, active-threads, etc."""
        try:
            # Map context types to KB search patterns
            context_search_map = {
                "current-session": "current-session OR session-state OR active-context",
                "active-threads": "active-threads OR threads OR project-status", 
                "daily-plan": "daily-plan OR today OR priorities OR schedule",
                "chat-instructions": "chat-instructions OR chat-context OR preferences",
                "project-context": f"project-context OR {project}" if project else "project-context"
            }
            
            search_query = context_search_map.get(context_type, context_type)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/search",
                    json={"message": f"KOS context: {search_query}"},
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        content = result.get("response", "Context not found")
                        return {"success": True, "content": content, "context_type": context_type}
                    else:
                        return {"success": False, "error": result.get("response", "Unknown error")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"KOS context load error: {e}")
            return {"success": False, "error": str(e)}

    async def _interpret_knowledge(self, query: str, context_path: str, mode: str) -> Dict[str, Any]:
        """Use KB Agent to interpret knowledge and make intelligent decisions."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/agent/interpret",
                    json={
                        "query": query,
                        "context_path": context_path,
                        "mode": mode
                    },
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        agent_result = result.get("result", {})
                        interpretation = agent_result.get("interpretation", "No interpretation available")
                        model_used = agent_result.get("model_used", "unknown")
                        context_files = agent_result.get("context_files", 0)

                        return {
                            "success": True,
                            "content": f"KB Agent Analysis ({mode} mode, {context_files} files, {model_used}):\n\n{interpretation}",
                            "mode": mode,
                            "model_used": model_used,
                            "context_files": context_files
                        }
                    else:
                        return {"success": False, "error": result.get("detail", "Unknown error")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}

        except Exception as e:
            logger.error(f"KB Agent interpret error: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_workflow(self, workflow_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow defined in the knowledge base using KB Agent."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/agent/workflow",
                    json={
                        "workflow_path": workflow_path,
                        "parameters": parameters
                    },
                    headers=self.headers,
                    timeout=60.0  # Workflows might take longer
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        agent_result = result.get("result", {})
                        execution_result = agent_result.get("execution_result", "No result available")
                        model_used = agent_result.get("model_used", "unknown")

                        return {
                            "success": True,
                            "content": f"Workflow Execution Result ({model_used}):\n\n{execution_result}",
                            "workflow_path": workflow_path,
                            "parameters": parameters,
                            "model_used": model_used
                        }
                    else:
                        return {"success": False, "error": result.get("detail", "Unknown error")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}

        except Exception as e:
            logger.error(f"KB Agent workflow error: {e}")
            return {"success": False, "error": str(e)}

    async def _validate_rules(self, action: str, rules_path: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate an action against rules using KB Agent."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/agent/validate",
                    json={
                        "action": action,
                        "rules_path": rules_path,
                        "context": context
                    },
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        agent_result = result.get("result", {})
                        validation_result = agent_result.get("validation_result", "No validation result")
                        rules_checked = agent_result.get("rules_checked", 0)
                        model_used = agent_result.get("model_used", "unknown")

                        return {
                            "success": True,
                            "content": f"Rule Validation ({rules_checked} rules checked, {model_used}):\n\n{validation_result}",
                            "action": action,
                            "rules_path": rules_path,
                            "validation_result": validation_result,
                            "model_used": model_used
                        }
                    else:
                        return {"success": False, "error": result.get("detail", "Unknown error")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}

        except Exception as e:
            logger.error(f"KB Agent validation error: {e}")
            return {"success": False, "error": str(e)}