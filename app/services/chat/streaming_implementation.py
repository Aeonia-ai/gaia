"""
Real LLM Streaming Implementation for UnifiedChatHandler

This module extends UnifiedChatHandler with real streaming capabilities.
"""

import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, Any, Optional

from app.services.streaming_buffer import StreamBuffer
from app.services.llm.chat_service import chat_service

logger = logging.getLogger(__name__)


async def stream_response(
    self,
    message: str,
    conversation_id: Optional[str] = None,
    use_real_streaming: bool = False,
    route_type: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream a response with optional real LLM streaming.

    This is a wrapper that provides the interface expected by tests,
    delegating to the existing process_stream method with enhancements.

    Args:
        message: The user's message
        conversation_id: Optional conversation ID for context
        use_real_streaming: Whether to use real LLM streaming (for direct path only)
        route_type: Override for route type (for testing)
        **kwargs: Additional parameters

    Yields:
        Streaming chunks in v0.3 format
    """
    # Build auth context (simplified for testing)
    auth = kwargs.get("auth", {"user_id": "test-user"})

    # Build context with conversation_id if provided
    context = {}
    if conversation_id:
        context["conversation_id"] = conversation_id

    # If route_type is specified (for testing), handle it directly
    if route_type == "direct" and use_real_streaming:
        # Use real streaming for direct LLM path
        async for chunk in self._stream_direct_real(message, auth, context):
            yield chunk
    elif route_type == "kb_tools":
        # KB tools path - always simulated
        from .kb_agent import KBAgent
        kb_agent = self.kb_agent if hasattr(self, 'kb_agent') else KBAgent()

        # Use the new progressive streaming method if available
        if hasattr(kb_agent, 'process_streaming'):
            async for event in kb_agent.process_streaming(message, stream=True):
                yield event
        else:
            # Fallback to simulated streaming
            response = await kb_agent.process(message)
            buffer = StreamBuffer(preserve_json=True)
            async for chunk in buffer.process(response):
                yield {"type": "content", "content": chunk}

    elif route_type == "mcp_agent":
        # MCP agent path - always simulated for now
        from app.models.chat import ChatRequest
        chat_request = ChatRequest(message=message)

        if hasattr(self, 'mcp_agent') and hasattr(self.mcp_agent, 'process_streaming'):
            async for event in self.mcp_agent.process_streaming(
                {"message": message},
                stream=True
            ):
                yield event
        else:
            # Fallback to existing MCP hot service
            result = await self.mcp_hot_service.process_chat(
                request=chat_request,
                auth_principal=auth
            )
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            buffer = StreamBuffer(preserve_json=True)
            async for chunk in buffer.process(content):
                yield {"type": "content", "content": chunk}
    else:
        # Use the existing process_stream method with modifications
        # Convert to the expected format
        async for chunk in self.process_stream(message, auth, context):
            # Convert OpenAI format to v0.3 format for tests
            if "choices" in chunk and chunk["choices"]:
                delta = chunk["choices"][0].get("delta", {})
                if "content" in delta:
                    yield {"type": "content", "content": delta["content"]}
                elif "role" in delta:
                    yield {"type": "metadata", "role": delta["role"]}

            # Pass through metadata
            if "_metadata" in chunk:
                yield {"type": "metadata", "data": chunk["_metadata"]}


async def _stream_direct_real(
    self,
    message: str,
    auth: dict,
    context: Optional[dict] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream direct LLM response using real streaming API.

    Args:
        message: The user's message
        auth: Authentication context
        context: Optional conversation context

    Yields:
        Streaming chunks with real LLM streaming
    """
    try:
        # Build messages for LLM
        messages = []

        # Add conversation history if available
        if context and context.get("conversation_history"):
            for msg in context["conversation_history"]:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })

        # Get system prompt
        system_prompt = await self.get_routing_prompt(context) if hasattr(self, 'get_routing_prompt') else ""

        # Use real streaming from chat_service
        response_content = ""
        buffer = StreamBuffer(preserve_json=True)

        # Check if chat_completion_stream exists
        if hasattr(chat_service, 'chat_completion_stream'):
            # Real streaming available!
            async for chunk in chat_service.chat_completion_stream(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=4096
            ):
                # Extract content from streaming chunk
                if chunk.get("type") == "content":
                    chunk_text = chunk.get("content", "")
                elif "choices" in chunk:
                    # Handle OpenAI format
                    delta = chunk["choices"][0].get("delta", {})
                    chunk_text = delta.get("content", "")
                else:
                    chunk_text = chunk.get("content", "")

                if chunk_text:
                    response_content += chunk_text

                    # Use StreamBuffer for intelligent boundaries
                    async for output in buffer.process(chunk_text):
                        yield {"type": "content", "content": output}

                # Pass through metadata
                if chunk.get("type") == "metadata":
                    yield chunk

            # Flush any remaining content
            async for output in buffer.flush():
                if output:
                    yield {"type": "content", "content": output}

            # Save to conversation history if we have the store
            if hasattr(self, 'conversation_store') and context.get('conversation_id'):
                self.conversation_store.add_message(
                    context['conversation_id'],
                    "assistant",
                    response_content
                )

        else:
            # Fallback to non-streaming with simulated streaming
            response = await chat_service.chat_completion(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=4096
            )

            content = response.get("response", "")

            # Simulate streaming with StreamBuffer
            async for chunk in buffer.process(content):
                yield {"type": "content", "content": chunk}

            # Flush remaining
            async for chunk in buffer.flush():
                if chunk:
                    yield {"type": "content", "content": chunk}

    except NotImplementedError as e:
        # Streaming not supported, fallback to complete response
        logger.info(f"Streaming not supported, falling back: {e}")

        response = await chat_service.chat_completion(
            messages=messages,
            system_prompt=system_prompt if 'system_prompt' in locals() else "",
            temperature=0.7,
            max_tokens=4096
        )

        content = response.get("response", "")
        buffer = StreamBuffer(preserve_json=True)

        async for chunk in buffer.process(content):
            yield {"type": "content", "content": chunk}

        async for chunk in buffer.flush():
            if chunk:
                yield {"type": "content", "content": chunk}

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield {"type": "error", "content": str(e)}


# Monkey-patch the methods onto UnifiedChatHandler
def patch_unified_chat_handler():
    """Patch UnifiedChatHandler with real streaming methods."""
    from app.services.chat.unified_chat import UnifiedChatHandler

    # Add the new methods
    UnifiedChatHandler.stream_response = stream_response
    UnifiedChatHandler._stream_direct_real = _stream_direct_real

    logger.info("Patched UnifiedChatHandler with real streaming support")