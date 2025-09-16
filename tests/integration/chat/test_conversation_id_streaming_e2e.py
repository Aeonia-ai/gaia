"""
Integration tests for conversation_id delivery in V0.3 streaming responses.

Tests the complete flow from HTTP request through streaming response,
ensuring conversation_id is delivered early in the stream via metadata events.
"""
import pytest
import httpx
import json
import asyncio
import re
from typing import List, Dict, Any, Optional
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_conversation_id_streaming_e2e")


@pytest.mark.integration
@pytest.mark.requires_db
class TestConversationIdStreamingE2E:
    """End-to-end tests for conversation_id in streaming responses"""

    @pytest.fixture
    def gateway_url(self):
        """Gateway URL for accessing chat endpoints."""
        import os
        return os.getenv("GATEWAY_URL", "http://gateway:8000")

    @pytest.fixture
    def api_key(self):
        """API key for testing."""
        import os
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
        if not api_key:
            pytest.skip("No API key available")
        return api_key

    async def parse_sse_stream(self, response) -> List[Dict[str, Any]]:
        """Parse SSE stream and return list of events"""
        events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]  # Remove "data: " prefix
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    events.append(chunk)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse SSE data: {data_str}")
        return events

    def extract_conversation_id_from_events(self, events: List[Dict[str, Any]]) -> Optional[str]:
        """Extract conversation_id from list of SSE events"""
        for event in events:
            if event.get("type") == "metadata" and "conversation_id" in event:
                return event["conversation_id"]
            # Also check if conversation_id is at root level (for compatibility)
            if "conversation_id" in event:
                return event["conversation_id"]
        return None

    @pytest.mark.asyncio
    async def test_v03_streaming_delivers_conversation_id_new_conversation(self, gateway_url, api_key):
        """Test that V0.3 streaming delivers conversation_id for new conversations"""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "X-Response-Format": "v0.3"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Hello, start a new conversation",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200

                # Parse SSE events
                events = await self.parse_sse_stream(response)

                # Verify we got events
                assert len(events) > 0, "Should receive at least one SSE event"

                # Extract conversation_id
                conversation_id = self.extract_conversation_id_from_events(events)

                # Verify conversation_id was delivered
                assert conversation_id is not None, f"conversation_id not found in events: {events}"
                assert isinstance(conversation_id, str), "conversation_id should be a string"
                assert len(conversation_id) > 0, "conversation_id should not be empty"

                # Verify it looks like a UUID (basic format check)
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                assert re.match(uuid_pattern, conversation_id, re.IGNORECASE), \
                    f"conversation_id should be UUID format: {conversation_id}"

                logger.info(f"✅ New conversation created with ID: {conversation_id}")

    @pytest.mark.asyncio
    async def test_v03_streaming_conversation_id_appears_early(self, gateway_url, api_key):
        """Test that conversation_id appears in early events, not just at the end"""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "X-Response-Format": "v0.3"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Tell me a long story about artificial intelligence",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200

                events = []
                conversation_id_event_index = None

                # Process events one by one to track when conversation_id appears
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_part = line[6:]
                        if data_part == "[DONE]":
                            break
                        try:
                            event = json.loads(data_part)
                            events.append(event)

                            # Check if this event contains conversation_id
                            if conversation_id_event_index is None:
                                if (event.get("type") == "metadata" and "conversation_id" in event) or \
                                   "conversation_id" in event:
                                    conversation_id_event_index = len(events) - 1
                                    logger.info(f"Found conversation_id in event {conversation_id_event_index}: {event}")
                        except json.JSONDecodeError:
                            continue

                # Verify conversation_id appeared early
                assert conversation_id_event_index is not None, "conversation_id not found in any event"
                assert conversation_id_event_index <= 2, \
                    f"conversation_id should appear in first 3 events, found at index {conversation_id_event_index}"

                logger.info(f"✅ conversation_id appeared at event index {conversation_id_event_index} out of {len(events)} total events")

    @pytest.mark.asyncio
    async def test_v03_streaming_resume_existing_conversation(self, gateway_url, api_key):
        """Test that streaming works correctly when resuming an existing conversation"""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "X-Response-Format": "v0.3"
        }

        # First, create a conversation
        async with httpx.AsyncClient(timeout=30.0) as client:
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Hello, this is message 1",
                    "stream": False  # Non-streaming to get conversation_id easily
                }
            )
            assert response1.status_code == 200

            data1 = response1.json()
            assert "conversation_id" in data1, f"conversation_id missing from response: {data1}"
            conversation_id = data1["conversation_id"]

            logger.info(f"Created conversation: {conversation_id}")

        # Now, resume with streaming
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "This is message 2, continuing our conversation",
                    "conversation_id": conversation_id,
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200

                events = await self.parse_sse_stream(response)

                # Extract conversation_id from stream
                streamed_conversation_id = self.extract_conversation_id_from_events(events)

                # Verify the same conversation_id is returned
                assert streamed_conversation_id == conversation_id, \
                    f"Streamed conversation_id {streamed_conversation_id} should match original {conversation_id}"

                logger.info(f"✅ Successfully resumed conversation: {conversation_id}")

    @pytest.mark.asyncio
    async def test_v03_streaming_handles_invalid_conversation_id(self, gateway_url, api_key):
        """Test that streaming handles invalid conversation_id gracefully"""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "X-Response-Format": "v0.3"
        }

        invalid_conversation_id = "invalid-uuid-123"

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Try to resume invalid conversation",
                    "conversation_id": invalid_conversation_id,
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200

                events = await self.parse_sse_stream(response)

                # Extract conversation_id from stream
                actual_conversation_id = self.extract_conversation_id_from_events(events)

                # Should create a new conversation, not use the invalid ID
                assert actual_conversation_id is not None, "Should create new conversation_id"
                assert actual_conversation_id != invalid_conversation_id, \
                    "Should not use invalid conversation_id"

                # Verify it's a valid UUID format
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                assert re.match(uuid_pattern, actual_conversation_id, re.IGNORECASE), \
                    f"New conversation_id should be valid UUID: {actual_conversation_id}"

                logger.info(f"✅ Created new conversation {actual_conversation_id} when invalid ID {invalid_conversation_id} was provided")

    @pytest.mark.asyncio
    async def test_conversation_id_consistency_streaming_vs_nonstreaming(self, gateway_url, api_key):
        """Test that conversation_id behavior is consistent between streaming and non-streaming"""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "X-Response-Format": "v0.3"
        }

        # Test 1: New conversation - non-streaming
        async with httpx.AsyncClient(timeout=30.0) as client:
            response_ns = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Non-streaming new conversation",
                    "stream": False
                }
            )
            assert response_ns.status_code == 200
            data_ns = response_ns.json()
            conv_id_ns = data_ns["conversation_id"]

        # Test 2: New conversation - streaming
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Streaming new conversation",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                events = await self.parse_sse_stream(response)
                conv_id_s = self.extract_conversation_id_from_events(events)

        # Verify both created valid conversation IDs
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, conv_id_ns, re.IGNORECASE), "Non-streaming should create valid UUID"
        assert re.match(uuid_pattern, conv_id_s, re.IGNORECASE), "Streaming should create valid UUID"
        assert conv_id_ns != conv_id_s, "Should create different conversation IDs"

        logger.info(f"✅ Consistent behavior: Non-streaming={conv_id_ns}, Streaming={conv_id_s}")

    @pytest.mark.asyncio
    async def test_metadata_event_structure(self, gateway_url, api_key):
        """Test that metadata event containing conversation_id has correct structure"""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "X-Response-Format": "v0.3"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Test metadata structure",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200

                events = await self.parse_sse_stream(response)

                # Find metadata event with conversation_id
                metadata_event = None
                for event in events:
                    if event.get("type") == "metadata" and "conversation_id" in event:
                        metadata_event = event
                        break

                assert metadata_event is not None, f"No metadata event with conversation_id found in: {events}"

                # Verify metadata event structure
                assert metadata_event["type"] == "metadata"
                assert "conversation_id" in metadata_event
                assert "timestamp" in metadata_event or "model" in metadata_event, \
                    "Metadata should include additional context (timestamp or model)"

                # Verify conversation_id format
                conversation_id = metadata_event["conversation_id"]
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                assert re.match(uuid_pattern, conversation_id, re.IGNORECASE), \
                    f"conversation_id in metadata should be valid UUID: {conversation_id}"

                logger.info(f"✅ Metadata event structure valid: {metadata_event}")

    @pytest.mark.asyncio
    async def test_v03_streaming_conversation_id_with_explicit_new(self, gateway_url, api_key):
        """Test streaming behavior when conversation_id='new' is explicitly specified"""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "X-Response-Format": "v0.3"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Explicitly request new conversation",
                    "conversation_id": "new",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200

                events = await self.parse_sse_stream(response)
                conversation_id = self.extract_conversation_id_from_events(events)

                # Should create new conversation
                assert conversation_id is not None, "Should create new conversation when 'new' specified"
                assert conversation_id != "new", "Should not return literal 'new' as conversation_id"

                # Verify UUID format
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                assert re.match(uuid_pattern, conversation_id, re.IGNORECASE), \
                    f"conversation_id should be valid UUID: {conversation_id}"

                logger.info(f"✅ Created new conversation when 'new' specified: {conversation_id}")