"""
Unit tests for real LLM streaming implementation.
Written in TDD style - these tests define the expected behavior
BEFORE implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from typing import AsyncGenerator, Dict, Any, List

# Test the core streaming behaviors we want


class TestRealLLMStreaming:
    """Define expected behavior for real LLM streaming."""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service with streaming capability."""
        service = MagicMock()

        # Setup non-streaming method (current behavior)
        service.chat_completion = AsyncMock(return_value={
            "response": "Complete response text",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "usage": {"total_tokens": 100}
        })

        # Setup streaming method (new behavior)
        async def mock_stream():
            chunks = [
                {"type": "content", "content": "Hello "},
                {"type": "content", "content": "world! "},
                {"type": "content", "content": "How are you?"},
                {"type": "metadata", "model": "gpt-4o-mini", "provider": "openai"}
            ]
            for chunk in chunks:
                yield chunk
                await asyncio.sleep(0.01)  # Simulate network delay

        service.chat_completion_stream = mock_stream
        return service

    @pytest.mark.asyncio
    async def test_direct_llm_uses_real_streaming(self, mock_llm_service):
        """Test that direct LLM path can use real streaming."""
        from app.services.chat.unified_chat import UnifiedChatHandler
        from app.services.chat.streaming_implementation import patch_unified_chat_handler

        # Patch the handler with streaming methods
        patch_unified_chat_handler()

        handler = UnifiedChatHandler()
        handler.llm_service = mock_llm_service

        # Configure to use real streaming
        chunks = []
        async for chunk in handler.stream_response(
            message="Test message",
            use_real_streaming=True,  # New parameter
            route_type="direct"
        ):
            chunks.append(chunk)

        # Should have multiple chunks (not one big chunk)
        print(f"DEBUG: Got {len(chunks)} chunks: {chunks}")
        assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}: {chunks}"
        # Check that we got some content
        assert any("Hello" in str(c) for c in chunks)

    @pytest.mark.asyncio
    async def test_streaming_accumulates_for_history(self, mock_llm_service):
        """Test that streamed responses are accumulated for conversation history."""
        from app.services.chat.unified_chat import UnifiedChatHandler

        handler = UnifiedChatHandler()
        handler.llm_service = mock_llm_service
        handler.conversation_store = MagicMock()

        conversation_id = "test-conv-123"
        chunks = []

        async for chunk in handler.stream_response(
            message="Test",
            conversation_id=conversation_id,
            use_real_streaming=True,
            route_type="direct"
        ):
            if chunk.get("type") == "content":
                chunks.append(chunk.get("content", ""))

        # Verify complete response was saved
        handler.conversation_store.add_message.assert_called()
        call_args = handler.conversation_store.add_message.call_args

        # Should save the complete accumulated response
        assert call_args[0][0] == conversation_id
        assert call_args[0][1] == "assistant"
        assert call_args[0][2] == "Hello world! How are you?"  # Full text

    @pytest.mark.asyncio
    async def test_streaming_preserves_word_boundaries(self, mock_llm_service):
        """Test that StreamBuffer is still used with real streaming."""
        from app.services.chat.unified_chat import UnifiedChatHandler
        from app.services.streaming_buffer import StreamBuffer

        handler = UnifiedChatHandler()
        handler.llm_service = mock_llm_service

        # Mock LLM to send badly chunked content
        async def bad_chunks():
            # Simulate LLM sending partial words
            yield {"type": "content", "content": "Hel"}
            yield {"type": "content", "content": "lo wo"}
            yield {"type": "content", "content": "rld!"}

        handler.llm_service.chat_completion_stream = bad_chunks

        chunks = []
        async for chunk in handler.stream_response(
            message="Test",
            use_real_streaming=True,
            route_type="direct"
        ):
            if chunk.get("type") == "content":
                chunks.append(chunk.get("content"))

        # Should never have partial words
        assert "Hel" not in chunks
        assert "lo wo" not in chunks
        # Should have complete words
        assert any("Hello" in c for c in chunks)
        assert any("world!" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_fallback_when_streaming_unavailable(self):
        """Test graceful fallback to complete response when streaming fails."""
        from app.services.chat.unified_chat import UnifiedChatHandler

        handler = UnifiedChatHandler()
        handler.llm_service = MagicMock()

        # Make streaming fail
        handler.llm_service.chat_completion_stream = AsyncMock(
            side_effect=NotImplementedError("Streaming not supported")
        )

        # But complete response works
        handler.llm_service.chat_completion = AsyncMock(return_value={
            "response": "Fallback complete response",
            "model": "gpt-4o-mini"
        })

        chunks = []
        async for chunk in handler.stream_response(
            message="Test",
            use_real_streaming=True,  # Request streaming
            route_type="direct"
        ):
            chunks.append(chunk)

        # Should have fallen back to complete response
        assert handler.llm_service.chat_completion.called
        full_text = "".join(c.get("content", "") for c in chunks)
        assert "Fallback complete response" in full_text

    @pytest.mark.asyncio
    async def test_streaming_with_json_directives(self):
        """Test that JSON directives stay atomic even with real streaming."""
        from app.services.chat.unified_chat import UnifiedChatHandler

        handler = UnifiedChatHandler()

        # Mock streaming that splits JSON badly
        async def json_stream():
            yield {"type": "content", "content": "I'll spawn "}
            yield {"type": "content", "content": '{"m":"'}
            yield {"type": "content", "content": 'pause","p":'}
            yield {"type": "content", "content": '{"secs":1.5}}'}
            yield {"type": "content", "content": " for you!"}

        handler.llm_service = MagicMock()
        handler.llm_service.chat_completion_stream = json_stream

        chunks = []
        async for chunk in handler.stream_response(
            message="Test",
            use_real_streaming=True,
            route_type="direct"
        ):
            if chunk.get("type") == "content":
                chunks.append(chunk.get("content"))

        # JSON should be in one atomic chunk
        json_chunks = [c for c in chunks if "{" in c]
        assert len(json_chunks) == 1
        assert json_chunks[0] == '{"m":"pause","p":{"secs":1.5}}'

    @pytest.mark.asyncio
    async def test_streaming_disabled_for_kb_tools(self):
        """Test that KB tools path doesn't try to use real streaming."""
        from app.services.chat.unified_chat import UnifiedChatHandler

        handler = UnifiedChatHandler()
        handler.kb_agent = MagicMock()
        handler.kb_agent.process = AsyncMock(return_value="KB response")

        chunks = []
        async for chunk in handler.stream_response(
            message="Search for something",
            use_real_streaming=True,  # Request streaming
            route_type="kb_tools"  # But using KB route
        ):
            chunks.append(chunk)

        # Should use KB agent's complete response
        handler.kb_agent.process.assert_called_once()
        # Should still simulate streaming of the complete response
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_streaming_disabled_for_mcp_agent(self):
        """Test that MCP agent path doesn't try to use real streaming."""
        from app.services.chat.unified_chat import UnifiedChatHandler

        handler = UnifiedChatHandler()
        handler.mcp_agent = MagicMock()
        handler.mcp_agent.process_request = AsyncMock(return_value={
            "response": "MCP response"
        })

        chunks = []
        async for chunk in handler.stream_response(
            message="Execute tool",
            use_real_streaming=True,  # Request streaming
            route_type="mcp_agent"  # But using MCP route
        ):
            chunks.append(chunk)

        # Should use MCP agent's complete response
        handler.mcp_agent.process_request.assert_called_once()
        # Should still simulate streaming
        assert len(chunks) > 0


class TestKBAgentProgressiveStreaming:
    """Define expected behavior for KB agent progressive streaming."""

    @pytest.mark.asyncio
    async def test_kb_sends_metadata_then_content(self):
        """Test KB agent sends search metadata before streaming content."""
        from app.services.kb.kb_agent_streaming import StreamingKBAgent as KBAgent

        agent = KBAgent()
        agent.search_kb = AsyncMock(return_value=[
            {"path": "doc1.md", "content": "Test content"},
            {"path": "doc2.md", "content": "More content"}
        ])

        # Mock LLM streaming
        async def llm_stream(*args, **kwargs):
            yield {"content": "Based on the documents, "}
            yield {"content": "here is the answer."}

        agent.llm.chat_completion_stream = llm_stream

        events = []
        async for event in agent.process_streaming("test query", stream=True):
            events.append(event)

        # First event should be search metadata
        assert events[0]["type"] == "metadata"
        assert events[0]["phase"] == "search_complete"
        assert events[0]["documents_found"] == 2

        # Then content chunks
        content_events = [e for e in events if e["type"] == "content"]
        assert len(content_events) >= 2

        # Finally completion metadata
        assert events[-1]["type"] == "metadata"
        assert events[-1]["phase"] == "complete"

    @pytest.mark.asyncio
    async def test_kb_handles_no_results(self):
        """Test KB agent handles case when no documents found."""
        from app.services.kb.kb_agent_streaming import StreamingKBAgent as KBAgent

        agent = KBAgent()
        agent.search_kb = AsyncMock(return_value=[])  # No results

        events = []
        async for event in agent.process_streaming("unknown query", stream=True):
            events.append(event)

        # Should send metadata about no results
        assert events[0]["type"] == "metadata"
        assert events[0]["documents_found"] == 0

        # Should send helpful message
        assert events[1]["type"] == "content"
        assert "couldn't find" in events[1]["content"].lower()


class TestMCPAgentProgressiveStreaming:
    """Define expected behavior for MCP agent progressive streaming."""

    @pytest.mark.asyncio
    async def test_mcp_sends_tool_status_then_streams(self):
        """Test MCP agent sends tool execution status then streams response."""
        from app.services.chat.mcp_agent_streaming import MCPAgent

        agent = MCPAgent()
        agent._select_tool = MagicMock(return_value="weather_tool")
        agent._execute_tool = AsyncMock(return_value={
            "temperature": 72,
            "conditions": "sunny",
            "narrative": "The weather is beautiful today..."  # Triggers streaming
        })

        # Mock LLM streaming for narrative
        async def llm_stream(*args, **kwargs):
            yield {"content": "The weather is "}
            yield {"content": "beautiful today with "}
            yield {"content": "clear sunny skies."}

        agent.streaming_agent.llm.chat_completion_stream = llm_stream

        events = []
        async for event in agent.process_streaming(
            {"tool": "weather", "location": "SF"},
            stream=True
        ):
            events.append(event)

        # Should send tool selection metadata
        assert events[0]["type"] == "metadata"
        assert events[0]["phase"] == "tool_selected"
        assert events[0]["tool"] == "weather_tool"

        # Should send tool completion metadata
        assert events[1]["type"] == "metadata"
        assert events[1]["phase"] == "tool_complete"

        # Then stream the narrative
        content_events = [e for e in events if e["type"] == "content"]
        assert len(content_events) >= 3

    @pytest.mark.asyncio
    async def test_mcp_doesnt_stream_json_results(self):
        """Test MCP agent doesn't stream pure JSON tool results."""
        from app.services.chat.mcp_agent_streaming import MCPAgent

        agent = MCPAgent()
        agent._select_tool = MagicMock(return_value="data_tool")
        agent._execute_tool = AsyncMock(return_value={
            "data": [1, 2, 3, 4, 5],
            "type": "array"
            # No narrative field - shouldn't stream
        })

        events = []
        async for event in agent.process_streaming(
            {"tool": "data"},
            stream=True  # Requesting streaming
        ):
            events.append(event)

        # Should NOT stream, just return complete JSON
        content_events = [e for e in events if e["type"] == "content"]
        assert len(content_events) == 1  # Single chunk
        assert '"data": [1, 2, 3, 4, 5]' in content_events[0]["content"]


if __name__ == "__main__":
    # Run with: pytest tests/unit/test_real_streaming.py -v
    pytest.main([__file__, "-v"])