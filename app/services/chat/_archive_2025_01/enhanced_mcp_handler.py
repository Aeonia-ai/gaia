"""
Enhanced MCP Handler - Direct MCP with Advanced Features

Incorporates best practices from mcp-agent without the overhead
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
import time
from collections import defaultdict

from anthropic import Anthropic
from openai import OpenAI
import httpx

from app.shared.logging import logger
from app.shared.redis_client import CacheManager


@dataclass
class MCPToolCall:
    id: str
    server: str
    tool: str
    arguments: Dict[str, Any]
    
@dataclass
class MCPToolResult:
    call_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    duration_ms: int = 0


class EnhancedMCPHandler:
    """
    Direct MCP integration with advanced features:
    - Connection pooling
    - Parallel tool execution
    - Result caching
    - Error recovery
    - Streaming responses
    """
    
    def __init__(self):
        self.anthropic = Anthropic()
        self.openai = OpenAI()
        self.connection_pool = {}
        self.cache = CacheManager(prefix="mcp_tools")
        self.metrics = defaultdict(lambda: {"calls": 0, "errors": 0, "total_ms": 0})
        
    async def process_with_tools(
        self,
        message: str,
        tools: List[str],
        model: str = "claude-sonnet-4-5",
        stream: bool = False,
        cache_results: bool = True
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Process a message with MCP tools
        
        Yields streaming updates if stream=True
        """
        start_time = time.time()
        
        # 1. Connect to required MCP servers (reuse connections)
        if stream:
            yield {"type": "status", "message": "Connecting to tools..."}
            
        available_tools = await self._ensure_connections(tools)
        
        # 2. Initial LLM call with tools
        if stream:
            yield {"type": "status", "message": "Processing request..."}
            
        llm_response = await self._llm_call_with_tools(
            message, 
            available_tools, 
            model
        )
        
        # 3. Execute any tool calls in parallel
        if llm_response.get("tool_calls"):
            if stream:
                yield {
                    "type": "tool_use", 
                    "tools": [tc["tool"] for tc in llm_response["tool_calls"]]
                }
            
            tool_results = await self._execute_tools_parallel(
                llm_response["tool_calls"],
                cache_results
            )
            
            # 4. Final LLM call with tool results
            final_response = await self._llm_call_with_results(
                message,
                llm_response,
                tool_results,
                model
            )
            
            response_text = final_response["content"]
        else:
            response_text = llm_response["content"]
        
        # 5. Return final result
        total_time = int((time.time() - start_time) * 1000)
        
        yield {
            "type": "completion",
            "content": response_text,
            "usage": llm_response.get("usage", {}),
            "metrics": {
                "total_ms": total_time,
                "tool_calls": len(llm_response.get("tool_calls", [])),
                "cached_tools": sum(1 for r in tool_results if r.get("cached"))
            }
        }
    
    async def _ensure_connections(self, tools: List[str]) -> List[Dict]:
        """Ensure connections to MCP servers, reusing when possible"""
        available_tools = []
        
        for tool_name in tools:
            if tool_name in self.connection_pool:
                # Reuse existing connection
                conn = self.connection_pool[tool_name]
                if await self._check_connection_health(conn):
                    tools_list = conn["tools"]
                    available_tools.extend(tools_list)
                    continue
            
            # New connection needed
            try:
                conn = await self._connect_mcp_server(tool_name)
                self.connection_pool[tool_name] = conn
                available_tools.extend(conn["tools"])
            except Exception as e:
                logger.warning(f"Failed to connect to {tool_name}: {e}")
        
        return available_tools
    
    async def _connect_mcp_server(self, server_name: str) -> Dict:
        """Connect to an MCP server based on configuration"""
        # In production, load from config
        server_configs = {
            "filesystem": {
                "command": ["npx", "@modelcontextprotocol/server-filesystem", "/tmp"]
            },
            "github": {
                "docker": "mcp/github-server:latest",
                "port": 8080
            },
            "postgres": {
                "endpoint": "http://mcp-postgres:8080"
            }
        }
        
        config = server_configs.get(server_name, {})
        
        if "command" in config:
            # Local stdio connection
            from mcp import ClientSession, StdioServerParameters
            params = StdioServerParameters(
                command=config["command"][0],
                args=config["command"][1:]
            )
            session = ClientSession(params)
            await session.start()
            
            tools = await session.list_tools()
            return {
                "session": session,
                "tools": [self._convert_tool_format(t, server_name) for t in tools],
                "type": "stdio"
            }
            
        elif "docker" in config:
            # Docker container connection
            # Implementation would start container and connect
            pass
            
        elif "endpoint" in config:
            # HTTP endpoint connection
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{config['endpoint']}/tools")
                tools = resp.json()
                return {
                    "endpoint": config["endpoint"],
                    "tools": [self._convert_tool_format(t, server_name) for t in tools],
                    "type": "http"
                }
    
    async def _execute_tools_parallel(
        self,
        tool_calls: List[Dict],
        cache_results: bool
    ) -> List[MCPToolResult]:
        """Execute multiple tool calls in parallel with caching"""
        tasks = []
        
        for call in tool_calls:
            # Check cache first
            if cache_results:
                cache_key = f"{call['server']}:{call['tool']}:{json.dumps(call['arguments'], sort_keys=True)}"
                cached = await self.cache.get(cache_key)
                if cached:
                    tasks.append(asyncio.create_task(
                        self._return_cached(call["id"], cached)
                    ))
                    continue
            
            # Execute tool
            task = self._execute_single_tool(call)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(MCPToolResult(
                    call_id=tool_calls[i]["id"],
                    success=False,
                    result=None,
                    error=str(result)
                ))
            else:
                final_results.append(result)
                
                # Cache successful results
                if cache_results and result.success:
                    call = tool_calls[i]
                    cache_key = f"{call['server']}:{call['tool']}:{json.dumps(call['arguments'], sort_keys=True)}"
                    await self.cache.set(cache_key, result.result, ttl=300)  # 5 min cache
        
        return final_results
    
    async def _execute_single_tool(self, call: Dict) -> MCPToolResult:
        """Execute a single tool call with timing and error handling"""
        start_time = time.time()
        server_name = call["server"]
        
        try:
            conn = self.connection_pool.get(server_name)
            if not conn:
                raise ValueError(f"No connection to {server_name}")
            
            # Execute based on connection type
            if conn["type"] == "stdio":
                result = await conn["session"].call_tool(
                    call["tool"],
                    call["arguments"]
                )
            elif conn["type"] == "http":
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{conn['endpoint']}/tools/{call['tool']}",
                        json=call["arguments"]
                    )
                    result = resp.json()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Update metrics
            self.metrics[server_name]["calls"] += 1
            self.metrics[server_name]["total_ms"] += duration_ms
            
            return MCPToolResult(
                call_id=call["id"],
                success=True,
                result=result,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics[server_name]["errors"] += 1
            
            logger.error(f"Tool execution failed: {server_name}.{call['tool']}: {e}")
            
            return MCPToolResult(
                call_id=call["id"],
                success=False,
                result=None,
                error=str(e),
                duration_ms=duration_ms
            )
    
    async def _llm_call_with_tools(
        self,
        message: str,
        tools: List[Dict],
        model: str
    ) -> Dict:
        """Initial LLM call with available tools"""
        # Convert to Anthropic format
        anthropic_tools = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            }
            for tool in tools
        ]
        
        response = self.anthropic.messages.create(
            model=model,
            messages=[{"role": "user", "content": message}],
            tools=anthropic_tools if anthropic_tools else None,
            max_tokens=2000
        )
        
        # Parse response
        result = {
            "content": "",
            "tool_calls": [],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens
            }
        }
        
        for block in response.content:
            if block.type == "text":
                result["content"] += block.text
            elif block.type == "tool_use":
                result["tool_calls"].append({
                    "id": block.id,
                    "server": self._extract_server_from_tool(block.name),
                    "tool": block.name,
                    "arguments": block.input
                })
        
        return result
    
    def _extract_server_from_tool(self, tool_name: str) -> str:
        """Extract server name from tool name"""
        # Simple heuristic - in production use proper mapping
        if tool_name.startswith("fs_"):
            return "filesystem"
        elif tool_name.startswith("github_"):
            return "github"
        elif tool_name.startswith("pg_"):
            return "postgres"
        return "unknown"
    
    async def cleanup(self):
        """Clean up all connections"""
        for conn in self.connection_pool.values():
            try:
                if conn["type"] == "stdio":
                    await conn["session"].stop()
            except:
                pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        metrics = {}
        for server, data in self.metrics.items():
            if data["calls"] > 0:
                metrics[server] = {
                    "total_calls": data["calls"],
                    "error_rate": data["errors"] / data["calls"],
                    "avg_latency_ms": data["total_ms"] / data["calls"]
                }
        return metrics


# Integration with chat service
class MCPChatEndpoint:
    """Chat endpoint with intelligent MCP routing"""
    
    def __init__(self):
        from .intelligent_mcp_router import IntelligentMCPRouter
        self.router = IntelligentMCPRouter()
        self.direct_mcp = EnhancedMCPHandler()
        
    async def process_request(
        self,
        message: str,
        requested_tools: Optional[List[str]] = None,
        workflow_type: Optional[str] = None,
        model: str = "claude-sonnet-4-5",
        stream: bool = False
    ):
        """Process chat request with intelligent routing"""
        
        # Determine routing
        handler, metadata = self.router.determine_routing(
            message,
            requested_tools,
            {"workflow_type": workflow_type}
        )
        
        logger.info(f"Routing to {handler}: {metadata}")
        
        if handler == "direct_llm":
            # Fast path - no tools
            return await self._direct_llm_call(message, model)
            
        elif handler == "direct_mcp":
            # Our enhanced direct MCP handler
            tools = metadata.get("tools", []) or requested_tools or []
            
            if stream:
                # Return async generator for streaming
                return self.direct_mcp.process_with_tools(
                    message, tools, model, stream=True
                )
            else:
                # Collect all results
                results = []
                async for chunk in self.direct_mcp.process_with_tools(
                    message, tools, model, stream=True
                ):
                    results.append(chunk)
                
                # Return final completion
                return results[-1]
                
        else:  # mcp_agent
            # Complex workflows still use mcp-agent
            return await self._mcp_agent_workflow(
                message, 
                metadata,
                workflow_type
            )
    
    async def _direct_llm_call(self, message: str, model: str):
        """Direct LLM call without tools"""
        # Your existing fast path
        pass