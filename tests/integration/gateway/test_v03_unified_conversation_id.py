"""
Test V0.3 unified conversation_id delivery behavior.
Ensures both streaming and non-streaming deliver conversation_id with consistent timing.
"""

import pytest
import httpx
import json
import time
import os
from typing import Dict, Any, Optional
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_v03_unified_conversation_id")


class TestV03UnifiedConversationId:
    """Test unified conversation_id behavior for V0.3 streaming and non-streaming."""

    @pytest.fixture
    def gateway_url(self) -> str:
        """Gateway URL for tests."""
        return "http://gateway:8000"

    @pytest.fixture
    def api_key(self) -> str:
        """API key for testing."""
        return os.getenv("API_KEY") or os.getenv("TEST_API_KEY", "test-key-123")

    @pytest.mark.asyncio
    async def test_v03_non_streaming_conversation_id_always_present(self, gateway_url, api_key):
        """Test that non-streaming V0.3 ALWAYS returns conversation_id immediately."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = time.time()

            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Hello, create new conversation",
                    "stream": False
                }
            )

            response_time = time.time() - start_time

            assert response.status_code == 200
            data = response.json()

            # MUST have conversation_id (not optional)
            assert "conversation_id" in data, "conversation_id must be present in non-streaming response"
            assert isinstance(data["conversation_id"], str)
            assert len(data["conversation_id"]) > 0

            # conversation_id should be available reasonably quickly
            assert response_time < 5.0, f"Non-streaming conversation_id took {response_time:.2f}s (should be under 5s)"

            # Standard V0.3 response format
            assert "response" in data
            assert isinstance(data["response"], str)

            logger.info(f"Non-streaming conversation_id delivered in {response_time:.3f}s: {data['conversation_id']}")

    @pytest.mark.asyncio
    async def test_v03_streaming_conversation_id_timing(self, gateway_url, api_key):
        """Test that streaming V0.3 delivers conversation_id in first metadata event."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = time.time()

            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Hello, streaming test",
                    "stream": True
                }
            )

            assert response.status_code == 200
            assert response.headers.get("content-type", "").startswith("text/event-stream")

            conversation_id = None
            conversation_id_time = None
            event_count = 0

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()

                    if data_str and data_str != "[DONE]":
                        try:
                            event_data = json.loads(data_str)
                            event_count += 1

                            # Look for conversation_id in metadata event
                            if event_data.get("type") == "metadata" and "conversation_id" in event_data:
                                conversation_id = event_data["conversation_id"]
                                conversation_id_time = time.time() - start_time
                                logger.info(f"Streaming conversation_id found at event {event_count} in {conversation_id_time:.3f}s")
                                break

                        except json.JSONDecodeError:
                            continue

                # Stop if we've collected enough events
                if event_count > 5:
                    break

            # MUST have found conversation_id in metadata event
            assert conversation_id is not None, "conversation_id must be present in streaming metadata event"
            assert conversation_id_time is not None
            assert conversation_id_time < 3.0, f"Streaming conversation_id took {conversation_id_time:.2f}s (should be under 3s)"
            assert event_count <= 2, f"conversation_id should appear in first few events, found at event {event_count}"

    @pytest.mark.asyncio
    async def test_v03_conversation_id_timing_consistency(self, gateway_url, api_key):
        """Test that streaming and non-streaming have similar conversation_id timing."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test non-streaming timing
            start_time = time.time()
            non_streaming_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Non-streaming timing test",
                    "stream": False
                }
            )
            non_streaming_time = time.time() - start_time

            assert non_streaming_response.status_code == 200
            non_streaming_data = non_streaming_response.json()
            assert "conversation_id" in non_streaming_data

            # Test streaming timing
            start_time = time.time()
            streaming_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Streaming timing test",
                    "stream": True
                }
            )

            streaming_conversation_id_time = None
            async for line in streaming_response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            event_data = json.loads(data_str)
                            if event_data.get("type") == "metadata" and "conversation_id" in event_data:
                                streaming_conversation_id_time = time.time() - start_time
                                break
                        except json.JSONDecodeError:
                            continue

            assert streaming_conversation_id_time is not None

            # Both should be reasonably fast for AI processing
            assert non_streaming_time < 4.0, f"Non-streaming took {non_streaming_time:.2f}s (should be under 4s)"
            assert streaming_conversation_id_time < 4.0, f"Streaming took {streaming_conversation_id_time:.2f}s (should be under 4s)"

            # They should be within reasonable range of each other (within 2 seconds)
            time_diff = abs(non_streaming_time - streaming_conversation_id_time)
            assert time_diff < 2.0, f"Timing difference too large: {time_diff:.2f}s (non-streaming: {non_streaming_time:.2f}s, streaming: {streaming_conversation_id_time:.2f}s)"

            logger.info(f"Timing comparison - Non-streaming: {non_streaming_time:.3f}s, Streaming: {streaming_conversation_id_time:.3f}s, Diff: {time_diff:.3f}s")

    @pytest.mark.asyncio
    async def test_v03_conversation_continuity_with_explicit_id(self, gateway_url, api_key):
        """Test that both streaming and non-streaming can continue conversations with explicit conversation_id."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Start with non-streaming to get conversation_id
            response1 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "My favorite color is blue. Remember this.",
                    "stream": False
                }
            )

            assert response1.status_code == 200
            data1 = response1.json()
            assert "conversation_id" in data1
            conversation_id = data1["conversation_id"]

            # Continue with streaming using same conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "What is my favorite color?",
                    "conversation_id": conversation_id,
                    "stream": True
                }
            )

            assert response2.status_code == 200

            # Extract conversation_id from streaming response
            returned_conversation_id = None
            content_chunks = []

            async for line in response2.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            event_data = json.loads(data_str)

                            if event_data.get("type") == "metadata" and "conversation_id" in event_data:
                                returned_conversation_id = event_data["conversation_id"]
                            elif event_data.get("type") == "content":
                                content_chunks.append(event_data.get("content", ""))

                        except json.JSONDecodeError:
                            continue

                # Stop after collecting some content
                if len(content_chunks) > 3:
                    break

            # Should return same conversation_id
            assert returned_conversation_id == conversation_id, f"Expected {conversation_id}, got {returned_conversation_id}"

            # Response should reference the color from first message
            full_content = "".join(content_chunks).lower()
            assert "blue" in full_content, f"AI should remember blue color, but said: {full_content}"

            logger.info(f"✅ Conversation continuity maintained: {conversation_id}")

    @pytest.mark.asyncio
    async def test_v03_conversation_id_format_validation(self, gateway_url, api_key):
        """Test that conversation_id has consistent format in both streaming and non-streaming."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test non-streaming conversation_id format
            non_streaming_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Test conversation_id format",
                    "stream": False
                }
            )

            assert non_streaming_response.status_code == 200
            non_streaming_data = non_streaming_response.json()
            non_streaming_conv_id = non_streaming_data["conversation_id"]

            # Test streaming conversation_id format
            streaming_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Test streaming conversation_id format",
                    "stream": True
                }
            )

            streaming_conv_id = None
            async for line in streaming_response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            event_data = json.loads(data_str)
                            if event_data.get("type") == "metadata" and "conversation_id" in event_data:
                                streaming_conv_id = event_data["conversation_id"]
                                break
                        except json.JSONDecodeError:
                            continue

            assert streaming_conv_id is not None

            # Both should be valid UUIDs (36 characters with hyphens)
            import re
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

            assert re.match(uuid_pattern, non_streaming_conv_id), f"Non-streaming conversation_id invalid format: {non_streaming_conv_id}"
            assert re.match(uuid_pattern, streaming_conv_id), f"Streaming conversation_id invalid format: {streaming_conv_id}"

            # Both should be different (new conversations)
            assert non_streaming_conv_id != streaming_conv_id, "Each request should create unique conversation_id"

            logger.info(f"✅ Valid UUID formats - Non-streaming: {non_streaming_conv_id}, Streaming: {streaming_conv_id}")

    @pytest.mark.asyncio
    async def test_v03_missing_conversation_id_creates_new(self, gateway_url, api_key):
        """Test that missing conversation_id creates new conversation in both modes."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test non-streaming without conversation_id
            response1 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "First message without conversation_id",
                    "stream": False
                }
            )

            assert response1.status_code == 200
            data1 = response1.json()
            assert "conversation_id" in data1
            conv_id_1 = data1["conversation_id"]

            # Test streaming without conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Second message without conversation_id",
                    "stream": True
                }
            )

            conv_id_2 = None
            async for line in response2.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            event_data = json.loads(data_str)
                            if event_data.get("type") == "metadata" and "conversation_id" in event_data:
                                conv_id_2 = event_data["conversation_id"]
                                break
                        except json.JSONDecodeError:
                            continue

            assert conv_id_2 is not None

            # Should create different conversations
            assert conv_id_1 != conv_id_2, "Missing conversation_id should create unique conversations"

            logger.info(f"✅ New conversations created - Non-streaming: {conv_id_1}, Streaming: {conv_id_2}")

    @pytest.mark.asyncio
    async def test_v03_invalid_conversation_id_returns_404(self, gateway_url, api_key):
        """Test that invalid conversation_id returns 404 error (REST-compliant behavior)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            invalid_conv_id = "invalid-conversation-id-123"

            # Test non-streaming with invalid conversation_id - should return 404
            response1 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Test with invalid conversation_id",
                    "conversation_id": invalid_conv_id,
                    "stream": False
                }
            )

            # Should return 404 for invalid conversation_id (REST-compliant)
            assert response1.status_code == 404
            error_data = response1.json()
            assert "detail" in error_data
            assert "not found" in error_data["detail"].lower()

            # Test streaming with invalid conversation_id - should also return 404 for consistency
            response2 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Test streaming with invalid conversation_id",
                    "conversation_id": invalid_conv_id,
                    "stream": True
                }
            )

            # Streaming should also return 404 for unified behavior
            assert response2.status_code == 404
            error_data2 = response2.json()
            assert "detail" in error_data2
            assert "not found" in error_data2["detail"].lower()

            logger.info(f"✅ Invalid conversation_id correctly returns 404 error for both streaming and non-streaming")