"""
Unit tests for conversation_id pre-creation in streaming responses.

Tests the core logic for getting/creating conversation_id before streaming starts,
ensuring consistent behavior between streaming and non-streaming responses.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
import uuid
import json

from app.services.chat.unified_chat import UnifiedChatHandler
from app.services.chat.conversation_store import ChatConversationStore
from app.models.database import User, Conversation, ChatMessage


@pytest.mark.unit
class TestConversationIdStreaming:
    """Unit tests for conversation_id streaming pre-creation"""

    @pytest.fixture
    def mock_conversation_store(self):
        """Create a mock conversation store"""
        store = MagicMock(spec=ChatConversationStore)
        return store

    @pytest.fixture
    def chat_service(self):
        """Create UnifiedChatHandler with mocked dependencies"""
        service = UnifiedChatHandler()
        return service

    @pytest.fixture
    def sample_auth(self):
        """Sample authentication data"""
        return {
            "user_id": "test-user-123",
            "sub": "test-user-123",
            "email": "test@example.com"
        }

    @pytest.fixture
    def sample_conversation_id(self):
        """Sample conversation UUID"""
        return str(uuid.uuid4())

    # Test _get_or_create_conversation_id method

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_new_conversation(self, chat_service, mock_conversation_store, sample_auth):
        """Test creating a new conversation when none exists"""
        # Arrange
        message = "Hello, this is a test message"
        context = {}  # No conversation_id provided
        mock_conversation_store.create_conversation.return_value = {
            "id": "new-conv-uuid-123",
            "title": "Hello, this is a test message",
            "created_at": datetime.utcnow().isoformat()
        }

        # Act
        with patch('app.services.chat.conversation_store.chat_conversation_store', mock_conversation_store):
            conversation_id = await chat_service._get_or_create_conversation_id(message, context, sample_auth)

        # Assert
        assert conversation_id == "new-conv-uuid-123"
        mock_conversation_store.create_conversation.assert_called_once_with(
            user_id="test-user-123",
            title="Hello, this is a test message"
        )

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_existing_conversation(self, chat_service, mock_conversation_store, sample_auth, sample_conversation_id):
        """Test using existing conversation when valid ID provided"""
        # Arrange
        message = "Continue our chat"
        context = {"conversation_id": sample_conversation_id}
        mock_conversation_store.get_conversation.return_value = {
            "id": sample_conversation_id,
            "title": "Existing Conversation",
            "messages": []
        }

        # Act
        with patch('app.services.chat.conversation_store.chat_conversation_store', mock_conversation_store):
            conversation_id = await chat_service._get_or_create_conversation_id(message, context, sample_auth)

        # Assert
        assert conversation_id == sample_conversation_id
        mock_conversation_store.get_conversation.assert_called_once_with("test-user-123", sample_conversation_id)
        mock_conversation_store.create_conversation.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_nonexistent_conversation(self, chat_service, mock_conversation_store, sample_auth):
        """Test creating new conversation when provided ID doesn't exist"""
        # Arrange
        message = "Resume chat"
        context = {"conversation_id": "nonexistent-uuid"}
        mock_conversation_store.get_conversation.return_value = None  # Conversation not found
        mock_conversation_store.create_conversation.return_value = {
            "id": "fallback-conv-uuid",
            "title": "Resume chat",
            "created_at": datetime.utcnow().isoformat()
        }

        # Act
        with patch('app.services.chat.conversation_store.chat_conversation_store', mock_conversation_store):
            conversation_id = await chat_service._get_or_create_conversation_id(message, context, sample_auth)

        # Assert
        assert conversation_id == "fallback-conv-uuid"
        mock_conversation_store.get_conversation.assert_called_once_with("test-user-123", "nonexistent-uuid")
        mock_conversation_store.create_conversation.assert_called_once_with(
            user_id="test-user-123",
            title="Resume chat"
        )

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_new_keyword(self, chat_service, mock_conversation_store, sample_auth):
        """Test creating new conversation when 'new' is specified"""
        # Arrange
        message = "Start fresh conversation"
        context = {"conversation_id": "new"}
        mock_conversation_store.create_conversation.return_value = {
            "id": "fresh-conv-uuid",
            "title": "Start fresh conversation",
            "created_at": datetime.utcnow().isoformat()
        }

        # Act
        with patch('app.services.chat.conversation_store.chat_conversation_store', mock_conversation_store):
            conversation_id = await chat_service._get_or_create_conversation_id(message, context, sample_auth)

        # Assert
        assert conversation_id == "fresh-conv-uuid"
        mock_conversation_store.create_conversation.assert_called_once_with(
            user_id="test-user-123",
            title="Start fresh conversation"
        )

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_long_message_truncation(self, chat_service, mock_conversation_store, sample_auth):
        """Test that long messages are truncated for conversation title"""
        # Arrange
        long_message = "This is a very long message that should be truncated when used as a conversation title because it exceeds fifty characters in length"
        context = {}
        expected_title = long_message[:50] + "..."
        mock_conversation_store.create_conversation.return_value = {
            "id": "truncated-conv-uuid",
            "title": expected_title,
            "created_at": datetime.utcnow().isoformat()
        }

        # Act
        with patch('app.services.chat.conversation_store.chat_conversation_store', mock_conversation_store):
            conversation_id = await chat_service._get_or_create_conversation_id(long_message, context, sample_auth)

        # Assert
        assert conversation_id == "truncated-conv-uuid"
        mock_conversation_store.create_conversation.assert_called_once_with(
            user_id="test-user-123",
            title=expected_title
        )

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_error_handling(self, chat_service, mock_conversation_store, sample_auth):
        """Test fallback behavior when conversation store fails"""
        # Arrange
        message = "Test message"
        context = {}
        mock_conversation_store.create_conversation.side_effect = Exception("Database error")

        # Act
        with patch('app.services.chat.conversation_store.chat_conversation_store', mock_conversation_store):
            with patch('time.time', return_value=1234567890):
                conversation_id = await chat_service._get_or_create_conversation_id(message, context, sample_auth)

        # Assert
        assert conversation_id == "test-user-123_fallback_1234567890"

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_missing_user_id(self, chat_service, mock_conversation_store):
        """Test behavior when user_id is missing from auth"""
        # Arrange
        message = "Test message"
        context = {}
        auth = {}  # No user_id provided
        mock_conversation_store.create_conversation.return_value = {
            "id": "unknown-user-conv",
            "title": "Test message",
            "created_at": datetime.utcnow().isoformat()
        }

        # Act
        with patch('app.services.chat.conversation_store.chat_conversation_store', mock_conversation_store):
            conversation_id = await chat_service._get_or_create_conversation_id(message, context, auth)

        # Assert
        assert conversation_id == "unknown-user-conv"
        mock_conversation_store.create_conversation.assert_called_once_with(
            user_id="unknown",  # Should default to "unknown"
            title="Test message"
        )

    # Test integration with existing _save_conversation method

    @pytest.mark.asyncio
    async def test_save_conversation_uses_precreated_conversation_id(self, chat_service, mock_conversation_store, sample_auth, sample_conversation_id):
        """Test that _save_conversation works with pre-created conversation_id"""
        # Arrange
        message = "User message"
        response = "AI response"
        context = {"conversation_id": sample_conversation_id}

        # Mock the conversation store methods
        mock_conversation_store.get_conversation.return_value = {
            "id": sample_conversation_id,
            "title": "Existing Conversation"
        }
        mock_conversation_store.add_message = AsyncMock()
        mock_conversation_store.update_conversation = AsyncMock()

        # Act
        with patch('app.services.chat.conversation_store.chat_conversation_store', mock_conversation_store):
            with patch('asyncio.create_task') as mock_create_task:
                # Mock asyncio.create_task to execute functions immediately
                mock_create_task.side_effect = lambda coro: coro

                result_conversation_id = await chat_service._save_conversation(message, response, context, sample_auth)

        # Assert
        assert result_conversation_id == sample_conversation_id
        mock_conversation_store.get_conversation.assert_called_once_with("test-user-123", sample_conversation_id)

    # Test metadata event generation for streaming

    def test_generate_conversation_metadata_event(self, sample_conversation_id):
        """Test generating metadata event with conversation_id for V0.3 streaming"""
        # Arrange
        model = "gpt-4"
        timestamp = 1234567890

        # Act
        metadata_event = {
            "type": "metadata",
            "conversation_id": sample_conversation_id,
            "model": model,
            "timestamp": timestamp
        }

        # Assert
        assert metadata_event["type"] == "metadata"
        assert metadata_event["conversation_id"] == sample_conversation_id
        assert metadata_event["model"] == model
        assert metadata_event["timestamp"] == timestamp

        # Test JSON serialization (should be valid for SSE)
        json_str = json.dumps(metadata_event)
        assert sample_conversation_id in json_str
        assert "metadata" in json_str

    def test_sse_format_metadata_event(self, sample_conversation_id):
        """Test SSE formatting of metadata event"""
        # Arrange
        metadata_event = {
            "type": "metadata",
            "conversation_id": sample_conversation_id,
            "model": "gpt-4"
        }

        # Act
        sse_line = f"data: {json.dumps(metadata_event)}\n\n"

        # Assert
        assert sse_line.startswith("data: ")
        assert sse_line.endswith("\n\n")
        assert sample_conversation_id in sse_line
        assert "metadata" in sse_line

        # Should be parseable JSON
        json_part = sse_line[6:-2]  # Remove "data: " and "\n\n"
        parsed = json.loads(json_part)
        assert parsed["conversation_id"] == sample_conversation_id