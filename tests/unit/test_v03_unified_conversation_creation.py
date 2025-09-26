"""
Unit tests for V0.3 unified conversation creation logic.
Tests the core conversation creation behavior that should be consistent
between streaming and non-streaming modes.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import time


class TestV03UnifiedConversationCreation:
    """Test unified conversation creation for V0.3 streaming and non-streaming."""

    @pytest.fixture
    def mock_conversation_store(self):
        """Mock conversation store."""
        store = MagicMock()
        store.create_conversation = MagicMock(return_value={
            "id": str(uuid.uuid4()),
            "title": "Test Conversation",
            "created_at": "2025-09-16T00:00:00Z"
        })
        store.get_conversation = MagicMock(return_value=None)  # Default: conversation doesn't exist
        return store

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication context."""
        return {
            "user_id": "test-user-123",
            "api_key": "test-api-key",
            "email": "test@example.com"
        }

    @pytest.fixture
    def unified_chat_handler(self, mock_conversation_store):
        """Create UnifiedChatHandler with mocked dependencies."""
        with patch('app.services.chat.conversation_store.chat_conversation_store', mock_conversation_store):
            from app.services.chat.unified_chat import UnifiedChatHandler
            handler = UnifiedChatHandler()
            return handler

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_creates_new_when_none_provided(
        self, unified_chat_handler, mock_conversation_store, mock_auth
    ):
        """Test that missing conversation_id creates new conversation."""
        message = "Hello, this is a test message"
        context = {}  # No conversation_id

        conversation_id = await unified_chat_handler._get_or_create_conversation_id(
            message, context, mock_auth
        )

        # Should have created new conversation
        mock_conversation_store.create_conversation.assert_called_once()
        create_call = mock_conversation_store.create_conversation.call_args

        assert create_call[1]["user_id"] == "test-user-123"
        assert create_call[1]["title"] == "Hello, this is a test message"  # Full message as title

        # Should return valid UUID
        assert isinstance(conversation_id, str)
        assert len(conversation_id) > 0
        uuid.UUID(conversation_id)  # Should not raise exception if valid UUID

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_creates_new_when_new_specified(
        self, unified_chat_handler, mock_conversation_store, mock_auth
    ):
        """Test that conversation_id='new' creates new conversation."""
        message = "Create new conversation please"
        context = {"conversation_id": "new"}

        conversation_id = await unified_chat_handler._get_or_create_conversation_id(
            message, context, mock_auth
        )

        # Should have created new conversation
        mock_conversation_store.create_conversation.assert_called_once()
        create_call = mock_conversation_store.create_conversation.call_args

        assert create_call[1]["user_id"] == "test-user-123"
        assert create_call[1]["title"] == "Create new conversation please"

        # Should return valid UUID (not "new")
        assert conversation_id != "new"
        uuid.UUID(conversation_id)

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_uses_existing_valid_id(
        self, unified_chat_handler, mock_conversation_store, mock_auth
    ):
        """Test that valid existing conversation_id is returned unchanged."""
        existing_id = str(uuid.uuid4())
        message = "Continue existing conversation"
        context = {"conversation_id": existing_id}

        # Mock that conversation exists
        mock_conversation_store.get_conversation = MagicMock(return_value={
            "id": existing_id,
            "title": "Existing Conversation"
        })

        conversation_id = await unified_chat_handler._get_or_create_conversation_id(
            message, context, mock_auth
        )

        # Should NOT have created new conversation
        mock_conversation_store.create_conversation.assert_not_called()

        # Should return same ID
        assert conversation_id == existing_id

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_truncates_long_title(
        self, unified_chat_handler, mock_conversation_store, mock_auth
    ):
        """Test that long messages are truncated for conversation title."""
        long_message = "This is a very long message that should be truncated because it exceeds the fifty character limit that we set for conversation titles to keep them manageable"
        context = {}

        conversation_id = await unified_chat_handler._get_or_create_conversation_id(
            long_message, context, mock_auth
        )

        # Should have created conversation with truncated title
        mock_conversation_store.create_conversation.assert_called_once()
        create_call = mock_conversation_store.create_conversation.call_args

        title = create_call[1]["title"]
        assert len(title) <= 53  # 50 chars + "..."
        assert title.endswith("...")
        assert title.startswith("This is a very long message that should be truncated")

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_handles_different_auth_formats(
        self, unified_chat_handler, mock_conversation_store
    ):
        """Test conversation creation with different auth formats."""
        message = "Test auth formats"
        context = {}

        # Test with user_id
        auth1 = {"user_id": "user-123"}
        conv_id_1 = await unified_chat_handler._get_or_create_conversation_id(
            message, context, auth1
        )

        # Test with sub (JWT format)
        auth2 = {"sub": "user-456"}
        conv_id_2 = await unified_chat_handler._get_or_create_conversation_id(
            message, context, auth2
        )

        # Test with fallback to unknown
        auth3 = {"api_key": "some-key"}  # No user_id or sub
        conv_id_3 = await unified_chat_handler._get_or_create_conversation_id(
            message, context, auth3
        )

        # All should have created conversations
        assert mock_conversation_store.create_conversation.call_count == 3

        # Check user_id values
        calls = mock_conversation_store.create_conversation.call_args_list
        assert calls[0][1]["user_id"] == "user-123"
        assert calls[1][1]["user_id"] == "user-456"
        assert calls[2][1]["user_id"] == "unknown"

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_performance(
        self, unified_chat_handler, mock_conversation_store, mock_auth
    ):
        """Test that conversation creation is fast enough for unified behavior."""
        message = "Performance test message"
        context = {}

        start_time = time.time()
        conversation_id = await unified_chat_handler._get_or_create_conversation_id(
            message, context, mock_auth
        )
        creation_time = time.time() - start_time

        # Should be very fast (mocked, but testing the logic)
        assert creation_time < 0.1, f"Conversation creation took {creation_time:.3f}s (should be instant with mocks)"

        # Should have created conversation
        mock_conversation_store.create_conversation.assert_called_once()

        # Should return valid UUID
        uuid.UUID(conversation_id)

    @pytest.mark.asyncio
    async def test_unified_conversation_creation_consistent_across_modes(
        self, unified_chat_handler, mock_conversation_store, mock_auth
    ):
        """Test that streaming and non-streaming use same conversation creation logic."""
        message = "Test unified conversation creation"

        # Test "streaming" path
        context_streaming = {"stream": True}
        conv_id_streaming = await unified_chat_handler._get_or_create_conversation_id(
            message, context_streaming, mock_auth
        )

        # Test "non-streaming" path
        context_non_streaming = {"stream": False}
        conv_id_non_streaming = await unified_chat_handler._get_or_create_conversation_id(
            message, context_non_streaming, mock_auth
        )

        # Both should have created conversations with same logic
        assert mock_conversation_store.create_conversation.call_count == 2

        # Both should return valid UUIDs
        uuid.UUID(conv_id_streaming)
        uuid.UUID(conv_id_non_streaming)

        # Should be different conversations (both new)
        assert conv_id_streaming != conv_id_non_streaming

        # Both should have used same title and user_id
        calls = mock_conversation_store.create_conversation.call_args_list
        assert calls[0][1]["title"] == message
        assert calls[1][1]["title"] == message
        assert calls[0][1]["user_id"] == "test-user-123"
        assert calls[1][1]["user_id"] == "test-user-123"

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_id_error_handling(
        self, unified_chat_handler, mock_auth
    ):
        """Test error handling in conversation creation."""
        message = "Test error handling"
        context = {}

        # Mock conversation store to raise exception
        with patch('app.services.chat.conversation_store.chat_conversation_store') as mock_store:
            mock_store.create_conversation.side_effect = Exception("Database error")

            # Should propagate exception (let caller handle it)
            with pytest.raises(Exception, match="Database error"):
                await unified_chat_handler._get_or_create_conversation_id(
                    message, context, mock_auth
                )

    @pytest.mark.asyncio
    async def test_conversation_id_format_validation(
        self, unified_chat_handler, mock_conversation_store, mock_auth
    ):
        """Test that conversation_id format is consistent."""
        message = "Test conversation_id format"
        context = {}

        # Mock to return specific UUID format
        test_uuid = str(uuid.uuid4())
        mock_conversation_store.create_conversation.return_value = {"id": test_uuid}

        conversation_id = await unified_chat_handler._get_or_create_conversation_id(
            message, context, mock_auth
        )

        # Should return exact UUID from store
        assert conversation_id == test_uuid

        # Should be valid UUID format
        uuid.UUID(conversation_id)
        assert len(conversation_id) == 36  # Standard UUID length
        assert conversation_id.count("-") == 4  # Standard UUID hyphens