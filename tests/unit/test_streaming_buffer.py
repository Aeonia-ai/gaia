"""
Unit tests for the streaming buffer that preserves word and JSON boundaries.
"""
import pytest
import json
from app.services.streaming_buffer import StreamBuffer, create_buffered_stream


class TestStreamBuffer:
    """Test the StreamBuffer class for word and JSON boundary preservation"""
    
    @pytest.mark.asyncio
    async def test_word_boundary_preservation(self):
        """Test that word boundaries are preserved when chunks split words"""
        buffer = StreamBuffer()
        
        # Simulate chunks that split "Hello world" badly
        chunks = ["Hel", "lo wo", "rld!"]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # Flush any remaining
        async for output in buffer.flush():
            results.append(output)
        
        # v3 buffer preserves word boundaries more granularly
        assert len(results) == 2
        assert results == ["Hello ", "world!"]  # Batched complete phrase
    
    @pytest.mark.asyncio
    async def test_phrase_passthrough(self):
        """Test that complete phrases are passed through immediately"""
        buffer = StreamBuffer()
        
        # Simulate chunks with complete phrases
        chunks = [" is wonderful ", "and amazing!"]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # Phrases should pass through immediately
        assert len(results) == 2
        assert results[0] == " is wonderful "
        assert results[1] == "and amazing!"
    
    @pytest.mark.asyncio
    async def test_json_directive_buffering(self):
        """Test that JSON directives are buffered until complete"""
        buffer = StreamBuffer(preserve_json=True)
        
        # Simulate chunks that split a JSON directive
        chunks = [
            'I will spawn a fairy! {"m":"sp',
            'awn_char',
            'acter","p":{"ty',
            'pe":"fairy"}}'
        ]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # Should get text before JSON, then complete JSON
        assert len(results) == 2
        assert results[0] == "I will spawn a fairy! "
        assert results[1] == '{"m":"spawn_character","p":{"type":"fairy"}}'
        
        # Verify JSON is valid
        directive = json.loads(results[1])
        assert directive["m"] == "spawn_character"
        assert directive["p"]["type"] == "fairy"
    
    @pytest.mark.asyncio
    async def test_mixed_content_and_json(self):
        """Test handling of mixed text and JSON content"""
        buffer = StreamBuffer(preserve_json=True)
        
        chunks = [
            "Here's your ",
            'fairy: {"m":"spawn","p":{',
            '"type":"fairy"}}',
            " Enjoy!"
        ]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        async for output in buffer.flush():
            results.append(output)
        
        # v3 splits more granularly around JSON
        assert len(results) == 4
        assert results[0] == "Here's your "
        assert results[1] == "fairy: "
        assert results[2] == '{"m":"spawn","p":{"type":"fairy"}}'
        assert results[3] == " Enjoy!"
    
    @pytest.mark.asyncio
    async def test_single_character_chunks(self):
        """Test extreme case of single character chunks"""
        buffer = StreamBuffer()
        
        text = "Hello world"
        results = []
        
        # Send one character at a time
        for char in text:
            async for output in buffer.process(char):
                results.append(output)
        
        async for output in buffer.flush():
            results.append(output)
        
        # Should still preserve word boundaries
        assert len(results) == 2
        assert results[0] == "Hello "
        assert results[1] == "world"
    
    @pytest.mark.asyncio
    async def test_punctuation_boundaries(self):
        """Test that punctuation acts as word boundary"""
        buffer = StreamBuffer()
        
        chunks = ["Hello", ", ", "world", "!"]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # v3 batches punctuation with words
        assert len(results) == 2
        assert results[0] == "Hello, "
        assert results[1] == "world!"
    
    @pytest.mark.asyncio
    async def test_newline_boundaries(self):
        """Test that newlines act as word boundaries"""
        buffer = StreamBuffer()
        
        chunks = ["Line 1", "\n", "Line 2"]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # Flush remaining
        async for output in buffer.flush():
            results.append(output)
        
        # v3 splits on spaces before newlines
        assert len(results) == 4
        assert results[0] == "Line "
        assert results[1] == "1\n"
        assert results[2] == "Line "
        assert results[3] == "2"
    
    @pytest.mark.asyncio
    async def test_incomplete_json_warning(self):
        """Test that incomplete JSON is flushed with warning"""
        buffer = StreamBuffer(preserve_json=True)
        
        # Start JSON but don't complete it
        chunks = ['{"m":"spawn_character","p":{']
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # Flush should output incomplete JSON
        async for output in buffer.flush():
            results.append(output)
        
        # Should get the incomplete JSON
        assert len(results) == 1
        assert results[0] == '{"m":"spawn_character","p":{'
    
    @pytest.mark.asyncio
    async def test_empty_chunks_ignored(self):
        """Test that empty chunks don't break buffering"""
        buffer = StreamBuffer()
        
        chunks = ["Hello", "", " ", "", "world"]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        async for output in buffer.flush():
            results.append(output)
        
        # Empty strings should be ignored
        assert len(results) == 2
        assert results[0] == "Hello "
        assert results[1] == "world"


class TestBufferedStream:
    """Test the create_buffered_stream wrapper function"""
    
    async def async_generator(self, chunks):
        """Helper to create async generator from list"""
        for chunk in chunks:
            yield chunk
    
    @pytest.mark.asyncio
    async def test_buffered_stream_preserves_metadata(self):
        """Test that buffered stream preserves chunk metadata"""
        chunks = [
            {"type": "content", "content": "Hel", "provider": "openai", "model": "gpt-4"},
            {"type": "content", "content": "lo wo", "provider": "openai", "model": "gpt-4"},
            {"type": "content", "content": "rld", "provider": "openai", "model": "gpt-4"}
        ]
        
        results = []
        async for chunk in create_buffered_stream(
            self.async_generator(chunks),
            preserve_boundaries=True
        ):
            results.append(chunk)
        
        # Should preserve metadata in output chunks
        assert len(results) == 2
        assert results[0]["content"] == "Hello "
        assert results[0]["provider"] == "openai"
        assert results[0]["model"] == "gpt-4"
        assert results[1]["content"] == "world"
    
    @pytest.mark.asyncio
    async def test_buffered_stream_passthrough_mode(self):
        """Test that buffering can be disabled"""
        chunks = [
            {"type": "content", "content": "Hel"},
            {"type": "content", "content": "lo"}
        ]
        
        results = []
        async for chunk in create_buffered_stream(
            self.async_generator(chunks),
            preserve_boundaries=False  # Disable buffering
        ):
            results.append(chunk)
        
        # Should pass through unchanged
        assert len(results) == 2
        assert results[0]["content"] == "Hel"
        assert results[1]["content"] == "lo"
    
    @pytest.mark.asyncio
    async def test_buffered_stream_non_content_passthrough(self):
        """Test that non-content chunks pass through with flush"""
        chunks = [
            {"type": "content", "content": "Partial"},
            {"type": "metadata", "model": "gpt-4"},
            {"type": "content", "content": " word"}
        ]
        
        results = []
        async for chunk in create_buffered_stream(
            self.async_generator(chunks),
            preserve_boundaries=True
        ):
            results.append(chunk)
        
        # v3 adds extra space handling
        assert len(results) == 4
        assert results[0]["type"] == "content"
        assert results[0]["content"] == "Partial"
        assert results[1]["type"] == "metadata"
        assert results[2]["type"] == "content"
        assert results[2]["content"] == " "
        assert results[3]["type"] == "content"
        assert results[3]["content"] == "word"
    
    @pytest.mark.asyncio
    async def test_real_world_streaming_pattern(self):
        """Test with realistic streaming patterns from our analysis"""
        # Based on actual OpenAI streaming patterns we observed
        chunks = [
            {"type": "content", "content": "The"},
            {"type": "content", "content": " quick"},
            {"type": "content", "content": " brown"},
            {"type": "content", "content": " fox"},
            {"type": "content", "content": " j"},  # Split word!
            {"type": "content", "content": "umps"},
            {"type": "content", "content": " over"},
            {"type": "content", "content": " the"},
            {"type": "content", "content": " lazy"},
            {"type": "content", "content": " dog"},
            {"type": "content", "content": "."}
        ]
        
        results = []
        async for chunk in create_buffered_stream(
            self.async_generator(chunks),
            preserve_boundaries=True
        ):
            if chunk["type"] == "content":
                results.append(chunk["content"])
        
        # v3 attaches punctuation to words
        expected = ["The ", "quick ", "brown ", "fox ", "jumps ", "over ", "the ", "lazy ", "dog."]
        assert results == expected
    
    @pytest.mark.asyncio
    async def test_json_directive_in_stream(self):
        """Test JSON directive handling in full stream"""
        chunks = [
            {"type": "content", "content": "I'll spawn "},
            {"type": "content", "content": 'a fairy! {"m":"sp'},
            {"type": "content", "content": 'awn_character","p":{'},
            {"type": "content", "content": '"type":"fairy"}}'},
            {"type": "content", "content": " for you."}
        ]
        
        results = []
        async for chunk in create_buffered_stream(
            self.async_generator(chunks),
            preserve_boundaries=True,
            preserve_json=True
        ):
            if chunk["type"] == "content":
                results.append(chunk["content"])
        
        # v3 splits text more granularly before JSON
        assert len(results) == 4
        assert results[0] == "I'll spawn "
        assert results[1] == "a fairy! "
        assert results[2] == '{"m":"spawn_character","p":{"type":"fairy"}}'
        assert results[3] == " for you."
        
        # Verify JSON is valid
        directive = json.loads(results[2])
        assert directive["m"] == "spawn_character"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])