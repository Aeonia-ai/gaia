"""
Unified Intelligent Chat Handler

A single endpoint that uses LLM tool-calling to intelligently handle requests:
- Direct responses for simple queries (no tools)
- KB tools for knowledge base operations
- MCP agent for file/system operations
- Multi-agent orchestration for complex analysis
"""
import logging
import time
import uuid
import json
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
from enum import Enum

from app.services.llm.chat_service import chat_service
from app.services.chat.lightweight_chat_hot import hot_chat_service
from app.services.llm import LLMProvider
import httpx
from app.shared.config import settings
from .kb_tools import KB_TOOLS, KBToolExecutor

logger = logging.getLogger(__name__)


class RouteType(str, Enum):
    """Types of routing decisions"""
    DIRECT = "direct"
    MCP_AGENT = "mcp_agent"
    MULTIAGENT = "multiagent"


class UnifiedChatHandler:
    """
    Handles all chat requests with intelligent routing via LLM tool-calling.
    
    Uses a single LLM call to decide whether to:
    1. Respond directly (no tools needed)
    2. Route to MCP agent (for tool use)
    3. Route to multi-agent orchestration (for complex analysis)
    """
    
    def __init__(self):
        # Pre-initialized services (hot-loaded)
        self.mcp_hot_service = hot_chat_service  # Already initialized at startup
        self.multiagent_orchestrator = None  # TODO: Initialize when available
        
        # Routing tools definition (for services that need routing)
        self.routing_tools = [
            {
                "type": "function",
                "function": {
                    "name": "use_mcp_agent",
                    "description": "Use this ONLY when the user explicitly asks to: read/write files outside KB, run system commands, search the web, make API calls, or perform system operations. Do NOT use for general questions or KB operations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reasoning": {
                                "type": "string",
                                "description": "Brief explanation of why MCP agent is needed"
                            }
                        },
                        "required": ["reasoning"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "use_asset_service", 
                    "description": "Use this ONLY when the user explicitly asks to generate/create an image, 3D model, audio file, or video. Keywords: 'generate', 'create', 'make' + asset type",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "asset_type": {
                                "type": "string",
                                "enum": ["image", "3d_model", "audio", "video"],
                                "description": "Type of asset to generate"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the asset to generate"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why asset service is needed"
                            }
                        },
                        "required": ["asset_type", "description", "reasoning"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "use_multiagent_orchestration",
                    "description": "Use this for complex requests that require multiple expert perspectives, cross-domain analysis, or coordinated reasoning across different specialties (technical, business, creative, etc.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "domains": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of domains needed (e.g., ['technical', 'business', 'creative'])"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why multiple agents are needed"
                            }
                        },
                        "required": ["domains", "reasoning"]
                    }
                }
            }
        ]
        
        # Metrics tracking
        self._routing_metrics = {
            RouteType.DIRECT: 0,
            RouteType.MCP_AGENT: 0,
            RouteType.MULTIAGENT: 0,
            "total_requests": 0,
            "avg_routing_time_ms": 0,
            "avg_total_time_ms": 0
        }
    
    async def process(self, message: str, auth: dict, context: Optional[dict] = None) -> dict:
        """
        Process message with intelligent routing.
        
        Returns a standardized response format regardless of routing path.
        """
        start_time = time.time()
        request_id = f"chat-{uuid.uuid4()}"
        
        # Update metrics
        self._routing_metrics["total_requests"] += 1
        
        # Build context (user info, conversation history, etc.)
        full_context = await self.build_context(auth, context)
        
        # Single LLM call with routing capability - but no "routing overhead"
        llm_start = time.time()
        
        try:
            # Prepare messages for routing decision
            messages = [
                {
                    "role": "system",
                    "content": self.get_routing_prompt(full_context)
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
            
            # Combine routing tools with KB tools
            all_tools = self.routing_tools + KB_TOOLS
            
            # Use chat service with all available tools
            routing_response = await chat_service.chat_completion(
                messages=messages,
                tools=all_tools,
                tool_choice={"type": "auto"},  # Let LLM decide: direct response or tool use
                temperature=0.7,
                max_tokens=4096,
                request_id=f"{request_id}-routing"
            )
            
            llm_time = (time.time() - llm_start) * 1000
            
            # Check if LLM made tool calls
            if routing_response.get("tool_calls"):
                tool_calls = routing_response["tool_calls"]
                
                # Check if any KB tools were called
                kb_tool_names = {tool["function"]["name"] for tool in KB_TOOLS}
                kb_calls = [tc for tc in tool_calls if tc["function"]["name"] in kb_tool_names]
                
                if kb_calls:
                    # Handle KB tool calls directly
                    kb_executor = KBToolExecutor(auth)
                    tool_results = []
                    
                    for tool_call in kb_calls:
                        tool_name = tool_call["function"]["name"]
                        tool_args_raw = tool_call["function"].get("arguments", "{}")
                        if isinstance(tool_args_raw, str):
                            tool_args = json.loads(tool_args_raw)
                        else:
                            tool_args = tool_args_raw
                        
                        logger.info(f"[{request_id}] Executing KB tool: {tool_name} with args: {tool_args}")
                        result = await kb_executor.execute_tool(tool_name, tool_args)
                        tool_results.append({
                            "tool": tool_name,
                            "result": result
                        })
                    
                    # Make another LLM call with the tool results to generate final response
                    # For Anthropic, tool results are included as user messages
                    tool_result_content = "\n\nTool Results:\n"
                    for result in tool_results:
                        tool_result_content += f"\n{result['tool']}:\n{json.dumps(result['result'], indent=2)}\n"
                    
                    messages.append({
                        "role": "user",
                        "content": tool_result_content
                    })
                    
                    # Get final response from LLM with tool results
                    final_response = await chat_service.chat_completion(
                        messages=messages,
                        temperature=0.7,
                        max_tokens=4096,
                        request_id=f"{request_id}-final"
                    )
                    
                    return {
                        "id": request_id,
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": final_response.get("model", "unknown"),
                        "choices": final_response.get("choices", []),
                        "usage": final_response.get("usage", {}),
                        "_metadata": {
                            "route_type": "kb_tools",
                            "tools_used": [tr["tool"] for tr in tool_results],
                            "total_time_ms": int((time.time() - start_time) * 1000),
                            "request_id": request_id
                        }
                    }
                
                # Handle routing tools (non-KB)
                tool_call = tool_calls[0]  # For routing, we only use the first
                tool_name = tool_call["function"]["name"]
                
                # Parse tool arguments
                tool_args_raw = tool_call["function"].get("arguments", "{}")
                if isinstance(tool_args_raw, str):
                    tool_args = json.loads(tool_args_raw)
                else:
                    tool_args = tool_args_raw
                
                if tool_name == "use_mcp_agent":
                    # Route to MCP agent for tool use
                    route_type = RouteType.MCP_AGENT
                    self._routing_metrics[route_type] += 1
                    
                    logger.info(
                        f"[{request_id}] Routing to MCP agent - {tool_args.get('reasoning', 'No reason provided')}"
                    )
                    
                    # Use the hot-loaded MCP service
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Add routing metadata
                    routing_overhead = llm_time  # Time to decide routing
                    result["_metadata"] = {
                        "route_type": route_type,
                        "routing_time_ms": int(routing_overhead),
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "reasoning": tool_args.get("reasoning"),
                        "request_id": request_id
                    }
                    
                    return result
                
                elif tool_name == "use_asset_service":
                    # Route to Asset service
                    route_type = RouteType.MCP_AGENT  # For now, use MCP agent for assets
                    self._routing_metrics[route_type] += 1
                    
                    asset_type = tool_args.get("asset_type", "image")
                    description = tool_args.get("description", "")
                    reasoning = tool_args.get("reasoning", "")
                    
                    logger.info(
                        f"[{request_id}] Routing to Asset service - type: {asset_type}, desc: {description}"
                    )
                    
                    # For now, use MCP agent to handle asset generation
                    # TODO: Implement direct asset service integration
                    from app.models.chat import ChatRequest
                    asset_message = f"Generate a {asset_type}: {description}"
                    chat_request = ChatRequest(message=asset_message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Add routing metadata
                    result["_metadata"] = {
                        "route_type": "asset_service",
                        "routing_time_ms": int(llm_time),  # Time to decide routing
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "asset_type": asset_type,
                        "description": description,
                        "reasoning": reasoning,
                        "request_id": request_id,
                        "note": "Using MCP agent for asset generation"
                    }
                    
                    return result
                    
                elif tool_name == "use_multiagent_orchestration":
                    # Route to multi-agent system
                    route_type = RouteType.MULTIAGENT
                    self._routing_metrics[route_type] += 1
                    
                    domains = tool_args.get("domains", [])
                    reasoning = tool_args.get("reasoning", "")
                    
                    logger.info(
                        f"[{request_id}] Routing to multi-agent - domains: {domains}, reason: {reasoning}"
                    )
                    
                    # For now, fall back to MCP agent until multiagent is ready
                    # TODO: Implement actual multiagent orchestration
                    logger.warning("Multi-agent orchestration not yet implemented, using MCP agent")
                    
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Add routing metadata
                    result["_metadata"] = {
                        "route_type": route_type,
                        "routing_time_ms": int(llm_time),  # Time to decide routing
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "domains": domains,
                        "reasoning": reasoning,
                        "request_id": request_id,
                        "fallback": "mcp_agent"  # Remove when multiagent is ready
                    }
                    
                    return result
                
                else:
                    # Unknown tool - fallback to MCP agent
                    logger.warning(f"Unknown routing tool: {tool_name}, falling back to MCP agent")
                    route_type = RouteType.MCP_AGENT
                    self._routing_metrics[route_type] += 1
                    
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    result["_metadata"] = {
                        "route_type": route_type,
                        "routing_time_ms": int(llm_time),  # Time to decide routing
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "request_id": request_id,
                        "error": f"Unknown tool: {tool_name}, used fallback"
                    }
                    
                    return result
            
            else:
                # Direct response - no routing needed, just normal LLM response
                route_type = RouteType.DIRECT
                self._routing_metrics[route_type] += 1
                
                # Extract content from the response structure
                content = routing_response.get("response", "")
                model = routing_response.get("model", "claude-3-5-sonnet-20241022")
                usage = routing_response.get("usage", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                })
                
                logger.info(
                    f"[{request_id}] Direct response in {llm_time:.0f}ms (no routing needed)"
                )
                
                # Update routing metrics - no routing overhead for direct responses
                self._update_timing_metrics(0, (time.time() - start_time) * 1000)
                
                return {
                    "id": request_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": usage,
                    "_metadata": {
                        "route_type": route_type,
                        "routing_time_ms": 0,  # No routing overhead for direct responses
                        "llm_time_ms": int(llm_time),  # Actual LLM response time
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "request_id": request_id
                    }
                }
                
        except Exception as e:
            logger.error(f"[{request_id}] Routing error: {e}", exc_info=True)
            # Fall back to direct MCP agent on error
            from app.models.chat import ChatRequest
            chat_request = ChatRequest(message=message)
            
            result = await self.mcp_hot_service.process_chat(
                request=chat_request,
                auth_principal=auth
            )
            
            result["_metadata"] = {
                "route_type": RouteType.MCP_AGENT,
                "error": str(e),
                "fallback": True,
                "request_id": request_id
            }
            
            return result
    
    async def process_stream(
        self, 
        message: str, 
        auth: dict, 
        context: Optional[dict] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process message with intelligent routing and streaming response.
        
        Yields OpenAI-compatible SSE chunks for streaming.
        """
        start_time = time.time()
        request_id = f"chat-{uuid.uuid4()}"
        
        # Update metrics
        self._routing_metrics["total_requests"] += 1
        
        # Build context
        full_context = await self.build_context(auth, context)
        
        # Make routing decision
        llm_start = time.time()
        
        try:
            # Prepare messages for routing decision
            messages = [
                {
                    "role": "system",
                    "content": self.get_routing_prompt(full_context)
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
            
            # First, make routing decision (non-streaming)
            routing_response = await chat_service.chat_completion(
                messages=messages,
                tools=self.routing_tools,
                tool_choice={"type": "auto"},
                temperature=0.7,
                max_tokens=4096,
                request_id=f"{request_id}-routing"
            )
            
            llm_time = (time.time() - llm_start) * 1000
            
            # Check if LLM made tool calls
            if routing_response.get("tool_calls"):
                # Route to appropriate service with streaming
                tool_call = routing_response["tool_calls"][0]
                tool_name = tool_call["function"]["name"]
                
                # Parse tool arguments
                tool_args_raw = tool_call["function"].get("arguments", "{}")
                if isinstance(tool_args_raw, str):
                    tool_args = json.loads(tool_args_raw)
                else:
                    tool_args = tool_args_raw
                
                # Tool-routed responses - simulate streaming for better UX
                if tool_name == "use_mcp_agent":
                    route_type = RouteType.MCP_AGENT
                    self._routing_metrics[route_type] += 1
                    
                    logger.info(f"[{request_id}] Routing to MCP agent with simulated streaming")
                    
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    # Get the full response from MCP agent
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Extract the content
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    model = result.get("model", "unknown")
                    
                    # Stream the content in chunks for better perceived performance
                    # Use larger chunks for tool responses since they often contain structured data
                    chunk_size = 50  # Characters per chunk
                    
                    # First chunk with role
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }]
                    }
                    
                    # Stream content chunks
                    for i in range(0, len(content), chunk_size):
                        chunk_text = content[i:i + chunk_size]
                        
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        
                        # Small delay to simulate streaming (shorter than direct responses)
                        await asyncio.sleep(0.005)
                    
                    # Final chunk with metadata
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "_metadata": {
                            "route_type": route_type.value,
                            "routing_time_ms": int(llm_time),
                            "total_time_ms": int((time.time() - start_time) * 1000),
                            "reasoning": tool_args.get("reasoning"),
                            "request_id": request_id,
                            "mcp_response_time_ms": result.get("_response_time_ms", 0)
                        }
                    }
                
                elif tool_name == "use_kb_service":
                    # KB service streaming
                    route_type = RouteType.MCP_AGENT  # Using MCP for now
                    self._routing_metrics[route_type] += 1
                    
                    query = tool_args.get("query", message)
                    logger.info(f"[{request_id}] Routing to KB service with simulated streaming")
                    
                    from app.models.chat import ChatRequest
                    kb_message = f"Search my knowledge base for: {query}"
                    chat_request = ChatRequest(message=kb_message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Stream the KB response
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    model = result.get("model", "unknown")
                    
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }]
                    }
                    
                    # Stream KB results in chunks
                    chunk_size = 100  # Larger chunks for KB results
                    for i in range(0, len(content), chunk_size):
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content[i:i + chunk_size]},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.003)
                    
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "_metadata": {
                            "route_type": "kb_service",
                            "routing_time_ms": int(llm_time),
                            "total_time_ms": int((time.time() - start_time) * 1000),
                            "query": query,
                            "reasoning": tool_args.get("reasoning"),
                            "request_id": request_id
                        }
                    }
                    
                elif tool_name == "use_asset_service":
                    # Asset service streaming
                    route_type = RouteType.MCP_AGENT  # Using MCP for now
                    self._routing_metrics[route_type] += 1
                    
                    asset_type = tool_args.get("asset_type", "image")
                    description = tool_args.get("description", "")
                    
                    logger.info(f"[{request_id}] Routing to Asset service with simulated streaming")
                    
                    from app.models.chat import ChatRequest
                    asset_message = f"Generate a {asset_type}: {description}"
                    chat_request = ChatRequest(message=asset_message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Stream asset generation response
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    model = result.get("model", "unknown")
                    
                    # For asset generation, show progress updates
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant", "content": f"🎨 Generating {asset_type}...\n"},
                            "finish_reason": None
                        }]
                    }
                    
                    # Stream the actual response
                    chunk_size = 80
                    for i in range(0, len(content), chunk_size):
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content[i:i + chunk_size]},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.005)
                    
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "_metadata": {
                            "route_type": "asset_service",
                            "routing_time_ms": int(llm_time),
                            "total_time_ms": int((time.time() - start_time) * 1000),
                            "asset_type": asset_type,
                            "description": description,
                            "reasoning": tool_args.get("reasoning"),
                            "request_id": request_id
                        }
                    }
                    
                elif tool_name == "use_multiagent_orchestration":
                    # Multi-agent streaming
                    route_type = RouteType.MULTIAGENT
                    self._routing_metrics[route_type] += 1
                    
                    domains = tool_args.get("domains", [])
                    logger.info(f"[{request_id}] Routing to multi-agent with simulated streaming")
                    
                    # For now, use MCP agent as fallback
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    model = result.get("model", "unknown")
                    
                    # Show multi-agent coordination
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant", "content": f"🤝 Coordinating {', '.join(domains)} agents...\n\n"},
                            "finish_reason": None
                        }]
                    }
                    
                    # Stream response
                    chunk_size = 60
                    for i in range(0, len(content), chunk_size):
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content[i:i + chunk_size]},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.008)  # Slightly slower for multi-agent
                    
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "_metadata": {
                            "route_type": route_type.value,
                            "routing_time_ms": int(llm_time),
                            "total_time_ms": int((time.time() - start_time) * 1000),
                            "domains": domains,
                            "reasoning": tool_args.get("reasoning"),
                            "request_id": request_id,
                            "fallback": "mcp_agent"
                        }
                    }
                    
                else:
                    # Unknown tool - fallback
                    logger.warning(f"[{request_id}] Unknown tool {tool_name}, using MCP fallback")
                    # Use same pattern as MCP agent...
                    
            else:
                # Direct response - stream the LLM response
                route_type = RouteType.DIRECT
                self._routing_metrics[route_type] += 1
                
                logger.info(f"[{request_id}] Direct streaming response")
                
                # Stream the response from LLM
                model = routing_response.get("model", "claude-3-5-sonnet-20241022")
                content = routing_response.get("response", "")
                
                # For direct responses, we already have the full content
                # Stream it in chunks for better UX
                chunk_size = 20  # Characters per chunk
                
                for i in range(0, len(content), chunk_size):
                    chunk_text = content[i:i + chunk_size]
                    
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk_text},
                            "finish_reason": None
                        }]
                    }
                    
                    # Small delay to simulate streaming
                    await asyncio.sleep(0.01)
                
                # Final chunk with metadata
                yield {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }],
                    "_metadata": {
                        "route_type": route_type.value,
                        "routing_time_ms": 0,
                        "llm_time_ms": int(llm_time),
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "request_id": request_id
                    }
                }
                
                # Update metrics
                self._update_timing_metrics(0, (time.time() - start_time) * 1000)
                
        except Exception as e:
            logger.error(f"[{request_id}] Streaming error: {e}", exc_info=True)
            
            # Error chunk
            yield {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "error",
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "error"
                }],
                "error": {
                    "message": str(e),
                    "type": "streaming_error"
                }
            }
    
    def get_routing_prompt(self, context: dict) -> str:
        """
        System prompt that helps LLM make routing decisions.
        """
        return f"""You are an intelligent assistant that can either respond directly or use specialized tools when needed.

Current context:
- User: {context.get('user_id', 'unknown')}
- Conversation: {context.get('conversation_id', 'new')}
- Message count: {context.get('message_count', 0)}

Knowledge Base (KB) tools are available for when users reference their personal knowledge or work context.

Use KB tools naturally when users indicate they want:
- Personal knowledge: "what do I know about X", "find my notes on Y" → search_knowledge_base
- Work continuity: "continue where we left off", "what was I working on" → load_kos_context  
- Thread management: "show active threads", "load project context" → load_kos_context
- Cross-domain synthesis: "how does X relate to Y", "connect A with B" → synthesize_kb_information

Direct responses (NO tools needed) for general queries:
- General knowledge: "What's the capital of France?" → "Paris"
- Math: "What is 2+2?" → "4"
- Explanations: "How does photosynthesis work?" → Direct explanation
- Opinions: "What do you think about AI?" → Direct discussion

Respond DIRECTLY (without tools) for:
- Greetings and casual conversation ("Hello", "How are you?", "Thank you")
- Simple arithmetic and math ("What is 2+2?", "Calculate 5*3")
- General knowledge questions ("What's the capital of France?", "Who invented the telephone?")
- Explanations and teaching ("Explain quantum computing", "How does photosynthesis work?")
- Opinions, advice, and discussions ("What do you think about...", "Should I...")
- Creative tasks ("Tell me a joke", "Write a poem", "Create a story")
- Questions about yourself ("What's your name?", "What can you do?")
- Hypotheticals and theoretical questions ("What if...", "Imagine...")

Use tools ONLY when the user explicitly asks for:
- File system operations: "read file X", "create file Y", "list files in directory Z", "what files are in..."
  → use_mcp_agent
- Knowledge base operations are handled directly with KB tools (search_knowledge_base, read_kb_file, etc.)
- Asset generation: "generate an image of...", "create a 3D model of...", "make audio of..."
  → use_asset_service
- Web searches: "search the web for...", "find online information about...", "what's the latest news on..."
  → use_mcp_agent
- System commands: "run command X", "execute script Y", "what's the current time/date"
  → use_mcp_agent
- Complex analysis requiring multiple perspectives: "analyze this from technical, business, and legal angles"
  → use_multiagent_orchestration

Key principles:
1. If you can answer the question with your knowledge, respond directly
2. Only use tools when the user explicitly asks for an external action
3. "What is X?" or "Explain Y" are knowledge questions - answer directly
4. "Find X in my files/KB" or "Search for X online" require tools
5. When uncertain, prefer direct responses - tools add latency"""
    
    async def build_context(self, auth: dict, additional_context: Optional[dict] = None) -> dict:
        """
        Build context for routing decision.
        """
        context = {
            "user_id": auth.get("sub") or auth.get("key", "unknown"),
            "conversation_id": additional_context.get("conversation_id", "new") if additional_context else "new",
            "message_count": additional_context.get("message_count", 0) if additional_context else 0,
            "timestamp": int(time.time())
        }
        
        # Add any additional context
        if additional_context:
            context.update(additional_context)
        
        return context
    
    def _update_timing_metrics(self, routing_time_ms: float, total_time_ms: float):
        """Update rolling average timing metrics"""
        total = self._routing_metrics["total_requests"]
        
        # Update routing time average
        avg_routing = self._routing_metrics["avg_routing_time_ms"]
        self._routing_metrics["avg_routing_time_ms"] = (
            (avg_routing * (total - 1) + routing_time_ms) / total
        )
        
        # Update total time average
        avg_total = self._routing_metrics["avg_total_time_ms"]
        self._routing_metrics["avg_total_time_ms"] = (
            (avg_total * (total - 1) + total_time_ms) / total
        )
    
    def get_metrics(self) -> dict:
        """Get routing metrics for monitoring"""
        total = self._routing_metrics["total_requests"]
        if total == 0:
            return self._routing_metrics
            
        return {
            **self._routing_metrics,
            "distribution": {
                RouteType.DIRECT: f"{(self._routing_metrics[RouteType.DIRECT] / total * 100):.1f}%",
                RouteType.MCP_AGENT: f"{(self._routing_metrics[RouteType.MCP_AGENT] / total * 100):.1f}%",
                RouteType.MULTIAGENT: f"{(self._routing_metrics[RouteType.MULTIAGENT] / total * 100):.1f}%"
            }
        }


# Global instance
unified_chat_handler = UnifiedChatHandler()