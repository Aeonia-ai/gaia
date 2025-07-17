"""Simple in-memory conversation storage for development"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

class ConversationStore:
    """In-memory conversation storage"""
    
    def __init__(self):
        # Store conversations by user ID
        self._conversations: Dict[str, Dict[str, Dict]] = defaultdict(dict)
        # Store messages by conversation ID
        self._messages: Dict[str, List[Dict]] = defaultdict(list)
    
    def create_conversation(self, user_id: str, title: Optional[str] = None) -> Dict:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        conversation = {
            "id": conversation_id,
            "user_id": user_id,
            "title": title or "New Conversation",
            "preview": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._conversations[user_id][conversation_id] = conversation
        return conversation
    
    def get_conversations(self, user_id: str) -> List[Dict]:
        """Get all conversations for a user"""
        user_convs = self._conversations.get(user_id, {})
        # Sort by updated_at descending
        return sorted(
            user_convs.values(),
            key=lambda x: x.get("updated_at", ""),
            reverse=True
        )
    
    def get_conversation(self, user_id: str, conversation_id: str) -> Optional[Dict]:
        """Get a specific conversation"""
        return self._conversations.get(user_id, {}).get(conversation_id)
    
    def update_conversation(self, user_id: str, conversation_id: str, 
                          title: Optional[str] = None, preview: Optional[str] = None) -> Optional[Dict]:
        """Update conversation metadata"""
        conv = self.get_conversation(user_id, conversation_id)
        if conv:
            if title:
                conv["title"] = title
            if preview:
                conv["preview"] = preview[:100]  # Limit preview length
            conv["updated_at"] = datetime.now().isoformat()
            return conv
        return None
    
    def add_message(self, conversation_id: str, role: str, content: str) -> Dict:
        """Add a message to a conversation"""
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "created_at": datetime.now().isoformat()
        }
        self._messages[conversation_id].append(message)
        return message
    
    def get_messages(self, conversation_id: str) -> List[Dict]:
        """Get all messages for a conversation"""
        return self._messages.get(conversation_id, [])
    
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Delete a conversation"""
        if user_id in self._conversations and conversation_id in self._conversations[user_id]:
            del self._conversations[user_id][conversation_id]
            if conversation_id in self._messages:
                del self._messages[conversation_id]
            return True
        return False


# Global store instance
conversation_store = ConversationStore()