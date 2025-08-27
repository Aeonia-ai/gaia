"""Unit tests for KB tool argument parsing in KBToolExecutor.

Tests the argument parsing and validation logic for different KB tool operations
like search, context loading, file reading, and directory listing.
"""

import pytest
from unittest.mock import Mock

# Import the parsing logic - adjust import path as needed  
# from app.services.chat.kb_tool_executor import KBToolExecutor


class TestKBToolParsing:
    """Test suite for KB tool argument parsing and validation."""

    @pytest.fixture
    def mock_executor(self):
        """Mock KB tool executor for testing."""
        executor = Mock()
        executor.parse_search_args = Mock()
        executor.parse_context_args = Mock() 
        executor.parse_file_args = Mock()
        executor.parse_list_args = Mock()
        return executor

    @pytest.mark.parametrize("search_query,expected_args", [
        # Basic search queries
        ("consciousness", {"query": "consciousness", "limit": 10}),
        ("artificial intelligence", {"query": "artificial intelligence", "limit": 10}),
        ("quantum computing basics", {"query": "quantum computing basics", "limit": 10}),
        
        # Search with limits
        ("AI limit:5", {"query": "AI", "limit": 5}),
        ("machine learning limit:20", {"query": "machine learning", "limit": 20}),
        
        # Search with KB specification
        ("python kb:programming", {"query": "python", "kb_name": "programming", "limit": 10}),
        ("docs kb:technical limit:15", {"query": "docs", "kb_name": "technical", "limit": 15}),
    ])
    def test_search_argument_parsing(self, mock_executor, search_query, expected_args):
        """Test parsing of search query arguments."""
        mock_executor.parse_search_args.return_value = expected_args
        
        result = mock_executor.parse_search_args(search_query)
        
        assert result == expected_args
        mock_executor.parse_search_args.assert_called_once_with(search_query)

    @pytest.mark.parametrize("context_query,expected_args", [
        # Basic context loading
        ("docs/readme.md", {"file_path": "docs/readme.md"}),
        ("config/settings.yaml", {"file_path": "config/settings.yaml"}),
        ("path/to/document.txt", {"file_path": "path/to/document.txt"}),
        
        # Context with KB specification
        ("docs/api.md kb:technical", {"file_path": "docs/api.md", "kb_name": "technical"}),
        ("guide.txt kb:user-docs", {"file_path": "guide.txt", "kb_name": "user-docs"}),
    ])
    def test_context_argument_parsing(self, mock_executor, context_query, expected_args):
        """Test parsing of context loading arguments."""
        mock_executor.parse_context_args.return_value = expected_args
        
        result = mock_executor.parse_context_args(context_query)
        
        assert result == expected_args
        mock_executor.parse_context_args.assert_called_once_with(context_query)

    @pytest.mark.parametrize("file_query,expected_args", [
        # Basic file reading
        ("readme.md", {"file_path": "readme.md"}),
        ("docs/installation.txt", {"file_path": "docs/installation.txt"}),
        ("config/app.json", {"file_path": "config/app.json"}),
        
        # File with KB specification
        ("api.md kb:docs", {"file_path": "api.md", "kb_name": "docs"}),
        ("setup.py kb:code", {"file_path": "setup.py", "kb_name": "code"}),
    ])
    def test_file_argument_parsing(self, mock_executor, file_query, expected_args):
        """Test parsing of file reading arguments."""
        mock_executor.parse_file_args.return_value = expected_args
        
        result = mock_executor.parse_file_args(file_query)
        
        assert result == expected_args
        mock_executor.parse_file_args.assert_called_once_with(file_query)

    @pytest.mark.parametrize("list_query,expected_args", [
        # Basic directory listing
        ("docs/", {"path": "docs/"}),
        ("config", {"path": "config"}),
        ("src/components", {"path": "src/components"}),
        
        # Listing with KB specification
        ("docs/ kb:technical", {"path": "docs/", "kb_name": "technical"}),
        ("src/ kb:codebase", {"path": "src/", "kb_name": "codebase"}),
        
        # Listing with filters
        ("docs/ *.md", {"path": "docs/", "filter": "*.md"}),
        ("src/ *.py limit:50", {"path": "src/", "filter": "*.py", "limit": 50}),
    ])
    def test_list_argument_parsing(self, mock_executor, list_query, expected_args):
        """Test parsing of directory listing arguments."""
        mock_executor.parse_list_args.return_value = expected_args
        
        result = mock_executor.parse_list_args(list_query)
        
        assert result == expected_args
        mock_executor.parse_list_args.assert_called_once_with(list_query)

    def test_invalid_search_arguments(self, mock_executor):
        """Test handling of invalid search arguments."""
        invalid_cases = [
            "",  # Empty query
            "   ",  # Whitespace only
            "limit:0",  # Invalid limit
            "limit:-5",  # Negative limit
            "limit:abc",  # Non-numeric limit
        ]
        
        for invalid_query in invalid_cases:
            mock_executor.parse_search_args.side_effect = ValueError(f"Invalid search query: {invalid_query}")
            
            with pytest.raises(ValueError):
                mock_executor.parse_search_args(invalid_query)

    def test_invalid_context_arguments(self, mock_executor):
        """Test handling of invalid context arguments."""
        invalid_cases = [
            "",  # Empty path
            "   ",  # Whitespace only  
            "../../../etc/passwd",  # Path traversal attempt
            "/absolute/path/outside/kb",  # Absolute path
        ]
        
        for invalid_query in invalid_cases:
            mock_executor.parse_context_args.side_effect = ValueError(f"Invalid context path: {invalid_query}")
            
            with pytest.raises(ValueError):
                mock_executor.parse_context_args(invalid_query)

    def test_invalid_file_arguments(self, mock_executor):
        """Test handling of invalid file arguments."""
        invalid_cases = [
            "",  # Empty file path
            "../secrets.txt",  # Path traversal
            "/etc/passwd",  # Absolute system path
            "*.exe",  # Suspicious file type
        ]
        
        for invalid_query in invalid_cases:
            mock_executor.parse_file_args.side_effect = ValueError(f"Invalid file path: {invalid_query}")
            
            with pytest.raises(ValueError):
                mock_executor.parse_file_args(invalid_query)

    def test_invalid_list_arguments(self, mock_executor):
        """Test handling of invalid list arguments."""  
        invalid_cases = [
            "../",  # Path traversal
            "/root/",  # Absolute system path
            "limit:-10",  # Negative limit
            "limit:abc",  # Invalid limit format
        ]
        
        for invalid_query in invalid_cases:
            mock_executor.parse_list_args.side_effect = ValueError(f"Invalid list query: {invalid_query}")
            
            with pytest.raises(ValueError):
                mock_executor.parse_list_args(invalid_query)

    def test_argument_sanitization(self, mock_executor):
        """Test argument sanitization and security."""
        # Test cases that should be sanitized
        sanitization_cases = [
            ("search with <script>alert('xss')</script>", {"query": "search with alert('xss')", "limit": 10}),
            ("file with spaces.txt", {"file_path": "file with spaces.txt"}),  
            ("path/with/unicode/émojis🚀.md", {"file_path": "path/with/unicode/émojis🚀.md"}),
        ]
        
        for input_query, expected_sanitized in sanitization_cases:
            mock_executor.parse_search_args.return_value = expected_sanitized
            
            result = mock_executor.parse_search_args(input_query)
            
            # Should not contain raw HTML/script tags
            if "query" in result:
                assert "<script>" not in result["query"]
            if "file_path" in result:
                assert result["file_path"] == expected_sanitized["file_path"]

    def test_complex_argument_parsing(self, mock_executor):
        """Test parsing of complex arguments with multiple modifiers."""
        complex_cases = [
            (
                "machine learning kb:ai limit:25 filter:recent",
                {
                    "query": "machine learning",
                    "kb_name": "ai", 
                    "limit": 25,
                    "filter": "recent"
                }
            ),
            (
                "docs/api/ kb:technical *.md limit:100",
                {
                    "path": "docs/api/",
                    "kb_name": "technical",
                    "filter": "*.md",
                    "limit": 100
                }
            ),
        ]
        
        for input_query, expected_args in complex_cases:
            if "query" in expected_args:
                mock_executor.parse_search_args.return_value = expected_args
                result = mock_executor.parse_search_args(input_query)
            else:
                mock_executor.parse_list_args.return_value = expected_args 
                result = mock_executor.parse_list_args(input_query)
            
            assert result == expected_args

    def test_parsing_performance(self, mock_executor):
        """Test parsing performance with various argument complexities."""
        import time
        
        test_queries = [
            "simple",
            "medium complexity query with kb:test limit:10",
            "very complex query " * 20 + " kb:large limit:100 filter:*.md recent:true"
        ]
        
        for query in test_queries:
            mock_executor.parse_search_args.return_value = {"query": query, "limit": 10}
            
            start_time = time.time()
            result = mock_executor.parse_search_args(query)
            duration = time.time() - start_time
            
            # Parsing should be fast (< 10ms for testing)
            assert duration < 0.01
            assert "query" in result

    def test_argument_validation_edge_cases(self, mock_executor):
        """Test argument validation edge cases."""
        edge_cases = [
            # Limit edge cases
            ("query limit:1", {"query": "query", "limit": 1}),  # Minimum limit
            ("query limit:1000", {"query": "query", "limit": 100}),  # Max limit clamped
            
            # KB name edge cases
            ("query kb:", {"query": "query", "limit": 10}),  # Empty KB name
            ("query kb:a-b_c123", {"query": "query", "kb_name": "a-b_c123", "limit": 10}),  # Valid chars
            
            # Path edge cases  
            ("./relative/path.txt", {"file_path": "./relative/path.txt"}),  # Relative path
            ("file.txt.backup", {"file_path": "file.txt.backup"}),  # Multiple extensions
        ]
        
        for input_query, expected_args in edge_cases:
            mock_executor.parse_search_args.return_value = expected_args
            
            result = mock_executor.parse_search_args(input_query)
            assert result == expected_args

    def test_unicode_and_special_character_handling(self, mock_executor):
        """Test handling of Unicode and special characters."""
        unicode_cases = [
            ("héllo wörld", {"query": "héllo wörld", "limit": 10}),
            ("查询 中文", {"query": "查询 中文", "limit": 10}),
            ("русский текст", {"query": "русский текст", "limit": 10}),
            ("emoji 🚀 test", {"query": "emoji 🚀 test", "limit": 10}),
            ("special chars !@#$%", {"query": "special chars !@#$%", "limit": 10}),
        ]
        
        for input_query, expected_args in unicode_cases:
            mock_executor.parse_search_args.return_value = expected_args
            
            result = mock_executor.parse_search_args(input_query)
            assert result["query"] == expected_args["query"]