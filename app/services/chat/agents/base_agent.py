"""
Base Agent Architecture for Gaia

Provides flexible agent patterns that can work with or without MCP servers.
Supports both lightweight agents and MCP-enabled agents.
"""
from typing import Optional, List, Dict, Any, Protocol
from abc import ABC, abstractmethod
import logging

from mcp_agent.agents.agent import Agent as MCPAgent
from mcp_agent.workflows.llm.augmented_llm import AugmentedLLM

logger = logging.getLogger(__name__)


class ToolProtocol(Protocol):
    """Protocol for tools that agents can use"""
    
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters"""
        ...


class BaseAgent(ABC):
    """
    Base agent class that can work with or without MCP.
    
    This provides a common interface for:
    - Lightweight agents (no MCP overhead)
    - MCP-enabled agents (access to MCP servers)
    - Hybrid agents (mix of local tools and MCP servers)
    """
    
    def __init__(
        self,
        name: str,
        instruction: str,
        tools: Optional[List[ToolProtocol]] = None,
        mcp_servers: Optional[List[str]] = None
    ):
        self.name = name
        self.instruction = instruction
        self.tools = tools or []
        self.mcp_servers = mcp_servers or []
        self._llm: Optional[AugmentedLLM] = None
        
    @abstractmethod
    async def process(self, message: str, **kwargs) -> str:
        """Process a message and return response"""
        pass
        
    async def add_tool(self, tool: ToolProtocol):
        """Add a local tool to the agent"""
        self.tools.append(tool)
        
    async def add_mcp_server(self, server_name: str):
        """Add an MCP server to the agent"""
        self.mcp_servers.append(server_name)


class LightweightAgent(BaseAgent):
    """
    Lightweight agent without MCP overhead.
    Uses only local tools and direct LLM calls.
    """
    
    def __init__(
        self,
        name: str,
        instruction: str,
        tools: Optional[List[ToolProtocol]] = None,
        llm_provider: str = "anthropic"
    ):
        super().__init__(name, instruction, tools)
        self.llm_provider = llm_provider
        
    async def process(self, message: str, **kwargs) -> str:
        """
        Process message using direct LLM calls and local tools.
        No MCP overhead - just pure function calls.
        """
        # Implementation would use direct Anthropic/OpenAI SDK
        # with local tool execution
        logger.info(f"Lightweight agent {self.name} processing: {message[:50]}...")
        
        # For now, return a placeholder
        return f"[Lightweight Agent {self.name}] Processed: {message}"


class MCPEnabledAgent(BaseAgent):
    """
    MCP-enabled agent that can connect to MCP servers.
    Supports both local and remote MCP servers.
    """
    
    def __init__(
        self,
        name: str,
        instruction: str,
        tools: Optional[List[ToolProtocol]] = None,
        mcp_servers: Optional[List[str]] = None,
        mcp_config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(name, instruction, tools, mcp_servers)
        self.mcp_config = mcp_config or {}
        self._mcp_agent: Optional[MCPAgent] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        if self.mcp_servers:
            self._mcp_agent = MCPAgent(
                name=self.name,
                instruction=self.instruction,
                server_names=self.mcp_servers
            )
            await self._mcp_agent.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._mcp_agent:
            await self._mcp_agent.__aexit__(exc_type, exc_val, exc_tb)
            
    async def process(self, message: str, **kwargs) -> str:
        """
        Process message using MCP servers and tools.
        """
        if not self._mcp_agent:
            raise RuntimeError("MCP agent not initialized. Use async context manager.")
            
        # TEMPORARY FIX: Bypass MCP agent due to authentication issues
        # Use direct Anthropic client instead
        import os
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": message}]
        )

        return response.content[0].text


class HybridAgent(BaseAgent):
    """
    Hybrid agent that can use both local tools and MCP servers.
    Intelligently decides when to use MCP vs local execution.
    """
    
    def __init__(
        self,
        name: str,
        instruction: str,
        tools: Optional[List[ToolProtocol]] = None,
        mcp_servers: Optional[List[str]] = None,
        prefer_local: bool = True
    ):
        super().__init__(name, instruction, tools, mcp_servers)
        self.prefer_local = prefer_local
        self._lightweight = LightweightAgent(name, instruction, tools)
        self._mcp_enabled = MCPEnabledAgent(name, instruction, tools, mcp_servers)
        
    async def process(self, message: str, **kwargs) -> str:
        """
        Process using the most appropriate method.
        Can use local tools for speed or MCP for capabilities.
        """
        # Decision logic: use local tools if available and preferred
        needs_mcp = self._requires_mcp_capabilities(message)
        
        if needs_mcp and self.mcp_servers:
            async with self._mcp_enabled as agent:
                return await agent.process(message, **kwargs)
        else:
            return await self._lightweight.process(message, **kwargs)
            
    def _requires_mcp_capabilities(self, message: str) -> bool:
        """Determine if the message requires MCP server capabilities"""
        # Simple heuristic - could be made more sophisticated
        mcp_keywords = ['file', 'read', 'write', 'fetch', 'url', 'browse']
        return any(keyword in message.lower() for keyword in mcp_keywords)


# Factory function for easy agent creation
def create_agent(
    name: str,
    instruction: str,
    agent_type: str = "hybrid",
    **kwargs
) -> BaseAgent:
    """
    Factory function to create different types of agents.
    
    Args:
        name: Agent name
        instruction: Agent instruction/prompt
        agent_type: One of "lightweight", "mcp", or "hybrid"
        **kwargs: Additional arguments for specific agent types
        
    Returns:
        Configured agent instance
    """
    if agent_type == "lightweight":
        return LightweightAgent(name, instruction, **kwargs)
    elif agent_type == "mcp":
        return MCPEnabledAgent(name, instruction, **kwargs)
    elif agent_type == "hybrid":
        return HybridAgent(name, instruction, **kwargs)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")