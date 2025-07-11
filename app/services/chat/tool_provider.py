from typing import List, Dict, Any, Optional
import logging
from app.models.chat import Tool, FunctionDefinition
from app.core.mcp_config import get_mcp_settings
from app.services.mcp.process_client import MCPClient

logger = logging.getLogger(__name__)

class ToolProvider:
    """Manages tool definitions and instructions for different activities"""
    
    # Knowledge Base Operations
    KB_DELETE = {
        "name": "delete_file",
        "description": "Delete a note from the knowledge base using the note's hierarchical name",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Note name using dot notation hierarchy (e.g., 'project.component.feature.md')"
                }
            },
            "required": ["path"]
        }
    }

    KB_READ = {
        "name": "read_file",
        "description": "Read content from the knowledge base using the note's hierarchical name",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Note name using dot notation hierarchy (e.g., 'project.component.feature.md')"
                }
            },
            "required": ["path"]
        }
    }

    KB_WRITE = {
        "name": "write_file",
        "description": "Update or create a note in the knowledge base using hierarchical naming",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Note name using dot notation hierarchy (e.g., 'project.component.feature.md')"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write, including frontmatter with metadata"
                }
            },
            "required": ["path", "content"]
        }
    }

    KB_LIST = {
        "name": "list_directory",
        "description": "List notes in the knowledge base, optionally filtered by hierarchy prefix",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Optional hierarchy prefix to filter notes (e.g., 'project.component' will match all notes under that hierarchy)"
                }
            },
            "required": ["path"]
        }
    }

    # Session Management
    SESSION_HISTORY = {
        "name": "get_chat_history",
        "description": "Get the chat history for the current session",
        "parameters": {
            "type": "object",
            "properties": {
                "auth_key": {
                    "type": "string", 
                    "description": "Authentication key for the current session"
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of messages to return (optional)",
                    "minimum": 1
                }
            },
            "required": ["auth_key"]
        }
    }

    # Activity to Tools mapping with semantic grouping
    ACTIVITY_TOOLS = {
        "knowledge_base": [KB_READ, KB_WRITE, KB_LIST, KB_DELETE],
        "chat": [SESSION_HISTORY],
        "development": []  # Reserved for future development tools
    }

    # Cache of MCP clients
    _mcp_clients: Dict[str, MCPClient] = {}

    @classmethod
    async def _get_mcp_client(cls, server_name: str) -> Optional[MCPClient]:
        """Get or create an MCP client for a server"""
        if server_name not in cls._mcp_clients:
            settings = get_mcp_settings()
            if server_name not in settings.MCP_SERVERS:
                logger.error(f"MCP server {server_name} not configured")
                return None
                
            config = settings.MCP_SERVERS[server_name]
            client = MCPClient(
                command=config.command,
                args=config.args,
                env=config.env or {}
            )
            try:
                await client.connect()
                cls._mcp_clients[server_name] = client
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_name}: {e}")
                return None
                
        return cls._mcp_clients[server_name]

    @classmethod
    async def _get_mcp_tools(cls) -> List[Tool]:
        """Get tools from configured MCP servers"""
        logger.debug("Getting MCP tools from configured servers")
        tools = []
        settings = get_mcp_settings()
        
        # Get tools from other MCP servers
        for server_name in settings.MCP_SERVERS:
            try:
                logger.debug(f"Connecting to MCP server: {server_name}")
                client = await cls._get_mcp_client(server_name)
                if client:
                    # Get tools from server
                    logger.debug(f"Requesting tools from server: {server_name}")
                    response = await client.session.list_tools()
                    logger.debug(f"Received {len(response.tools)} tools from server {server_name}")
                    for tool in response.tools:
                        tool_name = f"mcp_{server_name}_{tool.name}"
                        logger.debug(f"Adding MCP tool: {tool_name}")
                        # Ensure tool parameters have proper schema structure
                        parameters = tool.parameters if hasattr(tool, 'parameters') else {}
                        if isinstance(parameters, dict) and "type" not in parameters:
                            parameters = {
                                "type": "object",
                                "properties": parameters,
                                "required": []
                            }
                        tools.append(Tool(
                            type="function",
                            function=FunctionDefinition(
                                name=tool_name,
                                description=tool.description if hasattr(tool, 'description') else "",
                                parameters=parameters
                            )
                        ))
            except Exception as e:
                logger.error(f"Failed to get tools from MCP server {server_name}: {e}")
                
        return tools

    @staticmethod
    def _format_tool_section(tools: List[Dict[str, Any]]) -> str:
        """Format tools with semantic grouping and hierarchy"""
        sections = []
        
        # Group tools by semantic purpose
        tool_groups = {
            "Knowledge Base Operations": {
                "description": "Core tools for accessing and maintaining the knowledge base",
                "tools": [t for t in tools if t['name'] in ['read_file', 'write_file', 'list_directory', 'delete_file']]
            },
            "Session Management": {
                "description": "Tools for managing conversation context",
                "tools": [t for t in tools if t['name'] in ['get_chat_history']]
            }
        }

        sections.append("## Available Tool Categories\n")
        
        # Format each group
        for group_name, group_info in tool_groups.items():
            if not group_info['tools']:
                continue
                
            sections.append(f"\n### {group_name}")
            sections.append(group_info['description'])
            
            # Format tools in group
            for tool in group_info['tools']:
                sections.append(f"\n#### {tool['name']}")
                sections.append(f"{tool['description']}")
                
                # Parameters section
                if params := tool.get('parameters', {}).get('properties', {}):
                    sections.append("\nParameters:")
                    for param_name, param_info in params.items():
                        required = param_name in tool.get('parameters', {}).get('required', [])
                        sections.append(f"- {param_name}{'*' if required else ''}: {param_info.get('description', '')}")
        
        return "\n".join(sections)

    @classmethod
    async def get_tools_for_activity(cls, activity: str) -> List[Tool]:
        """Get tools appropriate for the activity type"""
        tools = []
        
        # Always include knowledge base tools as base capability
        tools.extend([Tool(
            type="function",
            function=FunctionDefinition(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"]
            )
        ) for tool in cls.ACTIVITY_TOOLS.get("knowledge_base", [])])

        # Add activity-specific tools
        if activity in cls.ACTIVITY_TOOLS:
            tools.extend([Tool(
                type="function",
                function=FunctionDefinition(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=tool["parameters"]
                )
            ) for tool in cls.ACTIVITY_TOOLS[activity]])

        # Get MCP tools (with semantic naming)
        try:
            logger.debug("Attempting to get MCP tools")
            mcp_tools = await cls._get_mcp_tools()
            if mcp_tools:
                logger.debug(f"Found {len(mcp_tools)} MCP tools")
                tools.extend(mcp_tools)
            else:
                logger.debug("No MCP tools found")
        except Exception as e:
            logger.error(f"Failed to add MCP tools for activity {activity}: {e}")

        logger.debug(f"Total tools prepared: {len(tools)}")
        for tool in tools:
            logger.debug(f"Tool ready: {tool.function.name}")
        
        return tools

    @classmethod
    def get_all_activities(cls) -> List[str]:
        """Get a list of all available activities"""
        activities = list(cls.ACTIVITY_TOOLS.keys())
        logger.debug(f"Available activities: {activities}")
        return activities

    @classmethod
    async def initialize_tools(cls) -> None:
        """Initialize tool system by connecting to MCP servers and loading tools"""
        logger.debug("Initializing tool system")
        try:
            # Initialize MCP tools
            await cls._get_mcp_tools()
            logger.debug("Tool system initialization completed")
        except Exception as e:
            logger.error(f"Failed to initialize tool system: {e}")
            raise
