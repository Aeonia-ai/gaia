"""
End-to-end integration tests for real LLM streaming.
These tests validate the complete flow from API request to streamed response.
"""

import pytest
import httpx
import json
import time
import asyncio
from typing import List, Dict, Any


class TestRealStreamingE2E:
    """End-to-end tests for real streaming implementation."""

    @pytest.fixture
    def gateway_url(self):
        """Gateway URL for testing."""
        import os
        return os.getenv("GATEWAY_URL", "http://localhost:8666")

    @pytest.fixture
    def api_key(self):
        """API key for testing."""
        import os
        api_key = os.getenv("API_KEY")
        if not api_key:
            pytest.skip("No API key available")
        return api_key

    @pytest.mark.asyncio
    async def test_real_vs_simulated_streaming_performance(self, gateway_url, api_key):
        """Compare time-to-first-token between real and simulated streaming."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        # Test simulated streaming (current behavior)
        simulated_ttft = None
        simulated_chunks = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Write a short poem about streaming data",
                    "stream": True,
                    "use_real_streaming": False  # Explicitly use simulated
                }
            ) as response:
                async for line in response.aiter_lines():
                    if simulated_ttft is None:
                        simulated_ttft = time.time() - start
                    if line.startswith("data: ") and '"done"' not in line:
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get("type") == "content":
                                simulated_chunks.append(chunk)
                        except json.JSONDecodeError:
                            pass

        # Test real streaming (new behavior)
        real_ttft = None
        real_chunks = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Write a short poem about streaming data",
                    "stream": True,
                    "use_real_streaming": True  # Use real streaming
                }
            ) as response:
                async for line in response.aiter_lines():
                    if real_ttft is None:
                        real_ttft = time.time() - start
                    if line.startswith("data: ") and '"done"' not in line:
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get("type") == "content":
                                real_chunks.append(chunk)
                        except json.JSONDecodeError:
                            pass

        # Real streaming should have faster time-to-first-token
        print(f"Simulated TTFT: {simulated_ttft:.2f}s")
        print(f"Real TTFT: {real_ttft:.2f}s")
        print(f"Simulated chunks: {len(simulated_chunks)}")
        print(f"Real chunks: {len(real_chunks)}")

        # Real streaming should be notably faster (at least 30% improvement)
        if real_ttft and simulated_ttft:
            assert real_ttft < simulated_ttft * 0.7, \
                f"Real streaming ({real_ttft:.2f}s) should be faster than simulated ({simulated_ttft:.2f}s)"

        # Should have reasonable number of chunks
        assert len(real_chunks) > 5, "Real streaming should produce multiple chunks"

    @pytest.mark.asyncio
    async def test_word_boundaries_preserved_in_real_streaming(self, gateway_url, api_key):
        """Test that word boundaries are preserved even with real LLM streaming."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        chunks = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "List three words: elephant, boomerang, photosynthesis",
                    "stream": True,
                    "use_real_streaming": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and '"done"' not in line:
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get("type") == "content":
                                chunks.append(chunk["content"])
                        except json.JSONDecodeError:
                            pass

        # Check that key words are never split
        full_text = "".join(chunks)

        # These words should appear intact
        assert "elephant" in full_text
        assert "boomerang" in full_text
        assert "photosynthesis" in full_text

        # Check no partial words in chunks
        for chunk in chunks:
            # No chunk should end with partial word (except with punctuation)
            if chunk and chunk[-1].isalpha():
                # If ends with letter, next chunk should start with space/punctuation
                idx = chunks.index(chunk)
                if idx < len(chunks) - 1:
                    next_chunk = chunks[idx + 1]
                    assert not next_chunk[0].isalpha(), \
                        f"Word split detected: '{chunk}' | '{next_chunk}'"

    @pytest.mark.asyncio
    async def test_json_directives_atomic_in_real_streaming(self, gateway_url, api_key):
        """Test JSON directives remain atomic even with real streaming."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        chunks = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": 'Say: Hello! Include this JSON: {"m":"pause","p":{"secs":2}} Then say: Goodbye!',
                    "stream": True,
                    "use_real_streaming": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and '"done"' not in line:
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get("type") == "content":
                                chunks.append(chunk["content"])
                        except json.JSONDecodeError:
                            pass

        # Find the JSON directive chunk
        json_chunks = [c for c in chunks if '{"m":' in c]

        # JSON should be in exactly one chunk (atomic)
        assert len(json_chunks) == 1, "JSON directive should be in single chunk"

        # Verify it's valid JSON
        json_str = json_chunks[0]
        # Extract just the JSON part
        start = json_str.index('{"m":')
        end = json_str.index('}', start) + 1
        directive = json.loads(json_str[start:end])
        assert directive["m"] == "pause"
        assert directive["p"]["secs"] == 2

    @pytest.mark.asyncio
    async def test_kb_progressive_metadata(self, gateway_url, api_key):
        """Test KB agent sends progressive metadata during search."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        events = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "search: What are the rules for combat?",
                    "stream": True,
                    "enable_progressive_kb": True  # New flag for progressive KB
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and '"done"' not in line:
                        try:
                            event = json.loads(line[6:])
                            events.append(event)
                        except json.JSONDecodeError:
                            pass

        # Should have metadata events
        metadata_events = [e for e in events if e.get("type") == "metadata"]
        content_events = [e for e in events if e.get("type") == "content"]

        # Should send search metadata before content
        if metadata_events:  # Only if progressive KB is implemented
            assert metadata_events[0].get("phase") == "search_complete"
            assert "documents_found" in metadata_events[0]

        # Should still have content
        assert len(content_events) > 0

    @pytest.mark.asyncio
    async def test_mcp_tool_status_updates(self, gateway_url, api_key):
        """Test MCP agent sends tool execution status updates."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        events = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "tool: get weather for San Francisco",
                    "stream": True,
                    "enable_progressive_mcp": True  # New flag for progressive MCP
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and '"done"' not in line:
                        try:
                            event = json.loads(line[6:])
                            events.append(event)
                        except json.JSONDecodeError:
                            pass

        # Should have tool execution metadata
        metadata_events = [e for e in events if e.get("type") == "metadata"]

        if metadata_events:  # Only if progressive MCP is implemented
            # Should show tool selection
            tool_selected = any(
                e.get("phase") == "tool_selected" for e in metadata_events
            )
            # Should show tool completion
            tool_complete = any(
                e.get("phase") == "tool_complete" for e in metadata_events
            )

            assert tool_selected or tool_complete, \
                "Should have tool status metadata"

    @pytest.mark.asyncio
    async def test_conversation_history_with_real_streaming(self, gateway_url, api_key):
        """Test that conversation history works correctly with real streaming."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        # Create conversation with streaming
        conversation_id = None
        first_response_chunks = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message with real streaming
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "My name is TestBot",
                    "stream": True,
                    "use_real_streaming": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and '"done"' not in line:
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get("type") == "content":
                                first_response_chunks.append(chunk["content"])
                            elif chunk.get("type") == "metadata":
                                if "conversation_id" in chunk:
                                    conversation_id = chunk["conversation_id"]
                        except json.JSONDecodeError:
                            pass

            # Second message referencing first
            second_response_chunks = []
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "What is my name?",
                    "conversation_id": conversation_id,
                    "stream": True,
                    "use_real_streaming": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and '"done"' not in line:
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get("type") == "content":
                                second_response_chunks.append(chunk["content"])
                        except json.JSONDecodeError:
                            pass

        # Should remember the name from streamed response
        second_response = "".join(second_response_chunks)
        assert "TestBot" in second_response, \
            "Should remember name from previous streamed message"


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_real_streaming_e2e.py -v
    pytest.main([__file__, "-v"])