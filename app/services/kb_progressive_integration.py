"""
Integration example: Progressive response delivery for KB Agent operations.
Shows how to integrate the progressive response system with existing KB tools.
"""
import asyncio
import httpx
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from .progressive_response import create_kb_progressive_stream
from app.shared.config import settings

logger = logging.getLogger(__name__)

# KB service URL
KB_SERVICE_URL = settings.KB_SERVICE_URL or "http://kb-service:8000"


async def progressive_interpret_knowledge(
    query: str,
    context_path: Optional[str] = None,
    operation_mode: str = "decision",
    conversation_id: Optional[str] = None,
    auth_header: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Progressive KB knowledge interpretation with immediate acknowledgment.

    This replaces the synchronous interpret_knowledge tool call with a
    streaming version that provides immediate feedback.

    Args:
        query: The question or analysis request
        context_path: Optional KB path to focus analysis
        operation_mode: decision, synthesis, validation, or workflow
        conversation_id: Optional conversation ID
        auth_header: Authentication header

    Yields:
        Progressive V0.3 format events:
        1. Immediate: "🤖 Coordinating technical, knowledge_management agents..."
        2. Analysis: "📊 Analyzing knowledge base content..."
        3. Detailed: Full KB agent response
        4. Complete: Metadata and timing
    """

    async def detailed_kb_analysis():
        """Generator for detailed KB analysis response."""
        try:
            # Determine knowledge scope for better messaging
            scope = "general"
            if context_path:
                if "development" in context_path.lower():
                    scope = "development"
                elif "architecture" in context_path.lower():
                    scope = "architecture"
                elif "deployment" in context_path.lower():
                    scope = "deployment"
                else:
                    scope = "specialized"

            # Make actual KB service call
            headers = {}
            if auth_header:
                if auth_header.startswith("Bearer "):
                    headers["Authorization"] = auth_header
                else:
                    headers["X-API-Key"] = auth_header

            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "query": query,
                    "operation_mode": operation_mode
                }
                if context_path:
                    payload["context_path"] = context_path

                response = await client.post(
                    f"{KB_SERVICE_URL}/agent/interpret",
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    error_detail = f"KB service error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", error_detail)
                    except:
                        pass

                    yield {
                        "type": "content",
                        "content": f"❌ **Error**: {error_detail}\n\n"
                    }
                    return

                result = response.json()

                # Debug: Log the KB service response
                logger.warning(f"[DEBUG] KB service response keys: {list(result.keys())}")
                logger.warning(f"[DEBUG] KB service response: {result}")

                # Stream the interpretation result progressively
                # Handle nested response structure: content is in result.result.*
                result_data = result.get("result", {})
                interpretation = result_data.get("interpretation", "")
                reasoning = result_data.get("reasoning", "")
                sources = result_data.get("sources_used", [])

                # Debug: Log what we extracted
                logger.warning(f"[DEBUG] Extracted interpretation length: {len(interpretation) if interpretation else 0}")
                logger.warning(f"[DEBUG] Extracted reasoning length: {len(reasoning) if reasoning else 0}")
                logger.warning(f"[DEBUG] Extracted sources count: {len(sources)}")

                # Main interpretation content
                yield {
                    "type": "content",
                    "content": f"## 🧠 KB Agent Analysis\n\n"
                }

                if interpretation:
                    # Stream interpretation in chunks for better UX
                    chunks = interpretation.split('\n\n')
                    for i, chunk in enumerate(chunks):
                        if chunk.strip():
                            yield {
                                "type": "content",
                                "content": chunk.strip() + "\n\n"
                            }
                            # Small delay for progressive feel
                            if i < len(chunks) - 1:
                                await asyncio.sleep(0.2)

                # Add reasoning if available
                if reasoning:
                    yield {
                        "type": "content",
                        "content": "### 🔍 **Decision Logic**\n\n"
                    }

                    reasoning_chunks = reasoning.split('\n\n')
                    for chunk in reasoning_chunks:
                        if chunk.strip():
                            yield {
                                "type": "content",
                                "content": chunk.strip() + "\n\n"
                            }
                            await asyncio.sleep(0.1)

                # Add sources if available
                if sources:
                    yield {
                        "type": "content",
                        "content": "### 📚 **Knowledge Sources**\n\n"
                    }

                    for source in sources[:5]:  # Limit to top 5
                        yield {
                            "type": "content",
                            "content": f"- `{source}`\n"
                        }
                        await asyncio.sleep(0.05)

                    if len(sources) > 5:
                        yield {
                            "type": "content",
                            "content": f"\n*... and {len(sources) - 5} more sources*\n"
                        }

                # Performance metadata
                performance = result.get("performance", {})
                if performance:
                    query_time = performance.get("query_time", 0)
                    model_used = performance.get("model_used", "unknown")

                    yield {
                        "type": "metadata",
                        "kb_query_time": query_time,
                        "kb_model": model_used,
                        "kb_sources_count": len(sources),
                        "kb_operation": operation_mode
                    }

        except Exception as e:
            logger.error(f"Error in progressive KB interpretation: {e}")
            yield {
                "type": "content",
                "content": f"❌ **Unexpected error**: {str(e)}\n\n"
            }

    # Determine knowledge scope for messaging
    scope = "general"
    if context_path:
        if any(term in context_path.lower() for term in ["dev", "code", "programming"]):
            scope = "development"
        elif any(term in context_path.lower() for term in ["arch", "design", "system"]):
            scope = "architecture"
        elif any(term in context_path.lower() for term in ["deploy", "ops", "production"]):
            scope = "deployment"
        else:
            scope = "specialized"

    # Create progressive stream
    async for event in create_kb_progressive_stream(
        operation="interpret_knowledge",
        detailed_generator=detailed_kb_analysis(),
        conversation_id=conversation_id,
        knowledge_scope=scope
    ):
        yield event


async def progressive_synthesize_information(
    sources: list,
    focus: Optional[str] = None,
    conversation_id: Optional[str] = None,
    auth_header: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Progressive KB information synthesis with immediate acknowledgment.

    Args:
        sources: List of KB paths or topics to synthesize
        focus: Optional focus for synthesis
        conversation_id: Optional conversation ID
        auth_header: Authentication header

    Yields:
        Progressive synthesis response
    """

    async def detailed_synthesis():
        """Generator for detailed synthesis response."""
        try:
            headers = {}
            if auth_header:
                if auth_header.startswith("Bearer "):
                    headers["Authorization"] = auth_header
                else:
                    headers["X-API-Key"] = auth_header

            async with httpx.AsyncClient(timeout=45.0) as client:
                payload = {
                    "sources": sources
                }
                if focus:
                    payload["focus"] = focus

                response = await client.post(
                    f"{KB_SERVICE_URL}/agent/synthesize",
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    error_detail = f"KB synthesis error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", error_detail)
                    except:
                        pass

                    yield {
                        "type": "content",
                        "content": f"❌ **Synthesis Error**: {error_detail}\n\n"
                    }
                    return

                result = response.json()

                # Stream synthesis results
                synthesis = result.get("synthesis", "")
                connections = result.get("connections", [])
                insights = result.get("insights", [])

                yield {
                    "type": "content",
                    "content": f"## 🔄 Knowledge Synthesis\n\n"
                }

                if focus:
                    yield {
                        "type": "content",
                        "content": f"**Focus**: {focus}\n\n"
                    }

                # Main synthesis content
                if synthesis:
                    sections = synthesis.split('\n\n')
                    for section in sections:
                        if section.strip():
                            yield {
                                "type": "content",
                                "content": section.strip() + "\n\n"
                            }
                            await asyncio.sleep(0.3)

                # Cross-domain connections
                if connections:
                    yield {
                        "type": "content",
                        "content": "### 🌐 **Cross-Domain Connections**\n\n"
                    }

                    for i, connection in enumerate(connections[:3]):
                        yield {
                            "type": "content",
                            "content": f"{i+1}. {connection}\n\n"
                        }
                        await asyncio.sleep(0.2)

                # Key insights
                if insights:
                    yield {
                        "type": "content",
                        "content": "### 💡 **Key Insights**\n\n"
                    }

                    for insight in insights:
                        yield {
                            "type": "content",
                            "content": f"- {insight}\n"
                        }
                        await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in progressive synthesis: {e}")
            yield {
                "type": "content",
                "content": f"❌ **Synthesis error**: {str(e)}\n\n"
            }

    # Create progressive stream for synthesis
    async for event in create_kb_progressive_stream(
        operation="synthesize_information",
        detailed_generator=detailed_synthesis(),
        conversation_id=conversation_id,
        knowledge_scope=f"{len(sources)} knowledge sources"
    ):
        yield event


# Integration with chat service routing
async def handle_kb_tool_progressively(
    tool_name: str,
    tool_args: Dict[str, Any],
    conversation_id: Optional[str] = None,
    auth_header: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Progressive handler for KB tools that replaces synchronous tool calls.

    Args:
        tool_name: Name of the KB tool
        tool_args: Tool arguments
        conversation_id: Optional conversation ID
        auth_header: Authentication header

    Yields:
        Progressive V0.3 format events
    """

    if tool_name == "interpret_knowledge":
        async for event in progressive_interpret_knowledge(
            query=tool_args.get("query", ""),
            context_path=tool_args.get("context_path"),
            operation_mode=tool_args.get("operation_mode", "decision"),
            conversation_id=conversation_id,
            auth_header=auth_header
        ):
            yield event

    elif tool_name == "synthesize_kb_information":
        async for event in progressive_synthesize_information(
            sources=tool_args.get("sources", []),
            focus=tool_args.get("focus"),
            conversation_id=conversation_id,
            auth_header=auth_header
        ):
            yield event

    else:
        # For other tools, use regular synchronous handling
        # (This would call the existing kb_tools functions)
        yield {
            "type": "content",
            "content": f"🔧 **Tool**: {tool_name} - Using standard synchronous processing\n\n"
        }


# Example usage in chat service
"""
# In unified_chat.py or similar:

if selected_tool == "interpret_knowledge":
    # Instead of synchronous tool call:
    # result = await call_kb_tool(tool_name, tool_args)

    # Use progressive version:
    async for event in handle_kb_tool_progressively(
        tool_name="interpret_knowledge",
        tool_args=tool_args,
        conversation_id=conversation_id,
        auth_header=request.headers.get("X-API-Key")
    ):
        yield event
"""