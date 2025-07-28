"""
KB Tools for LLM Integration

Provides direct KB service tools that can be used by the LLM during chat.
These tools make HTTP calls to the KB service endpoints.
"""

import httpx
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
            "description": "Search the user's knowledge base when they ask about their personal knowledge, past work, notes, or specific information they've stored. Use when queries include: 'what do I know about', 'find my notes on', 'show my work on', 'search my KB for'.",
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
    }
]


class KBToolExecutor:
    """Executes KB tool calls by making HTTP requests to the KB service."""
    
    def __init__(self, auth_principal: Dict[str, Any]):
        self.auth_principal = auth_principal
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": auth_principal.get("key", "")
        }
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a KB tool and return the result."""
        
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