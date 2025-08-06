"""
Conversation management endpoints for the chat service.
Provides REST API for conversation CRUD operations.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.shared.security import get_current_auth_legacy
from app.shared.logging import setup_service_logger
from .conversation_store import chat_conversation_store

logger = setup_service_logger("chat_conversations")

router = APIRouter()

# Request/Response Models
class ConversationCreateRequest(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    preview: Optional[str] = None

class MessageCreateRequest(BaseModel):
    role: str
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    tokens_used: Optional[int] = None

class ConversationResponse(BaseModel):
    id: str
    title: str
    preview: str
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    tokens_used: Optional[int] = None
    created_at: str

class ConversationsListResponse(BaseModel):
    conversations: List[ConversationResponse]

class MessagesListResponse(BaseModel):
    messages: List[MessageResponse]

class ConversationStatsResponse(BaseModel):
    total_conversations: int
    total_messages: int

# Endpoints
@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: ConversationCreateRequest,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Create a new conversation"""
    try:
        user_id = auth.get("sub") or auth.get("key", "unknown")
        conversation = chat_conversation_store.create_conversation(
            user_id=user_id,
            title=request.title
        )
        logger.info(f"Created conversation {conversation['id']} for user {user_id}")
        return ConversationResponse(**conversation)
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations", response_model=ConversationsListResponse)
async def list_conversations(
    auth: dict = Depends(get_current_auth_legacy)
):
    """List all conversations for the authenticated user"""
    try:
        user_id = auth.get("sub") or auth.get("key", "unknown")
        conversations = chat_conversation_store.get_conversations(user_id)
        logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
        return ConversationsListResponse(
            conversations=[ConversationResponse(**conv) for conv in conversations]
        )
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get a specific conversation"""
    try:
        user_id = auth.get("sub") or auth.get("key", "unknown")
        conversation = chat_conversation_store.get_conversation(user_id, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        logger.info(f"Retrieved conversation {conversation_id} for user {user_id}")
        return ConversationResponse(**conversation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Update a conversation"""
    try:
        user_id = auth.get("sub") or auth.get("key", "unknown")
        success = chat_conversation_store.update_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            title=request.title,
            preview=request.preview
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get updated conversation
        conversation = chat_conversation_store.get_conversation(user_id, conversation_id)
        logger.info(f"Updated conversation {conversation_id} for user {user_id}")
        return ConversationResponse(**conversation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Delete a conversation"""
    try:
        user_id = auth.get("sub") or auth.get("key", "unknown")
        success = chat_conversation_store.delete_conversation(user_id, conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    conversation_id: str,
    request: MessageCreateRequest,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Add a message to a conversation"""
    try:
        message = chat_conversation_store.add_message(
            conversation_id=conversation_id,
            role=request.role,
            content=request.content,
            model=request.model,
            provider=request.provider,
            tokens_used=request.tokens_used
        )
        logger.info(f"Added {request.role} message to conversation {conversation_id}")
        return MessageResponse(**message)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}/messages", response_model=MessagesListResponse)
async def get_messages(
    conversation_id: str,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get all messages for a conversation"""
    try:
        messages = chat_conversation_store.get_messages(conversation_id)
        logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
        return MessagesListResponse(
            messages=[MessageResponse(**msg) for msg in messages]
        )
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/search/{query}", response_model=ConversationsListResponse)
async def search_conversations(
    query: str,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Search conversations by title or content"""
    try:
        user_id = auth.get("sub") or auth.get("key", "unknown")
        conversations = chat_conversation_store.search_conversations(user_id, query)
        logger.info(f"Found {len(conversations)} conversations matching '{query}' for user {user_id}")
        return ConversationsListResponse(
            conversations=[ConversationResponse(**conv) for conv in conversations]
        )
    except Exception as e:
        logger.error(f"Error searching conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/stats", response_model=ConversationStatsResponse)
async def get_conversation_stats(
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get conversation statistics for the authenticated user"""
    try:
        user_id = auth.get("sub") or auth.get("key", "unknown")
        stats = chat_conversation_store.get_conversation_stats(user_id)
        logger.info(f"Retrieved stats for user {user_id}: {stats}")
        return ConversationStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting conversation stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))