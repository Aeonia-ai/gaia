"""
Streaming chat endpoint for reduced latency
Adapted from LLM Platform for Gaia Platform architecture
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import logging
import json
import asyncio
import time
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime

from app.shared.security import get_current_auth_legacy as get_current_auth
from app.models.chat import ChatRequest, Message
from app.shared.tool_provider import ToolProvider
from app.shared.prompt_manager import PromptManager
from app.services.memory_cache import (
    get_cached_persona_memory, 
    get_cached_tools_memory,
    invalidate_persona_cache,
    invalidate_tools_cache,
    get_cache_status
)
from app.services.cache_warming import cache_warming_service
from app.services.model_selector import model_selector, ContextType, ModelPriority
from app.services.llm.chat_service import chat_service
from app.services.llm import LLMProvider, ModelCapability
from app.services.llm.multi_provider_selector import ContextType as LLMContextType, ModelPriority as LLMModelPriority

router = APIRouter()
logger = logging.getLogger(__name__)

# Store chat histories per session (should be in Redis in production)
chat_histories: dict[str, List[Message]] = {}


async def stream_multi_provider_response(
    messages: List[Dict[str, Any]], 
    system_prompt: str,
    tools: Optional[List] = None,
    auth_key: str = "default",
    model: Optional[str] = None,
    provider: Optional[str] = None,
    priority: Optional[str] = None,
    context_type: Optional[str] = None,
    max_response_time_ms: Optional[int] = None,
    required_capabilities: Optional[List[str]] = None,
    enable_fallback: bool = True,
    force_provider: bool = False
) -> AsyncGenerator[str, None]:
    """Stream response from any available LLM provider"""
    try:
        # Convert string enums to proper types
        llm_provider = None
        if provider:
            try:
                llm_provider = LLMProvider(provider)
            except ValueError:
                logger.warning(f"Invalid provider: {provider}, will use auto-selection")
        
        llm_priority = None
        if priority:
            try:
                llm_priority = LLMModelPriority(priority)
            except ValueError:
                logger.warning(f"Invalid priority: {priority}, will use default")
        
        llm_context_type = None
        if context_type:
            try:
                llm_context_type = LLMContextType(context_type)
            except ValueError:
                logger.warning(f"Invalid context_type: {context_type}, will auto-detect")
        
        # Convert capability strings to enums
        llm_capabilities = []
        if required_capabilities:
            for cap in required_capabilities:
                try:
                    llm_capabilities.append(ModelCapability(cap))
                except ValueError:
                    logger.warning(f"Invalid capability: {cap}, skipping")
        
        # Use multi-provider chat service for streaming
        first_chunk = True
        async for chunk_data in chat_service.chat_completion_stream(
            messages=messages,
            model=model,
            provider=llm_provider,
            priority=llm_priority,
            context_type=llm_context_type,
            max_response_time_ms=max_response_time_ms,
            required_capabilities=llm_capabilities,
            user_id=auth_key,
            enable_fallback=enable_fallback,
            force_provider=force_provider,
            tools=tools
        ):
            # Convert chunk data to proper SSE format
            if chunk_data.get("type") == "model_selection" and first_chunk:
                logger.info(f"Selected model: {chunk_data.get('model')} from {chunk_data.get('provider')}")
                event_data = {
                    "type": "model_selection",
                    "model": chunk_data.get("model"),
                    "provider": chunk_data.get("provider"),
                    "reasoning": chunk_data.get("reasoning")
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                first_chunk = False
            
            elif chunk_data.get("type") == "content":
                event_data = {
                    "type": "content",
                    "content": chunk_data.get("content", ""),
                    "provider": chunk_data.get("provider"),
                    "model": chunk_data.get("model")
                }
                yield f"data: {json.dumps(event_data)}\n\n"
            
            elif chunk_data.get("type") == "error":
                event_data = {
                    "type": "error",
                    "error": chunk_data.get("error"),
                    "provider": chunk_data.get("provider"),
                    "fallback_available": chunk_data.get("fallback_available", False)
                }
                yield f"data: {json.dumps(event_data)}\n\n"
            
            elif chunk_data.get("type") == "fallback_attempt":
                event_data = {
                    "type": "fallback_attempt",
                    "message": chunk_data.get("message")
                }
                yield f"data: {json.dumps(event_data)}\n\n"
            
            elif chunk_data.get("type") == "metadata":
                event_data = {
                    "type": "metadata",
                    "response_time_ms": chunk_data.get("response_time_ms"),
                    "fallback_used": chunk_data.get("fallback_used", False),
                    "total_tokens": chunk_data.get("total_tokens", 0)
                }
                yield f"data: {json.dumps(event_data)}\n\n"
            
            elif chunk_data.get("tool_calls"):
                # Handle tool calls (simplified for now)
                for tool_call in chunk_data["tool_calls"]:
                    try:
                        # Placeholder tool execution
                        tool_result = f"Tool {tool_call['function']['name']} executed"
                        
                        event_data = {
                            "type": "tool_use",
                            "tool": tool_call["function"]["name"],
                            "result": tool_result
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                    except Exception as tool_error:
                        logger.error(f"Tool execution error: {str(tool_error)}")
                        event_data = {
                            "type": "tool_error",
                            "tool": tool_call["function"]["name"],
                            "error": str(tool_error)
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
        
    except Exception as e:
        logger.error(f"Multi-provider streaming error: {str(e)}")
        event_data = {
            "type": "error",
            "error": str(e),
            "provider": "unknown"
        }
        yield f"data: {json.dumps(event_data)}\n\n"


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    auth_data: dict = Depends(get_current_auth)
):
    """
    Stream chat responses for reduced latency
    
    Returns Server-Sent Events (SSE) stream with:
    - Progressive response tokens
    - Tool execution results
    - Performance metrics
    """
    try:
        # Start response immediately
        logger.info(f"Streaming chat request from {auth_data.get('auth_type', 'unknown')}")
        
        # Create async tasks for parallel fetching  
        auth_key = auth_data.get('api_key') or auth_data.get('user_id', 'anonymous')
        user_id = auth_data.get('user_id', auth_key)
        
        # Initialize chat history if needed
        if auth_key not in chat_histories:
            chat_histories[auth_key] = []
        
        async def event_generator():
            # Register user activity for cache warming
            await cache_warming_service.register_user_activity(user_id)
            
            # Yield immediate acknowledgment in proper SSE format
            event_data = {
                "type": "start",
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(event_data)}\n\n"
            
            # Start ALL operations in parallel for maximum performance
            start_parallel_time = time.time()
            
            # 1. Fetch persona (cached in memory after first request)
            persona_task = get_cached_persona_memory(
                auth_data.get('active_persona_id', 'default'),
                user_id
            )
            
            # 2. Fetch tools (cached in memory after first request)  
            tools_task = get_cached_tools_memory(
                request.activity or "generic"
            )
            
            # Start all tasks in parallel for maximum performance
            persona_future = asyncio.create_task(persona_task)
            tools_future = asyncio.create_task(tools_task)
            
            # Add user message to history immediately
            chat_histories[auth_key].append(Message(
                role="user",
                content=request.message
            ))
            
            # Wait for all parallel operations to complete
            persona_data, tools = await asyncio.gather(
                persona_future,
                tools_future
            )
            
            parallel_time = (time.time() - start_parallel_time) * 1000
            logger.info(f"Parallel fetch completed in {parallel_time:.0f}ms")
            
            # Send ready event with performance info
            event_data = {
                "type": "ready",
                "timestamp": datetime.utcnow().isoformat(),
                "parallel_fetch_ms": parallel_time,
                "cache_hits": {
                    "persona": True,  # We'll track this properly later
                    "tools": True
                }
            }
            yield f"data: {json.dumps(event_data)}\n\n"
            
            # Prepare system prompt
            system_prompt = persona_data.get("system_prompt", "You are a helpful AI assistant.")
            
            # Prepare messages for LLM
            messages = []
            for msg in chat_histories[auth_key]:
                if msg.content and msg.content.strip():
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Add system prompt at the beginning
            if system_prompt:
                messages.insert(0, {
                    "role": "system", 
                    "content": system_prompt
                })
            
            # Format tools for LLM
            formatted_tools = []
            for tool in tools:
                if hasattr(tool, 'model_dump'):
                    formatted_tools.append(tool.model_dump())
                else:
                    formatted_tools.append(tool)
            
            # Start streaming the response
            response_content = ""
            async for sse_chunk in stream_multi_provider_response(
                messages=messages,
                system_prompt=system_prompt,
                tools=formatted_tools,
                auth_key=auth_key,
                model=request.model,
                provider=request.provider,
                priority=request.priority,
                context_type=request.context_type,
                max_response_time_ms=request.max_response_time_ms,
                required_capabilities=request.required_capabilities,
                enable_fallback=request.enable_fallback,
                force_provider=request.force_provider
            ):
                # Track content for history
                try:
                    chunk_json = json.loads(sse_chunk.replace("data: ", "").strip())
                    if chunk_json.get("type") == "content":
                        response_content += chunk_json.get("content", "")
                except:
                    pass
                
                yield sse_chunk
            
            # Add assistant response to history
            if response_content.strip():
                chat_histories[auth_key].append(Message(
                    role="assistant",
                    content=response_content
                ))
            
            # Send completion event
            event_data = {
                "type": "complete",
                "timestamp": datetime.utcnow().isoformat(),
                "response_length": len(response_content)
            }
            yield f"data: {json.dumps(event_data)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except Exception as e:
        logger.error(f"Stream chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Streaming chat failed: {str(e)}")


@router.post("/stream/cache/invalidate")
async def invalidate_streaming_cache(
    cache_type: str = Query(..., description="Cache type: 'persona', 'tools', or 'all'"),
    user_id: Optional[str] = Query(None, description="Specific user ID to invalidate"),
    activity: Optional[str] = Query(None, description="Specific activity to invalidate"),
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Invalidate streaming cache for performance optimization."""
    try:
        if cache_type == "persona" or cache_type == "all":
            invalidate_persona_cache(user_id=user_id)
        
        if cache_type == "tools" or cache_type == "all":
            invalidate_tools_cache(activity=activity)
        
        return {
            "status": "success",
            "cache_type": cache_type,
            "invalidated_user": user_id,
            "invalidated_activity": activity,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cache invalidation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/cache/status")
async def get_streaming_cache_status(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Get current streaming cache status and statistics."""
    try:
        return {
            "cache_stats": get_cache_status(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cache status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/status")
async def get_streaming_status(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Get streaming chat status with performance metrics."""
    try:
        auth_key = auth_principal.get("user_id") or auth_principal.get("key")
        
        history_count = 0
        if auth_key and auth_key in chat_histories:
            history_count = len(chat_histories[auth_key])
        
        return {
            "status": "ready",
            "performance_mode": "optimized",
            "message_count": history_count,
            "has_history": history_count > 0,
            "cache_status": get_cache_status(),
            "capabilities": {
                "sse_streaming": True,
                "model_selection": True,
                "cache_optimization": True,
                "parallel_fetching": True
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Streaming status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/stream/history")
async def clear_streaming_history(
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """Clear streaming chat history for performance reset."""
    try:
        auth_key = auth_principal.get("user_id") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Could not determine unique auth key.")
        
        if auth_key in chat_histories:
            chat_histories[auth_key] = []
            logger.info(f"Cleared streaming history for user {auth_key}")
        
        return {
            "status": "success",
            "message": "Streaming chat history cleared",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Clear streaming history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Model selection endpoints for streaming optimization
@router.get("/stream/models")
async def list_streaming_models(auth_principal: Dict[str, Any] = Depends(get_current_auth)):
    """List available models with streaming performance characteristics"""
    # This would use model_selector from LLM Platform, but we'll provide a simplified version
    models = [
        {
            "model_id": "claude-3-haiku-20240307",
            "name": "Claude 3 Haiku",
            "provider": "anthropic",
            "avg_ttft_ms": 800,
            "quality_score": 8.5,
            "vr_suitable": True
        },
        {
            "model_id": "gpt-4o-mini",
            "name": "GPT-4o Mini", 
            "provider": "openai",
            "avg_ttft_ms": 1200,
            "quality_score": 9.0,
            "vr_suitable": False
        }
    ]
    
    return {
        "models": models,
        "default_selection": "intelligent",
        "selection_criteria": [
            "message_content",
            "activity_context", 
            "user_preferences",
            "performance_requirements"
        ]
    }




@router.get("/stream/models/performance")
async def get_streaming_model_performance_comparison(auth_principal: Dict[str, Any] = Depends(get_current_auth)):
    """Get detailed performance comparison of all models for streaming"""
    models = [
        {
            "model_id": "claude-3-haiku-20240307",
            "name": "Claude 3 Haiku",
            "avg_ttft_ms": 800,
            "quality_score": 8.5,
            "vr_suitable": True
        },
        {
            "model_id": "gpt-4o-mini", 
            "name": "GPT-4o Mini",
            "avg_ttft_ms": 1200,
            "quality_score": 9.0,
            "vr_suitable": False
        }
    ]
    
    # Sort by different criteria
    fastest_models = sorted(models, key=lambda m: m["avg_ttft_ms"])
    quality_models = sorted(models, key=lambda m: m["quality_score"], reverse=True)
    
    return {
        "all_models": models,
        "rankings": {
            "fastest_ttft": [{"rank": i+1, "model": m["name"], "ttft_ms": m["avg_ttft_ms"]} 
                           for i, m in enumerate(fastest_models)],
            "highest_quality": [{"rank": i+1, "model": m["name"], "quality": m["quality_score"]} 
                              for i, m in enumerate(quality_models)],
            "vr_suitable": [{"model": m["name"], "ttft_ms": m["avg_ttft_ms"]} 
                          for m in models if m["vr_suitable"]]
        },
        "recommendations": {
            "vr_best": fastest_models[0]["model_id"] if fastest_models else None,
            "quality_best": quality_models[0]["model_id"] if quality_models else None,
            "balanced": "claude-3-haiku-20240307",
            "emergency": fastest_models[0]["model_id"] if fastest_models else None
        }
    }