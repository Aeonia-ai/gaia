from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import logging
import time
from typing import List, Optional, Dict, Any, AsyncGenerator
import json

from app.shared.security import get_current_auth_legacy as get_current_auth
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
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
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
            auth_key = auth_principal.get("sub") or auth_principal.get("key")
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
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
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
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
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
    """Clear the chat history and reinitialize with system prompt"""
    try:
        # Use a unique key for chat history based on auth_principal
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Could not determine unique auth key for chat history.")

        if auth_key in chat_histories:
            logger.debug("Clearing chat history and reinitializing with system prompt")
            system_prompt = await PromptManager.get_system_prompt(user_id=auth_key)
            chat_histories[auth_key] = [
                Message(
                    role="system",
                    content=system_prompt
                )
            ]
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
