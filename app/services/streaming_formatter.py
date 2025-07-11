"""
Streaming formatter for OpenAI-compatible responses
"""
import json
import time
from typing import AsyncGenerator, Dict, Any

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