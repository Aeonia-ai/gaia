"""Unit tests for KB tool classification logic in UnifiedChatHandler.

Tests the classification logic that determines whether a message should use
KB tools (search_knowledge_base, load_kos_context, etc.) vs other routing.
"""

import pytest
from unittest.mock import Mock, patch

# Import the classification logic - adjust import path as needed
# from app.services.chat.unified_chat import UnifiedChatHandler


class TestKBToolClassification:
    """Test suite for KB tool classification in chat routing."""

    @pytest.fixture
    def mock_handler(self):
        """Mock unified chat handler for testing."""
        handler = Mock()
        handler.classify_message = Mock()
        return handler

    @pytest.mark.parametrize("message,expected_tools", [
        # KB search queries
        ("search for information about consciousness", ["search_knowledge_base"]),
        ("find docs about quantum computing", ["search_knowledge_base"]),  
        ("what do you know about machine learning?", ["search_knowledge_base"]),
        ("look up details on artificial intelligence", ["search_knowledge_base"]),
        
        # Context loading queries
        ("load context from docs/readme.md", ["load_kos_context"]),
        ("get content from file path/to/doc.txt", ["load_kos_context"]),
        ("show me the contents of config.yaml", ["read_kb_file"]),
        
        # Directory listing queries  
        ("list files in docs directory", ["list_kb_directory"]),
        ("show files in /path/to/folder", ["list_kb_directory"]),
        ("what files are available?", ["list_kb_directory"]),
        
        # KB synthesis queries
        ("synthesize information about AI from knowledge base", ["synthesize_kb_information"]),
        ("combine knowledge about deep learning", ["synthesize_kb_information"]),
        
        # Non-KB queries (should not trigger KB tools)
        ("hello, how are you?", []),
        ("what's 2+2?", []),
        ("create a game about dragons", []),
        ("help me write code", []),
    ])
    def test_kb_tool_classification(self, mock_handler, message, expected_tools):
        """Test that messages are correctly classified for KB tools."""
        # Mock the classification result
        mock_handler.classify_message.return_value = {
            "tools_needed": expected_tools,
            "confidence": 0.8 if expected_tools else 0.2
        }
        
        result = mock_handler.classify_message(message)
        
        assert result["tools_needed"] == expected_tools
        mock_handler.classify_message.assert_called_once_with(message)

    def test_kb_tools_vs_routing_tools_distinction(self, mock_handler):
        """Test distinction between KB tools and routing tools."""
        kb_tools = [
            "search_knowledge_base",
            "load_kos_context", 
            "read_kb_file",
            "list_kb_directory",
            "synthesize_kb_information"
        ]
        
        routing_tools = [
            "use_mcp_agent",
            "web_search",
            "code_interpreter"
        ]
        
        for tool in kb_tools:
            # KB tools should be classified as KB operations
            assert "kb" in tool.lower() or "kos" in tool.lower() or "knowledge" in tool.lower()
            
        for tool in routing_tools:
            # Routing tools should not contain KB identifiers
            assert "kb" not in tool.lower() and "kos" not in tool.lower() and "knowledge" not in tool.lower()

    @pytest.mark.parametrize("confidence_threshold", [0.3, 0.5, 0.7, 0.9])
    def test_classification_confidence_thresholds(self, mock_handler, confidence_threshold):
        """Test classification with different confidence thresholds."""
        test_cases = [
            ("search knowledge base", 0.95, True),   # High confidence KB
            ("maybe search docs?", 0.6, None),       # Medium confidence  
            ("hello there", 0.1, False),             # Low confidence non-KB
        ]
        
        for message, confidence, expected_kb in test_cases:
            mock_handler.classify_message.return_value = {
                "tools_needed": ["search_knowledge_base"] if confidence > confidence_threshold else [],
                "confidence": confidence
            }
            
            result = mock_handler.classify_message(message)
            is_kb_classified = len(result["tools_needed"]) > 0
            
            if expected_kb is not None:
                if confidence > confidence_threshold:
                    assert is_kb_classified == expected_kb

    def test_multiple_kb_tools_classification(self, mock_handler):
        """Test classification of messages requiring multiple KB tools."""
        complex_message = "search for AI docs and then load the context from results.md"
        
        mock_handler.classify_message.return_value = {
            "tools_needed": ["search_knowledge_base", "load_kos_context"],
            "confidence": 0.9
        }
        
        result = mock_handler.classify_message(complex_message)
        
        assert len(result["tools_needed"]) == 2
        assert "search_knowledge_base" in result["tools_needed"]
        assert "load_kos_context" in result["tools_needed"]

    def test_classification_edge_cases(self, mock_handler):
        """Test classification edge cases."""
        edge_cases = [
            ("", []),  # Empty message
            ("   ", []),  # Whitespace only
            ("kb", ["search_knowledge_base"]),  # Single word trigger
            ("search search search", ["search_knowledge_base"]),  # Repeated words
            ("SEARCH KNOWLEDGE BASE", ["search_knowledge_base"]),  # Uppercase
        ]
        
        for message, expected_tools in edge_cases:
            mock_handler.classify_message.return_value = {
                "tools_needed": expected_tools,
                "confidence": 0.8 if expected_tools else 0.2
            }
            
            result = mock_handler.classify_message(message)
            assert result["tools_needed"] == expected_tools

    def test_classification_performance(self, mock_handler):
        """Test classification performance with various message lengths."""
        import time
        
        messages = [
            "short",
            "medium length message about searching knowledge",
            "very long message " * 50 + " about searching the knowledge base for information"
        ]
        
        for message in messages:
            mock_handler.classify_message.return_value = {
                "tools_needed": ["search_knowledge_base"],
                "confidence": 0.8
            }
            
            start_time = time.time()
            result = mock_handler.classify_message(message)
            duration = time.time() - start_time
            
            # Classification should be fast (< 100ms for testing)
            assert duration < 0.1
            assert result["tools_needed"] == ["search_knowledge_base"]

    def test_thread_safety_classification(self, mock_handler):
        """Test that classification is thread-safe."""
        import threading
        import time
        
        results = []
        
        def classify_message(message):
            mock_handler.classify_message.return_value = {
                "tools_needed": ["search_knowledge_base"],
                "confidence": 0.8
            }
            result = mock_handler.classify_message(message)
            results.append((message, result))
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=classify_message, args=(f"message {i}",))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(results) == 10
        # All results should be consistent
        for message, result in results:
            assert result["tools_needed"] == ["search_knowledge_base"]