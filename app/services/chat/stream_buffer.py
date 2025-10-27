"""
StreamBuffer - Intelligent text chunking for streaming responses.
Ensures chunks break at sentence boundaries for better Unity client compatibility.
"""

import re
from typing import List, Optional


class StreamBuffer:
    """Buffer for accumulating and chunking text at sentence boundaries."""

    # Sentence ending patterns
    SENTENCE_ENDINGS = re.compile(r'[.!?]+[\s"\'\)]*')

    # Minimum chunk size to avoid tiny fragments
    MIN_CHUNK_SIZE = 30

    # Maximum chunk size before forcing a split
    MAX_CHUNK_SIZE = 200

    # Preferred chunk size range
    PREFERRED_MIN = 50
    PREFERRED_MAX = 150

    def __init__(self):
        self.buffer = ""
        self.chunks = []

    def add_text(self, text: str) -> List[str]:
        """
        Add text to the buffer and return complete chunks.

        Args:
            text: New text to add to buffer

        Returns:
            List of complete chunks ready to send
        """
        self.buffer += text
        ready_chunks = []

        # Process buffer for complete sentences
        while len(self.buffer) > self.PREFERRED_MIN:
            chunk = self._extract_chunk()
            if chunk:
                ready_chunks.append(chunk)
            else:
                break

        return ready_chunks

    def _extract_chunk(self) -> Optional[str]:
        """Extract a single chunk from the buffer."""

        # If buffer is too large, force a chunk
        if len(self.buffer) > self.MAX_CHUNK_SIZE:
            return self._force_chunk()

        # Look for sentence endings
        match = self.SENTENCE_ENDINGS.search(self.buffer)

        if match:
            end_pos = match.end()

            # If the sentence is within preferred range, extract it
            if self.PREFERRED_MIN <= end_pos <= self.PREFERRED_MAX:
                chunk = self.buffer[:end_pos]
                self.buffer = self.buffer[end_pos:].lstrip()
                return chunk

            # If sentence is too short, look for next sentence
            elif end_pos < self.PREFERRED_MIN:
                # Find second sentence ending
                second_match = self.SENTENCE_ENDINGS.search(self.buffer, end_pos)
                if second_match and second_match.end() <= self.PREFERRED_MAX:
                    chunk = self.buffer[:second_match.end()]
                    self.buffer = self.buffer[second_match.end():].lstrip()
                    return chunk
                # If no good second sentence, wait for more text
                return None

            # If sentence is too long but within MAX, take it
            elif end_pos <= self.MAX_CHUNK_SIZE:
                chunk = self.buffer[:end_pos]
                self.buffer = self.buffer[end_pos:].lstrip()
                return chunk

        # No sentence ending found, wait for more text
        return None

    def _force_chunk(self) -> str:
        """Force a chunk when buffer is too large."""
        # Try to break at a comma or semicolon
        for sep in [', ', '; ', ' - ', ' — ']:
            pos = self.buffer.rfind(sep, 0, self.MAX_CHUNK_SIZE)
            if pos > self.MIN_CHUNK_SIZE:
                chunk = self.buffer[:pos + len(sep.rstrip())]
                self.buffer = self.buffer[pos + len(sep):].lstrip()
                return chunk

        # Try to break at a space
        pos = self.buffer.rfind(' ', 0, self.MAX_CHUNK_SIZE)
        if pos > self.MIN_CHUNK_SIZE:
            chunk = self.buffer[:pos]
            self.buffer = self.buffer[pos:].lstrip()
            return chunk

        # Last resort: break at MAX_CHUNK_SIZE
        chunk = self.buffer[:self.MAX_CHUNK_SIZE]
        self.buffer = self.buffer[self.MAX_CHUNK_SIZE:]
        return chunk

    def flush(self) -> Optional[str]:
        """Return any remaining text in the buffer."""
        if self.buffer.strip():
            chunk = self.buffer.strip()
            self.buffer = ""
            return chunk
        return None


def chunk_text_smart(text: str) -> List[str]:
    """
    Chunk text intelligently at sentence boundaries.

    Args:
        text: The text to chunk

    Returns:
        List of chunks
    """
    buffer = StreamBuffer()
    chunks = buffer.add_text(text)

    # Get any remaining text
    final = buffer.flush()
    if final:
        chunks.append(final)

    return chunks