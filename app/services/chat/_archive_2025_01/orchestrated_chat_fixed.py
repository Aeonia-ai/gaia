"""
Orchestrated Chat Service - Fixed Version

Integrates with existing chat infrastructure for intelligent request routing
without duplicating message management or storage.
"""
import asyncio
import time
from typing import Dict, List, Any, Optional
import logging

from fastapi import HTTPException
from anthropic import Anthropic

from app.shared.config import GaiaSettings as Settings
from app.services.chat.custom_orchestration import CustomOrchestrator, SimpleOrchestrator
from app.services.chat.semantic_mcp_router import HybridRouter

logger = logging.getLogger(__name__)


class OrchestratedChatService:
    """
    Enhanced chat service with intelligent routing
    
    This version properly integrates with existing chat infrastructure:
    - Accepts standard ChatRequest format (message, not messages)
    - Can leverage existing Redis history if needed
    - Returns standard response format
    """
    
    def __init__(self, settings: Optional[Settings] = None, redis_service=None):
        self.settings = settings or Settings()
        self.anthropic = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)
        self.redis_service = redis_service  # Optional Redis integration
        
        # Initialize components
        self.router = HybridRouter()
        self.orchestrator = CustomOrchestrator(settings)
        self.simple_orchestrator = SimpleOrchestrator(settings)
        
        # Performance tracking
        self.metrics = {
            "total_requests": 0,
            "direct_llm": 0,
            "mcp_requests": 0,
            "orchestrated": 0,
            "avg_response_time": 0
        }
    
    async def process_chat(
        self,
        request: Dict[str, Any],
        auth_principal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process chat request with intelligent routing
        
        Accepts standard format: {"message": "...", ...}
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # Extract message from standard format
            message = request.get("message")
            if not message:
                raise HTTPException(status_code=400, detail="No message provided")
            
            # Optionally get conversation history from Redis
            user_id = auth_principal.get("user_id")
            conversation_id = request.get("conversation_id")
            
            # Build messages array for internal processing
            messages = []
            
            # Add history if available and needed
            if self.redis_service and user_id and conversation_id:
                try:
                    # Get recent history from Redis (last 5 messages for context)
                    history = await self.redis_service.get_chat_history(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        limit=5
                    )
                    messages.extend(history)
                except Exception as e:
                    logger.warning(f"Could not retrieve history: {e}")
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Route the request based on the message content
            route, decision = await self.router.route(message)
            logger.info(f"Routed to: {route} (confidence: {decision.confidence})")
            
            # Execute based on route
            if route == "direct_llm":
                response = await self._handle_direct_llm(messages)
                self.metrics["direct_llm"] += 1
                
            elif route == "direct_mcp":
                response = await self._handle_direct_mcp(messages, decision.required_tools)
                self.metrics["mcp_requests"] += 1
                
            elif route == "mcp_agent":
                # For complex orchestration, use full message history
                response = await self._handle_orchestrated(message, messages)
                self.metrics["orchestrated"] += 1
                
            else:
                # Fallback to direct LLM
                response = await self._handle_direct_llm(messages)
                self.metrics["direct_llm"] += 1
            
            # Track performance
            execution_time = time.time() - start_time
            self._update_avg_response_time(execution_time)
            
            # Store in Redis if available
            if self.redis_service and user_id:
                try:
                    await self.redis_service.store_message(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message=message,
                        response=response.get("content", ""),
                        metadata={"route": route, "execution_time": execution_time}
                    )
                except Exception as e:
                    logger.warning(f"Could not store in Redis: {e}")
            
            # Format response to match standard chat response
            return self._format_standard_response(response, execution_time, route)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _handle_direct_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Handle simple direct LLM requests"""
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            max_tokens=2000
        )
        
        return {
            "content": response.content[0].text,
            "type": "direct_llm",
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }
    
    async def _handle_direct_mcp(
        self,
        messages: List[Dict[str, str]],
        required_tools: List[str]
    ) -> Dict[str, Any]:
        """Handle requests that need specific MCP tools"""
        # This would integrate with the MCP system
        # For now, simulate tool usage
        
        tool_descriptions = self._get_tool_descriptions(required_tools)
        
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            tools=tool_descriptions,
            max_tokens=2000
        )
        
        # Process tool calls if any
        tool_results = []
        final_content = ""
        
        for content in response.content:
            if content.type == "text":
                final_content += content.text
            elif content.type == "tool_use":
                # Would execute actual MCP tool here
                tool_results.append({
                    "tool": content.name,
                    "result": f"Simulated result for {content.name}"
                })
        
        return {
            "content": final_content,
            "type": "direct_mcp",
            "model": response.model,
            "tools_used": [t["tool"] for t in tool_results],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }
    
    async def _handle_orchestrated(
        self,
        latest_message: str,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Handle complex multi-agent orchestration"""
        # Use the orchestrator for complex workflows
        result = await self.orchestrator.orchestrate(
            task=latest_message,
            context={"messages": messages}
        )
        
        return {
            "content": result.get("response", ""),
            "type": "orchestrated",
            "model": "multi-agent",
            "agents_used": result.get("agents_used", []),
            "steps": result.get("steps", [])
        }
    
    def _format_standard_response(
        self,
        response: Dict[str, Any],
        execution_time: float,
        route: str
    ) -> Dict[str, Any]:
        """Format response to match standard chat endpoint format"""
        return {
            "response": response.get("content", ""),
            "model": response.get("model", "claude-3-5-sonnet-20241022"),
            "usage": response.get("usage", {}),
            "_metadata": {
                "route": route,
                "execution_time_ms": int(execution_time * 1000),
                "type": response.get("type", "unknown"),
                "tools_used": response.get("tools_used", []),
                "agents_used": response.get("agents_used", [])
            }
        }
    
    def _get_tool_descriptions(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        """Get tool descriptions for specified tools"""
        # This would fetch actual tool descriptions from MCP
        # For now, return mock descriptions
        tool_map = {
            "filesystem": {
                "name": "filesystem",
                "description": "Read and write files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "path": {"type": "string"}
                    }
                }
            },
            "github": {
                "name": "github",
                "description": "Interact with GitHub",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "repo": {"type": "string"}
                    }
                }
            }
        }
        
        return [tool_map.get(name, {}) for name in tool_names if name in tool_map]
    
    def _update_avg_response_time(self, execution_time: float):
        """Update average response time metric"""
        total = sum(self.metrics[k] for k in ["direct_llm", "mcp_requests", "orchestrated"])
        if total > 0:
            current_avg = self.metrics["avg_response_time"]
            self.metrics["avg_response_time"] = (
                (current_avg * (total - 1) + execution_time) / total
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            **self.metrics,
            "avg_response_time_ms": int(self.metrics["avg_response_time"] * 1000)
        }