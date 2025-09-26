"""
Progressive streaming implementation for KB Agent.

Provides metadata about search progress and streams LLM generation.
"""

import time
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional

from app.services.streaming_buffer import StreamBuffer
from app.services.llm.chat_service import chat_service

logger = logging.getLogger(__name__)


class StreamingKBAgent:
    """KB Agent with progressive streaming capabilities."""

    def __init__(self, auth: dict = None):
        """Initialize the streaming KB agent."""
        self.auth = auth or {}
        self.buffer = StreamBuffer(preserve_json=True)
        self.llm = chat_service  # Reference to LLM service
        # Mock KB search for testing
        self._kb_store = {}

    async def search_kb(self, query: str) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for relevant documents.

        This is a mock implementation for testing.
        In production, this would call the actual KB search service.
        """
        # Simulate search delay
        await asyncio.sleep(0.1)

        # Mock search results based on query
        if "combat" in query.lower() or "rules" in query.lower():
            return [
                {
                    "path": "docs/combat-rules.md",
                    "content": "Combat in Wylding Woods follows turn-based rules...",
                    "relevance": 0.95
                },
                {
                    "path": "docs/player-guide.md",
                    "content": "Players take turns in combat...",
                    "relevance": 0.88
                },
                {
                    "path": "docs/abilities.md",
                    "content": "Special abilities can be used in combat...",
                    "relevance": 0.82
                }
            ]
        elif "unknown" in query.lower():
            return []  # No results
        else:
            return [
                {
                    "path": "docs/general.md",
                    "content": f"Information about {query}",
                    "relevance": 0.75
                }
            ]

    def _format_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format search results into context for LLM."""
        if not documents:
            return "No documents found."

        context_parts = []
        for doc in documents[:3]:  # Limit to top 3
            context_parts.append(f"From {doc['path']}:\n{doc['content']}")

        return "\n\n".join(context_parts)

    async def process_streaming(
        self,
        query: str,
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process KB query with progressive streaming.

        Args:
            query: The search query
            stream: Whether to stream the response generation

        Yields:
            Events with metadata and content chunks
        """
        # Phase 1: Search (immediate metadata)
        search_start = time.time()
        documents = await self.search_kb(query)
        search_time = time.time() - search_start

        # Send search complete metadata
        yield {
            "type": "metadata",
            "phase": "search_complete",
            "documents_found": len(documents),
            "search_time_ms": int(search_time * 1000),
            "sources": [doc["path"] for doc in documents[:3]] if documents else []
        }

        # Handle no results case
        if not documents:
            yield {
                "type": "content",
                "content": "I couldn't find any relevant information in the knowledge base."
            }
            return

        # Phase 2: Build context and prompt
        context = self._format_context(documents)
        prompt = f"""Based on these knowledge base documents:

{context}

Please answer the user's question: {query}

Provide a clear, comprehensive answer based on the information found."""

        # Phase 3: Generate response
        if stream and hasattr(chat_service, 'chat_completion_stream'):
            # Real streaming from LLM
            response_buffer = ""

            try:
                async for chunk in chat_service.chat_completion_stream(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2048
                ):
                    # Extract content from chunk
                    chunk_text = ""
                    if chunk.get("type") == "content":
                        chunk_text = chunk.get("content", "")
                    elif "choices" in chunk:
                        delta = chunk["choices"][0].get("delta", {})
                        chunk_text = delta.get("content", "")

                    if chunk_text:
                        response_buffer += chunk_text

                        # Stream through buffer for intelligent chunking
                        async for output in self.buffer.process(chunk_text):
                            yield {
                                "type": "content",
                                "content": output
                            }

                # Flush remaining content
                async for output in self.buffer.flush():
                    if output:
                        yield {
                            "type": "content",
                            "content": output
                        }

                # Send completion metadata
                yield {
                    "type": "metadata",
                    "phase": "complete",
                    "total_response_length": len(response_buffer),
                    "model_used": chunk.get("model", "unknown") if 'chunk' in locals() else "unknown"
                }

            except (AttributeError, NotImplementedError):
                # Streaming not available, fallback
                await self._fallback_complete_response(prompt, documents, query)

        else:
            # Non-streaming or fallback path
            await self._fallback_complete_response(prompt, documents, query)

    async def _fallback_complete_response(
        self,
        prompt: str,
        documents: List[Dict[str, Any]],
        query: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Fallback to complete response when streaming unavailable."""
        try:
            response = await chat_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048
            )

            content = response.get("response", f"Found {len(documents)} documents about: {query}")

            # Simulate streaming with buffer
            async for chunk in self.buffer.process(content):
                yield {
                    "type": "content",
                    "content": chunk
                }

            # Flush remaining
            async for chunk in self.buffer.flush():
                if chunk:
                    yield {
                        "type": "content",
                        "content": chunk
                    }

        except Exception as e:
            logger.error(f"KB fallback error: {e}")
            yield {
                "type": "content",
                "content": f"Found {len(documents)} relevant documents for your query."
            }

    async def process(self, query: str) -> str:
        """
        Legacy non-streaming process method.

        Args:
            query: The search query

        Returns:
            Complete response text
        """
        documents = await self.search_kb(query)

        if not documents:
            return "I couldn't find any relevant information in the knowledge base."

        context = self._format_context(documents)
        prompt = f"""Based on these knowledge base documents:

{context}

Please answer the user's question: {query}"""

        try:
            response = await chat_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048
            )
            return response.get("response", f"Found {len(documents)} documents about: {query}")
        except Exception as e:
            logger.error(f"KB process error: {e}")
            return f"Found {len(documents)} relevant documents for your query."


# Add missing import
import asyncio


# Monkey-patch existing KBAgent if needed
def patch_kb_agent():
    """Add streaming capabilities to existing KBAgent."""
    try:
        from app.services.kb.kb_agent import KBAgent

        # Create a streaming version
        streaming_agent = StreamingKBAgent()

        # Add the streaming method
        async def process_streaming_wrapper(self, query: str, stream: bool = True):
            """Wrapper to add streaming to existing KBAgent."""
            # Use the streaming implementation
            async for event in streaming_agent.process_streaming(query, stream):
                yield event

        # Patch the method onto KBAgent
        KBAgent.process_streaming = process_streaming_wrapper

        logger.info("Patched KBAgent with streaming support")

    except ImportError:
        logger.warning("Could not import KBAgent to patch")