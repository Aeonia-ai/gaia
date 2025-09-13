"""
Streaming formatter for GAIA v0.3 format with smart buffering.
"""
import json
import time
from typing import AsyncGenerator, Dict, Any
from .streaming_buffer import create_buffered_stream


async def create_v03_stream(
    chunk_generator: AsyncGenerator[Dict[str, Any], None]
) -> AsyncGenerator[str, None]:
    """
    Convert internal streaming format to GAIA v0.3 SSE format.
    
    v0.3 format is simpler than OpenAI:
    - {"type":"content","content":"text"}
    - {"type":"metadata","model":"gpt-4"}
    - {"type":"done","finish_reason":"stop"}
    """
    
    async for chunk_data in chunk_generator:
        # Pass through our simple format directly
        if chunk_data.get("type") == "content":
            yield f"data: {json.dumps(chunk_data)}\n\n"
        elif chunk_data.get("type") == "metadata":
            yield f"data: {json.dumps(chunk_data)}\n\n"
        elif chunk_data.get("type") == "error":
            yield f"data: {json.dumps(chunk_data)}\n\n"
        elif chunk_data.get("finish_reason"):
            # Convert finish reason to done event
            yield f'data: {{"type":"done","finish_reason":"{chunk_data.get("finish_reason")}"}}\n\n'
    
    # Send final done signal
    yield "data: [DONE]\n\n"


async def create_smart_v03_stream(
    chunk_generator: AsyncGenerator[Dict[str, Any], None],
    preserve_boundaries: bool = True,
    preserve_json: bool = True
) -> AsyncGenerator[str, None]:
    """
    Create a v0.3 SSE stream with smart buffering for word/JSON boundaries.
    
    Args:
        chunk_generator: Original stream of chunks
        preserve_boundaries: Whether to preserve word boundaries
        preserve_json: Whether to buffer JSON directives
        
    Yields:
        SSE-formatted events in v0.3 format with preserved boundaries
    """
    # First apply smart buffering
    buffered_stream = create_buffered_stream(
        chunk_generator,
        preserve_boundaries=preserve_boundaries,
        preserve_json=preserve_json
    )
    
    # Then format as v0.3 SSE
    async for event in create_v03_stream(buffered_stream):
        yield event