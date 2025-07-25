"""
Unified Intelligent Chat Handler

A single endpoint that uses LLM tool-calling to intelligently route requests:
- Direct responses for simple queries (no tools)
- MCP agent for tool-requiring tasks
- Multi-agent orchestration for complex analysis
"""
import logging
import time
import uuid
import json
from typing import Dict, Any, Optional, List
from enum import Enum

from app.services.llm.chat_service import chat_service
from app.services.chat.lightweight_chat_hot import hot_chat_service
from app.services.llm import LLMProvider
import httpx
from app.shared.config import settings

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
        
        # Routing tools definition
        self.routing_tools = [
            {
                "type": "function",
                "function": {
                    "name": "use_mcp_agent",
                    "description": "Use this when the user's request requires external tools such as: reading/writing files, web search, API calls, calculations, system operations, or any interaction beyond conversation",
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
                    "name": "use_kb_service",
                    "description": "Use this when the user wants to search, access, or manage their knowledge base, personal notes, documents, or any content in their KB",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "What to search for or access in the KB"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why KB service is needed"
                            }
                        },
                        "required": ["query", "reasoning"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "use_asset_service", 
                    "description": "Use this when the user wants to generate images, 3D models, audio, or other digital assets",
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
        
        # Single LLM call for routing decision
        routing_start = time.time()
        
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
            
            # Use chat service with routing tools
            routing_response = await chat_service.chat_completion(
                messages=messages,
                tools=self.routing_tools,
                tool_choice={"type": "auto"},  # Let LLM decide: direct response or tool use
                temperature=0.7,
                max_tokens=4096,
                request_id=f"{request_id}-routing"
            )
            
            routing_time = (time.time() - routing_start) * 1000
            
            # Check if LLM made tool calls
            if routing_response.get("tool_calls"):
                # LLM decided to use specialized routing
                tool_call = routing_response["tool_calls"][0]
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
                    result["_metadata"] = {
                        "route_type": route_type,
                        "routing_time_ms": int(routing_time),
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "reasoning": tool_args.get("reasoning"),
                        "request_id": request_id
                    }
                    
                    return result
                
                elif tool_name == "use_kb_service":
                    # Route to KB service
                    route_type = RouteType.MCP_AGENT  # For now, use MCP agent for KB
                    self._routing_metrics[route_type] += 1
                    
                    query = tool_args.get("query", message)
                    reasoning = tool_args.get("reasoning", "")
                    
                    logger.info(
                        f"[{request_id}] Routing to KB service - query: {query}, reason: {reasoning}"
                    )
                    
                    # For now, use MCP agent to handle KB queries
                    # TODO: Implement direct KB service integration
                    from app.models.chat import ChatRequest
                    kb_message = f"Search my knowledge base for: {query}"
                    chat_request = ChatRequest(message=kb_message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Add routing metadata
                    result["_metadata"] = {
                        "route_type": "kb_service",
                        "routing_time_ms": int(routing_time),
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "query": query,
                        "reasoning": reasoning,
                        "request_id": request_id,
                        "note": "Using MCP agent for KB queries"
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
                        "routing_time_ms": int(routing_time),
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
                        "routing_time_ms": int(routing_time),
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
                        "routing_time_ms": int(routing_time),
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "request_id": request_id,
                        "error": f"Unknown tool: {tool_name}, used fallback"
                    }
                    
                    return result
            
            else:
                # Direct response - no specialized tools needed
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
                    f"[{request_id}] Direct response in {routing_time:.0f}ms"
                )
                
                # Update routing metrics
                self._update_timing_metrics(routing_time, (time.time() - start_time) * 1000)
                
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
                        "routing_time_ms": int(routing_time),
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
    
    def get_routing_prompt(self, context: dict) -> str:
        """
        System prompt that helps LLM make routing decisions.
        """
        return f"""You are an intelligent assistant that can either respond directly or use specialized tools when needed.

Current context:
- User: {context.get('user_id', 'unknown')}
- Conversation: {context.get('conversation_id', 'new')}
- Message count: {context.get('message_count', 0)}

Respond directly for:
- Greetings, casual conversation
- Simple questions with straightforward answers
- Clarifications or follow-ups to previous messages
- General knowledge queries
- Opinions, explanations, or discussions

Use tools only when the request explicitly requires:
- File operations or code analysis (use_mcp_agent)
- Web searches or API calls (use_mcp_agent)
- System operations or external integrations (use_mcp_agent)
- Complex multi-domain analysis (use_multiagent_orchestration)
- Coordinated expert reasoning (use_multiagent_orchestration)

When in doubt, prefer direct responses. Tools add latency and should only be used when truly beneficial."""
    
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