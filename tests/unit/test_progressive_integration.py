"""
Test progressive response integration with KB tools.
This verifies that the enhanced KB tools work with progressive delivery.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.chat.kb_tools import KBToolExecutor


class TestProgressiveIntegration:
    """Test progressive response integration."""

    @pytest.mark.asyncio
    async def test_kb_tool_executor_progressive_mode(self):
        """Test that KBToolExecutor supports progressive mode."""
        auth_principal = {"key": "test-key", "auth_type": "api_key"}

        # Test with progressive mode enabled
        executor = KBToolExecutor(
            auth_principal=auth_principal,
            progressive_mode=True,
            conversation_id="test-conv-123"
        )

        assert executor.progressive_mode is True
        assert executor.conversation_id == "test-conv-123"
        assert executor.headers["X-API-Key"] == "test-key"

    @pytest.mark.asyncio
    async def test_kb_tool_executor_fallback_mode(self):
        """Test that KBToolExecutor defaults to regular mode."""
        auth_principal = {"key": "test-key", "auth_type": "api_key"}

        # Test with default mode (progressive=False)
        executor = KBToolExecutor(auth_principal=auth_principal)

        assert executor.progressive_mode is False
        assert executor.conversation_id is None

    @pytest.mark.asyncio
    async def test_interpret_knowledge_progressive_check(self):
        """Test that interpret_knowledge checks progressive mode correctly."""
        auth_principal = {"key": "test-key", "auth_type": "api_key"}

        # Test with progressive mode disabled (should use regular path)
        executor = KBToolExecutor(auth_principal=auth_principal, progressive_mode=False)

        with patch.object(executor, '_interpret_knowledge') as mock_interpret:
            mock_interpret.return_value = {"success": True, "content": "Test response"}

            result = await executor.execute_tool("interpret_knowledge", {
                "query": "test query",
                "context_path": "/test",
                "mode": "decision"
            })

            # Should call the regular method
            mock_interpret.assert_called_once_with("test query", "/test", "decision")
            assert result == {"success": True, "content": "Test response"}

    @pytest.mark.asyncio
    async def test_interpret_knowledge_progressive_generator(self):
        """Test that interpret_knowledge uses progressive generator when enabled."""
        auth_principal = {"key": "test-key", "auth_type": "api_key"}

        # Test with progressive mode enabled
        executor = KBToolExecutor(
            auth_principal=auth_principal,
            progressive_mode=True,
            conversation_id="test-conv"
        )

        # Mock the progressive function
        async def mock_progressive_generator():
            yield {"type": "metadata", "phase": "immediate", "content": "Starting..."}
            yield {"type": "content", "content": "Progressive content"}
            yield {"type": "metadata", "phase": "complete", "total_time": 1500}

        with patch('app.services.kb_progressive_integration.progressive_interpret_knowledge') as mock_progressive:
            mock_progressive.return_value = mock_progressive_generator()

            # Execute the tool - should return a generator
            result = await executor.execute_tool("interpret_knowledge", {
                "query": "test query",
                "context_path": "/test",
                "mode": "decision"
            })

            # Should have called progressive function
            mock_progressive.assert_called_once_with(
                query="test query",
                context_path="/test",
                operation_mode="decision",
                conversation_id="test-conv",
                auth_header="test-key"
            )

    @pytest.mark.asyncio
    async def test_other_kb_tools_unchanged(self):
        """Test that other KB tools work normally regardless of progressive mode."""
        auth_principal = {"key": "test-key", "auth_type": "api_key"}

        for progressive_mode in [True, False]:
            executor = KBToolExecutor(
                auth_principal=auth_principal,
                progressive_mode=progressive_mode
            )

            with patch.object(executor, '_search_kb') as mock_search:
                mock_search.return_value = {"success": True, "content": "Search results"}

                result = await executor.execute_tool("search_knowledge_base", {
                    "query": "test query",
                    "limit": 10
                })

                # Should work the same regardless of progressive mode
                mock_search.assert_called_once_with("test query", 10)
                assert result == {"success": True, "content": "Search results"}

    def test_integration_ready(self):
        """Test that all integration components are ready."""
        # Verify that the imports work
        from app.services.progressive_response import ProgressiveResponse
        from app.services.kb_progressive_integration import progressive_interpret_knowledge
        from app.services.chat.kb_tools import KBToolExecutor

        # Should not raise any import errors
        assert ProgressiveResponse is not None
        assert progressive_interpret_knowledge is not None
        assert KBToolExecutor is not None

        # Verify enhanced constructor signature
        import inspect
        sig = inspect.signature(KBToolExecutor.__init__)
        params = list(sig.parameters.keys())

        assert 'progressive_mode' in params
        assert 'conversation_id' in params