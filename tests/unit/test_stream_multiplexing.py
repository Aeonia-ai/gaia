"""
Unit tests for Phase 1B: NATS World Updates - Stream Multiplexing

Tests the stream multiplexing utility and Chat Service integration with NATS.

🔴 TDD RED PHASE: These tests will FAIL until implementation is complete.

Key Test Areas:
1. Stream Multiplexing (merge_async_streams)
2. Chat Service NATS Subscription Lifecycle
3. Graceful Degradation
4. Health Check Accuracy
"""

import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

# These imports will FAIL until implementation exists - that's the RED phase!
from app.shared.stream_utils import merge_async_streams
from app.services.chat.unified_chat import UnifiedChatHandler
from app.shared.nats_client import NATSClient


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_nats_client():
    """Mock NATS client for testing."""
    client = AsyncMock(spec=NATSClient)
    client.is_connected.return_value = True
    client._subscription_ids = {}
    return client


async def create_test_llm_stream(chunks: list[str], delay: float = 0.01) -> AsyncGenerator[str, None]:
    """Create a test LLM async generator."""
    for chunk in chunks:
        await asyncio.sleep(delay)
        yield chunk


# ============================================================================
# Test Suite 1: Stream Multiplexing Utility (merge_async_streams)
# ============================================================================

class TestStreamMultiplexing:
    """Test suite for merge_async_streams utility."""

    @pytest.mark.asyncio
    async def test_nats_event_prioritization(self):
        """
        CRITICAL: NATS events should be yielded BEFORE LLM chunks when both available.

        Pattern: Queue NATS event, then LLM chunk, verify NATS comes first.
        """
        # Arrange
        llm_chunks = ["chunk1", "chunk2", "chunk3"]
        llm_stream = create_test_llm_stream(llm_chunks, delay=0.05)

        nats_queue = asyncio.Queue()
        await nats_queue.put({"type": "world_update", "data": "nats_event_1"})

        # Give LLM stream a head start
        await asyncio.sleep(0.02)

        # Act
        results = []
        async for item in merge_async_streams(llm_stream, nats_queue, timeout=1.0):
            results.append(item)

        # Assert
        assert len(results) == 4  # 1 NATS + 3 LLM chunks
        assert results[0] == {"type": "world_update", "data": "nats_event_1"}
        assert results[1:] == llm_chunks

    @pytest.mark.asyncio
    async def test_llm_stream_consumption(self):
        """Verify all LLM chunks are yielded when NATS queue empty."""
        # Arrange
        llm_chunks = ["chunk1", "chunk2", "chunk3", "chunk4"]
        llm_stream = create_test_llm_stream(llm_chunks, delay=0.01)
        nats_queue = asyncio.Queue()  # Empty queue

        # Act
        results = []
        async for item in merge_async_streams(llm_stream, nats_queue, timeout=1.0):
            results.append(item)

        # Assert
        assert len(results) == 4
        assert results == llm_chunks

    @pytest.mark.asyncio
    async def test_nats_queue_consumption(self):
        """Verify all NATS events are yielded."""
        # Arrange
        async def empty_llm_stream() -> AsyncGenerator[str, None]:
            return
            yield  # Make it a generator

        nats_events = [
            {"type": "world_update", "data": "event1"},
            {"type": "world_update", "data": "event2"},
            {"type": "world_update", "data": "event3"},
        ]

        llm_stream = empty_llm_stream()
        nats_queue = asyncio.Queue()
        for event in nats_events:
            await nats_queue.put(event)

        # Act
        results = []
        async for item in merge_async_streams(llm_stream, nats_queue, timeout=0.5):
            results.append(item)

        # Assert
        assert len(results) == 3
        assert results == nats_events

    @pytest.mark.asyncio
    async def test_timeout_behavior(self):
        """Verify function handles timeout gracefully."""
        # Arrange
        async def slow_llm_stream() -> AsyncGenerator[str, None]:
            await asyncio.sleep(2.0)  # Longer than timeout
            yield "too_late"

        llm_stream = slow_llm_stream()
        nats_queue = asyncio.Queue()

        # Act
        results = []
        async for item in merge_async_streams(llm_stream, nats_queue, timeout=0.5):
            results.append(item)

        # Assert
        assert len(results) == 0  # No items yielded due to timeout

    @pytest.mark.asyncio
    async def test_error_propagation_from_llm_stream(self):
        """Verify exceptions from LLM stream are propagated."""
        # Arrange
        async def error_llm_stream() -> AsyncGenerator[str, None]:
            yield "chunk1"
            raise ValueError("LLM stream error")

        llm_stream = error_llm_stream()
        nats_queue = asyncio.Queue()

        # Act & Assert
        with pytest.raises(ValueError, match="LLM stream error"):
            async for _ in merge_async_streams(llm_stream, nats_queue, timeout=1.0):
                pass

    @pytest.mark.asyncio
    async def test_empty_streams(self):
        """Test with empty LLM stream and empty NATS queue."""
        # Arrange
        async def empty_llm_stream() -> AsyncGenerator[str, None]:
            return
            yield  # Make it a generator

        llm_stream = empty_llm_stream()
        nats_queue = asyncio.Queue()

        # Act
        results = []
        async for item in merge_async_streams(llm_stream, nats_queue, timeout=0.5):
            results.append(item)

        # Assert
        assert len(results) == 0


# ============================================================================
# Test Suite 2: Chat Service NATS Subscription Lifecycle
# ============================================================================

class TestChatServiceNATSLifecycle:
    """Test suite for Chat Service NATS subscription lifecycle."""

    @pytest.mark.asyncio
    async def test_subscription_on_sse_open(self, mock_nats_client):
        """
        Verify nats_client.subscribe() is called with correct subject.

        Subject format: world.updates.user.{user_id}
        """
        # Arrange
        user_id = "test-user-123"

        # Mock the UnifiedChat dependencies
        mock_config = Mock()
        mock_kb_service = Mock()

        unified_chat = UnifiedChatHandler(
            config=mock_config,
            kb_service=mock_kb_service,
            nats_client=mock_nats_client
        )

        # Mock LLM stream
        async def mock_llm_stream():
            yield {"type": "content", "data": "chunk1"}

        # Act - process_stream should subscribe to NATS
        with patch.object(unified_chat, '_route_and_process', return_value=mock_llm_stream()):
            stream = unified_chat.process_stream(
                message="test message",
                user_id=user_id,
                session_id="test-session"
            )

            # Consume the stream
            async for _ in stream:
                pass

        # Assert
        expected_subject = f"world.updates.user.{user_id}"
        mock_nats_client.subscribe.assert_called_once()
        call_args = mock_nats_client.subscribe.call_args
        assert call_args[0][0] == expected_subject

    @pytest.mark.asyncio
    async def test_unsubscribe_on_sse_close_normal_completion(self, mock_nats_client):
        """
        CRITICAL: Verify nats_client.unsubscribe() is called on normal completion.

        Memory safety: Must unsubscribe even with normal flow.
        """
        # Arrange
        user_id = "test-user-123"

        mock_config = Mock()
        mock_kb_service = Mock()

        unified_chat = UnifiedChatHandler(
            config=mock_config,
            kb_service=mock_kb_service,
            nats_client=mock_nats_client
        )

        # Mock LLM stream
        async def mock_llm_stream():
            yield {"type": "content", "data": "chunk1"}

        # Act
        with patch.object(unified_chat, '_route_and_process', return_value=mock_llm_stream()):
            stream = unified_chat.process_stream(
                message="test message",
                user_id=user_id,
                session_id="test-session"
            )

            # Consume the stream completely
            async for _ in stream:
                pass

        # Assert - unsubscribe must be called
        expected_subject = f"world.updates.user.{user_id}"
        mock_nats_client.unsubscribe.assert_called_once_with(expected_subject)

    @pytest.mark.asyncio
    async def test_unsubscribe_on_exception_during_streaming(self, mock_nats_client):
        """
        CRITICAL: Verify nats_client.unsubscribe() is called even when exception occurs.

        Memory safety: Must unsubscribe in finally block.
        """
        # Arrange
        user_id = "test-user-123"

        mock_config = Mock()
        mock_kb_service = Mock()

        unified_chat = UnifiedChatHandler(
            config=mock_config,
            kb_service=mock_kb_service,
            nats_client=mock_nats_client
        )

        # Mock LLM stream that raises an exception
        async def error_llm_stream():
            yield {"type": "content", "data": "chunk1"}
            raise RuntimeError("Stream error")

        # Act
        with patch.object(unified_chat, '_route_and_process', return_value=error_llm_stream()):
            stream = unified_chat.process_stream(
                message="test message",
                user_id=user_id,
                session_id="test-session"
            )

            # Consume the stream until exception
            with pytest.raises(RuntimeError, match="Stream error"):
                async for _ in stream:
                    pass

        # Assert - unsubscribe MUST still be called
        expected_subject = f"world.updates.user.{user_id}"
        mock_nats_client.unsubscribe.assert_called_once_with(expected_subject)

    @pytest.mark.asyncio
    async def test_unsubscribe_on_client_disconnect(self, mock_nats_client):
        """
        CRITICAL: Verify unsubscribe when client disconnects mid-stream.

        Memory safety: Must unsubscribe even if stream not fully consumed.
        """
        # Arrange
        user_id = "test-user-123"

        mock_config = Mock()
        mock_kb_service = Mock()

        unified_chat = UnifiedChatHandler(
            config=mock_config,
            kb_service=mock_kb_service,
            nats_client=mock_nats_client
        )

        # Mock LLM stream
        async def mock_llm_stream():
            yield {"type": "content", "data": "chunk1"}
            yield {"type": "content", "data": "chunk2"}
            yield {"type": "content", "data": "chunk3"}

        # Act
        with patch.object(unified_chat, '_route_and_process', return_value=mock_llm_stream()):
            stream = unified_chat.process_stream(
                message="test message",
                user_id=user_id,
                session_id="test-session"
            )

            # Simulate client disconnect - only consume first chunk
            async for chunk in stream:
                break  # Client disconnects after first chunk

        # Assert - unsubscribe MUST be called
        expected_subject = f"world.updates.user.{user_id}"
        mock_nats_client.unsubscribe.assert_called_once_with(expected_subject)


# ============================================================================
# Test Suite 3: Graceful Degradation
# ============================================================================

class TestGracefulDegradation:
    """Test suite for graceful degradation when NATS is unavailable."""

    @pytest.mark.asyncio
    async def test_sse_works_without_nats_client_none(self):
        """
        Test SSE stream works when nats_client is None.

        Verify SSE stream contains only LLM chunks (no world_update).
        """
        # Arrange
        user_id = "test-user-123"

        mock_config = Mock()
        mock_kb_service = Mock()

        unified_chat = UnifiedChat(
            config=mock_config,
            kb_service=mock_kb_service,
            nats_client=None  # No NATS client
        )

        # Mock LLM stream
        async def mock_llm_stream():
            yield {"type": "content", "data": "chunk1"}
            yield {"type": "content", "data": "chunk2"}

        # Act
        with patch.object(unified_chat, '_route_and_process', return_value=mock_llm_stream()):
            stream = unified_chat.process_stream(
                message="test message",
                user_id=user_id,
                session_id="test-session"
            )

            results = []
            async for item in stream:
                results.append(item)

        # Assert - Should contain LLM chunks but no world_update events
        assert len(results) >= 2
        # All results should be content type, no world_update
        for result in results:
            if isinstance(result, dict) and "type" in result:
                assert result["type"] != "world_update"

    @pytest.mark.asyncio
    async def test_sse_works_when_nats_not_connected(self, mock_nats_client):
        """
        Test SSE stream works when nats_client.is_connected() returns False.

        Verify SSE stream contains only LLM chunks.
        """
        # Arrange
        mock_nats_client.is_connected.return_value = False

        user_id = "test-user-123"

        mock_config = Mock()
        mock_kb_service = Mock()

        unified_chat = UnifiedChatHandler(
            config=mock_config,
            kb_service=mock_kb_service,
            nats_client=mock_nats_client
        )

        # Mock LLM stream
        async def mock_llm_stream():
            yield {"type": "content", "data": "chunk1"}
            yield {"type": "content", "data": "chunk2"}

        # Act
        with patch.object(unified_chat, '_route_and_process', return_value=mock_llm_stream()):
            stream = unified_chat.process_stream(
                message="test message",
                user_id=user_id,
                session_id="test-session"
            )

            results = []
            async for item in stream:
                results.append(item)

        # Assert
        assert len(results) >= 2
        # subscribe should NOT be called when not connected
        mock_nats_client.subscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_nats_subscribe_failure(self, mock_nats_client):
        """
        Test when nats_client.subscribe() raises exception.

        Verify exception is logged but not raised.
        Verify SSE stream continues with LLM chunks only.
        """
        # Arrange
        mock_nats_client.subscribe.side_effect = Exception("NATS subscribe failed")

        user_id = "test-user-123"

        mock_config = Mock()
        mock_kb_service = Mock()

        unified_chat = UnifiedChatHandler(
            config=mock_config,
            kb_service=mock_kb_service,
            nats_client=mock_nats_client
        )

        # Mock LLM stream
        async def mock_llm_stream():
            yield {"type": "content", "data": "chunk1"}
            yield {"type": "content", "data": "chunk2"}

        # Act
        with patch.object(unified_chat, '_route_and_process', return_value=mock_llm_stream()):
            with patch('app.services.chat.unified_chat.logger') as mock_logger:
                stream = unified_chat.process_stream(
                    message="test message",
                    user_id=user_id,
                    session_id="test-session"
                )

                results = []
                # Should NOT raise exception - stream continues
                async for item in stream:
                    results.append(item)

        # Assert - Stream should continue despite subscribe failure
        assert len(results) >= 2

        # Error should be logged
        assert mock_logger.error.called or mock_logger.warning.called


# ============================================================================
# Test Suite 4: Health Check Accuracy
# ============================================================================

class TestHealthCheckAccuracy:
    """Test suite for health check NATS connection reporting."""

    @pytest.mark.asyncio
    async def test_health_check_with_nats_connected(self, mock_nats_client):
        """Verify health check returns nats_connected: True when connected."""
        # Arrange
        mock_nats_client.is_connected.return_value = True

        # Mock the global nats_client in chat service main
        with patch('app.services.chat.main.nats_client', mock_nats_client):
            from app.services.chat.main import health_check

            # Act
            result = await health_check()

        # Assert
        assert "nats_connected" in result
        assert result["nats_connected"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_nats_disconnected(self, mock_nats_client):
        """Verify health check returns nats_connected: False when disconnected."""
        # Arrange
        mock_nats_client.is_connected.return_value = False

        # Mock the global nats_client in chat service main
        with patch('app.services.chat.main.nats_client', mock_nats_client):
            from app.services.chat.main import health_check

            # Act
            result = await health_check()

        # Assert
        assert "nats_connected" in result
        assert result["nats_connected"] is False

    @pytest.mark.asyncio
    async def test_health_check_with_nats_client_none(self):
        """Verify health check handles nats_client = None gracefully."""
        # Arrange - Mock the global nats_client as None
        with patch('app.services.chat.main.nats_client', None):
            from app.services.chat.main import health_check

            # Act
            result = await health_check()

        # Assert
        assert "nats_connected" in result
        assert result["nats_connected"] is False
