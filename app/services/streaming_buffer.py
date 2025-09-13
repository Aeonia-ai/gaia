"""
Intelligent streaming buffer that preserves word and JSON boundaries.
Version 3: Optimized for minimal overhead - sends complete phrases when possible.
"""
import re
from typing import AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)


class StreamBuffer:
    """
    Smart buffer optimized for minimal server overhead:
    1. Forwards complete phrases/sentences when possible
    2. Only splits at word boundaries when necessary
    3. Preserves complete JSON directives
    """
    
    def __init__(self, preserve_json: bool = True):
        """
        Initialize the stream buffer.
        
        Args:
            preserve_json: Whether to detect and buffer JSON directives
        """
        self.incomplete_buffer = ""  # Buffer for incomplete content
        self.json_buffer = ""        # Buffer for JSON directive
        self.json_depth = 0          # Track brace nesting
        self.in_json = False         # Are we currently buffering JSON?
        self.preserve_json = preserve_json
        
        # Pattern to detect game directives
        self.directive_pattern = re.compile(r'\{"m"\s*:\s*"')
        
        # Natural phrase endings (where we prefer to send)
        self.phrase_endings = {'.', '!', '?', ':', ';', '\n'}
        
        # Word boundaries (where we can split if needed)
        self.word_boundaries = {' ', '\t', ',', '-', ')', ']', '}', '"', "'"}
    
    async def process(self, content: str) -> AsyncGenerator[str, None]:
        """
        Process a content chunk, optimizing for complete phrases.
        
        Strategy:
        1. If we get a complete phrase/sentence, send it whole
        2. If content ends mid-word, buffer the incomplete part
        3. Minimize the number of chunks yielded
        
        Args:
            content: The incoming content chunk from LLM
            
        Yields:
            Complete phrases or at minimum complete words
        """
        if not content:
            return
        
        # Combine with any buffered incomplete content
        text = self.incomplete_buffer + content
        self.incomplete_buffer = ""
        
        # If we're in JSON mode, continue buffering
        if self.in_json:
            self.json_buffer += text
            self.json_depth += text.count('{') - text.count('}')
            
            if self.json_depth <= 0:
                # JSON is complete!
                yield self.json_buffer
                self.in_json = False
                self.json_buffer = ""
                self.json_depth = 0
            return
        
        # Check for JSON directive start
        if self.preserve_json:
            match = self.directive_pattern.search(text)
            if match:
                json_start = match.start()
                
                # Send everything before the JSON
                if json_start > 0:
                    pre_json = text[:json_start]
                    async for chunk in self._process_text(pre_json, final=False):
                        yield chunk
                
                # Start buffering JSON
                self.in_json = True
                self.json_buffer = text[json_start:]
                self.json_depth = self.json_buffer.count('{') - self.json_buffer.count('}')
                
                # If JSON completes immediately
                if self.json_depth <= 0:
                    yield self.json_buffer
                    self.in_json = False
                    self.json_buffer = ""
                    self.json_depth = 0
                return
        
        # Process normal text
        async for chunk in self._process_text(text, final=False):
            yield chunk
    
    async def _process_text(self, text: str, final: bool = False) -> AsyncGenerator[str, None]:
        """
        Process text to send complete phrases when possible.
        
        Optimization strategy:
        1. If text ends with phrase ending (. ! ? etc), send everything
        2. If text ends with whitespace, send everything  
        3. If text ends mid-word, send complete part and buffer the rest
        4. Batch as much as possible to reduce overhead
        
        Args:
            text: Text to process
            final: Whether this is the final flush
            
        Yields:
            Complete phrases or words
        """
        if not text:
            return
        
        # Case 1: Text ends with phrase ending - send it all
        if text and text[-1] in self.phrase_endings:
            yield text
            return
        
        # Case 2: Text ends with whitespace - everything is complete
        if text and text[-1] in (' ', '\t', '\n'):
            yield text
            return
        
        # Case 3: Check if we have a good breaking point
        # Look for phrase endings first (optimal for batching)
        best_break = -1
        for ending in self.phrase_endings:
            pos = text.rfind(ending)
            if pos > best_break:
                best_break = pos
        
        # If we found a phrase ending, send everything up to there
        if best_break >= 0:
            # Include the punctuation
            complete_part = text[:best_break + 1]
            
            # Check if there's content after the punctuation
            remainder = text[best_break + 1:]
            
            # If remainder starts with space, include it in the complete part
            if remainder and remainder[0] in (' ', '\t', '\n'):
                # Find where the next word starts
                i = 0
                while i < len(remainder) and remainder[i] in (' ', '\t', '\n'):
                    i += 1
                
                # Include the whitespace in the complete part
                if i > 0:
                    complete_part += remainder[:i]
                    remainder = remainder[i:]
            
            # Send the complete phrase
            if complete_part:
                yield complete_part
            
            # Process the remainder
            if remainder:
                # If remainder has more complete content, process it
                if any(boundary in remainder for boundary in (' ', '\t', '\n')):
                    async for chunk in self._process_text(remainder, final):
                        yield chunk
                else:
                    # Remainder is an incomplete word, buffer it
                    self.incomplete_buffer = remainder
            return
        
        # Case 4: No phrase endings, look for word boundaries
        last_space = -1
        for boundary in (' ', '\t', '\n', ','):
            pos = text.rfind(boundary)
            if pos > last_space:
                last_space = pos
        
        if last_space >= 0:
            # Send complete words
            complete_part = text[:last_space + 1]
            yield complete_part
            
            # Buffer the incomplete word
            remainder = text[last_space + 1:]
            if remainder and not final:
                self.incomplete_buffer = remainder
            elif remainder and final:
                yield remainder
        else:
            # No boundaries at all - single incomplete word
            if final:
                yield text
            else:
                self.incomplete_buffer = text
    
    async def flush(self) -> AsyncGenerator[str, None]:
        """
        Flush any remaining buffered content.
        
        Yields:
            Any remaining buffered content
        """
        # Flush incomplete buffer
        if self.incomplete_buffer:
            async for chunk in self._process_text(self.incomplete_buffer, final=True):
                yield chunk
            self.incomplete_buffer = ""
        
        # Flush incomplete JSON (shouldn't happen normally)
        if self.json_buffer:
            logger.warning(f"Flushing incomplete JSON directive: {self.json_buffer[:50]}...")
            yield self.json_buffer
            self.json_buffer = ""
            self.in_json = False
            self.json_depth = 0


async def create_buffered_stream(
    chunk_generator: AsyncGenerator[dict, None],
    preserve_boundaries: bool = True,
    preserve_json: bool = True
) -> AsyncGenerator[dict, None]:
    """
    Wrap a stream with smart buffering optimized for minimal overhead.
    
    Args:
        chunk_generator: Original stream of chunks
        preserve_boundaries: Whether to preserve word boundaries
        preserve_json: Whether to buffer JSON directives
        
    Yields:
        Optimally batched chunks with preserved boundaries
    """
    if not preserve_boundaries:
        # Pass through unchanged
        async for chunk in chunk_generator:
            yield chunk
        return
    
    buffer = StreamBuffer(preserve_json=preserve_json)
    
    async for chunk in chunk_generator:
        if chunk.get("type") == "content":
            # Process content through buffer
            content = chunk.get("content", "")
            
            if content:
                async for buffered_content in buffer.process(content):
                    # Yield chunk with buffered content
                    yield {
                        **chunk,  # Preserve all metadata
                        "content": buffered_content
                    }
        else:
            # Non-content chunk (metadata, error, etc.)
            # First flush any pending content
            async for final_content in buffer.flush():
                if final_content:
                    yield {
                        "type": "content",
                        "content": final_content,
                        "provider": chunk.get("provider"),
                        "model": chunk.get("model")
                    }
            
            # Then pass through the non-content chunk
            yield chunk
    
    # Final flush at stream end
    async for final_content in buffer.flush():
        if final_content:
            yield {
                "type": "content",
                "content": final_content
            }