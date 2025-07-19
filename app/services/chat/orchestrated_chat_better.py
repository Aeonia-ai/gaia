"""
Better Orchestrated Chat Service - Routes to existing endpoints

This version doesn't reimplement anything - it just intelligently 
routes to the existing endpoints that already have Redis, history, etc.
"""
import time
from typing import Dict, Any, Optional
import logging

from fastapi import HTTPException
from app.services.chat.semantic_mcp_router import HybridRouter

logger = logging.getLogger(__name__)


class BetterOrchestratedChatService:
    """
    Pure routing layer - analyzes requests and forwards to appropriate endpoints
    
    No reimplementation of:
    - Redis caching (handled by ultrafast endpoints)
    - Message history (handled by direct-db endpoint)
    - MCP tools (handled by mcp-agent endpoint)
    """
    
    def __init__(self):
        self.router = HybridRouter()
        
        # Map routes to actual endpoints
        self.endpoint_map = {
            "direct_llm": {
                "fast": "/chat/ultrafast-redis-v3",  # Has Redis caching
                "standard": "/chat/direct",           # Standard direct chat
                "persistent": "/chat/direct-db"       # With DB persistence
            },
            "direct_mcp": "/chat/mcp-agent",         # Full MCP support
            "mcp_agent": "/chat/mcp-agent-hot",      # Pre-initialized
            "complex": "/chat/mcp-agent"             # Complex orchestration
        }
        
        # Performance tracking
        self.metrics = {
            "total_requests": 0,
            "route_distribution": {}
        }
    
    async def process_chat(
        self,
        request: Dict[str, Any],
        auth_principal: Dict[str, Any],
        chat_service  # Injected reference to call other endpoints
    ) -> Dict[str, Any]:
        """
        Analyze request and route to appropriate endpoint
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # Extract message
            message = request.get("message")
            if not message:
                raise HTTPException(status_code=400, detail="No message provided")
            
            # Analyze and route
            route, decision = await self.router.route(message)
            logger.info(f"Orchestrated routing: {route} (confidence: {decision.confidence})")
            
            # Determine best endpoint based on route and requirements
            if route == "direct_llm":
                # For simple queries, use ultrafast with Redis
                if decision.estimated_complexity < 3:
                    endpoint = self.endpoint_map["direct_llm"]["fast"]
                # For queries needing history, use DB-backed
                elif decision.needs_state:
                    endpoint = self.endpoint_map["direct_llm"]["persistent"]
                else:
                    endpoint = self.endpoint_map["direct_llm"]["standard"]
            
            elif route == "direct_mcp":
                # Needs specific tools
                endpoint = self.endpoint_map["direct_mcp"]
            
            elif route == "mcp_agent":
                # Complex multi-step tasks
                endpoint = self.endpoint_map["complex"]
            
            else:
                # Default fallback
                endpoint = self.endpoint_map["direct_llm"]["fast"]
            
            # Track routing
            self.metrics["route_distribution"][endpoint] = \
                self.metrics["route_distribution"].get(endpoint, 0) + 1
            
            # Call the actual endpoint!
            # This is the key - we're not reimplementing, just routing
            logger.info(f"Forwarding to endpoint: {endpoint}")
            
            # In a real implementation, this would call the endpoint
            # For now, return metadata about the routing decision
            execution_time = time.time() - start_time
            
            return {
                "response": f"Would route to {endpoint} for: {message}",
                "model": "orchestrated-router",
                "_routing": {
                    "endpoint": endpoint,
                    "route": route,
                    "confidence": decision.confidence,
                    "complexity": decision.estimated_complexity,
                    "needs_state": decision.needs_state,
                    "execution_time_ms": int(execution_time * 1000)
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get routing metrics"""
        return {
            "total_requests": self.metrics["total_requests"],
            "route_distribution": self.metrics["route_distribution"],
            "endpoints_used": list(self.metrics["route_distribution"].keys())
        }


# Example of how to properly integrate in chat.py:
"""
# In chat.py router:

@router.post("/orchestrated")
async def orchestrated_chat(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    # Analyze the request
    route_decision = await orchestrator.analyze(request.message)
    
    # Forward to appropriate endpoint based on analysis
    if route_decision.endpoint == "/chat/ultrafast-redis-v3":
        return await ultrafast_redis_v3(request, auth_principal)
    elif route_decision.endpoint == "/chat/mcp-agent":
        return await mcp_agent_chat(request, auth_principal)
    elif route_decision.endpoint == "/chat/direct-db":
        return await direct_db_chat(request, auth_principal)
    else:
        return await direct_chat(request, auth_principal)
"""