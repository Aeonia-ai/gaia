"""
Unified Intelligent Chat Handler

A single endpoint that uses LLM tool-calling to intelligently handle requests:
- Direct responses for simple queries (no tools)
- KB tools for knowledge base operations
- MCP agent for file/system operations
- Multi-agent orchestration for complex analysis
"""
import logging
import time
import uuid
import json
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
from enum import Enum

from app.services.llm.chat_service import chat_service
from app.services.streaming_buffer import StreamBuffer
from app.services.chat.lightweight_chat_hot import hot_chat_service
from app.services.llm import LLMProvider
import httpx
from app.shared.config import settings
from .kb_tools import KB_TOOLS, KBToolExecutor

logger = logging.getLogger(__name__)


class RouteType(str, Enum):
    """Types of routing decisions"""
    DIRECT = "direct"
    MCP_AGENT = "mcp_agent"
    MULTIAGENT = "multiagent"


def split_on_word_boundaries(text: str, target_chunk_size: int = 50) -> List[str]:
    """
    Split text into chunks on word boundaries, respecting token integrity and JSON blocks.
    
    Args:
        text: The text to split
        target_chunk_size: Target size for chunks (will split at nearest word boundary)
    
    Returns:
        List of text chunks split on word boundaries
    """
    if not text:
        return []
    
    import re
    
    chunks = []
    current_chunk = ""
    
    # Pattern to match JSON objects including nested ones
    # This uses a simple approach - for production, consider using json.loads to validate
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    
    # Split text preserving JSON blocks as single units
    parts = []
    last_end = 0
    
    for match in re.finditer(json_pattern, text):
        # Add text before JSON
        if match.start() > last_end:
            before_text = text[last_end:match.start()]
            # Split non-JSON text into words
            parts.extend(before_text.split())
        # Add entire JSON block as one "word"
        parts.append(match.group())
        last_end = match.end()
    
    # Add remaining text after last JSON
    if last_end < len(text):
        remaining = text[last_end:]
        parts.extend(remaining.split())
    
    # If no JSON found, just split normally
    if not parts:
        parts = text.split()
    
    # Now chunk the parts respecting boundaries
    for part in parts:
        # Check if adding this part would exceed target size
        if current_chunk and len(current_chunk) + len(part) + 1 > target_chunk_size:
            # Don't split if current chunk is empty or very small
            if len(current_chunk) > 10:  # Minimum chunk size
                chunks.append(current_chunk)
                current_chunk = part
            else:
                # Add to current chunk even if it exceeds target
                if current_chunk:
                    current_chunk += " " + part
                else:
                    current_chunk = part
        else:
            # Add part to current chunk
            if current_chunk:
                # Check if we need a space separator
                if current_chunk.endswith('}') or part.startswith('{'):
                    current_chunk += part  # No space between/around JSON
                else:
                    current_chunk += " " + part
            else:
                current_chunk = part
    
    # Add final chunk if any
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


class UnifiedChatHandler:
    """
    Handles all chat requests with intelligent routing via LLM tool-calling.
    
    Uses a single LLM call to decide whether to:
    1. Respond directly (no tools needed)
    2. Route to MCP agent (for tool use)
    3. Route to multi-agent orchestration (for complex analysis)
    """
    
    def __init__(self):
        # Pre-initialized services (hot-loaded)
        self.mcp_hot_service = hot_chat_service  # Already initialized at startup
        self.multiagent_orchestrator = None  # TODO: Initialize when available
        
        # Routing tools definition (for services that need routing)
        self.routing_tools = [
            {
                "type": "function",
                "function": {
                    "name": "use_mcp_agent",
                    "description": "Use this ONLY when the user explicitly asks to: read/write files outside KB, run system commands, search the web, make API calls, or perform system operations. Do NOT use for general questions or KB operations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reasoning": {
                                "type": "string",
                                "description": "Brief explanation of why MCP agent is needed"
                            }
                        },
                        "required": ["reasoning"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "use_asset_service", 
                    "description": "Use this ONLY when the user explicitly asks to generate/create an image, 3D model, audio file, or video. Keywords: 'generate', 'create', 'make' + asset type",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "asset_type": {
                                "type": "string",
                                "enum": ["image", "3d_model", "audio", "video"],
                                "description": "Type of asset to generate"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the asset to generate"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why asset service is needed"
                            }
                        },
                        "required": ["asset_type", "description", "reasoning"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "use_multiagent_orchestration",
                    "description": "Use this for complex requests that require multiple expert perspectives, cross-domain analysis, or coordinated reasoning across different specialties (technical, business, creative, etc.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "domains": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of domains needed (e.g., ['technical', 'business', 'creative'])"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why multiple agents are needed"
                            }
                        },
                        "required": ["domains", "reasoning"]
                    }
                }
            }
        ]
        
        # Metrics tracking
        self._routing_metrics = {
            RouteType.DIRECT: 0,
            RouteType.MCP_AGENT: 0,
            RouteType.MULTIAGENT: 0,
            "total_requests": 0,
            "avg_routing_time_ms": 0,
            "avg_total_time_ms": 0
        }
    
    async def process(self, message: str, auth: dict, context: Optional[dict] = None) -> dict:
        """
        Process message with intelligent routing.

        Returns a standardized response format regardless of routing path.

        TODO: REFACTOR NEEDED - Code Duplication with process_stream()
        ========================================================================
        This method shares ~60% of its code with process_stream() (~240 lines).
        The duplication has caused bugs in the past:
        - Bug: Streaming path (line 707) missing KB_TOOLS, causing LLM to report
          "I don't have access to a knowledge base search tool"
        - Root cause: Line 271 has `all_tools = self.routing_tools + KB_TOOLS` ✅
                      Line 707 only has `tools=self.routing_tools` ❌

        RECOMMENDED REFACTOR: Extract shared logic into _process_core(stream: bool)
        --------------------------------------------------------------------------
        Pattern (from Perplexity recommendation):

        async def _process_core(
            self,
            message: str,
            auth: dict,
            context: Optional[dict],
            stream: bool
        ) -> AsyncGenerator[Dict[str, Any], None]:
            '''
            Core routing and execution logic shared by both streaming and non-streaming.
            Yields chunks regardless of streaming mode.
            '''
            # Single source of truth for tools configuration
            all_tools = self.routing_tools + KB_TOOLS  # ✅ No divergence possible

            # All routing logic, tool execution, error handling...
            # Yield chunks incrementally

        async def process(...) -> dict:
            '''Non-streaming: Collect all chunks and return dict'''
            chunks = [chunk async for chunk in self._process_core(..., stream=False)]
            return self._assemble_response(chunks)

        async def process_stream(...) -> AsyncGenerator:
            '''Streaming: Yield chunks as they arrive'''
            async for chunk in self._process_core(..., stream=True):
                yield chunk

        Benefits:
        - Eliminates 240 lines of duplication
        - Prevents divergence bugs (single source of truth for tool config)
        - Easier to maintain and test
        - Changes only need to be made in one place

        See also: process_stream() at line 633 (needs same refactor)
        ========================================================================
        """
        start_time = time.time()
        request_id = f"chat-{uuid.uuid4()}"

        print(f"DEBUG: Starting unified chat process for message: {message[:50]}...")
        print(f"[AUTH DEBUG] Auth dict: {auth}")
        logger.info(f"[AUTH DEBUG] Auth dict: {auth}")

        # Update metrics
        self._routing_metrics["total_requests"] += 1

        # Pre-create conversation_id for unified behavior (matches streaming)
        conversation_id = await self._get_or_create_conversation_id(message, context, auth)

        # Update context with the conversation_id for any future operations
        if context is None:
            context = {}
        context["conversation_id"] = conversation_id

        # Build context (user info, conversation history, etc.)
        full_context = await self.build_context(auth, context)
        print(f"[CONTEXT DEBUG] Full context user_id: {full_context.get('user_id')}")
        logger.info(f"[CONTEXT DEBUG] Full context: {full_context}")

        # Single LLM call with routing capability - but no "routing overhead"
        llm_start = time.time()
        
        try:
            # Prepare messages for routing decision
            system_prompt = await self.get_routing_prompt(full_context)
            print(f"[SYSTEM PROMPT DEBUG] First 300 chars: {system_prompt[:300]}...")
            logger.info(f"[SYSTEM PROMPT DEBUG] First 200 chars: {system_prompt[:200]}...")
            
            # PERSONA FIX: Don't put system message in messages array
            messages = []  # Start with empty messages
            
            # Add conversation history if available (skip system messages!)
            if full_context.get("conversation_history"):
                for hist_msg in full_context["conversation_history"]:
                    if hist_msg["role"] in ["user", "assistant"]:  # Only user/assistant
                        messages.append({
                            "role": hist_msg["role"],
                            "content": hist_msg["content"]
                        })
            
            # Add current message
            messages.append({
                "role": "user",
                "content": message
            })
            
            # Debug: Print the messages being sent to LLM
            print(f"[MESSAGES DEBUG] Total messages: {len(messages)}")
            print(f"[PERSONA FIX] System prompt passed via parameter, not in messages")
            for i, msg in enumerate(messages):
                print(f"[MESSAGES DEBUG] Message {i} - Role: {msg['role']}, Content preview: {msg['content'][:100]}...")
            
            # Combine routing tools with KB tools
            all_tools = self.routing_tools + KB_TOOLS
            
            # Use chat service with all available tools
            routing_response = await chat_service.chat_completion(
                messages=messages,
                system_prompt=system_prompt,  # PASS SYSTEM PROMPT AS PARAMETER!
                tools=all_tools,
                tool_choice={"type": "auto"},  # Let LLM decide: direct response or tool use
                temperature=0.7,
                max_tokens=4096,
                request_id=f"{request_id}-routing"
            )
            
            llm_time = (time.time() - llm_start) * 1000
            
            # Check if LLM made tool calls
            if routing_response.get("tool_calls"):
                tool_calls = routing_response["tool_calls"]
                print(f"DEBUG: Found {len(tool_calls)} total tool calls")
                print(f"DEBUG: Tool call names: {[tc['function']['name'] for tc in tool_calls]}")
                
                # Check if any KB tools were called
                kb_calls = [tc for tc in tool_calls if self._classify_tool_call(tc["function"]["name"])[1]]
                print(f"DEBUG: KB calls found: {len(kb_calls)}")
                
                if kb_calls:
                    print(f"DEBUG: Found {len(kb_calls)} KB tool calls")
                    # Execute KB tools
                    tool_results = await self._execute_kb_tools(kb_calls, auth, request_id)
                    
                    # Make another LLM call with the tool results to generate final response
                    # For Anthropic, tool results are included as user messages
                    tool_result_content = "\n\nTool Results:\n"
                    for result in tool_results:
                        # Extract just the text content, not the full JSON to avoid formatting issues
                        if result['result'].get('success') and result['result'].get('content'):
                            # Clean the content of potential problematic characters
                            content = result['result']['content'].replace('🔍', '[SEARCH]').replace('**', '')
                            formatted_result = f"\n{result['tool']}:\n{content}\n"
                        else:
                            formatted_result = f"\n{result['tool']}:\nNo results found\n"
                        
                        print(f"DEBUG: Formatted result length: {len(formatted_result)}")
                        tool_result_content += formatted_result
                        print(f"DEBUG: After append, tool_result_content length: {len(tool_result_content)}")
                    
                    print(f"DEBUG: Tool results for final LLM call: {len(tool_results)} results")
                    print(f"DEBUG: Individual tool results: {tool_results}")
                    print(f"DEBUG: Final tool_result_content length: {len(tool_result_content)}")
                    print(f"DEBUG: Tool result content: {tool_result_content[:500]}...")
                    
                    messages.append({
                        "role": "user",
                        "content": tool_result_content
                    })
                    
                    print(f"DEBUG: Final messages for LLM: {len(messages)} messages")
                    
                    # Get final response from LLM with tool results
                    print(f"DEBUG: About to call LLM with {len(messages)} messages")
                    print(f"DEBUG: Last message content length: {len(messages[-1]['content'])}")
                    
                    try:
                        # Don't include tools in final call since we're providing results, not requesting tools
                        # IMPORTANT: Use same system_prompt as initial call to preserve persona!
                        final_response = await chat_service.chat_completion(
                            messages=messages,
                            temperature=0.7,
                            max_tokens=4096,
                            request_id=f"{request_id}-final",
                            system_prompt=system_prompt  # Preserve persona from initial call!
                        )
                        
                        print(f"DEBUG: LLM response received: {type(final_response)}")
                        
                        # Convert LLM service format to OpenAI format if needed
                        if 'response' in final_response and 'choices' not in final_response:
                            # LLM service returns direct response, convert to OpenAI format
                            final_response = {
                                "choices": [{
                                    "message": {
                                        "content": final_response['response']
                                    }
                                }],
                                "model": final_response.get('model', 'unknown'),
                                "usage": final_response.get('usage', {})
                            }
                            print(f"DEBUG: Converted LLM response to OpenAI format")
                        
                        print(f"DEBUG: LLM choices length: {len(final_response.get('choices', []))}")
                        if final_response.get('choices'):
                            choice_content = final_response['choices'][0].get('message', {}).get('content', '')
                            print(f"DEBUG: LLM choice content length: {len(choice_content)}")
                            print(f"DEBUG: LLM choice content preview: {choice_content[:100]}")
                    except Exception as e:
                        print(f"DEBUG: LLM call failed with error: {e}")
                        # Return tool results directly if LLM call fails
                        content = tool_result_content
                        final_response = {
                            "choices": [{"message": {"content": content}}],
                            "model": "fallback",
                            "usage": {"input_tokens": 0, "output_tokens": len(content) // 4}
                        }
                    
                    # Extract response content for saving
                    response_content = ""
                    if final_response.get("choices"):
                        response_content = final_response["choices"][0].get("message", {}).get("content", "")
                    
                    # Save conversation messages (conversation_id already created)
                    await self._save_conversation_messages(
                        conversation_id=conversation_id,
                        message=message,
                        response=response_content
                    )
                    
                    return {
                        "id": request_id,
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": final_response.get("model", "unknown"),
                        "choices": final_response.get("choices", []),
                        "usage": final_response.get("usage", {}),
                        "_metadata": {
                            "route_type": "kb_tools",
                            "tools_used": [tr["tool"] for tr in tool_results],
                            "total_time_ms": int((time.time() - start_time) * 1000),
                            "request_id": request_id,
                            "conversation_id": conversation_id
                        }
                    }
                
                # Handle routing tools (non-KB)
                tool_call = tool_calls[0]  # For routing, we only use the first
                tool_name = tool_call["function"]["name"]
                
                # Parse tool arguments
                tool_args_raw = tool_call["function"].get("arguments", "{}")
                if isinstance(tool_args_raw, str):
                    tool_args = json.loads(tool_args_raw)
                else:
                    tool_args = tool_args_raw
                
                if tool_name == "use_mcp_agent":
                    # Route to MCP agent for tool use
                    route_type = RouteType.MCP_AGENT
                    self._routing_metrics[route_type] += 1
                    
                    logger.info(
                        f"[{request_id}] Routing to MCP agent - {tool_args.get('reasoning', 'No reason provided')}"
                    )
                    
                    # Use the hot-loaded MCP service
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Add routing metadata
                    routing_overhead = llm_time  # Time to decide routing
                    result["_metadata"] = {
                        "route_type": route_type,
                        "routing_time_ms": int(routing_overhead),
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "reasoning": tool_args.get("reasoning"),
                        "request_id": request_id
                    }
                    
                    # Save conversation messages (conversation_id already created)
                    await self._save_conversation_messages(
                        conversation_id=conversation_id,
                        message=message,
                        response=result.get("response", "")
                    )

                    # Add conversation_id to metadata
                    result["_metadata"]["conversation_id"] = conversation_id
                    
                    return result
                
                elif tool_name == "use_asset_service":
                    # Route to Asset service
                    route_type = RouteType.MCP_AGENT  # For now, use MCP agent for assets
                    self._routing_metrics[route_type] += 1
                    
                    asset_type = tool_args.get("asset_type", "image")
                    description = tool_args.get("description", "")
                    reasoning = tool_args.get("reasoning", "")
                    
                    logger.info(
                        f"[{request_id}] Routing to Asset service - type: {asset_type}, desc: {description}"
                    )
                    
                    # For now, use MCP agent to handle asset generation
                    # TODO: Implement direct asset service integration
                    from app.models.chat import ChatRequest
                    asset_message = f"Generate a {asset_type}: {description}"
                    chat_request = ChatRequest(message=asset_message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Add routing metadata
                    result["_metadata"] = {
                        "route_type": "asset_service",
                        "routing_time_ms": int(llm_time),  # Time to decide routing
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "asset_type": asset_type,
                        "description": description,
                        "reasoning": reasoning,
                        "request_id": request_id,
                        "note": "Using MCP agent for asset generation"
                    }
                    
                    return result
                    
                elif tool_name == "use_multiagent_orchestration":
                    # Route to multi-agent system
                    route_type = RouteType.MULTIAGENT
                    self._routing_metrics[route_type] += 1
                    
                    domains = tool_args.get("domains", [])
                    reasoning = tool_args.get("reasoning", "")
                    
                    logger.info(
                        f"[{request_id}] Routing to multi-agent - domains: {domains}, reason: {reasoning}"
                    )
                    
                    # For now, fall back to MCP agent until multiagent is ready
                    # TODO: Implement actual multiagent orchestration
                    logger.warning("Multi-agent orchestration not yet implemented, using MCP agent")
                    
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Add routing metadata
                    result["_metadata"] = {
                        "route_type": route_type,
                        "routing_time_ms": int(llm_time),  # Time to decide routing
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "domains": domains,
                        "reasoning": reasoning,
                        "request_id": request_id,
                        "fallback": "mcp_agent"  # Remove when multiagent is ready
                    }
                    
                    return result
                
                else:
                    # Unknown tool - fallback to MCP agent
                    logger.warning(f"Unknown routing tool: {tool_name}, falling back to MCP agent")
                    route_type = RouteType.MCP_AGENT
                    self._routing_metrics[route_type] += 1
                    
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    result["_metadata"] = {
                        "route_type": route_type,
                        "routing_time_ms": int(llm_time),  # Time to decide routing
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "request_id": request_id,
                        "error": f"Unknown tool: {tool_name}, used fallback"
                    }
                    
                    return result
            
            else:
                # Direct response - no routing needed, just normal LLM response
                route_type = RouteType.DIRECT
                self._routing_metrics[route_type] += 1
                
                # Extract content from the response structure
                content = routing_response.get("response", "")
                model = routing_response.get("model", "claude-haiku-4-5")
                usage = routing_response.get("usage", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                })
                
                logger.info(
                    f"[{request_id}] Direct response in {llm_time:.0f}ms (no routing needed)"
                )
                
                # Update routing metrics - no routing overhead for direct responses
                self._update_timing_metrics(0, (time.time() - start_time) * 1000)
                
                # Save conversation messages (conversation_id already created)
                await self._save_conversation_messages(
                    conversation_id=conversation_id,
                    message=message,
                    response=content
                )
                
                return {
                    "id": request_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": usage,
                    "_metadata": {
                        "route_type": route_type,
                        "routing_time_ms": 0,  # No routing overhead for direct responses
                        "llm_time_ms": int(llm_time),  # Actual LLM response time
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "request_id": request_id,
                        "conversation_id": conversation_id  # Add conversation_id
                    }
                }
                
        except Exception as e:
            logger.error(f"[{request_id}] Routing error: {e}", exc_info=True)
            # Fall back to direct MCP agent on error
            from app.models.chat import ChatRequest
            chat_request = ChatRequest(message=message)
            
            result = await self.mcp_hot_service.process_chat(
                request=chat_request,
                auth_principal=auth
            )
            
            # Save conversation messages even on error fallback (conversation_id already created)
            await self._save_conversation_messages(
                conversation_id=conversation_id,
                message=message,
                response=result.get("response", "")
            )
            
            result["_metadata"] = {
                "route_type": RouteType.MCP_AGENT,
                "error": str(e),
                "fallback": True,
                "request_id": request_id,
                "conversation_id": conversation_id
            }
            
            return result
    
    async def process_stream(
        self,
        message: str,
        auth: dict,
        context: Optional[dict] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process message with intelligent routing and streaming response.

        Yields OpenAI-compatible SSE chunks for streaming.

        TODO: REFACTOR NEEDED - Code Duplication with process()
        ========================================================================
        This method shares ~60% of its code with process() (~240 lines).
        The duplication has caused bugs in the past:
        - Bug: This streaming path (line 707) missing KB_TOOLS
        - Symptom: LLM says "I don't have access to a knowledge base search tool"
        - Root cause: Line 707 only has `tools=self.routing_tools` ❌
                      Non-streaming (line 271) correctly has
                      `all_tools = self.routing_tools + KB_TOOLS` ✅

        Dead Code: Lines 729-815 handle KB execution but are unreachable because
                   LLM never sees KB tools in its tool list to call them.

        RECOMMENDED REFACTOR: Extract shared logic into _process_core(stream: bool)
        --------------------------------------------------------------------------
        Pattern (from Perplexity recommendation):

        async def _process_core(
            self,
            message: str,
            auth: dict,
            context: Optional[dict],
            stream: bool
        ) -> AsyncGenerator[Dict[str, Any], None]:
            '''
            Core routing and execution logic shared by both streaming and non-streaming.
            Yields chunks regardless of streaming mode.
            '''
            # Single source of truth for tools configuration
            all_tools = self.routing_tools + KB_TOOLS  # ✅ No divergence possible

            # All routing logic, tool execution, error handling...
            # Yield chunks incrementally

        async def process(...) -> dict:
            '''Non-streaming: Collect all chunks and return dict'''
            chunks = [chunk async for chunk in self._process_core(..., stream=False)]
            return self._assemble_response(chunks)

        async def process_stream(...) -> AsyncGenerator:
            '''Streaming: Yield chunks as they arrive'''
            async for chunk in self._process_core(..., stream=True):
                yield chunk

        Benefits:
        - Eliminates 240 lines of duplication
        - Prevents divergence bugs (single source of truth for tool config)
        - Removes dead code (unreachable KB execution path)
        - Easier to maintain and test
        - Changes only need to be made in one place

        See also: process() at line 208 (needs same refactor)
        ========================================================================
        """
        print(f"[TTFC DEBUG] process_stream() called with message: {message[:50]}")
        start_time = time.time()
        request_id = f"chat-{uuid.uuid4()}"
        first_content_time = None  # Track when first text content is sent
        time_to_first_chunk_ms = None  # Will be set when first chunk is sent

        # Update metrics
        self._routing_metrics["total_requests"] += 1

        # Build context
        full_context = await self.build_context(auth, context)

        # Pre-create conversation_id for streaming
        conversation_id = await self._get_or_create_conversation_id(message, context, auth)

        # Update context with the conversation_id for any future operations
        if context is None:
            context = {}
        context["conversation_id"] = conversation_id

        # Track accumulated response for saving after streaming
        accumulated_response = ""

        try:
            # Emit conversation metadata as first event for V0.3 streaming
            yield {
                "type": "metadata",
                "conversation_id": conversation_id,
                "model": "unified-chat",
                "timestamp": int(time.time())
            }

            print(f"[TTFC DEBUG] Metadata yielded, starting routing decision...")

            # Make routing decision
            llm_start = time.time()
            # Prepare messages for routing decision
            system_prompt = await self.get_routing_prompt(full_context)
            print(f"[SYSTEM PROMPT DEBUG] First 300 chars: {system_prompt[:300]}...")
            logger.info(f"[SYSTEM PROMPT DEBUG] First 200 chars: {system_prompt[:200]}...")
            
            # PERSONA FIX: Don't put system message in messages array
            messages = []  # Start with empty messages
            
            # Add conversation history if available (skip system messages!)
            if full_context.get("conversation_history"):
                for hist_msg in full_context["conversation_history"]:
                    if hist_msg["role"] in ["user", "assistant"]:  # Only user/assistant
                        messages.append({
                            "role": hist_msg["role"],
                            "content": hist_msg["content"]
                        })
            
            # Add current message
            messages.append({
                "role": "user",
                "content": message
            })

            # Combine routing tools with KB tools (matches non-streaming at line 320)
            all_tools = self.routing_tools + KB_TOOLS

            # First, make routing decision (non-streaming)
            routing_response = await chat_service.chat_completion(
                messages=messages,
                system_prompt=system_prompt,  # PASS SYSTEM PROMPT AS PARAMETER!
                tools=all_tools,
                tool_choice={"type": "auto"},
                temperature=0.7,
                max_tokens=4096,
                request_id=f"{request_id}-routing"
            )

            llm_time = (time.time() - llm_start) * 1000

            print(f"[TTFC DEBUG] LLM routing done in {llm_time:.0f}ms, has tool_calls: {bool(routing_response.get('tool_calls'))}")

            # Check if LLM made tool calls
            if routing_response.get("tool_calls"):
                # Route to appropriate service with streaming
                tool_call = routing_response["tool_calls"][0]
                tool_name = tool_call["function"]["name"]
                tool_args = self._parse_tool_arguments(tool_call)
                
                # Classify the tool
                tool_type, is_kb_tool = self._classify_tool_call(tool_name)
                
                # Handle KB tools first
                if is_kb_tool:
                    route_type = RouteType.DIRECT  # KB tools are direct responses
                    self._routing_metrics[route_type] += 1

                    print(f"[TTFC DEBUG] Taking KB TOOL streaming path: {tool_name}")
                    logger.info(f"[{request_id}] Executing KB tool in streaming mode: {tool_name}")
                    
                    # Execute KB tool
                    kb_executor = KBToolExecutor(auth)
                    kb_result = await kb_executor.execute_tool(tool_name, tool_args)
                    
                    # Format the response
                    if kb_result.get('success') and kb_result.get('content'):
                        content = kb_result['content']
                    else:
                        content = f"No results found for: {tool_args.get('query', 'your search')}"

                    # Track for saving after streaming
                    accumulated_response = content

                    # Stream the KB results
                    model = "kb-service"
                    
                    # First chunk with role
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }]
                    }
                    
                    # Use StreamBuffer for phrase-aware chunking
                    buffer = StreamBuffer(preserve_json=True, chunking_mode="phrase")

                    # Process content through buffer
                    async for chunk_text in buffer.process(content):
                        # Track first content chunk timing
                        if first_content_time is None:
                            first_content_time = time.time()
                            time_to_first_chunk_ms = int((first_content_time - start_time) * 1000)
                            print(f"[TTFC] [{request_id}] Time to first content chunk: {time_to_first_chunk_ms}ms")
                            logger.info(f"[{request_id}] Time to first content chunk: {time_to_first_chunk_ms}ms")

                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.003)

                    # Flush any remaining content
                    async for chunk_text in buffer.flush():
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.003)
                    
                    # Final chunk - send metadata then done
                    if time_to_first_chunk_ms is not None:
                        yield {
                            "type": "metadata",
                            "time_to_first_chunk_ms": time_to_first_chunk_ms,
                            "routing_time_ms": int(llm_time),
                            "total_time_ms": int((time.time() - start_time) * 1000)
                        }

                    yield {"type": "done", "finish_reason": "stop"}
                    return
                
                # Tool-routed responses - simulate streaming for better UX
                elif tool_name == "use_mcp_agent":
                    route_type = RouteType.MCP_AGENT
                    self._routing_metrics[route_type] += 1

                    print(f"[TTFC DEBUG] Taking MCP AGENT streaming path")
                    logger.info(f"[{request_id}] Routing to MCP agent with simulated streaming")
                    
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    # Get the full response from MCP agent
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Extract the content
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    model = result.get("model", "unknown")

                    # Track for saving after streaming
                    accumulated_response = content

                    # Stream the content in chunks for better perceived performance
                    # Use larger chunks for tool responses since they often contain structured data
                    chunk_size = 50  # Characters per chunk
                    
                    # First chunk with role
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }]
                    }
                    
                    # Use StreamBuffer for phrase-aware chunking
                    buffer = StreamBuffer(preserve_json=True, chunking_mode="phrase")

                    # Process content through buffer
                    async for chunk_text in buffer.process(content):
                        # Track first content chunk timing
                        if first_content_time is None:
                            first_content_time = time.time()
                            time_to_first_chunk_ms = int((first_content_time - start_time) * 1000)
                            logger.info(f"[{request_id}] Time to first content chunk: {time_to_first_chunk_ms}ms (MCP agent)")

                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        # Small delay to simulate streaming (shorter than direct responses)
                        await asyncio.sleep(0.005)

                    # Flush any remaining content
                    async for chunk_text in buffer.flush():
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.005)
                    
                    # Final chunk with metadata
                    final_metadata = {
                        "route_type": route_type.value,
                        "routing_time_ms": int(llm_time),
                        "total_time_ms": int((time.time() - start_time) * 1000),
                        "reasoning": tool_args.get("reasoning"),
                        "request_id": request_id,
                        "mcp_response_time_ms": result.get("_response_time_ms", 0)
                    }
                    if time_to_first_chunk_ms is not None:
                        final_metadata["time_to_first_chunk_ms"] = time_to_first_chunk_ms

                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "_metadata": final_metadata
                    }
                
                elif tool_name == "use_kb_service":
                    # KB service streaming
                    route_type = RouteType.MCP_AGENT  # Using MCP for now
                    self._routing_metrics[route_type] += 1
                    
                    query = tool_args.get("query", message)
                    logger.info(f"[{request_id}] Routing to KB service with simulated streaming")
                    
                    from app.models.chat import ChatRequest
                    kb_message = f"Search my knowledge base for: {query}"
                    chat_request = ChatRequest(message=kb_message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Stream the KB response
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    model = result.get("model", "unknown")

                    # Track for saving after streaming
                    accumulated_response = content

                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }]
                    }
                    
                    # Use StreamBuffer for sentence-aware chunking (KB results)
                    buffer = StreamBuffer(preserve_json=True, chunking_mode="phrase")
                    async for chunk_text in buffer.process(content):
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.003)

                    # Flush any remaining content
                    async for chunk_text in buffer.flush():
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.003)

                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "_metadata": {
                            "route_type": "kb_service",
                            "routing_time_ms": int(llm_time),
                            "total_time_ms": int((time.time() - start_time) * 1000),
                            "query": query,
                            "reasoning": tool_args.get("reasoning"),
                            "request_id": request_id
                        }
                    }
                    
                elif tool_name == "use_asset_service":
                    # Asset service streaming
                    route_type = RouteType.MCP_AGENT  # Using MCP for now
                    self._routing_metrics[route_type] += 1
                    
                    asset_type = tool_args.get("asset_type", "image")
                    description = tool_args.get("description", "")
                    
                    logger.info(f"[{request_id}] Routing to Asset service with simulated streaming")
                    
                    from app.models.chat import ChatRequest
                    asset_message = f"Generate a {asset_type}: {description}"
                    chat_request = ChatRequest(message=asset_message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Stream asset generation response
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    model = result.get("model", "unknown")

                    # Track for saving after streaming
                    accumulated_response = content

                    # For asset generation, show progress updates
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant", "content": f"🎨 Generating {asset_type}...\n"},
                            "finish_reason": None
                        }]
                    }
                    
                    # Stream the actual response
                    # Use StreamBuffer for sentence-aware chunking (asset response)
                    buffer = StreamBuffer(preserve_json=True, chunking_mode="phrase")
                    async for chunk_text in buffer.process(content):
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.005)

                    # Flush any remaining content
                    async for chunk_text in buffer.flush():
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.005)

                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "_metadata": {
                            "route_type": "asset_service",
                            "routing_time_ms": int(llm_time),
                            "total_time_ms": int((time.time() - start_time) * 1000),
                            "asset_type": asset_type,
                            "description": description,
                            "reasoning": tool_args.get("reasoning"),
                            "request_id": request_id
                        }
                    }
                    
                elif tool_name == "use_multiagent_orchestration":
                    # Multi-agent streaming
                    route_type = RouteType.MULTIAGENT
                    self._routing_metrics[route_type] += 1
                    
                    domains = tool_args.get("domains", [])
                    logger.info(f"[{request_id}] Routing to multi-agent with simulated streaming")
                    
                    # For now, use MCP agent as fallback
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    model = result.get("model", "unknown")

                    # Track for saving after streaming
                    accumulated_response = content

                    # Show multi-agent coordination
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant", "content": f"🤝 Coordinating {', '.join(domains)} agents...\n\n"},
                            "finish_reason": None
                        }]
                    }
                    
                    # Stream response
                    # Use StreamBuffer for sentence-aware chunking (multi-agent response)
                    buffer = StreamBuffer(preserve_json=True, chunking_mode="phrase")
                    async for chunk_text in buffer.process(content):
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.008)  # Slightly slower for multi-agent

                    # Flush any remaining content
                    async for chunk_text in buffer.flush():
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.008)

                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "_metadata": {
                            "route_type": route_type.value,
                            "routing_time_ms": int(llm_time),
                            "total_time_ms": int((time.time() - start_time) * 1000),
                            "domains": domains,
                            "reasoning": tool_args.get("reasoning"),
                            "request_id": request_id,
                            "fallback": "mcp_agent"
                        }
                    }
                    
                else:
                    # Unknown tool - fallback
                    logger.warning(f"[{request_id}] Unknown tool {tool_name}, using MCP fallback")
                    route_type = RouteType.MCP_AGENT
                    self._routing_metrics[route_type] += 1
                    
                    # Fallback to MCP agent for unknown tools
                    from app.models.chat import ChatRequest
                    chat_request = ChatRequest(message=message)
                    
                    result = await self.mcp_hot_service.process_chat(
                        request=chat_request,
                        auth_principal=auth
                    )
                    
                    # Stream the fallback response
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    model = result.get("model", "unknown")

                    # Track for saving after streaming
                    accumulated_response = content

                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }]
                    }
                    
                    # Use StreamBuffer for phrase-aware chunking
                    buffer = StreamBuffer(preserve_json=True, chunking_mode="phrase")
                    async for chunk_text in buffer.process(content):
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.01)

                    # Flush any remaining content
                    async for chunk_text in buffer.flush():
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk_text},
                                "finish_reason": None
                            }]
                        }
                        await asyncio.sleep(0.01)

                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "_metadata": {
                            "route_type": route_type.value,
                            "routing_time_ms": int(llm_time),
                            "total_time_ms": int((time.time() - start_time) * 1000),
                            "request_id": request_id,
                            "error": f"Unknown tool: {tool_name}, used fallback"
                        }
                    }
                    
            else:
                # Direct response - stream the LLM response
                route_type = RouteType.DIRECT
                self._routing_metrics[route_type] += 1

                print(f"[TTFC DEBUG] Taking DIRECT streaming path")
                logger.info(f"[{request_id}] Direct streaming response")

                # Stream the response from LLM
                model = routing_response.get("model", "claude-haiku-4-5")
                content = routing_response.get("response", "")

                print(f"[TTFC DEBUG] Got content from routing_response, length: {len(content)}")
                print(f"[TTFC DEBUG] Content preview: {content[:100] if content else 'EMPTY'}")

                # Track for saving after streaming
                accumulated_response = content

                # For direct responses, we already have the full content
                # Stream it in chunks for better UX
                chunk_size = 20  # Characters per chunk

                # Use StreamBuffer for sentence-aware chunking (error case)
                buffer = StreamBuffer(preserve_json=True, chunking_mode="phrase")
                print(f"[TTFC DEBUG] Starting buffer.process() loop...")
                async for chunk_text in buffer.process(content):
                    print(f"[TTFC DEBUG] Got chunk from buffer, length: {len(chunk_text)}")
                    # Track first content chunk timing
                    if first_content_time is None:
                        first_content_time = time.time()
                        time_to_first_chunk_ms = int((first_content_time - start_time) * 1000)
                        logger.info(f"[{request_id}] Time to first content chunk: {time_to_first_chunk_ms}ms (direct)")

                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk_text},
                            "finish_reason": None
                        }]
                    }
                    # Small delay to simulate streaming
                    await asyncio.sleep(0.01)
                async for chunk_text in buffer.flush():
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk_text},
                            "finish_reason": None
                        }]
                    }
                    await asyncio.sleep(0.01)
                
                # Final chunk - send metadata then done (v0.3 format)
                if time_to_first_chunk_ms is not None:
                    yield {
                        "type": "metadata",
                        "time_to_first_chunk_ms": time_to_first_chunk_ms,
                        "routing_time_ms": 0,
                        "llm_time_ms": int(llm_time),
                        "total_time_ms": int((time.time() - start_time) * 1000)
                    }

                yield {"type": "done", "finish_reason": "stop"}
                
                # Update metrics
                self._update_timing_metrics(0, (time.time() - start_time) * 1000)
                
        except Exception as e:
            logger.error(f"[{request_id}] Streaming error: {e}", exc_info=True)

            # Track error for saving
            accumulated_response = f"Error: {str(e)}"

            # Error chunk
            yield {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "error",
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "error"
                }],
                "error": {
                    "message": str(e),
                    "type": "streaming_error"
                }
            }
        finally:
            # Save conversation messages after streaming completes (success or error)
            if accumulated_response:
                try:
                    await self._save_conversation_messages(
                        conversation_id=conversation_id,
                        message=message,
                        response=accumulated_response
                    )
                    logger.info(f"[{request_id}] Saved streaming conversation {conversation_id}")
                except Exception as save_error:
                    logger.error(f"[{request_id}] Failed to save streaming conversation: {save_error}")
                    # Don't re-raise - stream already sent to client
    
    async def get_routing_prompt(self, context: dict) -> str:
        """
        System prompt that helps LLM make routing decisions with persona.
        """
        # Get persona prompt first
        user_id = context.get('user_id', 'unknown')
        try:
            from app.shared.prompt_manager import PromptManager
            persona_prompt = await PromptManager.get_system_prompt(user_id=user_id)
            logger.info(f"[PERSONA DEBUG] Loaded persona for user {user_id}: {persona_prompt[:100]}...")
        except Exception as e:
            logger.error(f"[PERSONA DEBUG] Failed to load persona for user {user_id}: {e}")
            persona_prompt = "You are a helpful AI assistant."
        
        # Build the tools/routing section
        tools_section = f"""You can either respond directly or use specialized tools when needed.

Current context:
- User: {context.get('user_id', 'unknown')}
- Conversation: {context.get('conversation_id', 'new')}
- Message count: {context.get('message_count', 0)}

IMPORTANT: Always check conversation history FIRST before using any tools.

Direct responses (NO tools needed) for:
- Questions about information mentioned in the current conversation
- Conversation memory: "What did I tell you about X?", "What is my lucky number?", "Remember when I said..."
- General knowledge: "What's the capital of France?" → "Paris"
- Math: "What is 2+2?" → "4"
- Explanations: "How does photosynthesis work?" → Direct explanation
- Opinions: "What do you think about AI?" → Direct discussion

Knowledge Base (KB) tools should ONLY be used when:
- Information is NOT available in conversation history AND
- User explicitly asks for stored/archived knowledge: "find my notes on Y", "search my documents for X"
- Work continuity: "continue where we left off", "what was I working on" → load_kos_context  
- Thread management: "show active threads", "load project context" → load_kos_context
- Cross-domain synthesis: "how does X relate to Y", "connect A with B" → synthesize_kb_information

Respond DIRECTLY (without tools) for:
- Greetings and casual conversation ("Hello", "How are you?", "Thank you")
- Simple arithmetic and math ("What is 2+2?", "Calculate 5*3")
- General knowledge questions ("What's the capital of France?", "Who invented the telephone?")
- Explanations and teaching ("Explain quantum computing", "How does photosynthesis work?")
- Opinions, advice, and discussions ("What do you think about...", "Should I...")
- Creative tasks ("Tell me a joke", "Write a poem", "Create a story")
- Questions about yourself ("What's your name?", "What can you do?")
- Hypotheticals and theoretical questions ("What if...", "Imagine...")

Use tools ONLY when the user explicitly asks for:
- File system operations: "read file X", "create file Y", "list files in directory Z", "what files are in..."
  → use_mcp_agent
- Knowledge base operations are handled directly with KB tools (search_knowledge_base, read_kb_file, etc.)
- Asset generation: "generate an image of...", "create a 3D model of...", "make audio of..."
  → use_asset_service
- Web searches: "search the web for...", "find online information about...", "what's the latest news on..."
  → use_mcp_agent
- System commands: "run command X", "execute script Y", "what's the current time/date"
  → use_mcp_agent
- Complex analysis requiring multiple perspectives: "analyze this from technical, business, and legal angles"
  → use_multiagent_orchestration

Key principles:
1. If you can answer the question with your knowledge, respond directly
2. Only use tools when the user explicitly asks for an external action
3. "What is X?" or "Explain Y" are knowledge questions - answer directly
4. "Find X in my files/KB" or "Search for X online" require tools
5. When uncertain, prefer direct responses - tools add latency"""
        
        # Check for directive-enhanced context and add JSON-RPC directive instructions
        if self._is_directive_enhanced_context(context):
            directive_section = """

DIRECTIVE-ENHANCED RESPONSES:
For immersive virtual world interactions, embed JSON-RPC directives within your responses.

Directive Format: {"m":"method_name","p":{"param":"value"}}

Available Methods:

PAUSE:
- pause: {"m":"pause","p":{"secs":2.0}} - Pause for 2 seconds
- pause: {"m":"pause","p":{"secs":0.5}} - Brief pause for half a second
- pause: {"m":"pause","p":{"secs":5.0}} - Longer pause for 5 seconds

Examples:
- "Let me think for a moment... {"m":"pause","p":{"secs":2.0}} I have an idea!"
- "Take a deep breath... {"m":"pause","p":{"secs":3.0}} ...and exhale slowly."
- "Wait for it... {"m":"pause","p":{"secs":1.5}} Surprise!"

Guidelines:
- Only use the "pause" method (currently the only supported directive)
- The "secs" parameter specifies duration in seconds (can be decimal)
- Embed directives naturally within conversational flow
- Multiple pauses can be used in one response"""
            
            tools_section += directive_section
        
        # Check if persona prompt has {tools_section} placeholder
        if "{tools_section}" in persona_prompt:
            # Replace the placeholder with the tools section
            final_prompt = persona_prompt.replace("{tools_section}", tools_section)
        else:
            # No placeholder, append tools section after persona
            final_prompt = f"{persona_prompt}\n\n{tools_section}"
        
        return final_prompt
    
    def _is_directive_enhanced_context(self, context: dict) -> bool:
        """
        Check if this context should use directive-enhanced responses.

        v0.3 API always uses directives for immersive experiences.
        """
        if context.get("response_format") == "v0.3":
            return True
            
        # Legacy: Check explicit directive flag
        if context.get("directive_enhanced"):
            return True
            
        # Legacy: Check for VR priority/context 
        if context.get("priority") == "vr" or context.get("context_type") == "vr":
            return True
            
        return False
    
    def _classify_tool_call(self, tool_name: str) -> tuple[str, bool]:
        """
        Classify a tool call and determine its type.
        
        Returns:
            tuple: (tool_type, is_kb_tool) where:
                - tool_type: 'kb', 'mcp_agent', 'asset_service', 'kb_service', 'multiagent', 'unknown'
                - is_kb_tool: True if this is a KB tool, False otherwise
        """
        # Check if it's a KB tool
        kb_tool_names = {tool["function"]["name"] for tool in KB_TOOLS}
        if tool_name in kb_tool_names:
            return ('kb', True)
        
        # Check routing tools
        routing_tool_map = {
            'use_mcp_agent': 'mcp_agent',
            'use_asset_service': 'asset_service',
            'use_kb_service': 'kb_service',
            'use_multiagent_orchestration': 'multiagent'
        }
        
        if tool_name in routing_tool_map:
            return (routing_tool_map[tool_name], False)
        
        return ('unknown', False)
    
    def _parse_tool_arguments(self, tool_call: dict) -> dict:
        """Parse tool arguments from a tool call."""
        tool_args_raw = tool_call["function"].get("arguments", "{}")
        if isinstance(tool_args_raw, str):
            return json.loads(tool_args_raw)
        return tool_args_raw
    
    async def _execute_kb_tools(self, kb_calls: list, auth: dict, request_id: str) -> list:
        """Execute KB tool calls and return results."""
        kb_executor = KBToolExecutor(auth)
        tool_results = []
        
        for tool_call in kb_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = self._parse_tool_arguments(tool_call)
            
            logger.info(f"[{request_id}] Executing KB tool: {tool_name} with args: {tool_args}")
            result = await kb_executor.execute_tool(tool_name, tool_args)
            tool_results.append({
                "tool": tool_name,
                "result": result
            })
        
        return tool_results
    
    async def build_context(self, auth: dict, additional_context: Optional[dict] = None) -> dict:
        """
        Build context for routing decision, including conversation history.
        """
        user_id = auth.get("user_id") or auth.get("sub") or "unknown"
        conversation_id = additional_context.get("conversation_id") if additional_context else None
        
        context = {
            "user_id": user_id,
            "conversation_id": conversation_id or "new",
            "message_count": 0,
            "timestamp": int(time.time()),
            "conversation_history": []
        }
        
        # Load actual conversation history if conversation_id exists
        if conversation_id:
            try:
                from .conversation_store import chat_conversation_store
                
                # First check if the conversation exists
                # Use consistent user_id extraction
                user_id = auth.get("user_id") or auth.get("sub") or "unknown"
                conversation = chat_conversation_store.get_conversation(user_id, conversation_id)
                
                if conversation is None:
                    # Conversation doesn't exist - don't use this invalid ID
                    logger.info(f"Conversation {conversation_id} not found, will create new conversation")
                    context["conversation_id"] = None  # Don't preserve invalid IDs
                else:
                    # Load messages for the existing conversation
                    messages = chat_conversation_store.get_messages(conversation_id)
                    
                    # Convert to conversation history format
                    conversation_history = []
                    for msg in messages:
                        conversation_history.append({
                            "role": msg["role"],
                            "content": msg["content"],
                            "timestamp": msg.get("created_at", "")
                        })
                    
                    context["conversation_history"] = conversation_history
                    context["message_count"] = len(conversation_history)
                    
                    logger.info(f"Loaded {len(conversation_history)} messages for conversation {conversation_id}")
                
            except Exception as e:
                logger.error(f"Error loading conversation history: {e}")
                # For unexpected errors, log but continue (conversation will be created if needed)
                context["conversation_id"] = None  # Don't preserve IDs on errors
        
        # Add any additional context
        if additional_context:
            context.update(additional_context)
        
        return context
    
    async def _get_or_create_conversation_id(self, message: str, context: Optional[dict], auth: dict) -> str:
        """Get existing conversation_id or create a new conversation.

        This method handles the conversation creation logic for streaming responses
        where we need the conversation_id early in the stream.

        Returns the conversation_id.
        """
        conversation_id = context.get("conversation_id") if context else None
        user_id = auth.get("user_id") or auth.get("sub") or "unknown"

        try:
            from .conversation_store import chat_conversation_store

            # Create conversation if needed
            if not conversation_id or conversation_id == "new":
                conv = chat_conversation_store.create_conversation(
                    user_id=user_id,
                    title=message[:50] + "..." if len(message) > 50 else message
                )
                conversation_id = conv["id"]
                logger.info(f"Created new conversation: {conversation_id}")
            else:
                # Check if conversation exists, create if not
                existing_conv = chat_conversation_store.get_conversation(user_id, conversation_id)
                if existing_conv is None:
                    # If conversation doesn't exist with the provided ID, create a new one
                    logger.warning(f"Conversation {conversation_id} not found, creating new conversation")
                    conv = chat_conversation_store.create_conversation(
                        user_id=user_id,
                        title=message[:50] + "..." if len(message) > 50 else message
                    )
                    conversation_id = conv["id"]  # Use the new ID
                    logger.info(f"Created new conversation: {conversation_id} (requested ID was not found)")

            return conversation_id

        except Exception as e:
            logger.error(f"Error getting/creating conversation: {e}")
            # Fallback to user-based conversation ID
            return f"{user_id}_fallback_{int(time.time())}"

    async def _save_conversation_messages(self, conversation_id: str, message: str, response: str) -> None:
        """Save user message and AI response to an existing conversation.

        This method assumes the conversation already exists and just adds the messages.
        """
        try:
            from .conversation_store import chat_conversation_store

            # Save user message first
            await asyncio.create_task(asyncio.to_thread(
                chat_conversation_store.add_message,
                conversation_id, "user", message
            ))

            # Save AI response
            await asyncio.create_task(asyncio.to_thread(
                chat_conversation_store.add_message,
                conversation_id, "assistant", response
            ))

            logger.info(f"Saved messages to conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Error saving conversation messages: {e}")
            # Don't fail the whole request if conversation saving fails

    async def _save_conversation(self, message: str, response: str, context: Optional[dict], auth: dict) -> str:
        """Save user message and AI response to conversation history.

        Returns the conversation_id (creates one if needed).

        NOTE: This method is kept for backwards compatibility and streaming use.
        Non-streaming should use _save_conversation_messages() after pre-creating conversation_id.
        """
        try:
            from .conversation_store import chat_conversation_store

            # Get or create conversation_id using the shared method
            conversation_id = await self._get_or_create_conversation_id(message, context, auth)

            # Save messages using the new method
            await self._save_conversation_messages(conversation_id, message, response)

            logger.info(f"Saved conversation for {conversation_id}")
            return conversation_id

        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            # Don't fail the whole request if conversation saving fails
            return conversation_id or ""
    
    def _update_timing_metrics(self, routing_time_ms: float, total_time_ms: float):
        """Update rolling average timing metrics"""
        total = self._routing_metrics["total_requests"]
        
        # Update routing time average
        avg_routing = self._routing_metrics["avg_routing_time_ms"]
        self._routing_metrics["avg_routing_time_ms"] = (
            (avg_routing * (total - 1) + routing_time_ms) / total
        )
        
        # Update total time average
        avg_total = self._routing_metrics["avg_total_time_ms"]
        self._routing_metrics["avg_total_time_ms"] = (
            (avg_total * (total - 1) + total_time_ms) / total
        )
    
    def get_metrics(self) -> dict:
        """Get routing metrics for monitoring"""
        total = self._routing_metrics["total_requests"]
        if total == 0:
            return self._routing_metrics
            
        return {
            **self._routing_metrics,
            "distribution": {
                RouteType.DIRECT: f"{(self._routing_metrics[RouteType.DIRECT] / total * 100):.1f}%",
                RouteType.MCP_AGENT: f"{(self._routing_metrics[RouteType.MCP_AGENT] / total * 100):.1f}%",
                RouteType.MULTIAGENT: f"{(self._routing_metrics[RouteType.MULTIAGENT] / total * 100):.1f}%"
            }
        }


# Global instance
unified_chat_handler = UnifiedChatHandler()
