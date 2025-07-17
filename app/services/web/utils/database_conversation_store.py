"""
Database-backed conversation store for persistent chat history.
Replaces the in-memory conversation_store with PostgreSQL persistence.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.shared.database import get_database_session
from app.models.database import User, Conversation, ChatMessage
from app.shared.logging import setup_service_logger
import uuid
from datetime import datetime

logger = setup_service_logger("database_conversation_store")

class DatabaseConversationStore:
    """Database-backed conversation storage using PostgreSQL"""
    
    def __init__(self):
        logger.info("Initialized DatabaseConversationStore")
    
    def _get_db_session(self):
        """Get database session context manager"""
        from app.shared.database import SessionLocal
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def _get_db(self) -> Session:
        """Get database session"""
        from app.shared.database import SessionLocal
        return SessionLocal()
    
    def _get_or_create_user(self, user_id: str) -> User:
        """Get or create user by ID"""
        db = self._get_db()
        try:
            # Handle dev user special case - always use the existing dev user
            if user_id == "dev-user-id":
                user = db.query(User).filter(User.email == "dev@gaia.local").first()
                if user:
                    return user
                # If dev user doesn't exist, create it with a proper UUID
                user = User(
                    email="dev@gaia.local",
                    name="Local Development User"
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"Created dev user: {user.id}")
                return user
            
            # For other users, try to parse as UUID
            try:
                # Try to get user by UUID
                user_uuid = uuid.UUID(user_id)
                user = db.query(User).filter(User.id == user_uuid).first()
                if user:
                    return user
            except ValueError:
                # user_id is not a valid UUID, treat as email
                user = db.query(User).filter(User.email == user_id).first()
                if user:
                    return user
            
            # Create new user if not found - with duplicate handling
            try:
                if "@" in user_id:
                    # user_id looks like an email
                    user = User(email=user_id, name="User")
                else:
                    # Create with generated email
                    user = User(email=f"{user_id}@gaia.local", name="User")
                
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"Created new user: {user.id}")
                return user
            except Exception as e:
                # If creation fails (likely duplicate), try to find existing user
                db.rollback()
                logger.warning(f"User creation failed, trying to find existing: {e}")
                
                if "@" in user_id:
                    user = db.query(User).filter(User.email == user_id).first()
                else:
                    user = db.query(User).filter(User.email == f"{user_id}@gaia.local").first()
                
                if user:
                    logger.info(f"Found existing user: {user.id}")
                    return user
                else:
                    logger.error(f"Could not find or create user for {user_id}")
                    raise e
        finally:
            db.close()
    
    def create_conversation(self, user_id: str, title: str = "New Conversation") -> Dict[str, Any]:
        """Create a new conversation"""
        db = self._get_db()
        try:
            user = self._get_or_create_user(user_id)
            
            conversation = Conversation(
                user_id=user.id,
                title=title,
                preview="",
                is_active=True
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            logger.info(f"Created conversation {conversation.id} for user {user_id}")
            
            return {
                "id": str(conversation.id),
                "title": conversation.title,
                "preview": conversation.preview or "",
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat()
            }
        finally:
            db.close()
    
    def get_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        db = self._get_db()
        try:
            user = self._get_or_create_user(user_id)
            
            conversations = db.query(Conversation).filter(
                Conversation.user_id == user.id,
                Conversation.is_active == True
            ).order_by(desc(Conversation.updated_at)).all()
            
            result = []
            for conv in conversations:
                result.append({
                    "id": str(conv.id),
                    "title": conv.title,
                    "preview": conv.preview or "",
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                })
            
            logger.info(f"Retrieved {len(result)} conversations for user {user_id}")
            return result
        finally:
            db.close()
    
    def get_conversation(self, user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific conversation"""
        db = self._get_db()
        try:
            user = self._get_or_create_user(user_id)
            
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
                Conversation.is_active == True
            ).first()
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
                return None
            
            return {
                "id": str(conversation.id),
                "title": conversation.title,
                "preview": conversation.preview or "",
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat()
            }
        finally:
            db.close()
    
    def update_conversation(self, user_id: str, conversation_id: str, 
                          title: Optional[str] = None, preview: Optional[str] = None) -> bool:
        """Update conversation metadata"""
        db = self._get_db()
        try:
            user = self._get_or_create_user(user_id)
            
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id
            ).first()
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for update")
                return False
            
            if title is not None:
                conversation.title = title
            if preview is not None:
                conversation.preview = preview
            
            conversation.updated_at = func.current_timestamp()
            db.commit()
            
            logger.info(f"Updated conversation {conversation_id}")
            return True
        finally:
            db.close()
    
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Delete a conversation (soft delete)"""
        db = self._get_db()
        try:
            user = self._get_or_create_user(user_id)
            
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id
            ).first()
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for deletion")
                return False
            
            conversation.is_active = False
            conversation.updated_at = func.current_timestamp()
            db.commit()
            
            logger.info(f"Deleted conversation {conversation_id}")
            return True
        finally:
            db.close()
    
    def add_message(self, conversation_id: str, role: str, content: str, 
                   model: Optional[str] = None, provider: Optional[str] = None,
                   tokens_used: Optional[int] = None) -> Dict[str, Any]:
        """Add a message to a conversation"""
        db = self._get_db()
        try:
            # Get conversation to determine user_id
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.is_active == True
            ).first()
            
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            message = ChatMessage(
                user_id=conversation.user_id,
                conversation_id=conversation.id,
                role=role,
                content=content,
                model=model,
                provider=provider,
                tokens_used=tokens_used
            )
            db.add(message)
            
            # Update conversation timestamp
            conversation.updated_at = func.current_timestamp()
            
            db.commit()
            db.refresh(message)
            
            logger.info(f"Added {role} message to conversation {conversation_id}")
            
            return {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "model": message.model,
                "provider": message.provider,
                "tokens_used": message.tokens_used,
                "created_at": message.created_at.isoformat()
            }
        finally:
            db.close()
    
    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a conversation"""
        db = self._get_db()
        try:
            messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation_id
            ).order_by(ChatMessage.created_at).all()
            
            result = []
            for msg in messages:
                result.append({
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "model": msg.model,
                    "provider": msg.provider,
                    "tokens_used": msg.tokens_used,
                    "created_at": msg.created_at.isoformat()
                })
            
            logger.info(f"Retrieved {len(result)} messages for conversation {conversation_id}")
            return result
        finally:
            db.close()
    
    def search_conversations(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """Search conversations by title or content"""
        db = self._get_db()
        try:
            user = self._get_or_create_user(user_id)
            
            # Search in conversation titles and message content
            conversations = db.query(Conversation).filter(
                Conversation.user_id == user.id,
                Conversation.is_active == True
            ).filter(
                # Search in title or preview
                func.lower(Conversation.title).contains(query.lower()) |
                func.lower(Conversation.preview).contains(query.lower())
            ).order_by(desc(Conversation.updated_at)).all()
            
            result = []
            for conv in conversations:
                result.append({
                    "id": str(conv.id),
                    "title": conv.title,
                    "preview": conv.preview or "",
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                })
            
            logger.info(f"Found {len(result)} conversations matching query '{query}' for user {user_id}")
            return result
        finally:
            db.close()
    
    def get_conversation_stats(self, user_id: str) -> Dict[str, int]:
        """Get conversation statistics for a user"""
        db = self._get_db()
        try:
            user = self._get_or_create_user(user_id)
            
            total_conversations = db.query(Conversation).filter(
                Conversation.user_id == user.id,
                Conversation.is_active == True
            ).count()
            
            total_messages = db.query(ChatMessage).filter(
                ChatMessage.user_id == user.id
            ).count()
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages
            }
        finally:
            db.close()

# Global instance
database_conversation_store = DatabaseConversationStore()