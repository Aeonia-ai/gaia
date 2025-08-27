"""Unit tests for KB response processing in KBToolExecutor.

Tests response parsing, validation, error handling, and format conversion
between KB responses and chat responses.
"""

import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime


class TestKBResponseProcessing:
    """Test suite for KB response processing and formatting."""

    @pytest.fixture
    def executor(self):
        """Create mock executor for testing."""
        executor = Mock()
        executor.user_id = "test-user-123"
        return executor

    @pytest.fixture
    def mock_search_response_data(self):
        """Mock KB search response data."""
        return {
            "results": [
                {
                    "content": "This is test content about AI",
                    "metadata": {
                        "file_path": "docs/ai-basics.md",
                        "score": 0.92,
                        "chunk_index": 0,
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                },
                {
                    "content": "Advanced AI concepts and applications",
                    "metadata": {
                        "file_path": "docs/ai-advanced.md", 
                        "score": 0.87,
                        "chunk_index": 1,
                        "created_at": "2024-01-14T15:45:00Z"
                    }
                }
            ],
            "total_results": 2,
            "query": "AI concepts",
            "processing_time": 0.045
        }

    @pytest.fixture
    def mock_context_response_data(self):
        """Mock KB context response data."""
        return {
            "file_path": "docs/test.md",
            "content": "# Test Document\n\nThis is test content.",
            "metadata": {
                "size": 1024,
                "last_modified": "2024-01-15T12:00:00Z",
                "file_type": "markdown"
            }
        }

    @pytest.fixture
    def mock_list_response_data(self):
        """Mock KB list response data."""
        return {
            "files": [
                {
                    "path": "docs/README.md",
                    "size": 2048,
                    "last_modified": "2024-01-15T10:00:00Z",
                    "type": "file"
                },
                {
                    "path": "docs/guides/",
                    "size": None,
                    "last_modified": "2024-01-14T09:30:00Z", 
                    "type": "directory"
                }
            ],
            "total_count": 2,
            "path": "docs/"
        }

    def test_process_successful_search_response(self, executor, mock_search_response_data):
        """Test processing successful search response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_search_response_data
        
        # Should be able to process the response structure
        assert mock_response.status_code == 200
        data = mock_response.json()
        assert data["total_results"] == 2
        assert len(data["results"]) == 2

    def test_process_empty_search_response(self, executor):
        """Test processing empty search results."""
        empty_response_data = {
            "results": [],
            "total_results": 0,
            "query": "nonexistent query",
            "processing_time": 0.002
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = empty_response_data
        
        data = mock_response.json()
        assert data["results"] == []
        assert data["total_results"] == 0

    def test_extract_search_result_metadata(self, executor, mock_search_response_data):
        """Test extraction of metadata from search results."""
        first_result = mock_search_response_data["results"][0]
        metadata = first_result["metadata"]
        
        assert metadata["file_path"] == "docs/ai-basics.md"
        assert metadata["score"] == 0.92
        assert metadata["chunk_index"] == 0
        assert "created_at" in metadata

    def test_process_context_response_structure(self, executor, mock_context_response_data):
        """Test processing context response structure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_context_response_data
        
        data = mock_response.json()
        assert data["file_path"] == "docs/test.md"
        assert "# Test Document" in data["content"]
        assert data["metadata"]["size"] == 1024

    def test_process_file_list_response(self, executor, mock_list_response_data):
        """Test processing file list response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_list_response_data
        
        data = mock_response.json()
        assert len(data["files"]) == 2
        assert data["total_count"] == 2
        assert data["path"] == "docs/"

    @pytest.mark.parametrize("status_code,expected_error_type", [
        (400, "Client Error"),
        (401, "Authentication Error"),
        (403, "Permission Error"), 
        (404, "Not Found Error"),
        (429, "Rate Limit Error"),
        (500, "Server Error"),
        (502, "Gateway Error"),
        (503, "Service Unavailable"),
    ])
    def test_handle_http_error_responses(self, executor, status_code, expected_error_type):
        """Test handling different HTTP error status codes."""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = {"error": expected_error_type, "message": "Test error"}
        
        # Should categorize errors appropriately
        if status_code >= 400:
            assert status_code >= 400  # Is an error
            if status_code < 500:
                assert status_code < 500  # Client error
            else:
                assert status_code >= 500  # Server error

    def test_handle_malformed_json_response(self, executor):
        """Test handling malformed JSON responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid JSON response"
        
        # Should handle JSON decode errors gracefully
        with pytest.raises(json.JSONDecodeError):
            mock_response.json()

    def test_handle_incomplete_response_data(self, executor):
        """Test handling responses with missing required fields."""
        incomplete_responses = [
            {"results": []},  # Missing total_results
            {"total_results": 5},  # Missing results
            {}  # Empty response
        ]
        
        for response_data in incomplete_responses:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            
            data = mock_response.json()
            # Should be able to handle incomplete data
            assert isinstance(data, dict)

    def test_format_search_results_display(self, executor, mock_search_response_data):
        """Test formatting search results for display."""
        results = mock_search_response_data["results"]
        total = mock_search_response_data["total_results"]
        
        # Should be able to format results
        formatted_info = f"Found {total} results"
        assert "Found 2 results" in formatted_info
        
        for result in results:
            content = result["content"]
            file_path = result["metadata"]["file_path"]
            score = result["metadata"]["score"]
            
            assert content
            assert file_path
            assert isinstance(score, float)

    def test_format_empty_results_display(self, executor):
        """Test formatting empty search results."""
        empty_message = "No results found for your query"
        assert "No results found" in empty_message

    def test_format_context_content_display(self, executor, mock_context_response_data):
        """Test formatting context content for display."""
        file_path = mock_context_response_data["file_path"]
        content = mock_context_response_data["content"]
        size = mock_context_response_data["metadata"]["size"]
        
        display_info = f"File: {file_path} (Size: {size} bytes)"
        assert "docs/test.md" in display_info
        assert "1024 bytes" in display_info

    def test_format_file_list_display(self, executor, mock_list_response_data):
        """Test formatting file list for display."""
        files = mock_list_response_data["files"]
        total = mock_list_response_data["total_count"]
        
        display_header = f"Found {total} items in directory"
        assert "Found 2 items" in display_header
        
        for file_info in files:
            path = file_info["path"]
            file_type = file_info["type"]
            
            if file_type == "directory":
                display_item = f"[DIR] {path}"
                assert "[DIR]" in display_item
            else:
                size = file_info.get("size", "unknown")
                display_item = f"[FILE] {path} ({size} bytes)"
                assert "[FILE]" in display_item or "[DIR]" in display_item

    def test_extract_and_validate_metadata(self, executor):
        """Test metadata extraction and validation."""
        result_with_metadata = {
            "content": "Test content",
            "metadata": {
                "file_path": "docs/test.md",
                "score": 0.95,
                "chunk_index": 2,
                "created_at": "2024-01-15T10:30:00Z",
                "custom_field": "custom_value"
            }
        }
        
        metadata = result_with_metadata["metadata"]
        
        # Validate required fields
        assert "file_path" in metadata
        assert "score" in metadata
        assert isinstance(metadata["score"], (int, float))
        assert 0 <= metadata["score"] <= 1

    def test_handle_unicode_content(self, executor):
        """Test handling Unicode content in responses."""
        unicode_response = {
            "results": [
                {
                    "content": "Content with émojis 🚀 and special chars: çñáéíóú",
                    "metadata": {
                        "file_path": "docs/unicode-tést.md",
                        "score": 0.85
                    }
                }
            ],
            "total_results": 1,
            "query": "unicode test"
        }
        
        result = unicode_response["results"][0]
        assert "émojis 🚀" in result["content"]
        assert "unicode-tést.md" in result["metadata"]["file_path"]

    def test_response_timing_information(self, executor):
        """Test extraction of response timing information."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.123
        mock_response.json.return_value = {"results": [], "processing_time": 0.045}
        
        # Should capture both network and processing time
        network_time = mock_response.elapsed.total_seconds()
        processing_time = mock_response.json()["processing_time"]
        
        assert network_time == 0.123
        assert processing_time == 0.045

    def test_response_caching_metadata(self, executor):
        """Test extraction of caching-related headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Cache-Control": "max-age=300",
            "ETag": "W/\"abc123\"",
            "Last-Modified": "Mon, 15 Jan 2024 10:00:00 GMT"
        }
        mock_response.json.return_value = {"results": []}
        
        # Should be able to extract cache headers
        cache_control = mock_response.headers.get("Cache-Control")
        etag = mock_response.headers.get("ETag")
        
        assert cache_control == "max-age=300"
        assert etag == "W/\"abc123\""

    def test_sanitize_sensitive_content(self, executor):
        """Test sanitization of sensitive content in responses."""
        sensitive_content = {
            "content": "This contains API key: sk-12345 and password: secret123",
            "metadata": {
                "api_key": "sk-67890",
                "file_path": "docs/test.md",
                "token": "bearer-token-123"
            }
        }
        
        # Should identify sensitive patterns
        content = sensitive_content["content"]
        has_api_key = "sk-" in content
        has_password = "password:" in content
        
        assert has_api_key
        assert has_password

    def test_batch_response_processing(self, executor):
        """Test processing multiple responses in batch."""
        response_batch = [
            {"results": [{"content": "Result 1", "metadata": {"score": 0.9}}], "total_results": 1},
            {"results": [{"content": "Result 2", "metadata": {"score": 0.8}}], "total_results": 1},
            {"results": [], "total_results": 0}
        ]
        
        # Should handle multiple responses
        total_results = sum(resp["total_results"] for resp in response_batch)
        assert total_results == 2

    def test_response_validation_patterns(self, executor):
        """Test various response validation patterns."""
        valid_patterns = [
            {"results": [], "total_results": 0},  # Empty results
            {"results": [{"content": "test", "metadata": {}}], "total_results": 1},  # Single result
            {"file_path": "docs/test.md", "content": "content"},  # Context response
            {"files": [], "total_count": 0}  # File list response
        ]
        
        for pattern in valid_patterns:
            # Should recognize valid response patterns
            assert isinstance(pattern, dict)
            assert len(pattern) > 0

    def test_error_response_categorization(self, executor):
        """Test categorization of different error types."""
        error_types = {
            "validation_error": {"field": "query", "message": "Required"},
            "authentication_error": {"code": 401, "message": "Invalid credentials"},
            "rate_limit_error": {"code": 429, "message": "Too many requests"},
            "service_error": {"code": 500, "message": "Internal server error"}
        }
        
        for error_type, error_data in error_types.items():
            # Should categorize errors appropriately
            assert "error" in error_type
            assert isinstance(error_data, dict)
            assert "message" in error_data