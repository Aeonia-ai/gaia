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
    },
    {
        "type": "function",
        "function": {
            "name": "interact_with_experience",
            "description": "Interact with a game experience using the unified state model. Use for: experience selection ('play west-of-house', 'I want to play wylding-woods'), game actions ('look around', 'take lamp', 'talk to Louisa'), or general gameplay. The system remembers which experience you're in, so you only need to select once. Returns narrative, available actions, and state updates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The user's message (can be experience selection or game action)"
                    },
                    "experience": {
                        "type": "string",
                        "description": "Optional: Explicitly specify which experience to interact with. If omitted, uses player's current experience."
                    },
                    "force_experience_selection": {
                        "type": "boolean",
                        "description": "Optional: Force experience selection prompt even if player has a current experience",
                        "default": False
                    }
                },
                "required": ["message"]
            }
        }
    },
    # ═══════════════════════════════════════════════════════════════════════════
    # ⚠️  MVP KLUDGE WARNING - NPC INTERACTION TOOLS
    # ═══════════════════════════════════════════════════════════════════════════
    #
    # The following tools are a TEMPORARY solution for the Phase 1 demo.
    #
    # CURRENT ARCHITECTURE (MVP KLUDGE):
    #   Unity → WebSocket → KB Service (receives "talk" action)
    #                       ↓
    #                       Chat Service (Louisa persona with these tools)
    #                       ↓
    #                       KB Service tools (check quest, accept bottle, etc.)
    #                       ↓
    #   Unity ← WebSocket ← KB Service (wraps chat response)
    #
    # WHY THIS IS A KLUDGE:
    #   1. Double-hop through services (KB → Chat → KB)
    #   2. Chat service needs game mechanic knowledge (quest IDs, bottle IDs)
    #   3. Tightly couples persona definitions to game state structure
    #   4. Inefficient HTTP calls for simple state checks
    #
    # PROPER FUTURE ARCHITECTURE:
    #   - Move LLM dialogue generation INTO KB service directly
    #   - NPC templates in KB markdown with personality/situation
    #   - KB service generates dialogue using MultiProviderChatService
    #   - Trust system, conversation history managed in KB state
    #   - See: docs/scratchpad/npc-llm-dialogue-system.md for full design
    #
    # TIMELINE: Refactor after Phase 1 demo (estimated 1-2 days)
    #
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "type": "function",
        "function": {
            "name": "check_quest_state",
            "description": "Check the player's current quest state and progress. Use when Louisa needs to know if player has accepted quest, how many bottles collected, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quest_id": {
                        "type": "string",
                        "description": "Quest ID to check (e.g., 'find_dream_bottles')"
                    },
                    "experience": {
                        "type": "string",
                        "description": "Experience ID (e.g., 'wylding-woods')",
                        "default": "wylding-woods"
                    }
                },
                "required": ["quest_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "accept_bottle_from_player",
            "description": "Accept a dream bottle from the player when they give it to Louisa. Removes bottle from player inventory, updates quest progress.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bottle_id": {
                        "type": "string",
                        "description": "Bottle instance ID (e.g., 'bottle_mystery', 'bottle_joy', 'bottle_energy', 'bottle_nature')"
                    },
                    "experience": {
                        "type": "string",
                        "description": "Experience ID",
                        "default": "wylding-woods"
                    }
                },
                "required": ["bottle_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grant_quest_reward",
            "description": "Grant a reward to the player for completing a quest or milestone. Use when player completes Louisa's quest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reward_type": {
                        "type": "string",
                        "enum": ["item", "trust", "quest_complete"],
                        "description": "Type of reward to grant"
                    },
                    "reward_data": {
                        "type": "object",
                        "description": "Reward-specific data (item_id for items, trust_amount for trust, etc.)"
                    },
                    "experience": {
                        "type": "string",
                        "description": "Experience ID",
                        "default": "wylding-woods"
                    }
                },
                "required": ["reward_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_inventory",
            "description": "Get the player's current inventory to see what bottles they're carrying. Use before accepting bottles to verify player has them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "experience": {
                        "type": "string",
                        "description": "Experience ID",
                        "default": "wylding-woods"
                    }
                },
                "required": []
            }
        }
    }
]


# ═══════════════════════════════════════════════════════════════════════════
# Organized Tool Lists by Persona Type
# ═══════════════════════════════════════════════════════════════════════════
#
# These organized lists allow different personas to have different tool access.
# This prevents confusion like Louisa trying to read your filesystem, or
# a general assistant trying to accept quest items.
#
# ═══════════════════════════════════════════════════════════════════════════

# NPC-specific tools (for Louisa and other NPCs)
NPC_TOOLS = [
    KB_TOOLS[7],  # check_quest_state
    KB_TOOLS[8],  # accept_bottle_from_player
    KB_TOOLS[9],  # grant_quest_reward
    KB_TOOLS[10], # get_player_inventory
]

# Experience/Game tools (for Game Master)
EXPERIENCE_TOOLS = [
    KB_TOOLS[6],  # interact_with_experience
]

# KB search/read tools (for Game Master to look up lore)
KB_SEARCH_TOOLS = [
    KB_TOOLS[0],  # search_knowledge_base
    KB_TOOLS[2],  # read_kb_file
]

# General KB tools (for default personas like Mu)
GENERAL_KB_TOOLS = [
    KB_TOOLS[0],  # search_knowledge_base
    KB_TOOLS[1],  # load_kos_context
    KB_TOOLS[2],  # read_kb_file
    KB_TOOLS[3],  # list_kb_directory
    KB_TOOLS[4],  # load_kb_context
    KB_TOOLS[5],  # synthesize_kb_information
]


class KBToolExecutor:
    """Executes KB tool calls by making HTTP requests to the KB service."""

    def __init__(self, auth_principal: Dict[str, Any]):
        self.auth_principal = auth_principal

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

        elif tool_name == "execute_game_command":
            return await self._execute_game_command(
                arguments.get("command"),
                arguments.get("experience"),
                arguments.get("session_state")
            )

        elif tool_name == "interact_with_experience":
            return await self._interact_with_experience(
                arguments.get("message"),
                arguments.get("experience"),
                arguments.get("force_experience_selection", False)
            )

        # ═══════════════════════════════════════════════════════════════════════════
        # ⚠️  MVP KLUDGE - NPC Interaction Tool Executors
        # ═══════════════════════════════════════════════════════════════════════════
        elif tool_name == "check_quest_state":
            return await self._check_quest_state(
                arguments.get("quest_id"),
                arguments.get("experience", "wylding-woods")
            )

        elif tool_name == "accept_bottle_from_player":
            return await self._accept_bottle_from_player(
                arguments.get("bottle_id"),
                arguments.get("experience", "wylding-woods")
            )

        elif tool_name == "grant_quest_reward":
            return await self._grant_quest_reward(
                arguments.get("reward_type"),
                arguments.get("reward_data", {}),
                arguments.get("experience", "wylding-woods")
            )

        elif tool_name == "get_player_inventory":
            return await self._get_player_inventory(
                arguments.get("experience", "wylding-woods")
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

    async def _execute_game_command(
        self,
        command: str,
        experience: str,
        session_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a game command through the KB service."""
        try:
            # Prepare request payload
            payload = {
                "command": command,
                "experience": experience,
                "user_context": {
                    "user_id": self.auth_principal.get("user_id", "unknown"),
                    "role": self.auth_principal.get("role", "player"),
                    "auth_type": self.auth_principal.get("auth_type", "api_key")
                }
            }

            if session_state:
                payload["session_state"] = session_state

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/game/command",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    # Game command endpoint returns structured GameCommandResponse
                    return result
                elif response.status_code == 403:
                    return {
                        "success": False,
                        "error": {
                            "code": "insufficient_permissions",
                            "message": "You don't have permission to execute this command"
                        }
                    }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "error": {
                            "code": "experience_not_found",
                            "message": f"Experience '{experience}' not found"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": {
                            "code": "http_error",
                            "message": f"HTTP {response.status_code}"
                        }
                    }

        except Exception as e:
            logger.error(f"Game command execution error: {e}")
            return {
                "success": False,
                "error": {
                    "code": "execution_error",
                    "message": str(e)
                }
            }

    async def _interact_with_experience(
        self,
        message: str,
        experience: Optional[str] = None,
        force_experience_selection: bool = False
    ) -> Dict[str, Any]:
        """
        Interact with a game experience using the unified state model.

        This is the NEW approach using the /experience/interact endpoint.
        Features:
        - Persistent experience selection (no need to specify each time)
        - Automatic player bootstrapping
        - Unified state management (shared or isolated based on config)
        - Markdown-driven game logic (when implemented)

        Args:
            message: User's message (can be experience selection or game action)
            experience: Optional explicit experience ID
            force_experience_selection: Force selection prompt

        Returns:
            Interaction response with narrative, actions, and metadata
        """
        try:
            # Prepare request payload
            payload = {
                "message": message,
                "force_experience_selection": force_experience_selection
            }

            if experience:
                payload["experience"] = experience

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/experience/interact",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    # Experience endpoint returns InteractResponse model
                    return result
                elif response.status_code == 401:
                    return {
                        "success": False,
                        "error": {
                            "code": "unauthorized",
                            "message": "Authentication required"
                        }
                    }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "error": {
                            "code": "experience_not_found",
                            "message": "Experience not found"
                        }
                    }
                elif response.status_code == 500:
                    error_detail = response.json().get("detail", "Internal server error")
                    return {
                        "success": False,
                        "error": {
                            "code": "server_error",
                            "message": error_detail
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": {
                            "code": "http_error",
                            "message": f"HTTP {response.status_code}"
                        }
                    }

        except httpx.TimeoutException:
            logger.error("Experience interaction timeout")
            return {
                "success": False,
                "error": {
                    "code": "timeout",
                    "message": "Request timed out"
                }
            }
        except Exception as e:
            logger.error(f"Experience interaction error: {e}")
            return {
                "success": False,
                "error": {
                    "code": "execution_error",
                    "message": str(e)
                }
            }

    # ═══════════════════════════════════════════════════════════════════════════
    # ⚠️  MVP KLUDGE - NPC Interaction Tool Implementations
    # ═══════════════════════════════════════════════════════════════════════════
    #
    # These methods make HTTP calls to KB service endpoints that DON'T EXIST YET.
    # They will need to be implemented in KB service as part of the demo work.
    #
    # Required KB endpoints:
    #   POST /experience/{exp}/quest/state
    #   POST /experience/{exp}/npc/accept_item
    #   POST /experience/{exp}/quest/reward
    #   GET  /experience/{exp}/player/inventory
    #
    # ═══════════════════════════════════════════════════════════════════════════

    async def _check_quest_state(self, quest_id: str, experience: str) -> Dict[str, Any]:
        """
        Check player's quest state.

        MVP KLUDGE: Makes HTTP call to KB service.
        Future: KB service would handle this internally when generating NPC dialogue.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/experience/{experience}/quest/state",
                    json={
                        "quest_id": quest_id,
                        "user_id": self.auth_principal.get("user_id")
                    },
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            logger.error(f"Check quest state error: {e}")
            return {"success": False, "error": str(e)}

    async def _accept_bottle_from_player(self, bottle_id: str, experience: str) -> Dict[str, Any]:
        """
        Accept a bottle from the player's inventory.

        MVP KLUDGE: Makes HTTP call to KB service.
        Future: KB service would handle this as part of "give_item" fast command.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/experience/{experience}/npc/accept_item",
                    json={
                        "item_id": bottle_id,
                        "npc_id": "louisa",  # Hardcoded for MVP
                        "user_id": self.auth_principal.get("user_id")
                    },
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            logger.error(f"Accept bottle error: {e}")
            return {"success": False, "error": str(e)}

    async def _grant_quest_reward(
        self,
        reward_type: str,
        reward_data: Dict[str, Any],
        experience: str
    ) -> Dict[str, Any]:
        """
        Grant a quest reward to the player.

        MVP KLUDGE: Makes HTTP call to KB service.
        Future: KB service would handle rewards as part of quest completion logic.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{KB_SERVICE_URL}/experience/{experience}/quest/reward",
                    json={
                        "reward_type": reward_type,
                        "reward_data": reward_data,
                        "user_id": self.auth_principal.get("user_id")
                    },
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            logger.error(f"Grant reward error: {e}")
            return {"success": False, "error": str(e)}

    async def _get_player_inventory(self, experience: str) -> Dict[str, Any]:
        """
        Get player's current inventory.

        MVP KLUDGE: Makes HTTP call to KB service.
        Future: KB service would include inventory in NPC dialogue context automatically.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{KB_SERVICE_URL}/experience/{experience}/player/inventory",
                    headers=self.headers,
                    params={"user_id": self.auth_principal.get("user_id")},
                    timeout=10.0
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            logger.error(f"Get inventory error: {e}")
            return {"success": False, "error": str(e)}