"""
Progressive streaming implementation for MCP Agent.

Sends tool execution status then streams narrative responses.
"""

import time
import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional

from app.services.streaming_buffer import StreamBuffer
from app.services.llm.chat_service import chat_service

logger = logging.getLogger(__name__)


class StreamingMCPAgent:
    """MCP Agent with progressive streaming capabilities."""

    def __init__(self):
        """Initialize the streaming MCP agent."""
        self.buffer = StreamBuffer(preserve_json=True)
        self.llm = chat_service  # Use the shared chat service

    def _select_tool(self, request: dict) -> str:
        """
        Select appropriate tool based on request.

        Mock implementation for testing.
        """
        message = request.get("message", "").lower()
        tool = request.get("tool", "").lower()

        if "weather" in message or "weather" in tool:
            return "weather_tool"
        elif "data" in message or "data" in tool:
            return "data_tool"
        elif "file" in message:
            return "file_tool"
        else:
            return "general_tool"

    async def _execute_tool(self, tool_name: str, request: dict) -> dict:
        """
        Execute the selected tool.

        Mock implementation for testing.
        """
        # Simulate tool execution delay
        await asyncio.sleep(0.2)

        if tool_name == "weather_tool":
            return {
                "temperature": 72,
                "conditions": "sunny",
                "humidity": 65,
                "narrative": "The weather today is beautiful with clear sunny skies and comfortable temperatures. Perfect for outdoor activities!"
            }
        elif tool_name == "data_tool":
            return {
                "data": [1, 2, 3, 4, 5],
                "type": "array",
                "count": 5
            }
        elif tool_name == "file_tool":
            return {
                "files": ["doc1.txt", "doc2.md", "script.py"],
                "directory": "/workspace",
                "narrative": "Found 3 files in the workspace directory."
            }
        else:
            return {
                "result": "Tool executed successfully",
                "narrative": f"The {tool_name} has been executed with the provided parameters."
            }

    def _should_stream_response(self, tool_result: dict) -> bool:
        """
        Determine if this tool result should be streamed.

        Stream narrative responses, not pure data.
        """
        # Stream if there's a narrative field
        if "narrative" in tool_result:
            return True

        # Stream if result is long text
        if isinstance(tool_result.get("result"), str):
            return len(tool_result["result"]) > 100

        # Don't stream pure data responses
        return False

    def _format_tool_result(self, tool_result: dict) -> str:
        """Format tool result for LLM generation."""
        if "narrative" in tool_result:
            # Use the narrative as base
            base = tool_result["narrative"]

            # Add data context if present
            if "temperature" in tool_result:
                return f"{base}\n\nDetails: Temperature: {tool_result['temperature']}°F, Conditions: {tool_result['conditions']}, Humidity: {tool_result['humidity']}%"
            elif "files" in tool_result:
                files_list = "\n".join(f"  - {f}" for f in tool_result["files"])
                return f"{base}\n\nFiles found:\n{files_list}"
            else:
                return base
        else:
            # Format as JSON for data responses
            return json.dumps(tool_result, indent=2)

    async def process_streaming(
        self,
        request: dict,
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process MCP request with progressive streaming.

        Args:
            request: The request containing tool and parameters
            stream: Whether to stream narrative responses

        Yields:
            Events with tool status and content
        """
        # Phase 1: Tool selection
        tool_name = self._select_tool(request)

        # Send tool selection metadata
        yield {
            "type": "metadata",
            "phase": "tool_selected",
            "tool": tool_name,
            "status": "executing"
        }

        # Phase 2: Tool execution
        try:
            tool_start = time.time()
            tool_result = await self._execute_tool(tool_name, request)
            tool_time = time.time() - tool_start

            # Send tool completion metadata
            yield {
                "type": "metadata",
                "phase": "tool_complete",
                "tool": tool_name,
                "status": "success",
                "execution_time_ms": int(tool_time * 1000)
            }

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            yield {
                "type": "error",
                "content": f"Tool execution failed: {str(e)}"
            }
            return

        # Phase 3: Response generation
        if stream and self._should_stream_response(tool_result):
            # Stream narrative response
            prompt = self._format_tool_result(tool_result)

            if hasattr(self.llm, 'chat_completion_stream'):
                try:
                    response_buffer = ""

                    async for chunk in self.llm.chat_completion_stream(
                        messages=[{"role": "user", "content": f"Format this result in a friendly way: {prompt}"}],
                        temperature=0.7,
                        max_tokens=1024
                    ):
                        # Extract content
                        chunk_text = ""
                        if chunk.get("type") == "content":
                            chunk_text = chunk.get("content", "")
                        elif "choices" in chunk:
                            delta = chunk["choices"][0].get("delta", {})
                            chunk_text = delta.get("content", "")

                        if chunk_text:
                            response_buffer += chunk_text

                            # Stream through buffer
                            async for output in self.buffer.process(chunk_text):
                                yield {
                                    "type": "content",
                                    "content": output
                                }

                    # Flush remaining
                    async for output in self.buffer.flush():
                        if output:
                            yield {
                                "type": "content",
                                "content": output
                            }

                except (AttributeError, NotImplementedError):
                    # Fallback to simulated streaming
                    await self._fallback_streaming(tool_result)

            else:
                # No streaming available, simulate
                await self._fallback_streaming(tool_result)

        else:
            # Don't stream pure data responses
            formatted = self._format_tool_result(tool_result)
            yield {
                "type": "content",
                "content": formatted
            }

    async def _fallback_streaming(self, tool_result: dict) -> AsyncGenerator[Dict[str, Any], None]:
        """Fallback streaming when real streaming unavailable."""
        formatted = self._format_tool_result(tool_result)

        # Simulate streaming with buffer
        async for chunk in self.buffer.process(formatted):
            yield {
                "type": "content",
                "content": chunk
            }

        async for chunk in self.buffer.flush():
            if chunk:
                yield {
                    "type": "content",
                    "content": chunk
                }

    async def process_request(self, request: dict) -> dict:
        """
        Legacy non-streaming process method.

        Args:
            request: The request to process

        Returns:
            Complete response dict
        """
        tool_name = self._select_tool(request)
        tool_result = await self._execute_tool(tool_name, request)
        formatted = self._format_tool_result(tool_result)

        return {
            "response": formatted,
            "tool_used": tool_name,
            "success": True
        }


# Monkey-patch existing MCPAgent if needed
def patch_mcp_agent():
    """Add streaming capabilities to existing MCPAgent."""
    try:
        # Try to import the actual MCP agent
        from app.services.chat.mcp_agent import MCPAgent

        # Create a streaming version
        streaming_agent = StreamingMCPAgent()

        # Add the streaming method
        async def process_streaming_wrapper(self, request: dict, stream: bool = True):
            """Wrapper to add streaming to existing MCPAgent."""
            async for event in streaming_agent.process_streaming(request, stream):
                yield event

        # Patch the method
        MCPAgent.process_streaming = process_streaming_wrapper

        logger.info("Patched MCPAgent with streaming support")

    except ImportError:
        logger.warning("Could not import MCPAgent to patch")


# Also create a standalone MCPAgent class for testing
class MCPAgent:
    """MCP Agent for testing."""

    def __init__(self):
        self.streaming_agent = StreamingMCPAgent()

    async def process_streaming(self, request: dict, stream: bool = True):
        """Process with streaming."""
        async for event in self.streaming_agent.process_streaming(request, stream):
            yield event

    async def process_request(self, request: dict) -> dict:
        """Process without streaming."""
        return await self.streaming_agent.process_request(request)