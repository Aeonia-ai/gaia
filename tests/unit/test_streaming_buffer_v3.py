"""
Unit tests for the v3 streaming buffer with optimized batching.
"""
import pytest
import json
from app.services.streaming_buffer import StreamBuffer, create_buffered_stream


class TestStreamBufferV3:
    """Test the v3 StreamBuffer with optimized phrase batching and sentence mode"""
    
    @pytest.mark.asyncio
    async def test_complete_sentence_batching(self):
        """Test that complete sentences are sent as one chunk"""
        buffer = StreamBuffer()
        
        chunks = ["The quick brown fox jumps over the lazy dog."]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # Complete sentence should be sent as one chunk
        assert len(results) == 1
        assert results[0] == "The quick brown fox jumps over the lazy dog."
    
    @pytest.mark.asyncio
    async def test_phrase_boundary_batching(self):
        """Test batching at natural phrase boundaries"""
        buffer = StreamBuffer()
        
        chunks = [
            "Hello there!",
            " How are you?",
            " I'm doing great."
        ]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # Should batch at sentence boundaries
        assert len(results) == 3
        assert results[0] == "Hello there!"
        assert results[1] == " How are you?"
        assert results[2] == " I'm doing great."
    
    @pytest.mark.asyncio
    async def test_word_boundary_preservation(self):
        """Test that word boundaries are preserved when chunks split words"""
        buffer = StreamBuffer()
        
        # Simulate chunks that split words badly
        chunks = ["The qui", "ck brown f", "ox"]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        async for output in buffer.flush():
            results.append(output)
        
        # Should preserve word boundaries
        assert len(results) == 3
        assert results[0] == "The "  # Complete word immediately sent
        assert results[1] == "quick brown "  # Complete words sent
        assert results[2] == "fox"  # Final word from flush
    
    @pytest.mark.asyncio
    async def test_json_directive_preservation(self):
        """Test that JSON directives are kept complete"""
        buffer = StreamBuffer(preserve_json=True)
        
        chunks = [
            'Spawning fairy: {"m":"sp',
            'awn_char',
            'acter","p":{"ty',
            'pe":"fairy"}}',
            ' for you!'
        ]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        async for output in buffer.flush():
            results.append(output)
        
        # Should have text, complete JSON, then more text
        assert len(results) == 3
        assert results[0] == "Spawning fairy: "
        assert results[1] == '{"m":"spawn_character","p":{"type":"fairy"}}'
        assert results[2] == " for you!"
        
        # Verify JSON is valid
        directive = json.loads(results[1])
        assert directive["m"] == "spawn_character"
    
    @pytest.mark.asyncio
    async def test_minimal_server_overhead(self):
        """Test that batching minimizes chunk count"""
        buffer = StreamBuffer()
        
        # Multiple chunks that can be batched
        chunks = [
            "The weather",
            " is nice today.",
            " Let's go",
            " for a walk."
        ]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # Should batch at phrase boundaries when possible
        assert len(results) == 4
        assert results[0] == "The "  # Partial word becomes complete
        assert results[1] == "weather is nice today."  # Phrase ending detected
        assert results[2] == " Let's "  # Partial word becomes complete
        assert results[3] == "go for a walk."  # Phrase ending detected
    
    @pytest.mark.asyncio
    async def test_incomplete_final_word_buffering(self):
        """Test that incomplete final words are buffered"""
        buffer = StreamBuffer()
        
        chunks = ["Hello wor"]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # Incomplete word should be buffered
        assert len(results) == 1
        assert results[0] == "Hello "
        
        # Flush should get the incomplete word
        async for output in buffer.flush():
            results.append(output)
        
        assert len(results) == 2
        assert results[1] == "wor"
    
    @pytest.mark.asyncio
    async def test_single_character_handling(self):
        """Test extreme case of single character chunks"""
        buffer = StreamBuffer()
        
        text = "Hi!"
        results = []
        
        # Send one character at a time
        for char in text:
            async for output in buffer.process(char):
                results.append(output)
        
        async for output in buffer.flush():
            results.append(output)
        
        # Should batch the complete phrase
        assert len(results) == 1
        assert results[0] == "Hi!"
    
    @pytest.mark.asyncio
    async def test_newline_as_phrase_boundary(self):
        """Test that newlines are treated as phrase endings"""
        buffer = StreamBuffer()
        
        chunks = ["Line 1\n", "Line 2\n", "Line 3"]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        async for output in buffer.flush():
            results.append(output)
        
        # Newlines should trigger output - but "Line 3" has no ending
        assert len(results) == 4
        assert results[0] == "Line 1\n"
        assert results[1] == "Line 2\n"
        assert results[2] == "Line "  # Complete word sent
        assert results[3] == "3"  # Final incomplete from flush
    
    @pytest.mark.asyncio
    async def test_realistic_llm_streaming(self):
        """Test with realistic LLM streaming patterns"""
        buffer = StreamBuffer()
        
        # Based on actual streaming patterns we observed
        chunks = [
            "I understand",
            " your question.",
            " Let me",
            " explain how",
            " this works."
        ]
        results = []
        
        for chunk in chunks:
            async for output in buffer.process(chunk):
                results.append(output)
        
        # Should output as it detects complete words and phrases
        assert len(results) == 5
        assert results[0] == "I "  # Complete word
        assert results[1] == "understand your question."  # Phrase ending
        assert results[2] == " Let "  # Complete word
        assert results[3] == "me explain "  # Complete words
        assert results[4] == "how this works."  # Phrase ending
    
    @pytest.mark.asyncio
    async def test_preserve_boundaries_flag(self):
        """Test that buffering can be disabled"""
        chunks = [
            {"type": "content", "content": "Hel"},
            {"type": "content", "content": "lo"}
        ]
        
        async def async_gen(items):
            for item in items:
                yield item
        
        # With buffering disabled
        results = []
        async for chunk in create_buffered_stream(
            async_gen(chunks),
            preserve_boundaries=False
        ):
            results.append(chunk)
        
        # Should pass through unchanged
        assert len(results) == 2
        assert results[0]["content"] == "Hel"
        assert results[1]["content"] == "lo"
    
    @pytest.mark.asyncio
    async def test_metadata_preservation(self):
        """Test that chunk metadata is preserved"""
        chunks = [
            {"type": "content", "content": "Hello ", "provider": "openai"},
            {"type": "content", "content": "world!", "provider": "openai"}
        ]
        
        async def async_gen(items):
            for item in items:
                yield item
        
        results = []
        async for chunk in create_buffered_stream(async_gen(chunks)):
            results.append(chunk)
        
        # Metadata should be preserved - but chunks processed individually
        assert len(results) == 2
        assert results[0]["content"] == "Hello "  # Space at end = complete
        assert results[0]["provider"] == "openai"
        assert results[1]["content"] == "world!"  # Punctuation = complete
        assert results[1]["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_sentence_mode_default_behavior(self):
        """Test that sentence mode is the default and behaves correctly"""
        # Test that default constructor uses sentence mode
        buffer = StreamBuffer()
        assert buffer.sentence_mode == True, "StreamBuffer should default to sentence_mode=True"

        # Test sentence mode behavior vs phrase mode behavior
        test_content = "First statement. Second: here we go; and more text"

        # Default (sentence mode) behavior
        sentence_chunks = []
        async for chunk in buffer.process(test_content):
            sentence_chunks.append(chunk)

        # Flush any remaining content
        async for chunk in buffer.flush():
            sentence_chunks.append(chunk)

        # Explicit phrase mode behavior
        phrase_buffer = StreamBuffer(sentence_mode=False)
        phrase_chunks = []
        async for chunk in phrase_buffer.process(test_content):
            phrase_chunks.append(chunk)

        # Flush any remaining content
        async for chunk in phrase_buffer.flush():
            phrase_chunks.append(chunk)

        # Sentence mode should produce fewer chunks (only at . ! ?)
        # Phrase mode should produce more chunks (at : ; as well)
        assert len(sentence_chunks) < len(phrase_chunks), "Sentence mode should produce fewer chunks than phrase mode"

        # Verify the actual chunking behavior
        # Sentence mode: should split only at "." (fewer chunks)
        expected_sentence = ["First statement. ", "Second: here we go; and more ", "text"]
        assert sentence_chunks == expected_sentence, f"Expected {expected_sentence}, got {sentence_chunks}"

        # Phrase mode: should split at ".", ":", and ";" (more chunks)
        expected_phrase = ["First statement. ", "Second: ", "here we go; ", "and more ", "text"]
        assert phrase_chunks == expected_phrase, f"Expected {expected_phrase}, got {phrase_chunks}"

    @pytest.mark.asyncio
    async def test_create_buffered_stream_sentence_default(self):
        """Test that create_buffered_stream also defaults to sentence mode"""
        chunks = [
            {"type": "content", "content": "First sentence. Second: clause; here."}
        ]

        async def async_gen(items):
            for item in items:
                yield item

        # Test with default parameters (should be sentence mode)
        results_default = []
        async for chunk in create_buffered_stream(async_gen(chunks)):
            results_default.append(chunk)

        # Test with explicit sentence_mode=False (phrase mode)
        results_phrase = []
        async for chunk in create_buffered_stream(async_gen(chunks), sentence_mode=False):
            results_phrase.append(chunk)

        # Default should behave like sentence mode (fewer chunks)
        # Sentence mode: splits only at sentence endings (.)
        assert len(results_default) == 2
        assert results_default[0]["content"] == "First sentence. "
        assert results_default[1]["content"] == "Second: clause; here."

        # Phrase mode: splits at sentence endings (.) and phrase endings (: ;)
        assert len(results_phrase) == 4
        assert results_phrase[0]["content"] == "First sentence. "
        assert results_phrase[1]["content"] == "Second: "
        assert results_phrase[2]["content"] == "clause; "
        assert results_phrase[3]["content"] == "here."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])