"""
Lightweight Chat with Existing Database Memory

Integrates mcp-agent lightweight chat with Gaia's existing
database conversation store.
"""
from typing import Dict, Any, List, Optional
from fastapi import Depends, HTTPException
import logging

from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm import RequestParams

from app.shared.security import get_current_auth_legacy as get_current_auth
from app.models.chat import ChatRequest, Message
from app.services.web.utils.database_conversation_store import database_conversation_store

logger = logging.getLogger(__name__)


class LightweightChatWithDB:
    """
    Lightweight chat service using mcp-agent with Gaia's existing database memory.
    
    Combines:
    - mcp-agent's lightweight agents (no MCP overhead)
    - Gaia's existing PostgreSQL conversation storage
    """
    
    def __init__(self):
        self.app = MCPApp(name="gaia_lightweight_chat_db")
        self.db_store = database_conversation_store
        
    async def create_chat_agent(self, user_context: Optional[Dict[str, Any]] = None) -> Agent:
        """Create a lightweight chat agent with no MCP servers"""
        
        instruction = """You are a helpful AI assistant integrated with Gaia platform.
        Maintain a conversational tone and be helpful, accurate, and concise."""
        
        if user_context and user_context.get("persona"):
            instruction += f"\nAdopt the personality of: {user_context['persona']}"
        
        # No server_names = no MCP overhead!
        agent = Agent(
            name="gaia_chat",
            instruction=instruction,
            server_names=[]  # Lightweight - no MCP servers
        )
        
        return agent
    
    async def process_chat_with_db(
        self,
        request: ChatRequest,
        auth_principal: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat request using lightweight mcp-agent with database memory.
        """
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
        if not auth_key:
            raise HTTPException(status_code=401, detail="Invalid auth")
        
        async with self.app.run() as mcp_app:
            # Get or create conversation
            if not conversation_id:
                # Create new conversation
                conv = self.db_store.create_conversation(
                    user_id=auth_key,
                    title="Chat Session"
                )
                conversation_id = conv["id"]
                logger.info(f"Created new conversation {conversation_id}")
            else:
                # Verify user owns this conversation
                conv = self.db_store.get_conversation(auth_key, conversation_id)
                if not conv:
                    raise HTTPException(status_code=404, detail="Conversation not found")
            
            # Get conversation history from database
            db_messages = self.db_store.get_messages(conversation_id)
            
            # Build context from database history
            context_messages = []
            for msg in db_messages[-10:]:  # Last 10 messages for context
                if msg['role'] in ['user', 'assistant']:
                    context_messages.append(f"{msg['role']}: {msg['content']}")
            
            # Create agent with user context
            user_context = {
                "user_id": auth_key,
                "persona": request.persona_id if hasattr(request, 'persona_id') else None,
                "conversation_id": conversation_id
            }
            agent = await self.create_chat_agent(user_context)
            
            async with agent:
                # Select LLM based on provider preference
                if request.provider and request.provider.lower() == "openai":
                    llm = await agent.attach_llm(OpenAIAugmentedLLM)
                else:
                    llm = await agent.attach_llm(AnthropicAugmentedLLM)
                
                # Build full prompt with history
                full_prompt = ""
                if context_messages:
                    full_prompt = "Previous conversation:\n" + "\n".join(context_messages) + "\n\n"
                full_prompt += f"User: {request.message}"
                
                # Generate response
                response = await llm.generate_str(
                    message=full_prompt,
                    request_params=RequestParams(
                        model=request.model or "claude-3-5-sonnet-20241022",
                        temperature=0.7,
                        max_tokens=2000
                    )
                )
                
                # Save messages to database
                # Add user message
                self.db_store.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=request.message,
                    model=request.model,
                    provider=request.provider
                )
                
                # Add assistant response
                self.db_store.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response,
                    model=request.model or "claude-3-5-sonnet-20241022",
                    provider=request.provider or "anthropic"
                )
                
                # Update conversation preview
                self.db_store.update_conversation(
                    user_id=auth_key,
                    conversation_id=conversation_id,
                    preview=response[:100] + "..." if len(response) > 100 else response
                )
                
                logger.info(f"Processed chat for conversation {conversation_id}")
                
                # Return response in Gaia-compatible format
                return {
                    "id": f"chat-{conversation_id}-{len(db_messages)+2}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": request.model or "claude-3-5-sonnet-20241022",
                    "conversation_id": conversation_id,
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
    
    async def get_user_conversations(self, auth_principal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
        if not auth_key:
            raise HTTPException(status_code=401, detail="Invalid auth")
        
        return self.db_store.get_conversations(auth_key)
    
    async def search_conversations(self, auth_principal: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Search user's conversations"""
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
        if not auth_key:
            raise HTTPException(status_code=401, detail="Invalid auth")
        
        return self.db_store.search_conversations(auth_key, query)


# Global instance
lightweight_chat_db_service = LightweightChatWithDB()


# FastAPI endpoints
import time

async def lightweight_chat_db_endpoint(
    request: ChatRequest,
    conversation_id: Optional[str] = None,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Lightweight chat endpoint with database memory.
    
    Features:
    - No MCP overhead
    - Full conversation history in PostgreSQL
    - Compatible with existing Gaia database schema
    """
    try:
        return await lightweight_chat_db_service.process_chat_with_db(
            request, 
            auth_principal,
            conversation_id
        )
    except Exception as e:
        logger.error(f"Lightweight chat DB error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def get_conversations_endpoint(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Get all conversations for the authenticated user"""
    return await lightweight_chat_db_service.get_user_conversations(auth_principal)


async def search_conversations_endpoint(
    query: str,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Search conversations"""
    return await lightweight_chat_db_service.search_conversations(auth_principal, query)


# Add to chat router:
"""
from .lightweight_chat_db import (
    lightweight_chat_db_endpoint,
    get_conversations_endpoint,
    search_conversations_endpoint
)

@router.post("/lightweight-db")
async def lightweight_chat_with_db(
    request: ChatRequest,
    conversation_id: Optional[str] = Query(None),
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    return await lightweight_chat_db_endpoint(request, conversation_id, auth_principal)

@router.get("/conversations")
async def get_conversations(auth_principal: Dict[str, Any] = Depends(get_current_auth)):
    return await get_conversations_endpoint(auth_principal)

@router.get("/conversations/search")
async def search_conversations(
    q: str = Query(..., description="Search query"),
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    return await search_conversations_endpoint(q, auth_principal)
"""