from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import logging
import time
from typing import List, Optional, Dict, Any, AsyncGenerator
import json

from app.shared.security import get_current_auth_legacy as get_current_auth
from fastapi import Request

# Helper to extract auth from request body (passed by gateway)
async def get_auth_from_request(request: Request) -> Dict[str, Any]:
    """Extract auth from request body when passed by gateway"""
    try:
        body = await request.json()
        return body.get("_auth", {})
    except:
        return {}
from app.models.chat import ChatRequest, ChatResponse, Message
from app.shared.tool_provider import ToolProvider
from app.shared.prompt_manager import PromptManager
from app.services.llm.chat_service import chat_service
from app.services.llm import LLMProvider, ModelCapability
from app.services.llm.multi_provider_selector import ContextType, ModelPriority
from app.shared.instrumentation import instrument_request, record_stage, instrumentation
from app.services.streaming_formatter import create_openai_compatible_stream

async def async_generator_from_dict(data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """Convert a single dictionary to an async generator"""
    yield data

router = APIRouter()
logger = logging.getLogger(__name__)

# Store chat history per session
# In a production environment, this should be in a proper database
chat_histories: dict[str, List[Message]] = {}

# Legacy function removed - now using multi-provider chat service

@router.post("/", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
) -> ChatResponse:
    """
    Process a chat completion request using the specified provider.
    Supports both built-in and MCP tools.
    """
    try:
        # Use a unique key for chat history based on auth_principal
        # Handle both JWT (user_id) and API key (key) authentication
        auth_key = auth_principal.get("sub") or auth_principal.get("user_id") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Could not determine unique auth key for chat history.")

        logger.debug("Processing chat completion request")
        
        # Get or initialize chat history with system prompt
        if auth_key not in chat_histories:
            logger.debug("Initializing new chat history with system prompt")
            system_prompt = await PromptManager.get_system_prompt(user_id=auth_key)
            chat_histories[auth_key] = [
                Message(
                    role="system",
                    content=system_prompt
                )
            ]

        # Add user message to history
        chat_histories[auth_key].append(Message(
            role="user",
            content=request.message
        ))
        logger.debug(f"Added user message to history. Total messages: {len(chat_histories[auth_key])}")

        # Prepare messages for API call (filter out empty messages)
        valid_messages = []
        for msg in chat_histories[auth_key]:
            if msg.content and msg.content.strip():
                valid_messages.append(msg.model_dump())
            else:
                logger.debug(f"Filtering out empty message with role: {msg.role}")
        messages = valid_messages

        # Get available tools for the chat
        logger.debug("Getting tools for chat completion")
        tools = await ToolProvider.get_tools_for_activity("generic")
        logger.debug(f"Retrieved {len(tools)} tools for generic activity")

        # Use the multi-provider chat service for consistent model selection
        logger.debug("Using multi-provider chat service for legacy chat endpoint")
        
        # Convert tools to proper format
        formatted_tools = []
        for tool in tools:
            tool_dict = tool.model_dump() if hasattr(tool, 'model_dump') else tool
            formatted_tools.append(tool_dict)

        # Use multi-provider chat service with force_provider=True for consistent behavior
        response = await chat_service.chat_completion(
            messages=messages,
            force_provider=True,  # Use default model selection
            tools=formatted_tools,
            user_id=auth_key
        )
        
        result_to_say = response["response"]
        model_used = response["model"]
        provider_used = response["provider"]
        
        logger.info(f"Successfully used multi-provider system: {model_used} from {provider_used}")

        if result_to_say:
            # Add response to history
            chat_histories[auth_key].append(Message(
                role="assistant",
                content=result_to_say
            ))
            logger.debug("Added assistant response to history")

            # Trim history if it gets too long
            if len(chat_histories[auth_key]) > 50:  # Arbitrary limit
                logger.debug("Trimming chat history to last 50 messages")
                # Keep system prompt and last 49 messages
                system_msg = chat_histories[auth_key][0]
                chat_histories[auth_key] = [system_msg] + chat_histories[auth_key][-49:]

            return ChatResponse(
                response=result_to_say,
                provider=provider_used,
                model=model_used
            )
        else:
            raise ValueError("No response received from provider")

    except Exception as e:
        logger.error(f"Chat completion error: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/unified")
async def unified_chat_endpoint(
    request: Request,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Unified intelligent chat endpoint with streaming support.
    
    The LLM decides whether to respond directly or use specialized tools.
    - Direct responses for simple queries (~1s)
    - MCP agent for tool-requiring tasks (~2-3s)
    - Multi-agent for complex analysis (~4-8s)
    
    Set stream=true for Server-Sent Events (SSE) streaming response.
    """
    try:
        # Parse request body (can handle both gateway format with _auth and direct format)
        body = await request.json()
        
        # Handle both gateway format (_auth in body) and direct format
        if "_auth" in body:
            # Gateway format - override auth_principal with what's in body
            message = body.get("message", "")
            auth_principal = body.get("_auth", {})
            stream = body.get("stream", False)
        else:
            # Direct format - use auth_principal from dependency injection
            message = body.get("message", "")
            stream = body.get("stream", False)
            # auth_principal already populated from Depends(get_current_auth)
        
        from .unified_chat import unified_chat_handler
        
        # Check for response format preference (can be in body or headers)
        response_format = body.get("response_format", request.headers.get("X-Response-Format", "openai")).lower()
        if response_format not in ["openai", "v0.3"]:
            response_format = "openai"  # Default to OpenAI format
        
        # Validate conversation_id if provided
        conversation_id = body.get("conversation_id")
        if conversation_id:
            # Check if the conversation actually exists
            try:
                from .conversation_store import chat_conversation_store
                user_id = auth_principal.get("sub") or auth_principal.get("user_id") or auth_principal.get("key", "unknown")
                conversation = chat_conversation_store.get_conversation(user_id, conversation_id)
                
                if conversation is None:
                    # Conversation doesn't exist - return 404
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Conversation {conversation_id} not found"
                    )
            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                logger.error(f"Error validating conversation {conversation_id}: {e}")
                # For unexpected errors, continue (will be handled in build_context)
        
        # Extract context if available
        context = {
            "conversation_id": conversation_id,
            "message_count": len(chat_histories.get(
                auth_principal.get("sub") or auth_principal.get("user_id") or auth_principal.get("key", ""), []
            )),
            "stream": stream,  # Pass streaming preference to handler
            "response_format": response_format  # Pass format preference
        }
        
        # Handle streaming response
        if stream:
            async def stream_generator():
                """Generate SSE stream from unified chat handler"""
                try:
                    # Process through unified handler with streaming
                    async for chunk in unified_chat_handler.process_stream(
                        message=message,
                        auth=auth_principal,
                        context=context
                    ):
                        # Format as SSE
                        yield f"data: {json.dumps(chunk)}\n\n"
                    
                    # Send final done signal
                    yield "data: [DONE]\n\n"
                    
                except Exception as e:
                    logger.error(f"Streaming error: {e}", exc_info=True)
                    error_chunk = {
                        "error": {
                            "message": str(e),
                            "type": "streaming_error"
                        }
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "Access-Control-Allow-Origin": "*"
                }
            )
        
        # Non-streaming response (existing behavior)
        else:
            # Process through unified handler
            result = await unified_chat_handler.process(
                message=message,
                auth=auth_principal,
                context=context
            )
            
            # Convert to requested format if needed
            if response_format == "v0.3":
                # Convert from OpenAI format to v0.3 format
                v03_response = {
                    "response": "",
                    "message": message,
                    "conversation_id": None
                }
                
                # Extract content from OpenAI format
                if "choices" in result and result["choices"]:
                    v03_response["response"] = result["choices"][0]["message"]["content"]
                
                # Preserve metadata if present
                if "_metadata" in result:
                    v03_response["_metadata"] = result["_metadata"]
                    # Extract conversation_id to top level
                    if "conversation_id" in result["_metadata"]:
                        v03_response["conversation_id"] = result["_metadata"]["conversation_id"]
                
                return v03_response
            
            # Default: return OpenAI format as-is
            return result
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 404) without modification
        logger.error(f"Unified chat HTTP error: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unified chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_unified_chat_metrics(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
) -> Dict[str, Any]:
    """
    Get metrics for the unified chat endpoint routing decisions.
    
    Returns routing distribution and performance metrics.
    """
    try:
        from .unified_chat import unified_chat_handler
        return unified_chat_handler.get_metrics()
    except Exception as e:
        logger.error(f"Error getting unified chat metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_chat_status(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
) -> Dict[str, Any]:
    """
    Get the current status of the chat history.
    
    Returns:
        Dict containing:
            message_count (int): Number of messages in history (excluding system prompt)
            has_history (bool): Whether any user/assistant messages exist
    """
    try:
        # Use a unique key for chat history based on auth_principal
        # Handle both JWT (user_id) and API key (key) authentication
        auth_key = auth_principal.get("sub") or auth_principal.get("user_id") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Could not determine unique auth key for chat history.")

        logger.debug("Getting chat status")
        if auth_key not in chat_histories:
            return {
                "message_count": 0,
                "has_history": False
            }
        
        # Get total message count excluding system prompt
        history = chat_histories[auth_key]
        message_count = sum(1 for msg in history if msg.role != "system")
        
        return {
            "message_count": message_count,
            "has_history": message_count > 0
        }
    except Exception as e:
        logger.error(f"Error getting chat status: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/multi-provider")
async def multi_provider_chat_completion(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Process a chat completion request using the multi-provider system.
    Supports intelligent provider selection and automatic fallback.
    
    Compatible with OpenAI and Anthropic streaming format:
    - Set stream=true for Server-Sent Events (SSE) streaming
    - Set stream=false or omit for regular JSON response
    """
    with instrument_request(metadata={"endpoint": "multi-provider", "auth_type": auth_principal.get('type', 'unknown'), "stream": request.stream}) as request_id:
        try:
            # Use a unique key for chat history based on auth_principal
            auth_key = auth_principal.get("sub") or auth_principal.get("user_id") or auth_principal.get("key")
            if not auth_key:
                raise ValueError("Could not determine unique auth key for chat history.")

            logger.info(f"Processing multi-provider chat request (stream={request.stream}) from {auth_principal.get('type', 'unknown')}")
            record_stage(request_id, "request_validation", metadata={"user_id": auth_key, "stream": request.stream})
            
            # Get or initialize chat history with system prompt
            if auth_key not in chat_histories:
                logger.debug("Initializing new chat history with system prompt")
                system_prompt = await PromptManager.get_system_prompt(user_id=auth_key)
                chat_histories[auth_key] = [
                    Message(
                        role="system",
                        content=system_prompt
                    )
                ]
            record_stage(request_id, "chat_history_initialized")

            # Add user message to history
            chat_histories[auth_key].append(Message(
                role="user",
                content=request.message
            ))
            logger.debug(f"Added user message to history. Total messages: {len(chat_histories[auth_key])}")

            # Prepare messages for API call (filter out empty messages)
            valid_messages = []
            for msg in chat_histories[auth_key]:
                if msg.content and msg.content.strip():
                    valid_messages.append(msg.model_dump())
                else:
                    logger.debug(f"Filtering out empty message with role: {msg.role}")
            messages = valid_messages
            record_stage(request_id, "messages_prepared", metadata={"message_count": len(messages)})

            # Get available tools for the chat
            logger.debug("Getting tools for chat completion")
            tools = await ToolProvider.get_tools_for_activity(request.activity or "generic")
            logger.debug(f"Retrieved {len(tools)} tools for {request.activity} activity")
            record_stage(request_id, "tools_retrieved", metadata={"tool_count": len(tools), "activity": request.activity})

            # Convert tools to proper format
            formatted_tools = []
            for tool in tools:
                tool_dict = tool.model_dump() if hasattr(tool, 'model_dump') else tool
                formatted_tools.append(tool_dict)

            # Convert enums for multi-provider system
            llm_provider = None
            if request.provider:
                try:
                    llm_provider = LLMProvider(request.provider)
                except ValueError:
                    logger.warning(f"Invalid provider: {request.provider}, using auto-selection")

            llm_priority = None
            if request.priority:
                try:
                    llm_priority = ModelPriority(request.priority)
                except ValueError:
                    logger.warning(f"Invalid priority: {request.priority}, using default")

            llm_context_type = None
            if request.context_type:
                try:
                    llm_context_type = ContextType(request.context_type)
                except ValueError:
                    logger.warning(f"Invalid context_type: {request.context_type}, auto-detecting")

            # Convert capability strings to enums
            llm_capabilities = []
            if request.required_capabilities:
                for cap in request.required_capabilities:
                    try:
                        llm_capabilities.append(ModelCapability(cap))
                    except ValueError:
                        logger.warning(f"Invalid capability: {cap}, skipping")

            record_stage(request_id, "request_parameters_prepared", metadata={
                "provider": request.provider,
                "model": request.model,
                "priority": request.priority,
                "context_type": request.context_type,
                "force_provider": request.force_provider,
                "enable_fallback": request.enable_fallback,
                "stream": request.stream
            })

            # Handle streaming response
            if request.stream:
                record_stage(request_id, "streaming_mode_enabled")
                
                async def stream_generator() -> AsyncGenerator[str, None]:
                    """Generate streaming response in OpenAI-compatible format"""
                    try:
                        response_content = ""
                        model_used = None
                        provider_used = None
                        
                        # Get streaming response from multi-provider service
                        async for chunk_data in chat_service.chat_completion_stream(
                            messages=messages,
                            model=request.model,
                            provider=llm_provider,
                            priority=llm_priority,
                            context_type=llm_context_type,
                            max_response_time_ms=request.max_response_time_ms,
                            required_capabilities=llm_capabilities,
                            user_id=auth_key,
                            enable_fallback=request.enable_fallback,
                            force_provider=request.force_provider,
                            tools=formatted_tools
                        ):
                            # Track model and provider from first chunk
                            if chunk_data.get("model") and not model_used:
                                model_used = chunk_data.get("model")
                            if chunk_data.get("provider") and not provider_used:
                                provider_used = chunk_data.get("provider")
                            
                            # Accumulate content for history
                            if chunk_data.get("type") == "content":
                                response_content += chunk_data.get("content", "")
                            
                            # Convert to OpenAI-compatible format
                            async for formatted_chunk in create_openai_compatible_stream(
                                async_generator_from_dict(chunk_data),
                                model_used or request.model or "unknown"
                            ):
                                yield formatted_chunk
                        
                        # Add response to history
                        if response_content.strip():
                            chat_histories[auth_key].append(Message(
                                role="assistant",
                                content=response_content
                            ))
                            record_stage(request_id, "streaming_response_saved_to_history", metadata={"response_length": len(response_content)})
                        
                        record_stage(request_id, "streaming_completed")
                        
                    except Exception as e:
                        record_stage(request_id, "streaming_error", metadata={"error": str(e)})
                        logger.error(f"Streaming error: {str(e)}")
                        # Send error in OpenAI format
                        error_chunk = {
                            "id": f"chatcmpl-error-{int(time.time())}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": request.model or "unknown",
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "error"
                                }
                            ],
                            "error": {
                                "message": str(e),
                                "type": "internal_error"
                            }
                        }
                        yield f"data: {json.dumps(error_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                
                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Cache-Control"
                    }
                )
            
            # Handle non-streaming response (original behavior)
            else:
                record_stage(request_id, "non_streaming_mode")
                
                response = await chat_service.chat_completion(
                    messages=messages,
                    model=request.model,
                    provider=llm_provider,
                    priority=llm_priority,
                    context_type=llm_context_type,
                    max_response_time_ms=request.max_response_time_ms,
                    required_capabilities=llm_capabilities,
                    user_id=auth_key,
                    enable_fallback=request.enable_fallback,
                    force_provider=request.force_provider,
                    tools=formatted_tools
                )
                
                record_stage(request_id, "llm_response_received", metadata={
                    "provider": response.get("provider"),
                    "model": response.get("model"),
                    "response_time_ms": response.get("response_time_ms"),
                    "usage": response.get("usage"),
                    "fallback_used": response.get("fallback_used", False)
                })

                # Add assistant response to history (only if not empty)
                assistant_content = response["response"]
                if assistant_content and assistant_content.strip():
                    chat_histories[auth_key].append(Message(
                        role="assistant",
                        content=assistant_content
                    ))
                    record_stage(request_id, "response_added_to_history", metadata={"response_length": len(assistant_content)})
                else:
                    logger.warning(f"Received empty response from provider {response['provider']}, not adding to history")

                chat_response = ChatResponse(
                    response=response["response"],
                    provider=response["provider"],
                    model=response["model"],
                    usage=response.get("usage"),
                    response_time_ms=response.get("response_time_ms"),
                    reasoning=response.get("reasoning"),
                    fallback_used=response.get("fallback_used", False)
                )
                
                record_stage(request_id, "response_serialized")
                return chat_response

        except Exception as e:
            record_stage(request_id, "error_occurred", metadata={"error": str(e)})
            logger.error(f"Multi-provider chat completion error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")


@router.post("/", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
) -> ChatResponse:
    """
    Process a chat completion request using the specified provider.
    Supports both built-in and MCP tools.
    """
    try:
        # Use a unique key for chat history based on auth_principal
        # Handle both JWT (user_id) and API key (key) authentication
        auth_key = auth_principal.get("sub") or auth_principal.get("user_id") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Could not determine unique auth key for chat history.")

        logger.debug("Processing chat completion request")
        
        # Get or initialize chat history with system prompt
        if auth_key not in chat_histories:
            logger.debug("Initializing new chat history with system prompt")
            system_prompt = await PromptManager.get_system_prompt(user_id=auth_key)
            chat_histories[auth_key] = [
                Message(
                    role="system",
                    content=system_prompt
                )
            ]

        # Add user message to history
        chat_histories[auth_key].append(Message(
            role="user",
            content=request.message
        ))
        logger.debug(f"Added user message to history. Total messages: {len(chat_histories[auth_key])}")

        # Prepare messages for API call (filter out empty messages)
        valid_messages = []
        for msg in chat_histories[auth_key]:
            if msg.content and msg.content.strip():
                valid_messages.append(msg.model_dump())
            else:
                logger.debug(f"Filtering out empty message with role: {msg.role}")
        messages = valid_messages

        # Get available tools for the chat
        logger.debug("Getting tools for chat completion")
        tools = await ToolProvider.get_tools_for_activity("generic")
        logger.debug(f"Retrieved {len(tools)} tools for generic activity")

        # Use the multi-provider chat service for consistent model selection
        logger.debug("Using multi-provider chat service for legacy chat endpoint")
        
        # Convert tools to proper format
        formatted_tools = []
        for tool in tools:
            tool_dict = tool.model_dump() if hasattr(tool, 'model_dump') else tool
            formatted_tools.append(tool_dict)

        # Use multi-provider chat service with force_provider=True for consistent behavior
        response = await chat_service.chat_completion(
            messages=messages,
            force_provider=True,  # Use default model selection
            tools=formatted_tools,
            user_id=auth_key
        )
        
        result_to_say = response["response"]
        model_used = response["model"]
        provider_used = response["provider"]
        
        logger.info(f"Successfully used multi-provider system: {model_used} from {provider_used}")

        if result_to_say:
            # Add response to history
            chat_histories[auth_key].append(Message(
                role="assistant",
                content=result_to_say
            ))
            logger.debug("Added assistant response to history")

            # Trim history if it gets too long
            if len(chat_histories[auth_key]) > 50:  # Arbitrary limit
                logger.debug("Trimming chat history to last 50 messages")
                # Keep system prompt and last 49 messages
                system_msg = chat_histories[auth_key][0]
                chat_histories[auth_key] = [system_msg] + chat_histories[auth_key][-49:]

            return ChatResponse(
                response=result_to_say,
                provider=provider_used,
                model=model_used
            )
        else:
            raise ValueError("No response received from provider")

    except Exception as e:
        logger.error(f"Chat completion error: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Return appropriate status codes based on error type
        if isinstance(e, ValueError):
            status_code = 401  # Unauthorized
        elif isinstance(e, ConnectionError):
            status_code = 503  # Service Unavailable
        else:
            status_code = 500  # Internal Server Error
            
        raise HTTPException(
            status_code=status_code,
            detail=str(e)
        )

@router.post("/reload-prompt")
async def reload_system_prompt(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Reload the system prompt from disk and update all active chat histories"""
    try:
        # Use a unique key for chat history based on auth_principal
        # Handle both JWT (user_id) and API key (key) authentication
        auth_key = auth_principal.get("sub") or auth_principal.get("user_id") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Could not determine unique auth key for chat history.")

        logger.debug("Reloading system prompt from disk")
        system_prompt = await PromptManager.get_system_prompt()
        
        # Update system prompt in all active chat histories
        for user_key, history in chat_histories.items():
            if history and history[0].role == "system":
                # Get persona-specific prompt for each user
                user_system_prompt = await PromptManager.get_system_prompt(user_id=user_key)
                history[0].content = user_system_prompt
                
        return {"status": "success", "message": "System prompt reloaded successfully"}
    except Exception as e:
        logger.error(f"Error reloading system prompt: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.delete("/history")
async def clear_chat_history(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Clear the chat history in both memory and Redis"""
    try:
        # Use a unique key for chat history based on auth_principal
        # Handle both JWT (user_id) and API key (key) authentication
        auth_key = auth_principal.get("sub") or auth_principal.get("user_id") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Could not determine unique auth key for chat history.")

        # Clear in-memory history
        if auth_key in chat_histories:
            logger.debug("Clearing in-memory chat history")
            system_prompt = await PromptManager.get_system_prompt(user_id=auth_key)
            chat_histories[auth_key] = [
                Message(
                    role="system",
                    content=system_prompt
                )
            ]
        
        # Clear Redis history
        try:
            from app.services.chat.redis_chat_history import redis_chat_history
            redis_chat_history.clear_history(auth_key)
            logger.debug("Cleared Redis chat history")
        except Exception as e:
            logger.warning(f"Could not clear Redis history: {e}")
        
        return {"status": "success", "cleared": ["memory", "redis"]}
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# Import MCP-agent chat service - working around import issues
try:
    # Use delayed import to avoid startup issues
    @router.post("/mcp-agent")
    async def mcp_agent_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """
        Advanced multiagent chat endpoint using mcp-agent orchestration.
        
        Provides sophisticated agent coordination:
        - Game Master + multiple NPCs for interactive scenes
        - Collaborative specialist teams for complex problems
        - Multi-perspective storytelling
        - Automatic scenario detection and routing
        
        Perfect for MMOIRL's complex interaction requirements.
        """
        try:
            # Import sophisticated multiagent orchestrator
            from .multiagent_orchestrator import multiagent_orchestrator_endpoint
            return await multiagent_orchestrator_endpoint(request, "auto", auth_principal)
        except ImportError as ie:
            logger.error(f"Import error in mcp-agent endpoint: {ie}")
            # Fall back to simple response for testing
            return {
                "id": f"mcp-agent-fallback-{int(time.time())}",
                "object": "chat.completion", 
                "created": int(time.time()),
                "model": request.model or "claude-3-5-sonnet-20241022",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant", 
                        "content": "MCP-agent endpoint is temporarily using fallback mode due to import issues."
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
            }
        except Exception as e:
            logger.error(f"Error in mcp-agent endpoint: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
    logger.info("✅ MCP-agent chat endpoint added with runtime import")
    
    # Add specific multiagent scenario endpoints
    @router.post("/gamemaster")
    async def gamemaster_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """Game Master orchestrating multiple NPCs for interactive scenes"""
        from .multiagent_orchestrator import gamemaster_scenario_endpoint
        return await gamemaster_scenario_endpoint(request, auth_principal)
    
    @router.post("/worldbuilding")
    async def worldbuilding_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """Collaborative world building with specialist agents"""
        from .multiagent_orchestrator import worldbuilding_scenario_endpoint
        return await worldbuilding_scenario_endpoint(request, auth_principal)
    
    @router.post("/storytelling")
    async def storytelling_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """Multi-perspective storytelling with different narrative viewpoints"""
        from .multiagent_orchestrator import storytelling_scenario_endpoint
        return await storytelling_scenario_endpoint(request, auth_principal)
    
    @router.post("/problemsolving")
    async def problemsolving_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """Expert team collaboration for complex problem solving"""
        from .multiagent_orchestrator import problemsolving_scenario_endpoint
        return await problemsolving_scenario_endpoint(request, auth_principal)
    
    logger.info("✅ Advanced multiagent orchestration endpoints added")
    
except Exception as e:
    logger.warning(f"⚠️ Could not create mcp-agent chat endpoint: {e}")
    import traceback
    logger.warning(f"⚠️ Traceback: {traceback.format_exc()}")

# Import direct chat (no framework overhead)
try:
    from .lightweight_chat_simple import simple_lightweight_chat_endpoint
    
    @router.post("/direct")
    async def direct_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """
        Direct chat endpoint - straight to Anthropic API.
        
        Fastest option (~2s) - no framework overhead.
        """
        return await simple_lightweight_chat_endpoint(request, auth_principal)
        
    logger.info("✅ Direct chat endpoint added")
    
except Exception as e:
    logger.warning(f"⚠️ Could not import direct chat: {e}")

# Import hot-loaded MCP-agent chat (keeps mcp-agent initialized)
try:
    from .lightweight_chat_hot import hot_lightweight_chat_endpoint
    
    @router.post("/mcp-agent-hot")
    async def mcp_agent_hot_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """
        Hot-loaded MCP-agent chat - keeps framework initialized.
        
        First request: ~3-5s (initialization)
        Subsequent requests: ~0.5-1s (reuses initialized agent)
        """
        return await hot_lightweight_chat_endpoint(request, auth_principal)
        
    logger.info("✅ Hot-loaded MCP-agent chat endpoint added")
    
except Exception as e:
    logger.warning(f"⚠️ Could not import hot MCP-agent chat: {e}")

# Import direct chat with database
try:
    from fastapi import Query
    from .lightweight_chat_db import (
        lightweight_chat_db_endpoint,
        get_conversations_endpoint,
        search_conversations_endpoint
    )
    logger.info("✅ Direct chat DB module imported successfully")
except Exception as e:
    logger.warning(f"⚠️ Could not import direct chat DB: {e}")

# Import ultrafast chat
try:
    from .ultrafast_chat import ultrafast_chat_endpoint
    
    @router.post("/ultrafast")
    async def ultrafast_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """
        Ultra-fast chat endpoint optimized for <1s responses.
        
        Uses Claude 3 Haiku and minimal overhead.
        """
        return await ultrafast_chat_endpoint(request, auth_principal)
        
    logger.info("✅ Ultrafast chat endpoint added")
    
except Exception as e:
    logger.warning(f"⚠️ Could not import ultrafast chat: {e}")

# Import ultrafast Redis chat
try:
    from .ultrafast_redis_chat import ultrafast_redis_chat_endpoint
    
    @router.post("/ultrafast-redis")
    async def ultrafast_redis_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """
        Ultra-fast chat with Redis-backed history.
        
        Target: <1s response time with full conversation context.
        """
        return await ultrafast_redis_chat_endpoint(request, auth_principal)
        
    logger.info("✅ Ultrafast Redis chat endpoint added")
    
except Exception as e:
    logger.warning(f"⚠️ Could not import ultrafast Redis chat: {e}")

# Import optimized ultrafast Redis chat
try:
    from .ultrafast_redis_optimized import ultrafast_redis_optimized_endpoint
    
    @router.post("/ultrafast-redis-v2")
    async def ultrafast_redis_v2_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """
        Optimized ultra-fast chat with Redis history.
        
        - Minimal context (3 messages)
        - Lower token limit (500)
        - Target: <500ms consistent
        """
        return await ultrafast_redis_optimized_endpoint(request, auth_principal)
        
    logger.info("✅ Ultrafast Redis V2 chat endpoint added")
    
except Exception as e:
    logger.warning(f"⚠️ Could not import ultrafast Redis V2 chat: {e}")

# Import parallel ultrafast Redis chat
try:
    from .ultrafast_redis_parallel import ultrafast_redis_parallel_endpoint
    
    @router.post("/ultrafast-redis-v3")
    async def ultrafast_redis_v3_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth),
        background_tasks: BackgroundTasks = BackgroundTasks()
    ):
        """
        Ultra-fast chat with parallel Redis operations.
        
        - Redis pipelining for batch operations
        - Background storage of responses
        - Target: <400ms consistent
        """
        return await ultrafast_redis_parallel_endpoint(request, auth_principal, background_tasks)
        
    logger.info("✅ Ultrafast Redis V3 (parallel) chat endpoint added")
    
except Exception as e:
    logger.warning(f"⚠️ Could not import ultrafast Redis V3 chat: {e}")

# Import orchestrated chat service
try:
    from .orchestrated_chat import OrchestratedChatService
    orchestrated_chat_service = OrchestratedChatService()
    logger.info("✅ Orchestrated chat service initialized")
    
    @router.post("/direct-db")
    async def direct_chat_with_db(
        request: ChatRequest,
        conversation_id: Optional[str] = Query(None),
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """
        Direct chat with database memory.
        
        Features:
        - Direct Anthropic API calls (~2s)
        - Full conversation history in PostgreSQL
        - Compatible with existing Gaia database schema
        """
        return await lightweight_chat_db_endpoint(request, conversation_id, auth_principal)
    
    @router.get("/conversations")
    async def get_conversations(auth_principal: Dict[str, Any] = Depends(get_current_auth)):
        """Get all conversations for the authenticated user"""
        return await get_conversations_endpoint(auth_principal)
    
    @router.get("/conversations/search")
    async def search_conversations(
        q: str = Query(..., description="Search query"),
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """Search conversations"""
        return await search_conversations_endpoint(q, auth_principal)
    
    logger.info("✅ Direct chat with DB endpoints added")
    
except Exception as e:
    logger.warning(f"⚠️ Could not import orchestrated chat: {e}")
    import traceback
    logger.warning(f"⚠️ Orchestrated Traceback: {traceback.format_exc()}")
    orchestrated_chat_service = None

# KB-enhanced multiagent orchestrator moved to separate KB service
# KB endpoints are now handled by kb-service and routed through the gateway

# Import intelligent chat with smart routing
try:
    from .intelligent_chat import intelligent_chat_endpoint, intelligent_chat_metrics_endpoint
    
    @router.post("/intelligent")
    async def intelligent_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """
        Intelligent chat with automatic routing based on message complexity.
        
        Features:
        - Pattern matching for ultra-fast simple messages (<1ms classification)
        - LLM classification for complex routing (~200ms)
        - Routes to optimal endpoint:
          - Simple dialog → Direct LLM (~1s)
          - Tool usage needed → Hot MCP agent (~2-3s)
          - Complex orchestration → Full multiagent (~3-5s)
        """
        return await intelligent_chat_endpoint(request, auth_principal)
    
    @router.post("/fast")
    async def fast_direct_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """
        Fast direct chat - bypasses ALL routing for guaranteed speed.
        
        Use this when you need the fastest possible response (~1s) and
        know the message doesn't need tools or orchestration.
        
        Same as the original /chat/direct endpoint.
        """
        # Direct to simple endpoint, no routing overhead at all
        from .lightweight_chat_simple import simple_lightweight_chat_endpoint
        return await simple_lightweight_chat_endpoint(request, auth_principal)
    
    @router.get("/intelligent/metrics")
    async def intelligent_metrics(auth_principal: Dict[str, Any] = Depends(get_current_auth)):
        """Get metrics for intelligent chat routing"""
        return await intelligent_chat_metrics_endpoint(auth_principal)
    
    logger.info("✅ Intelligent chat endpoints added")
    
except Exception as e:
    logger.warning(f"⚠️ Could not import intelligent chat: {e}")

# Add orchestrated chat endpoints if service is available
if orchestrated_chat_service:
    @router.post("/orchestrated")
    async def orchestrated_chat(
        request: ChatRequest,
        auth_principal: Dict[str, Any] = Depends(get_current_auth)
    ):
        """
        Orchestrated chat with intelligent routing and multi-agent support.
        
        Features:
        - Automatic routing (direct LLM, MCP tools, multi-agent)
        - Dynamic agent spawning for complex tasks
        - Efficient parallel execution
        - Performance metrics tracking
        """
        return await orchestrated_chat_service.process_chat(
            request=request.model_dump(),
            auth_principal=auth_principal
        )
    
    @router.get("/orchestrated/metrics")
    async def orchestrated_metrics(auth_principal: Dict[str, Any] = Depends(get_current_auth)):
        """Get orchestration performance metrics"""
        return await orchestrated_chat_service.get_metrics()
    
    logger.info("✅ Orchestrated chat endpoints added")
