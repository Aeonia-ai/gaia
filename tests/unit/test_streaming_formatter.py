"""
Unit tests for the streaming formatter service.
Tests OpenAI-compatible streaming response formatting.
"""
import pytest
import json
import time
from unittest.mock import patch
from app.services.streaming_formatter import create_openai_compatible_stream


class TestStreamingFormatter:
    """Test the streaming formatter functions"""
    
    async def async_generator(self, chunks):
        """Helper to create async generator from list"""
        for chunk in chunks:
            yield chunk
    
    @pytest.mark.asyncio
    async def test_create_openai_compatible_stream_basic(self):
        """Test basic streaming format conversion"""
        # Input chunks
        chunks = [
            {"type": "content", "content": "Hello"},
            {"type": "content", "content": " world"},
            {"type": "content", "content": "!"}
        ]
        
        # Collect output
        output = []
        async for chunk in create_openai_compatible_stream(
            self.async_generator(chunks), 
            model="gpt-4"
        ):
            output.append(chunk)
        
        # Should have 3 content chunks + final chunk + DONE
        assert len(output) == 5
        
        # Check content chunks
        for i in range(3):
            assert output[i].startswith("data: ")
            data = json.loads(output[i][6:])  # Skip "data: "
            assert data["object"] == "chat.completion.chunk"
            assert data["model"] == "gpt-4"
            assert data["choices"][0]["delta"]["content"] == chunks[i]["content"]
            assert data["choices"][0]["finish_reason"] is None
        
        # Check final chunk
        final_data = json.loads(output[3][6:])
        assert final_data["choices"][0]["delta"] == {}
        assert final_data["choices"][0]["finish_reason"] == "stop"
        
        # Check DONE message
        assert output[4] == "data: [DONE]\n\n"
    
    @pytest.mark.asyncio
    async def test_create_openai_compatible_stream_empty(self):
        """Test streaming with no content chunks"""
        chunks = []
        
        output = []
        async for chunk in create_openai_compatible_stream(
            self.async_generator(chunks), 
            model="claude-3"
        ):
            output.append(chunk)
        
        # Should have final chunk + DONE only
        assert len(output) == 2
        
        # Check final chunk
        final_data = json.loads(output[0][6:])
        assert final_data["choices"][0]["finish_reason"] == "stop"
        assert output[1] == "data: [DONE]\n\n"
    
    @pytest.mark.asyncio
    async def test_create_openai_compatible_stream_non_content_chunks(self):
        """Test that non-content chunks are filtered out"""
        chunks = [
            {"type": "metadata", "data": "ignored"},
            {"type": "content", "content": "Hello"},
            {"type": "error", "message": "ignored"},
            {"type": "content", "content": " world"}
        ]
        
        output = []
        async for chunk in create_openai_compatible_stream(
            self.async_generator(chunks), 
            model="test-model"
        ):
            output.append(chunk)
        
        # Should have 2 content chunks + final + DONE
        assert len(output) == 4
        
        # Verify only content chunks were processed
        data1 = json.loads(output[0][6:])
        assert data1["choices"][0]["delta"]["content"] == "Hello"
        
        data2 = json.loads(output[1][6:])
        assert data2["choices"][0]["delta"]["content"] == " world"
    
    @pytest.mark.asyncio
    async def test_create_openai_compatible_stream_chunk_id_consistency(self):
        """Test that chunk ID remains consistent throughout stream"""
        chunks = [
            {"type": "content", "content": "Part 1"},
            {"type": "content", "content": "Part 2"}
        ]
        
        chunk_ids = []
        async for chunk in create_openai_compatible_stream(
            self.async_generator(chunks), 
            model="test"
        ):
            if chunk.startswith("data: ") and chunk != "data: [DONE]\n\n":
                data = json.loads(chunk[6:])
                chunk_ids.append(data["id"])
        
        # All chunks should have the same ID
        assert len(set(chunk_ids)) == 1
        assert chunk_ids[0].startswith("chatcmpl-")
    
    @pytest.mark.asyncio
    @patch('time.time')
    async def test_create_openai_compatible_stream_timestamps(self, mock_time):
        """Test timestamp handling in chunks"""
        # Mock consistent time
        mock_time.return_value = 1234567890.123
        
        chunks = [{"type": "content", "content": "Test"}]
        
        output = []
        async for chunk in create_openai_compatible_stream(
            self.async_generator(chunks), 
            model="test"
        ):
            if chunk.startswith("data: ") and chunk != "data: [DONE]\n\n":
                output.append(json.loads(chunk[6:]))
        
        # Check timestamps
        for data in output:
            assert data["created"] == 1234567890
            assert data["id"] == "chatcmpl-1234567890"
    
    @pytest.mark.asyncio
    async def test_create_openai_compatible_stream_format_compliance(self):
        """Test output format complies with OpenAI SSE format"""
        chunks = [{"type": "content", "content": "Test message"}]
        
        async for chunk in create_openai_compatible_stream(
            self.async_generator(chunks), 
            model="gpt-3.5-turbo"
        ):
            # All chunks should end with double newline
            assert chunk.endswith("\n\n")
            
            # Data chunks should start with "data: "
            assert chunk.startswith("data: ")
            
            # Should be valid JSON after "data: " (except [DONE])
            if chunk != "data: [DONE]\n\n":
                json_str = chunk[6:-2]  # Remove "data: " and "\n\n"
                data = json.loads(json_str)  # Should not raise
                
                # Verify OpenAI structure
                assert "id" in data
                assert "object" in data
                assert "created" in data
                assert "model" in data
                assert "choices" in data
                assert isinstance(data["choices"], list)
                assert len(data["choices"]) == 1
                assert "index" in data["choices"][0]
                assert "delta" in data["choices"][0]
                assert "finish_reason" in data["choices"][0]
    
    @pytest.mark.asyncio
    async def test_create_openai_compatible_stream_empty_content(self):
        """Test handling of chunks with empty content"""
        chunks = [
            {"type": "content", "content": ""},
            {"type": "content", "content": "Hello"},
            {"type": "content", "content": ""}
        ]
        
        output = []
        async for chunk in create_openai_compatible_stream(
            self.async_generator(chunks), 
            model="test"
        ):
            if chunk.startswith("data: ") and chunk != "data: [DONE]\n\n":
                data = json.loads(chunk[6:])
                if data["choices"][0].get("delta", {}).get("content") is not None:
                    output.append(data["choices"][0]["delta"]["content"])
        
        # Should include empty strings
        assert output == ["", "Hello", "", {}]  # Last {} is from final chunk
    
    @pytest.mark.asyncio
    async def test_create_openai_compatible_stream_model_passthrough(self):
        """Test that model name is correctly passed through"""
        chunks = [{"type": "content", "content": "Test"}]
        
        models_to_test = ["gpt-4", "claude-3-opus", "custom-model-123"]
        
        for model_name in models_to_test:
            async for chunk in create_openai_compatible_stream(
                self.async_generator(chunks), 
                model=model_name
            ):
                if chunk.startswith("data: ") and chunk != "data: [DONE]\n\n":
                    data = json.loads(chunk[6:])
                    assert data["model"] == model_name
    
    @pytest.mark.asyncio
    async def test_create_openai_compatible_stream_choice_structure(self):
        """Test the choices array structure matches OpenAI format"""
        chunks = [{"type": "content", "content": "Test"}]
        
        async for chunk in create_openai_compatible_stream(
            self.async_generator(chunks), 
            model="test"
        ):
            if chunk.startswith("data: ") and chunk != "data: [DONE]\n\n":
                data = json.loads(chunk[6:])
                
                # Verify choices structure
                assert len(data["choices"]) == 1
                choice = data["choices"][0]
                
                assert choice["index"] == 0
                assert "delta" in choice
                assert "finish_reason" in choice
                
                # Content chunks should have content in delta
                if choice["finish_reason"] is None:
                    assert "content" in choice["delta"]
                else:
                    # Final chunk should have empty delta
                    assert choice["delta"] == {}
                    assert choice["finish_reason"] == "stop"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])