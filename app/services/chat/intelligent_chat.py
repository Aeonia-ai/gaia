"""
Intelligent Chat Service with Smart Routing

Automatically routes messages to the optimal endpoint based on complexity analysis.
Provides fast responses for simple dialog while maintaining sophisticated capabilities
for complex requests.
"""
import logging
import time
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import json

from app.models.chat import ChatRequest
from app.shared.security import get_current_auth_legacy as get_current_auth
from .intelligent_router import intelligent_router, ChatComplexity

# Import direct handlers for fast path
from .lightweight_chat_simple import simple_lightweight_chat_endpoint
from .lightweight_chat_hot import hot_lightweight_chat_endpoint
from .multiagent_orchestrator import multiagent_orchestrator_endpoint

logger = logging.getLogger(__name__)


class IntelligentChatService:
    """
    Intelligent chat service that automatically routes to the best handler.
    
    Features:
    - LLM-powered routing decision in ~200ms
    - Fast path for simple dialog (~1s total)
    - Medium path for tool usage (~2-3s total)
    - Full orchestration for complex tasks (~3-5s total)
    """
    
    def __init__(self):
        self._metrics = {
            "total_requests": 0,
            "routing_decisions": {"simple": 0, "moderate": 0, "complex": 0},
            "avg_total_time_ms": 0,
            "errors": 0
        }
    
    async def process_intelligent_chat(
        self,
        request: ChatRequest,
        auth_principal: Dict[str, Any],
        always_route: bool = False
    ) -> Any:
        """
        Process chat with intelligent routing.
        
        1. Quick classification (pattern match: <1ms, LLM: ~200ms)
        2. Route to optimal endpoint
        3. Return response with routing metadata
        
        Args:
            always_route: If False (default), may bypass routing for obvious simple messages
        """
        start_time = time.time()
        self._metrics["total_requests"] += 1
        
        try:
            # Get user context for better routing decisions
            auth_key = auth_principal.get("sub") or auth_principal.get("key")
            context = {
                "user_id": auth_key,
                "has_conversation_history": hasattr(request, "conversation_id"),
                "requested_model": request.model
            }
            
            # Classify the message
            logger.info(f"Classifying message for intelligent routing: {request.message[:100]}...")
            classification = await intelligent_router.classify_message(
                request.message,
                context
            )
            
            complexity = classification["complexity"]
            endpoint = classification["suggested_endpoint"]
            
            # Update metrics
            self._metrics["routing_decisions"][complexity.value] += 1
            
            logger.info(
                f"Routing to {endpoint} (complexity: {complexity.value}, "
                f"estimated time: {classification['estimated_response_time']})"
            )
            
            # Check if we already have a complete response from classification
            if classification.get("is_complete", False):
                # Ultra-fast path - LLM already provided the response during classification!
                # No additional endpoint call needed
                logger.info("Using ultra-fast direct response from classification")
                
                response = {
                    "id": f"chat-{auth_key}-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": classification.get("model_used", "claude-3-haiku-20240307"),
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": classification.get("direct_response", "")
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": len(request.message.split()),
                        "completion_tokens": len(classification.get("direct_response", "").split()),
                        "total_tokens": len(request.message.split()) + len(classification.get("direct_response", "").split())
                    }
                }
            
            elif endpoint == "/chat/direct":
                # Fast path - direct to LLM
                response = await simple_lightweight_chat_endpoint(request, auth_principal)
            
            elif endpoint == "/chat/mcp-agent-hot":
                # Medium path - hot-loaded agent for tool usage
                response = await hot_lightweight_chat_endpoint(request, auth_principal)
            
            elif endpoint == "/chat/mcp-agent":
                # Complex path - full multiagent orchestration
                # Determine scenario type from domains
                scenario_type = self._determine_scenario_type(classification.get("domains", []))
                response = await multiagent_orchestrator_endpoint(
                    request, 
                    scenario_type,
                    auth_principal
                )
            
            else:
                # Fallback to direct
                response = await simple_lightweight_chat_endpoint(request, auth_principal)
            
            # Add routing metadata to response
            total_time = (time.time() - start_time) * 1000
            
            # Update average time
            avg = self._metrics["avg_total_time_ms"]
            total_reqs = self._metrics["total_requests"]
            self._metrics["avg_total_time_ms"] = (
                (avg * (total_reqs - 1) + total_time) / total_reqs
            )
            
            # Enhance response with routing info
            if isinstance(response, dict):
                response["_intelligent_routing"] = {
                    "complexity": complexity.value,
                    "endpoint_used": endpoint,
                    "classification_time_ms": classification.get("classification_time_ms", 0),
                    "total_time_ms": int(total_time),
                    "reasoning": classification.get("reasoning", ""),
                    "domains": classification.get("domains", [])
                }
            
            return response
            
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Intelligent chat error: {e}", exc_info=True)
            
            # Fallback to simple endpoint on error
            try:
                logger.info("Falling back to simple endpoint after error")
                return await simple_lightweight_chat_endpoint(request, auth_principal)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _determine_scenario_type(self, domains: list) -> str:
        """Map domains to multiagent scenario types"""
        
        # Check domains for scenario indicators
        domain_text = " ".join(domains).lower()
        
        if any(word in domain_text for word in ["game", "npc", "character", "tavern"]):
            return "gamemaster"
        elif any(word in domain_text for word in ["world", "geography", "culture", "history"]):
            return "worldbuilding"
        elif any(word in domain_text for word in ["story", "narrative", "perspective"]):
            return "storytelling"
        elif any(word in domain_text for word in ["technical", "design", "problem", "solution"]):
            return "problemsolving"
        else:
            return "auto"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        total = self._metrics["total_requests"]
        if total == 0:
            return self._metrics
            
        return {
            **self._metrics,
            "routing_distribution": {
                "simple": f"{(self._metrics['routing_decisions']['simple'] / total * 100):.1f}%",
                "moderate": f"{(self._metrics['routing_decisions']['moderate'] / total * 100):.1f}%",
                "complex": f"{(self._metrics['routing_decisions']['complex'] / total * 100):.1f}%"
            },
            "error_rate": f"{(self._metrics['errors'] / total * 100):.1f}%"
        }


# Global service instance
intelligent_chat_service = IntelligentChatService()


# FastAPI endpoint
async def intelligent_chat_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Intelligent chat endpoint with automatic routing.
    
    This endpoint automatically determines the best processing path:
    - Simple dialog → Direct LLM (~1s)
    - Tool usage needed → Hot MCP agent (~2-3s)  
    - Complex orchestration → Full multiagent (~3-5s)
    
    The routing decision adds only ~200ms overhead but ensures
    optimal response times for all types of requests.
    """
    return await intelligent_chat_service.process_intelligent_chat(request, auth_principal)


async def intelligent_chat_metrics_endpoint(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Get metrics for intelligent chat routing"""
    return {
        "router_metrics": intelligent_router.get_metrics(),
        "service_metrics": intelligent_chat_service.get_metrics()
    }