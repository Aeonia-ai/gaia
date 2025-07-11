"""Filesystem MCP server integration."""
from typing import Dict, Any, List
import os
import logging
import json

from .process_client import MCPClient, MCPError

logger = logging.getLogger(__name__)

class FilesystemMCPError(MCPError):
    """Base exception for filesystem MCP server errors."""
    pass

class FilesystemMCPClient(MCPClient):
    """Client for the filesystem MCP server."""
    
    def __init__(self, allowed_paths: List[str]):
        """Initialize filesystem MCP server."""
        normalized_paths = []
        logger.info("Initializing with allowed paths: %s", allowed_paths)
        for path in allowed_paths:
            abs_path = os.path.abspath(path)
            logger.info("Checking path: %s (absolute: %s)", path, abs_path)
            if not os.path.exists(abs_path):
                logger.warning("Path does not exist, creating: %s", abs_path)
                os.makedirs(abs_path, exist_ok=True)
            normalized_paths.append(abs_path)
            
        command = os.getenv("MCP_FILESYSTEM_COMMAND", "npx")
        args = (["-y", "@modelcontextprotocol/server-filesystem"] if command == "npx" else []) + normalized_paths
        
        logger.debug("Initializing with command: %s %s", command, ' '.join(args))
        super().__init__(command=command, args=args)
        self.allowed_paths = normalized_paths
        
    def _parse_directory_entry(self, text: str) -> Dict[str, Any]:
        """Parse a text entry like '[FILE] test.txt' into a dictionary"""
        logger.debug("Parsing directory entry: '%s'", text)
        try:
            # Split "[TYPE] name" format
            type_str, name = text.strip().split("] ", 1)
            entry_type = type_str[1:].lower()  # Remove [ and convert to lowercase
            
            entry = {
                "name": name,
                "type": "directory" if entry_type == "dir" else "file",
                "size": 0
            }
            logger.debug("Successfully parsed entry: %s", entry)
            return entry
        except Exception as e:
            logger.debug("Failed to parse directory entry '%s': %s", text, e)
            return {
                "name": text,
                "type": "unknown",
                "size": 0
            }
    
    async def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """List contents of a directory."""
        logger.info("Listing directory: %s", path)
        try:
            result = await self.call_tool("list_directory", {"path": path})
            if not hasattr(result, 'content'):
                return []

            entries = []
            if isinstance(result.content, list):
                for item in result.content:
                    if hasattr(item, 'text'):
                        for line in item.text.strip().split('\n'):
                            if line.strip():  # Skip empty lines
                                entries.append(self._parse_directory_entry(line))
            
            logger.info("Final parsed entries: %s", entries)
            return entries
            
        except Exception as e:
            logger.error("Error in list_directory: %s", str(e), exc_info=True)
            raise

    async def read_file(self, path: str) -> str:
        """Read contents of a file."""
        logger.info("Reading file: %s", path)
        result = await self.call_tool("read_file", {"path": path})
        
        if not hasattr(result, 'content'):
            return ""
            
        content = result.content
        if hasattr(content, "text"):
            return content.text
        return str(content) if content else ""
        
    async def write_file(self, path: str, content: str) -> None:
        """Write content to a file."""
        logger.info("Writing to file: %s", path)
        await self.call_tool("write_file", {
            "path": path,
            "content": content
        })
    
    async def delete_file(self, path: str) -> None:
        """Delete a file."""
        logger.info("Deleting file: %s", path)
        await self.call_tool("delete_file", {"path": path})
    
    async def create_directory(self, path: str) -> None:
        """Create a directory."""
        logger.info("Creating directory: %s", path)
        await self.call_tool("create_directory", {"path": path})
    
    async def delete_directory(self, path: str) -> None:
        """Delete a directory."""
        logger.info("Deleting directory: %s", path)
        await self.call_tool("delete_directory", {"path": path})