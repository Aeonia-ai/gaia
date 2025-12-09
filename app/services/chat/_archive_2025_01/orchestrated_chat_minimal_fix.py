"""
Minimal fix for orchestrated_chat.py - just the process_chat method
"""

async def process_chat(
    self,
    request: Dict[str, Any],
    auth_principal: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process chat request with intelligent routing
    
    FIXED: Now accepts standard format {"message": "..."} instead of {"messages": [...]}
    """
    start_time = time.time()
    self.metrics["total_requests"] += 1
    
    try:
        # FIX: Extract message from standard format
        message = request.get("message")
        if not message:
            raise HTTPException(status_code=400, detail="No message provided")
        
        # Convert to messages array for internal use
        # (In future, could get history from Redis here)
        messages = [{"role": "user", "content": message}]
        
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
            # For complex orchestration, pass the original message
            response = await self._handle_orchestrated(message, messages)
            self.metrics["orchestrated"] += 1
            
        else:
            # Fallback to direct LLM
            response = await self._handle_direct_llm(messages)
            self.metrics["direct_llm"] += 1
        
        # Track performance
        execution_time = time.time() - start_time
        self._update_avg_response_time(execution_time)
        
        # FIX: Return standard format matching other endpoints
        return {
            "response": response.get("content", ""),
            "model": response.get("model", "claude-sonnet-4-5"),
            "usage": response.get("usage", {}),
            "_metadata": {
                "route": route,
                "execution_time_ms": int(execution_time * 1000),
                "type": response.get("type", "unknown")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))