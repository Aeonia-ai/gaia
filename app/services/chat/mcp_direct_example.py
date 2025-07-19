"""
Direct MCP Integration Example - No mcp-agent needed

Shows how to connect to MCP servers and use tools directly
"""
import json
from typing import List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from anthropic import Anthropic

class DirectMCPChat:
    def __init__(self):
        self.anthropic = Anthropic()
        self.mcp_sessions: Dict[str, ClientSession] = {}
    
    async def connect_mcp_server(self, server_name: str, command: List[str]):
        """Connect to an MCP server directly"""
        server_params = StdioServerParameters(
            command=command[0],
            args=command[1:] if len(command) > 1 else []
        )
        
        session = ClientSession(server_params)
        await session.start()
        
        # Get available tools
        tools = await session.list_tools()
        self.mcp_sessions[server_name] = session
        
        return tools
    
    async def chat_with_tools(self, message: str, available_servers: List[str]):
        """Chat with optional MCP tool usage"""
        
        # 1. Connect to requested MCP servers
        all_tools = []
        for server in available_servers:
            if server == "filesystem":
                tools = await self.connect_mcp_server(
                    "filesystem", 
                    ["npx", "@modelcontextprotocol/server-filesystem", "/tmp"]
                )
                all_tools.extend(tools)
            elif server == "github":
                tools = await self.connect_mcp_server(
                    "github",
                    ["npx", "@modelcontextprotocol/server-github"]
                )
                all_tools.extend(tools)
        
        # 2. Convert MCP tools to Anthropic format
        anthropic_tools = []
        for tool in all_tools:
            anthropic_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            })
        
        # 3. Call Anthropic with tools
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": message}],
            tools=anthropic_tools if anthropic_tools else None,
            max_tokens=2000
        )
        
        # 4. Handle tool calls if any
        if response.stop_reason == "tool_use":
            tool_results = []
            
            for tool_use in response.content:
                if tool_use.type == "tool_use":
                    # Find which MCP server has this tool
                    server_name = self._find_tool_server(tool_use.name)
                    if server_name:
                        session = self.mcp_sessions[server_name]
                        
                        # Call the tool via MCP
                        result = await session.call_tool(
                            tool_use.name,
                            tool_use.input
                        )
                        
                        tool_results.append({
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result)
                        })
            
            # Continue conversation with tool results
            messages = [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": tool_results}
            ]
            
            final_response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                messages=messages,
                max_tokens=2000
            )
            
            return final_response.content[0].text
        
        return response.content[0].text
    
    def _find_tool_server(self, tool_name: str) -> str:
        """Find which MCP server provides a tool"""
        # In real implementation, track this during connection
        # For now, simple heuristic
        if tool_name.startswith("fs_"):
            return "filesystem"
        elif tool_name.startswith("github_"):
            return "github"
        return None
    
    async def cleanup(self):
        """Close all MCP connections"""
        for session in self.mcp_sessions.values():
            await session.stop()


# Usage example:
async def main():
    chat = DirectMCPChat()
    
    # Example 1: Chat without tools (fast path)
    response = await chat.chat_with_tools(
        "What is 2+2?",
        available_servers=[]  # No MCP servers
    )
    
    # Example 2: Chat with filesystem access
    response = await chat.chat_with_tools(
        "List the files in /tmp",
        available_servers=["filesystem"]
    )
    
    # Example 3: Multiple tools
    response = await chat.chat_with_tools(
        "Check my GitHub notifications and save a summary to /tmp/notifications.txt",
        available_servers=["github", "filesystem"]
    )
    
    await chat.cleanup()