"""
Intelligent MCP Router with Advanced Features

Determines optimal processing path and handles remote/containerized MCPs
"""
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import re

@dataclass
class ToolRequirement:
    """Analyzes what a message needs"""
    tools_mentioned: Set[str]
    multi_step: bool
    needs_state: bool
    requires_coordination: bool
    estimated_tool_calls: int
    complexity_score: float

class MCPMode(Enum):
    STDIO = "stdio"          # Local process
    DOCKER = "docker"        # Containerized
    HTTP = "http"            # Remote HTTP
    SSE = "sse"              # Server-sent events

@dataclass 
class MCPServerConfig:
    name: str
    mode: MCPMode
    command: Optional[List[str]] = None
    docker_image: Optional[str] = None
    endpoint: Optional[str] = None
    capabilities: List[str] = None
    
class IntelligentMCPRouter:
    """Smart routing based on message analysis and tool requirements"""
    
    # Tool patterns that indicate usage
    TOOL_PATTERNS = {
        "filesystem": [
            r"(read|write|create|delete|list).*(file|folder|directory)",
            r"save.*to\s+['\"]?([/\\][\w/\\.-]+)",
            r"(cat|ls|mkdir|rm|touch)\s+",
        ],
        "github": [
            r"(check|review|merge|create).*(PR|pull request|issue)",
            r"github\s+(notification|repo|commit)",
            r"(push|pull|clone)\s+.*repo",
        ],
        "database": [
            r"(query|select|insert|update).*from.*table",
            r"database|postgres|mysql|sqlite",
            r"SQL\s+query",
        ],
        "terminal": [
            r"(run|execute|test).*command",
            r"(npm|pip|cargo|go)\s+(install|test|build)",
            r"shell|bash|terminal",
        ],
        "kubernetes": [
            r"(deploy|scale|check).*pod|deployment|service",
            r"kubectl|k8s|kubernetes",
            r"container.*status",
        ]
    }
    
    # Multi-step indicators
    MULTI_STEP_PATTERNS = [
        r"(then|after that|next|finally)",
        r"(first|second|third|step \d+)",
        r"and (then|also|additionally)",
        r"workflow|pipeline|process",
    ]
    
    # State requirement indicators  
    STATE_PATTERNS = [
        r"(remember|recall|previous|earlier)",
        r"(context|history|conversation)",
        r"based on.*earlier",
        r"continue.*from",
    ]
    
    def __init__(self):
        self.server_configs = self._load_server_configs()
        
    def _load_server_configs(self) -> Dict[str, MCPServerConfig]:
        """Load MCP server configurations"""
        return {
            "filesystem": MCPServerConfig(
                name="filesystem",
                mode=MCPMode.STDIO,
                command=["npx", "@modelcontextprotocol/server-filesystem", "/tmp"],
                capabilities=["read", "write", "list", "delete"]
            ),
            "github": MCPServerConfig(
                name="github", 
                mode=MCPMode.DOCKER,
                docker_image="mcp/github-server:latest",
                capabilities=["repos", "issues", "prs", "notifications"]
            ),
            "postgres": MCPServerConfig(
                name="postgres",
                mode=MCPMode.HTTP,
                endpoint="http://mcp-postgres:8080",
                capabilities=["query", "schema", "migrate"]
            ),
            "kubernetes": MCPServerConfig(
                name="kubernetes",
                mode=MCPMode.DOCKER,
                docker_image="mcp/k8s-server:latest",
                capabilities=["pods", "deployments", "logs", "exec"]
            )
        }
    
    def analyze_message(self, message: str) -> ToolRequirement:
        """Deeply analyze message to understand requirements"""
        message_lower = message.lower()
        
        # Detect mentioned tools
        tools_mentioned = set()
        for tool, patterns in self.TOOL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    tools_mentioned.add(tool)
                    break
        
        # Check for multi-step
        multi_step = any(
            re.search(pattern, message_lower) 
            for pattern in self.MULTI_STEP_PATTERNS
        )
        
        # Check for state requirements
        needs_state = any(
            re.search(pattern, message_lower)
            for pattern in self.STATE_PATTERNS
        )
        
        # Estimate tool calls
        estimated_calls = self._estimate_tool_calls(message, tools_mentioned)
        
        # Check coordination needs
        requires_coordination = (
            len(tools_mentioned) > 2 or
            (multi_step and len(tools_mentioned) > 1) or
            "pipeline" in message_lower or
            "workflow" in message_lower
        )
        
        # Calculate complexity score
        complexity_score = (
            len(tools_mentioned) * 1.0 +
            (2.0 if multi_step else 0) +
            (1.5 if needs_state else 0) +
            (2.5 if requires_coordination else 0) +
            estimated_calls * 0.5
        )
        
        return ToolRequirement(
            tools_mentioned=tools_mentioned,
            multi_step=multi_step,
            needs_state=needs_state,
            requires_coordination=requires_coordination,
            estimated_tool_calls=estimated_calls,
            complexity_score=complexity_score
        )
    
    def _estimate_tool_calls(self, message: str, tools: Set[str]) -> int:
        """Estimate number of tool calls needed"""
        # Count action words
        action_words = len(re.findall(
            r"(read|write|create|delete|list|check|query|run|execute|deploy)",
            message.lower()
        ))
        
        # Multiple files/resources mentioned
        file_refs = len(re.findall(r"['\"][\w/\\.-]+['\"]", message))
        
        return max(action_words, file_refs, len(tools))
    
    def determine_routing(
        self, 
        message: str,
        explicit_tools: Optional[List[str]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Determine optimal routing and return (handler, metadata)
        
        Returns:
            handler: "direct_llm", "direct_mcp", or "mcp_agent"
            metadata: Additional routing information
        """
        analysis = self.analyze_message(message)
        
        # Override: User explicitly requested tools
        if explicit_tools:
            analysis.tools_mentioned.update(explicit_tools)
            analysis.complexity_score += len(explicit_tools)
        
        # Route decision tree
        if not analysis.tools_mentioned:
            return "direct_llm", {"reason": "no_tools_needed"}
        
        # Complex scenarios → mcp-agent
        if analysis.complexity_score > 5.0:
            return "mcp_agent", {
                "reason": "high_complexity",
                "complexity_score": analysis.complexity_score,
                "factors": {
                    "tools": list(analysis.tools_mentioned),
                    "multi_step": analysis.multi_step,
                    "needs_state": analysis.needs_state,
                    "coordination": analysis.requires_coordination
                }
            }
        
        # Specific workflow patterns → mcp-agent
        workflow_keywords = ["pipeline", "workflow", "automate", "orchestrate"]
        if any(keyword in message.lower() for keyword in workflow_keywords):
            return "mcp_agent", {"reason": "workflow_requested"}
        
        # Simple tool usage → direct MCP
        return "direct_mcp", {
            "reason": "simple_tools",
            "tools": list(analysis.tools_mentioned),
            "estimated_calls": analysis.estimated_tool_calls
        }


class EnhancedDirectMCP:
    """Direct MCP with advanced features borrowed from mcp-agent"""
    
    def __init__(self):
        self.router = IntelligentMCPRouter()
        self.connection_pool = {}  # Reuse connections
        self.docker_client = None
        
    async def connect_mcp_server(
        self, 
        server_config: MCPServerConfig
    ) -> 'MCPConnection':
        """Connect to MCP server based on mode"""
        
        # Check connection pool
        if server_config.name in self.connection_pool:
            return self.connection_pool[server_config.name]
        
        if server_config.mode == MCPMode.STDIO:
            conn = await self._connect_stdio(server_config)
        elif server_config.mode == MCPMode.DOCKER:
            conn = await self._connect_docker(server_config)
        elif server_config.mode == MCPMode.HTTP:
            conn = await self._connect_http(server_config)
        else:
            raise ValueError(f"Unsupported mode: {server_config.mode}")
        
        # Cache connection
        self.connection_pool[server_config.name] = conn
        return conn
    
    async def _connect_stdio(self, config: MCPServerConfig):
        """Connect to local stdio MCP server"""
        from mcp import ClientSession, StdioServerParameters
        
        params = StdioServerParameters(
            command=config.command[0],
            args=config.command[1:]
        )
        
        session = ClientSession(params)
        await session.start()
        return session
    
    async def _connect_docker(self, config: MCPServerConfig):
        """Connect to containerized MCP server"""
        import docker
        
        if not self.docker_client:
            self.docker_client = docker.from_env()
        
        # Check if container exists
        container_name = f"mcp-{config.name}"
        try:
            container = self.docker_client.containers.get(container_name)
        except docker.errors.NotFound:
            # Start container
            container = self.docker_client.containers.run(
                config.docker_image,
                name=container_name,
                detach=True,
                network="gaia_net",  # Same network as services
                environment={
                    "MCP_MODE": "server",
                    "MCP_PORT": "8080"
                }
            )
        
        # Connect via HTTP to container
        endpoint = f"http://{container_name}:8080"
        return await self._connect_http_endpoint(endpoint)
    
    async def _connect_http(self, config: MCPServerConfig):
        """Connect to remote HTTP MCP server"""
        return await self._connect_http_endpoint(config.endpoint)
    
    async def _connect_http_endpoint(self, endpoint: str):
        """Connect to HTTP MCP endpoint with retries"""
        from mcp import HTTPClientSession
        
        # Implement retry logic
        for attempt in range(3):
            try:
                session = HTTPClientSession(endpoint)
                await session.start()
                return session
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(1 * (attempt + 1))
    
    # Additional features from mcp-agent
    
    async def parallel_tool_calls(
        self, 
        tool_calls: List[Dict[str, Any]]
    ) -> List[Any]:
        """Execute multiple tool calls in parallel"""
        tasks = []
        for call in tool_calls:
            server = call["server"]
            tool = call["tool"]
            args = call["args"]
            
            task = self._execute_tool(server, tool, args)
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    async def _execute_tool(self, server: str, tool: str, args: Dict):
        """Execute a tool with error handling and retries"""
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                conn = self.connection_pool.get(server)
                if not conn:
                    raise ValueError(f"Not connected to {server}")
                
                result = await conn.call_tool(tool, args)
                return {"success": True, "result": result}
                
            except Exception as e:
                if attempt == max_retries:
                    return {"success": False, "error": str(e)}
                await asyncio.sleep(0.5 * (attempt + 1))
    
    def cleanup(self):
        """Clean up connections and containers"""
        # Close MCP connections
        for conn in self.connection_pool.values():
            asyncio.create_task(conn.stop())
        
        # Stop Docker containers
        if self.docker_client:
            for config in self.router.server_configs.values():
                if config.mode == MCPMode.DOCKER:
                    try:
                        container = self.docker_client.containers.get(f"mcp-{config.name}")
                        container.stop()
                        container.remove()
                    except:
                        pass


# Example usage showing routing decision
async def example_chat_request(message: str):
    router = IntelligentMCPRouter()
    
    # Analyze and route
    handler, metadata = router.determine_routing(message)
    
    print(f"Message: {message}")
    print(f"Route to: {handler}")
    print(f"Metadata: {metadata}")
    print()

# Test cases
if __name__ == "__main__":
    import asyncio
    
    test_messages = [
        "What is 2+2?",  # → direct_llm
        "List the files in my home directory",  # → direct_mcp
        "Check my GitHub PRs and summarize them",  # → direct_mcp
        "Review my code, fix any bugs, test it, and create a PR",  # → mcp_agent
        "Set up a data pipeline that pulls from S3, processes with pandas, and saves to postgres",  # → mcp_agent
    ]
    
    for msg in test_messages:
        asyncio.run(example_chat_request(msg))