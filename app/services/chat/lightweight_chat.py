"""
Lightweight Chat Integration using mcp-agent

Demonstrates how to add mcp-agent's capabilities to Gaia's chat service
without MCP overhead - just pure LLM with structured responses.
"""
from typing import Dict, Any, List, Optional
from fastapi import Depends, HTTPException
import logging
import time

from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm import RequestParams

from app.shared.security import get_current_auth_legacy as get_current_auth
from app.models.chat import ChatRequest, Message

logger = logging.getLogger(__name__)


class LightweightChatService:
    """
    Lightweight chat service using mcp-agent without MCP servers.
    
    Benefits:
    - No MCP overhead
    - Direct LLM access
    - Compatible with existing Gaia auth/models
    - Easy to extend with consciousness patterns
    """
    
    def __init__(self):
        self.app = MCPApp(name="gaia_lightweight_chat")
        self.chat_histories: Dict[str, List[Message]] = {}
        self._initialized = False
        self._mcp_context = None
        
    async def create_chat_agent(self, user_context: Optional[Dict[str, Any]] = None) -> Agent:
        """Create a lightweight chat agent with no MCP servers"""
        
        # Build instruction based on user context
        instruction = """You are a helpful AI assistant integrated with Gaia platform.
        Maintain a conversational tone and be helpful, accurate, and concise."""
        
        if user_context:
            # Could customize based on user preferences, persona, etc.
            if user_context.get("persona"):
                instruction += f"\nAdopt the personality of: {user_context['persona']}"
        
        # No server_names = no MCP overhead!
        agent = Agent(
            name="gaia_chat",
            instruction=instruction,
            server_names=[]  # Lightweight - no MCP servers
        )
        
        return agent
    
    async def process_chat(
        self,
        request: ChatRequest,
        auth_principal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a chat request using lightweight mcp-agent.
        
        Compatible with Gaia's existing chat endpoint structure.
        """
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
        if not auth_key:
            raise HTTPException(status_code=401, detail="Invalid auth")
        
        async with self.app.run() as mcp_app:
            # Initialize chat history if needed
            if auth_key not in self.chat_histories:
                self.chat_histories[auth_key] = []
                logger.info(f"Initialized chat history for user: {auth_key}")
            
            # Create lightweight agent
            user_context = {
                "user_id": auth_key,
                "persona": request.persona if hasattr(request, 'persona') else None
            }
            agent = await self.create_chat_agent(user_context)
            
            async with agent:
                # Select LLM based on provider preference
                if request.provider and request.provider.lower() == "openai":
                    llm = await agent.attach_llm(OpenAIAugmentedLLM)
                else:
                    llm = await agent.attach_llm(AnthropicAugmentedLLM)
                
                # Build conversation context
                context_messages = []
                for msg in self.chat_histories[auth_key][-10:]:  # Last 10 messages
                    context_messages.append(f"{msg.role}: {msg.content}")
                
                # Add current message
                full_prompt = ""
                if context_messages:
                    full_prompt = "Previous conversation:\n" + "\n".join(context_messages) + "\n\n"
                full_prompt += f"User: {request.message}"
                
                # Generate response
                response = await llm.generate_str(
                    message=full_prompt,
                    request_params=RequestParams(
                        model=request.model or "claude-3-5-sonnet-20241022",
                        temperature=0.7,  # Default temperature
                        max_tokens=2000   # Default max tokens
                    )
                )
                
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
                    }
                }


# Global instance
lightweight_chat_service = LightweightChatService()


# FastAPI endpoint that can be added to Gaia's chat router
async def lightweight_chat_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Lightweight chat endpoint using mcp-agent without MCP overhead.
    
    Drop-in replacement for existing chat endpoints.
    """
    try:
        return await lightweight_chat_service.process_chat(request, auth_principal)
    except Exception as e:
        logger.error(f"Lightweight chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Example: Adding consciousness capabilities (no MCP needed!)
class ConsciousnessEnabledChat(LightweightChatService):
    """
    Extends lightweight chat with consciousness patterns.
    Still no MCP overhead - just intelligent agent coordination.
    """
    
    async def create_meditation_guide(self) -> Agent:
        """Create a meditation guide agent - no external tools needed"""
        
        agent = Agent(
            name="meditation_guide",
            instruction="""You are Mu, a gentle robotic meditation guide.
            Guide users through breathing exercises with 'Beep boop!' encouragement.
            Patterns: 5-sec calm, 6-sec deep relief, 3-sec energy.
            Adapt based on user feedback.""",
            server_names=[]  # No MCP needed for basic meditation
        )
        
        return agent
    
    async def process_meditation_request(
        self,
        request: ChatRequest,
        auth_principal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process meditation requests with specialized agent"""
        
        # Detect if this is a meditation request
        meditation_keywords = ['meditat', 'breath', 'calm', 'relax', 'mindful']
        is_meditation = any(kw in request.message.lower() for kw in meditation_keywords)
        
        if is_meditation:
            async with self.app.run() as mcp_app:
                agent = await self.create_meditation_guide()
                
                async with agent:
                    llm = await agent.attach_llm(AnthropicAugmentedLLM)
                    response = await llm.generate_str(request.message)
                    
                    # Return meditation-specific response
                    return {
                        "type": "meditation",
                        "content": response,
                        "agent": "mu_meditation_guide"
                    }
        else:
            # Fall back to regular chat
            return await self.process_chat(request, auth_principal)


# Usage in main chat router:
"""
# In app/services/chat/chat.py, add:

from .lightweight_chat import lightweight_chat_endpoint

@router.post("/lightweight")
async def lightweight_chat(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    return await lightweight_chat_endpoint(request, auth_principal)
"""