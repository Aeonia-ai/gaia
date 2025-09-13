"""
Streaming formatter for OpenAI-compatible responses
"""
import json
import time
from typing import AsyncGenerator, Dict, Any
from .streaming_buffer import create_buffered_stream

async def create_openai_compatible_stream(
    chunk_generator: AsyncGenerator[Dict[str, Any], None],
    model: str
) -> AsyncGenerator[str, None]:
    """
    Convert internal streaming format to OpenAI-compatible SSE format.
    """
    chunk_id = f"chatcmpl-{int(time.time())}"
    
    async for chunk_data in chunk_generator:
        if chunk_data.get("type") == "content":
            # Format as OpenAI streaming chunk
            openai_chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": chunk_data.get("content", "")
                        },
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(openai_chunk)}\n\n"
    
    # Send final chunk
    final_chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk", 
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }
        ]
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


async def create_smart_openai_stream(
    chunk_generator: AsyncGenerator[Dict[str, Any], None],
    model: str,
    preserve_boundaries: bool = True,
    preserve_json: bool = True
) -> AsyncGenerator[str, None]:
    """
    Create an OpenAI-compatible SSE stream with smart buffering.
    
    Args:
        chunk_generator: Original stream of chunks
        model: Model name for the response
        preserve_boundaries: Whether to preserve word boundaries
        preserve_json: Whether to buffer JSON directives
        
    Yields:
        SSE-formatted events with preserved boundaries
    """
    # First apply smart buffering
    buffered_stream = create_buffered_stream(
        chunk_generator,
        preserve_boundaries=preserve_boundaries,
        preserve_json=preserve_json
    )
    
    # Then format as OpenAI-compatible SSE
    async for event in create_openai_compatible_stream(buffered_stream, model):
        yield event