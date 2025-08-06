"""
Hot-Loaded Lightweight Chat with mcp-agent

TODO: This is Tech Debt, remove
Keeps mcp-agent initialized and ready to minimize per-request overhead.
"""
from typing import Dict, Any, List, Optional
from fastapi import Depends, HTTPException
import logging
import time
import asyncio
from contextlib import asynccontextmanager

from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm import RequestParams

from app.shared.security import get_current_auth_legacy as get_current_auth
from app.models.chat import ChatRequest, Message

logger = logging.getLogger(__name__)


class HotLoadedChatService:
    """
    Hot-loaded chat service that keeps mcp-agent initialized.
    
    Minimizes per-request overhead by maintaining:
    - MCPApp context
    - Agent instances
    - LLM connections
    """
    
    def __init__(self):
        self.app = MCPApp(name="gaia_hot_chat")
        self.chat_histories: Dict[str, List[Message]] = {}
        self._initialized = False
        self._agents: Dict[str, Agent] = {}  # Cache agents by user
        self._mcp_context = None
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize MCPApp context once and keep it hot"""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:  # Double-check
                return
                
            logger.info("🔥 Initializing hot-loaded mcp-agent...")
            start_time = time.time()
            
            # Start MCPApp context and keep it running
            self._mcp_context = self.app.run()
            await self._mcp_context.__aenter__()
            
            init_time = time.time() - start_time
            logger.info(f"✅ Hot-loaded mcp-agent ready in {init_time:.2f}s")
            self._initialized = True
    
    async def get_or_create_agent(self, user_id: str, persona: Optional[str] = None) -> Agent:
        """Get cached agent or create new one for user"""
        agent_key = f"{user_id}:{persona or 'default'}"
        
        if agent_key not in self._agents:
            # Create agent with user-specific context
            instruction = """You are a helpful AI assistant integrated with Gaia platform.
            Maintain a conversational tone and be helpful, accurate, and concise."""
            
            if persona:
                instruction += f"\nAdopt the personality of: {persona}"
            
            agent = Agent(
                name=f"gaia_chat_{user_id[:8]}",
                instruction=instruction,
                server_names=[]  # No MCP servers for speed
            )
            
            # Initialize agent
            await agent.__aenter__()
            
            # Attach LLM (reused across requests)
            llm = await agent.attach_llm(AnthropicAugmentedLLM)
            
            # Store both agent and LLM reference
            self._agents[agent_key] = (agent, llm)
            logger.debug(f"Created new agent for {agent_key}")
        
        return self._agents[agent_key]
    
    async def process_chat(
        self,
        request: ChatRequest,
        auth_principal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process chat with hot-loaded mcp-agent.
        
        Much faster than creating new context each time.
        """
        # Ensure initialized
        await self.initialize()
        
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
        if not auth_key:
            raise HTTPException(status_code=401, detail="Invalid auth")
        
        # Initialize chat history if needed
        if auth_key not in self.chat_histories:
            self.chat_histories[auth_key] = []
            logger.debug(f"Initialized chat history for user: {auth_key}")
        
        # Get or create agent for this user
        agent, llm = await self.get_or_create_agent(
            auth_key, 
            request.persona if hasattr(request, 'persona') else None
        )
        
        # Build conversation context
        context_messages = []
        for msg in self.chat_histories[auth_key][-10:]:  # Last 10 messages
            context_messages.append(f"{msg.role}: {msg.content}")
        
        # Add current message
        full_prompt = ""
        if context_messages:
            full_prompt = "Previous conversation:\n" + "\n".join(context_messages) + "\n\n"
        full_prompt += f"User: {request.message}"
        
        # Generate response (agent and LLM already initialized)
        start_time = time.time()
        response = await llm.generate_str(
            message=full_prompt,
            request_params=RequestParams(
                model=request.model or "claude-3-5-sonnet-20241022",
                temperature=0.7,
                max_tokens=2000
            )
        )
        
        response_time = time.time() - start_time
        
        # Update history
        self.chat_histories[auth_key].extend([
            Message(role="user", content=request.message),
            Message(role="assistant", content=response)
        ])
        
        # Keep history manageable
        if len(self.chat_histories[auth_key]) > 50:
            self.chat_histories[auth_key] = self.chat_histories[auth_key][-50:]
        
        # Return Gaia-compatible response
        return {
            "id": f"chat-{auth_key}-{len(self.chat_histories[auth_key])}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model or "claude-3-5-sonnet-20241022",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(full_prompt.split()),
                "completion_tokens": len(response.split()),
                "total_tokens": len(full_prompt.split()) + len(response.split())
            },
            "_response_time_ms": int(response_time * 1000),
            "_hot_loaded": True
        }
    
    async def cleanup(self):
        """Cleanup when service shuts down"""
        if self._initialized:
            logger.info("🛑 Shutting down hot-loaded mcp-agent...")
            
            # Clean up agents
            for agent, llm in self._agents.values():
                await agent.__aexit__(None, None, None)
            
            # Clean up MCPApp context
            if self._mcp_context:
                await self._mcp_context.__aexit__(None, None, None)
            
            self._initialized = False
            self._agents.clear()


# Global instance - stays hot across requests
hot_chat_service = HotLoadedChatService()


# FastAPI endpoint
async def hot_lightweight_chat_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Hot-loaded lightweight chat endpoint.
    
    After first request, subsequent requests should be much faster.
    """
    try:
        return await hot_chat_service.process_chat(request, auth_principal)
    except Exception as e:
        logger.error(f"Hot lightweight chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Cleanup hook for graceful shutdown
async def shutdown_hot_chat():
    """Call this on app shutdown"""
    await hot_chat_service.cleanup()