"""
MCP client integration using the official SDK.

This module provides functionality for managing and communicating with MCP servers
running in Docker containers, using the official MCP SDK for transport and protocol handling.
"""
from typing import Dict, Any, Optional
import logging
import os
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.exceptions.mcp import MCPError, MCPConnectionError

logger = logging.getLogger(__name__)

class MCPClient:
    """
    Client for managing subprocess-based MCP servers.
    
    Handles launching, communicating with, and managing MCP servers running as child processes.
    Features:
    - Process lifecycle management with state tracking
    - Robust error handling with detailed context
    - Comprehensive logging of all operations
    - Health checking and automatic recovery
    """
    
    def __init__(self, command: str, args: Optional[list[str]] = None, env: Optional[Dict[str, str]] = None):
        """
        Initialize MCP client with configuration.
        
        Args:
            command: Command to run the MCP server
            args: Optional list of arguments for the server
            env: Optional environment variables for the server
        """
        self.server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env
        )
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        
    async def connect(self):
        """
        Connect to the MCP server.
        
        Raises:
            MCPConnectionError: If connection fails
        """
        try:
            logger.info("Connecting to MCP server", extra={
                "command": self.server_params.command,
                "args": self.server_params.args
            })
            
            # Set up stdio transport with debug logging
            logger.info("[MCP] Setting up stdio transport")
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(self.server_params)
            )
            stdio, write = stdio_transport
            logger.info("[MCP] Stdio transport established")
            
            # Initialize client session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            await self.session.initialize()
            
            # List available tools
            response = await self.session.list_tools()
            tools = response.tools

            # Enhanced logging of tool details
            logger.info("=== MCP SERVER TOOLS ===")
            for tool in tools:
                logger.info(f"Tool: {tool.name}")
                logger.info(f"  Description: {getattr(tool, 'description', 'N/A')}")
                logger.info(f"  Schema: {getattr(tool, 'schema', 'N/A')}")
                logger.info(f"  Full tool object: {tool}")
            logger.info("=== END TOOLS ===")
            
        except Exception as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {str(e)}")
    
    async def disconnect(self):
        """
        Disconnect from the MCP server and clean up resources.
        """
        await self.exit_stack.aclose()
        self.session = None
        logger.info("Disconnected from MCP server")
    
    async def call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.
        
        Args:
            name: Name of the tool to call
            args: Arguments for the tool
            
        Returns:
            Tool execution result
            
        Raises:
            MCPError: If tool call fails
        """
        if not self.session:
            raise MCPError("Not connected to server")
            
        try:
            # Add enhanced logging before tool call
            logger.info(f"Calling tool: {name}")
            logger.info(f"Tool arguments: {args}")
            
            logger.info(f"[MCP] Calling tool '{name}' with args: {args}")
            result = await self.session.call_tool(name, args)
            logger.info(f"[MCP] Raw tool call result: {result}")
            logger.info(f"[MCP] Result type: {type(result)}")
            logger.info(f"[MCP] Result dir: {dir(result)}")
            if hasattr(result, 'content'):
                logger.info(f"[MCP] Content type: {type(result.content)}")
                logger.info(f"[MCP] Content: {result.content}")
            
            # Add enhanced logging of the result
            logger.info("=== TOOL RESPONSE DEBUG ===")
            logger.info(f"Raw result: {result}")
            logger.info(f"Result type: {type(result)}")
            for attr in ['content', 'text', 'data']:
                if hasattr(result, attr):
                    value = getattr(result, attr)
                    logger.info(f"Result.{attr}: {value}")
                    logger.info(f"Result.{attr} type: {type(value)}")
                    if isinstance(value, (dict, list)):
                        logger.info(f"Result.{attr} structure: {value}")
            logger.info("=== END TOOL RESPONSE DEBUG ===")
            
            return result
        except Exception as e:
            logger.error(f"Tool call failed: {str(e)}")
            raise MCPError(f"Tool call failed: {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
