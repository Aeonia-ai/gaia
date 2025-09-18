"""
Test progressive KB Agent response delivery.
Demonstrates immediate acknowledgment + detailed analysis pattern.
"""
import pytest
import json
import time
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.progressive_response import (
    KBAgentProgressiveResponse,
    create_kb_progressive_stream,
    example_kb_analysis_stream
)
from app.services.kb_progressive_integration import (
    progressive_interpret_knowledge,
    handle_kb_tool_progressively
)


class TestKBProgressiveResponse:
    """Test KB Agent progressive response delivery patterns."""

    @pytest.mark.asyncio
    async def test_basic_progressive_structure(self):
        """Test that progressive response has correct phase structure."""
        kb_response = KBAgentProgressiveResponse("interpret_knowledge", "development")

        # Mock detailed generator
        async def mock_detailed():
            yield {"type": "content", "content": "Detailed analysis result"}

        events = []
        async for event in kb_response.create_progressive_stream(
            mock_detailed(),
            conversation_id="test-conv-123"
        ):
            events.append(event)

        # Should have distinct phases
        phase_types = [event.get("type") for event in events]
        content_events = [e for e in events if e.get("type") == "content"]
        metadata_events = [e for e in events if e.get("type") == "metadata"]

        # Check structure
        assert len(metadata_events) >= 2  # Initial and complete metadata
        assert len(content_events) >= 3   # Immediate, analysis, detailed

        # Check immediate acknowledgment
        first_content = content_events[0]["content"]
        assert "Coordinating" in first_content
        assert "knowledge_management" in first_content

        # Check analysis status
        second_content = content_events[1]["content"]
        assert "Analyzing" in second_content or "development" in second_content

        # Check detailed content passed through
        detailed_content = content_events[2]["content"]
        assert "Detailed analysis result" in detailed_content

    @pytest.mark.asyncio
    async def test_operation_specific_messages(self):
        """Test that different operations have appropriate messages."""
        operations = [
            ("interpret_knowledge", "knowledge_management"),
            ("synthesize_information", "synthesis"),
            ("validate_rules", "validation"),
            ("execute_workflow", "workflow")
        ]

        for operation, expected_term in operations:
            kb_response = KBAgentProgressiveResponse(operation, "test")

            immediate_msg = kb_response.get_immediate_message()
            analysis_msg = kb_response.get_analysis_message()

            # Check immediate message contains operation-specific terms
            assert expected_term in immediate_msg or operation.split("_")[0] in immediate_msg

            # Check analysis message is descriptive
            assert len(analysis_msg) > 20
            assert "test" in analysis_msg  # Should include knowledge scope

    @pytest.mark.asyncio
    async def test_timing_requirements(self):
        """Test that progressive response meets timing requirements."""

        async def slow_detailed():
            """Simulate slow detailed processing."""
            await asyncio.sleep(0.5)  # Simulate processing
            yield {"type": "content", "content": "Slow result"}

        kb_response = KBAgentProgressiveResponse("interpret_knowledge")
        start_time = time.time()

        events = []
        immediate_delivered = None
        analysis_delivered = None

        async for event in kb_response.create_progressive_stream(slow_detailed()):
            current_time = time.time() - start_time
            events.append((event, current_time))

            if event.get("type") == "content":
                content = event.get("content", "")
                if "Coordinating" in content and immediate_delivered is None:
                    immediate_delivered = current_time
                elif "Analyzing" in content and analysis_delivered is None:
                    analysis_delivered = current_time

        # Timing requirements
        assert immediate_delivered is not None
        assert immediate_delivered < 0.1  # Immediate < 100ms

        assert analysis_delivered is not None
        assert analysis_delivered < 0.5   # Analysis status < 500ms

    @pytest.mark.asyncio
    async def test_conversation_id_propagation(self):
        """Test that conversation_id is properly propagated through events."""
        test_conv_id = "test-conversation-456"

        async def mock_detailed():
            yield {
                "type": "metadata",
                "some_detail": "test"
            }
            yield {
                "type": "content",
                "content": "Test content"
            }

        events = []
        async for event in create_kb_progressive_stream(
            operation="interpret_knowledge",
            detailed_generator=mock_detailed(),
            conversation_id=test_conv_id,
            knowledge_scope="test"
        ):
            events.append(event)

        # Check conversation_id in metadata events
        metadata_events = [e for e in events if e.get("type") == "metadata"]
        for metadata in metadata_events:
            assert metadata.get("conversation_id") == test_conv_id

    @pytest.mark.asyncio
    async def test_v03_format_compliance(self):
        """Test that events comply with V0.3 format."""

        async def mock_detailed():
            yield {"type": "content", "content": "Test"}
            yield {"type": "metadata", "test_key": "test_value"}

        events = []
        async for event in create_kb_progressive_stream(
            operation="interpret_knowledge",
            detailed_generator=mock_detailed(),
            conversation_id="test-conv",
            knowledge_scope="test"
        ):
            events.append(event)

        # All events should have required fields
        for event in events:
            assert "type" in event
            assert event["type"] in ["content", "metadata"]

            if event["type"] == "content":
                assert "content" in event
                assert isinstance(event["content"], str)

            if event["type"] == "metadata":
                # Should have provider/model info
                assert "provider" in event
                assert "model" in event
                assert event["provider"] == "gaia-kb-agent"

    @pytest.mark.asyncio
    async def test_error_handling_in_progressive_stream(self):
        """Test error handling during progressive delivery."""

        async def failing_detailed():
            yield {"type": "content", "content": "Start of analysis"}
            raise Exception("Simulated KB service error")

        events = []
        try:
            async for event in create_kb_progressive_stream(
                operation="interpret_knowledge",
                detailed_generator=failing_detailed(),
                conversation_id="test-conv",
                knowledge_scope="test"
            ):
                events.append(event)
        except Exception:
            pass  # Expected

        # Should still have immediate and analysis messages
        content_events = [e for e in events if e.get("type") == "content"]
        assert len(content_events) >= 2  # At least immediate + analysis

        # First should be immediate acknowledgment
        assert "Coordinating" in content_events[0]["content"]

    @pytest.mark.asyncio
    @patch('app.services.kb_progressive_integration.httpx.AsyncClient')
    async def test_progressive_interpret_knowledge_integration(self, mock_client):
        """Test integration with actual KB service call."""
        # Mock KB service response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "interpretation": "Test interpretation result",
            "reasoning": "Test reasoning",
            "sources_used": ["source1.md", "source2.md"],
            "performance": {
                "query_time": 1.5,
                "model_used": "claude-3-5-sonnet"
            }
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        events = []
        async for event in progressive_interpret_knowledge(
            query="Test KB analysis",
            context_path="development/architecture",
            conversation_id="test-conv",
            auth_header="test-api-key"
        ):
            events.append(event)

        # Should have progressive structure
        content_events = [e for e in events if e.get("type") == "content"]
        metadata_events = [e for e in events if e.get("type") == "metadata"]

        assert len(content_events) >= 3  # Immediate, analysis, detailed
        assert len(metadata_events) >= 2  # Initial, performance, complete

        # Check immediate message
        first_content = content_events[0]["content"]
        assert "Coordinating" in first_content
        assert "knowledge_management" in first_content

        # Check that interpretation result is included
        all_content = " ".join([e["content"] for e in content_events])
        assert "Test interpretation result" in all_content

        # Check sources section
        assert "Knowledge Sources" in all_content
        assert "source1.md" in all_content

        # Check performance metadata
        perf_metadata = [e for e in metadata_events if "kb_query_time" in e]
        assert len(perf_metadata) > 0
        assert perf_metadata[0]["kb_query_time"] == 1.5

    @pytest.mark.asyncio
    async def test_example_kb_analysis_stream(self):
        """Test the example KB analysis stream."""
        events = []
        async for event in example_kb_analysis_stream(
            query="Analyze KB Agent capabilities",
            conversation_id="example-conv"
        ):
            events.append(event)

        # Should demonstrate full progressive pattern
        content_events = [e for e in events if e.get("type") == "content"]
        metadata_events = [e for e in events if e.get("type") == "metadata"]

        assert len(content_events) >= 5  # Multiple progressive content chunks
        assert len(metadata_events) >= 2  # Initial and complete

        # Should contain example content
        all_content = " ".join([e["content"] for e in content_events])
        assert "Knowledge Base Analysis Results" in all_content
        assert "Key Capabilities" in all_content
        assert "Intelligence Features" in all_content

    @pytest.mark.asyncio
    async def test_knowledge_scope_messaging(self):
        """Test that knowledge scope affects messaging appropriately."""
        scopes = [
            ("development", "development knowledge"),
            ("architecture", "architecture knowledge"),
            ("deployment", "deployment knowledge"),
            ("general", "general knowledge")
        ]

        for scope, expected_term in scopes:
            kb_response = KBAgentProgressiveResponse("interpret_knowledge", scope)
            analysis_msg = kb_response.get_analysis_message()

            assert scope in analysis_msg or expected_term in analysis_msg

    @pytest.mark.asyncio
    async def test_handle_kb_tool_progressively_routing(self):
        """Test that tool routing works correctly."""

        # Test interpret_knowledge routing
        events = []
        with patch('app.services.kb_progressive_integration.progressive_interpret_knowledge') as mock_interpret:
            async def mock_generator():
                yield {"type": "content", "content": "Mocked interpretation"}

            mock_interpret.return_value = mock_generator()

            async for event in handle_kb_tool_progressively(
                tool_name="interpret_knowledge",
                tool_args={"query": "test", "context_path": "test"},
                conversation_id="test-conv",
                auth_header="test-key"
            ):
                events.append(event)

            # Should have called the progressive version
            mock_interpret.assert_called_once()

        # Test unknown tool fallback
        events = []
        async for event in handle_kb_tool_progressively(
            tool_name="unknown_tool",
            tool_args={},
            conversation_id="test-conv"
        ):
            events.append(event)

        content = events[0]["content"]
        assert "unknown_tool" in content
        assert "synchronous processing" in content