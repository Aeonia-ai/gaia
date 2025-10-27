"""
Intelligent streaming buffer that preserves word and JSON boundaries.
Version 3: Optimized for minimal overhead - sends complete phrases when possible.
"""
import re
from typing import AsyncGenerator, Optional, Literal
import logging

logger = logging.getLogger(__name__)

# Chunking mode type for clarity
ChunkingMode = Literal["sentence", "phrase"]


class StreamBuffer:
    """
    Smart buffer optimized for minimal server overhead:
    1. Forwards complete phrases/sentences when possible
    2. Only splits at word boundaries when necessary
    3. Preserves complete JSON directives
    4. Optional sentence-only mode for complete sentence delivery
    """

    def __init__(self, preserve_json: bool = True, chunking_mode: ChunkingMode = "sentence"):
        """
        Initialize the stream buffer.

        Args:
            preserve_json: Whether to detect and buffer JSON directives
            chunking_mode: "sentence" = only split at sentence endings (. ! ?) - DEFAULT
                          "phrase" = split at natural pause points (. ! ? : ; \n)
        """
        self.incomplete_buffer = ""  # Buffer for incomplete content
        self.json_buffer = ""        # Buffer for JSON directive
        self.json_depth = 0          # Track brace nesting
        self.in_json = False         # Are we currently buffering JSON?
        self.preserve_json = preserve_json
        self.chunking_mode = chunking_mode

        # Pattern to detect game directives
        self.directive_pattern = re.compile(r'\{"m"\s*:\s*"')

        # Sentence endings (strict sentence boundaries)
        self.sentence_endings = {'.', '!', '?'}

        # Natural phrase endings (where we prefer to send in phrase mode)
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
        
        # Check for JSON directive start (process before sentence/phrase logic)
        if self.preserve_json:
            match = self.directive_pattern.search(text)
            if match:
                json_start = match.start()

                # Send everything before the JSON
                if json_start > 0:
                    pre_json = text[:json_start]
                    async for chunk in self._process_text(pre_json, final=False):
                        yield chunk

                # Find where the JSON ends by counting braces
                json_content = text[json_start:]
                brace_depth = 0
                json_end = -1

                for i, char in enumerate(json_content):
                    if char == '{':
                        brace_depth += 1
                    elif char == '}':
                        brace_depth -= 1
                        if brace_depth == 0:
                            json_end = i + 1
                            break

                if json_end > 0:
                    # JSON is complete in this chunk
                    json_part = json_content[:json_end]
                    remaining_text = json_content[json_end:]

                    yield json_part

                    # Process any remaining text after the JSON (might contain more JSON)
                    # Use _process_text to maintain sentence/phrase logic but detect JSON first
                    if remaining_text:
                        # Check if remaining text has more JSON first
                        if self.directive_pattern.search(remaining_text):
                            # More JSON detected, recursively process to handle it properly
                            async for chunk in self.process(remaining_text):
                                yield chunk
                        else:
                            # No more JSON, use normal text processing
                            async for chunk in self._process_text(remaining_text, final=False):
                                yield chunk
                else:
                    # JSON is incomplete, start buffering
                    self.in_json = True
                    self.json_buffer = json_content
                    self.json_depth = json_content.count('{') - json_content.count('}')
                return
        
        # Process normal text
        async for chunk in self._process_text(text, final=False):
            yield chunk
    
    async def _process_text(self, text: str, final: bool = False) -> AsyncGenerator[str, None]:
        """
        Process text to send complete phrases or sentences when possible.

        Optimization strategy:
        - Sentence mode: Only send when we have complete sentences (. ! ?)
        - Phrase mode: Send complete phrases including colons, semicolons, etc.
        - Always fall back to word boundaries if no sentence/phrase endings

        Args:
            text: Text to process
            final: Whether this is the final flush

        Yields:
            Complete sentences/phrases or words based on mode
        """
        if not text:
            return

        # Determine which endings to use based on mode
        preferred_endings = self.sentence_endings if self.chunking_mode == "sentence" else self.phrase_endings

        # Case 1: Text ends with preferred ending
        # But first check if there are multiple endings inside that we should split on
        if text and text[-1] in preferred_endings:
            # Count how many preferred endings we have
            ending_count = sum(text.count(ending) for ending in preferred_endings)
            if ending_count == 1:
                # Only one ending and it's at the end - send it all
                yield text
                return
            # If multiple endings, fall through to Case 3 to split properly
        
        # Case 2: Text ends with whitespace - all words are complete
        if text and text[-1] in (' ', '\t', '\n'):
            yield text
            return

        # Case 3: Check if we have a good breaking point
        # Find the first occurrence of any preferred ending to create proper chunking
        first_break = len(text)
        for ending in preferred_endings:
            pos = text.find(ending)
            if pos != -1 and pos < first_break:
                first_break = pos

        # If we found a preferred ending, send everything up to there
        if first_break < len(text):
            # Include the punctuation
            complete_part = text[:first_break + 1]

            # Check if there's content after the punctuation
            remainder = text[first_break + 1:]

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
                # If remainder has more complete content, process it recursively
                async for chunk in self._process_text(remainder, final):
                    yield chunk
            return
        
        # Case 4: No preferred endings found - fall back to word boundaries
        # Both sentence and phrase mode should send complete words
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
    preserve_json: bool = True,
    chunking_mode: ChunkingMode = "sentence"
) -> AsyncGenerator[dict, None]:
    """
    Wrap a stream with smart buffering optimized for minimal overhead.

    Args:
        chunk_generator: Original stream of chunks
        preserve_boundaries: Whether to preserve word boundaries
        preserve_json: Whether to buffer JSON directives
        chunking_mode: "sentence" = only split at sentence endings (. ! ?) - DEFAULT
                      "phrase" = split at natural pause points (. ! ? : ; \n)

    Yields:
        Optimally batched chunks with preserved boundaries
    """
    if not preserve_boundaries:
        # Pass through unchanged
        async for chunk in chunk_generator:
            yield chunk
        return

    buffer = StreamBuffer(preserve_json=preserve_json, chunking_mode=chunking_mode)
    
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