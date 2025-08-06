"""
Unit tests for ChatConversationStore functionality.

Tests the core conversation management logic without integration dependencies.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import uuid

from app.services.chat.conversation_store import ChatConversationStore
from app.models.database import User, Conversation, ChatMessage


class TestChatConversationStore:
    """Unit tests for ChatConversationStore"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = MagicMock()
        return db
    
    @pytest.fixture
    def store(self):
        """Create a ChatConversationStore instance"""
        return ChatConversationStore()
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user"""
        user = Mock(spec=User)
        user.id = str(uuid.uuid4())
        user.email = "test@example.com"
        user.name = "Test User"
        return user
    
    @pytest.fixture
    def mock_conversation(self, mock_user):
        """Create a mock conversation"""
        conv = Mock(spec=Conversation)
        conv.id = str(uuid.uuid4())
        conv.user_id = mock_user.id
        conv.title = "Test Conversation"
        conv.preview = "Test preview"
        conv.created_at = datetime.utcnow()
        conv.updated_at = datetime.utcnow()
        conv.messages = []
        return conv
    
    def test_get_or_create_user_existing(self, store, mock_db, mock_user):
        """Test getting existing user"""
        with patch.object(store, '_get_db', return_value=mock_db):
            # Setup mock query
            mock_db.query.return_value.filter.return_value.first.return_value = mock_user
            
            result = store._get_or_create_user("test-user-id")
            
            # Verify query was made
            mock_db.query.assert_called_with(User)
            assert result == mock_user
    
    def test_get_or_create_user_new(self, store, mock_db):
        """Test creating new user when not exists"""
        with patch.object(store, '_get_db', return_value=mock_db):
            # Setup mock query to return None (user not found)
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # Mock the new user creation
            new_user = Mock(spec=User)
            new_user.id = str(uuid.uuid4())
            with patch('app.models.database.User', return_value=new_user):
                result = store._get_or_create_user("new-user-id")
                
                # Verify user was added to DB
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()
    
    def test_create_conversation(self, store, mock_db, mock_user):
        """Test creating a new conversation"""
        with patch.object(store, '_get_db', return_value=mock_db):
            with patch.object(store, '_get_or_create_user', return_value=mock_user):
                # Mock the conversation creation
                mock_conv = Mock(spec=Conversation)
                mock_conv.id = str(uuid.uuid4())
                mock_conv.title = "New Chat"
                mock_conv.preview = ""
                mock_conv.created_at = datetime.utcnow()
                mock_conv.updated_at = datetime.utcnow()
                
                with patch('app.models.database.Conversation', return_value=mock_conv):
                    result = store.create_conversation("test-user-id", "New Chat")
                    
                    # Verify conversation was created
                    mock_db.add.assert_called_once()
                    mock_db.commit.assert_called_once()
                    assert result['title'] == "New Chat"
                    assert 'id' in result
    
    def test_get_conversation_exists(self, store, mock_db, mock_conversation):
        """Test getting existing conversation"""
        with patch.object(store, '_get_db', return_value=mock_db):
            # Setup mock query
            mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_conversation
            
            result = store.get_conversation("test-user-id", mock_conversation.id)
            
            assert result is not None
            assert result['id'] == mock_conversation.id
            assert result['title'] == mock_conversation.title
    
    def test_get_conversation_not_exists(self, store, mock_db):
        """Test getting non-existent conversation returns None"""
        with patch.object(store, '_get_db', return_value=mock_db):
            # Setup mock query to return None
            mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
            
            result = store.get_conversation("test-user-id", "non-existent-id")
            
            assert result is None
    
    def test_add_message(self, store, mock_db, mock_conversation):
        """Test adding message to conversation"""
        with patch.object(store, '_get_db', return_value=mock_db):
            # Mock the message creation
            mock_message = Mock(spec=ChatMessage)
            mock_message.id = str(uuid.uuid4())
            mock_message.role = "user"
            mock_message.content = "Test message"
            mock_message.created_at = datetime.utcnow()
            
            with patch('app.models.database.ChatMessage', return_value=mock_message):
                result = store.add_message(mock_conversation.id, "user", "Test message")
                
                # Verify message was added
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()
                assert result['role'] == "user"
                assert result['content'] == "Test message"
    
    def test_get_messages(self, store, mock_db, mock_conversation):
        """Test retrieving messages from conversation"""
        with patch.object(store, '_get_db', return_value=mock_db):
            # Create mock messages
            mock_messages = []
            for i in range(3):
                msg = Mock(spec=ChatMessage)
                msg.id = str(uuid.uuid4())
                msg.role = "user" if i % 2 == 0 else "assistant"
                msg.content = f"Message {i}"
                msg.created_at = datetime.utcnow()
                mock_messages.append(msg)
            
            # Setup mock query
            mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_messages
            
            result = store.get_messages(mock_conversation.id)
            
            assert len(result) == 3
            assert result[0]['content'] == "Message 0"
            assert result[1]['role'] == "assistant"
    
    def test_update_conversation(self, store, mock_db, mock_conversation):
        """Test updating conversation metadata"""
        with patch.object(store, '_get_db', return_value=mock_db):
            # Setup mock query
            mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_conversation
            
            result = store.update_conversation(
                "test-user-id", 
                mock_conversation.id,
                title="Updated Title",
                preview="Updated preview"
            )
            
            # Verify conversation was updated
            assert mock_conversation.title == "Updated Title"
            assert mock_conversation.preview == "Updated preview"
            mock_db.commit.assert_called_once()
            assert result is True
    
    def test_delete_conversation(self, store, mock_db, mock_conversation):
        """Test deleting conversation"""
        with patch.object(store, '_get_db', return_value=mock_db):
            # Setup mock query
            mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_conversation
            
            result = store.delete_conversation("test-user-id", mock_conversation.id)
            
            # Verify conversation was deleted
            mock_db.delete.assert_called_with(mock_conversation)
            mock_db.commit.assert_called_once()
            assert result is True
    
    def test_get_conversations_list(self, store, mock_db, mock_user):
        """Test getting list of conversations for user"""
        with patch.object(store, '_get_db', return_value=mock_db):
            with patch.object(store, '_get_or_create_user', return_value=mock_user):
                # Create mock conversations
                mock_conversations = []
                for i in range(3):
                    conv = Mock(spec=Conversation)
                    conv.id = str(uuid.uuid4())
                    conv.title = f"Conversation {i}"
                    conv.preview = f"Preview {i}"
                    conv.created_at = datetime.utcnow()
                    conv.updated_at = datetime.utcnow()
                    conv.messages = []
                    mock_conversations.append(conv)
                
                # Setup mock query
                mock_query = mock_db.query.return_value.filter.return_value
                mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_conversations
                
                result = store.get_conversations("test-user-id", limit=10, offset=0)
                
                assert len(result) == 3
                assert result[0]['title'] == "Conversation 0"
                assert result[2]['preview'] == "Preview 2"
    
    def test_clear_conversation(self, store, mock_db, mock_conversation):
        """Test clearing messages from conversation"""
        with patch.object(store, '_get_db', return_value=mock_db):
            # Setup mock query
            mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_conversation
            
            # Mock messages to delete
            mock_messages = [Mock(spec=ChatMessage) for _ in range(3)]
            mock_db.query.return_value.filter.return_value.all.return_value = mock_messages
            
            result = store.clear_conversation("test-user-id", mock_conversation.id)
            
            # Verify messages were deleted
            assert mock_db.delete.call_count == 3
            mock_db.commit.assert_called_once()
            assert result is True
    
    def test_error_handling_db_error(self, store, mock_db):
        """Test error handling when database operations fail"""
        with patch.object(store, '_get_db', return_value=mock_db):
            # Make commit raise an exception
            mock_db.commit.side_effect = Exception("Database error")
            
            # This should handle the error gracefully
            with patch.object(store, '_get_or_create_user', return_value=Mock()):
                result = store.create_conversation("test-user-id", "Test")
                
                # Should rollback on error
                mock_db.rollback.assert_called_once()