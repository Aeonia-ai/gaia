"""
Unified chat service for multi-provider LLM support
"""
import logging
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from fastapi import HTTPException
from uuid import uuid4

from .base import (
    LLMProvider, 
    LLMMessage, 
    LLMRequest, 
    LLMResponse,
    StreamChunk,
    LLMProviderError,
    ModelCapability
)
from .registry import get_registry
from .multi_provider_selector import (
    multi_provider_selector, 
    ModelRecommendation, 
    ContextType, 
    ModelPriority
)
from .config import global_config
from app.shared.instrumentation import instrumentation, record_stage, instrument_async_operation

logger = logging.getLogger(__name__)

class MultiProviderChatService:
    """Unified chat service supporting multiple LLM providers"""
    
    def __init__(self):
        self.registry = None
        self.selector = multi_provider_selector
    
    async def initialize(self):
        """Initialize the service"""
        if not self.registry:
            self.registry = await get_registry()
            await self.selector.initialize()
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[LLMProvider] = None,
        priority: Optional[ModelPriority] = None,
        context_type: Optional[ContextType] = None,
        max_response_time_ms: Optional[int] = None,
        required_capabilities: Optional[List[ModelCapability]] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        enable_fallback: bool = True,
        force_provider: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a chat completion using the best available provider
        
        Args:
            messages: List of chat messages
            system_prompt: System prompt to use
            model: Specific model to use (if None, auto-select)
            provider: Preferred provider (if None, auto-select)
            priority: Model selection priority
            context_type: Context type for selection
            max_response_time_ms: Maximum response time requirement
            required_capabilities: Required model capabilities
            user_id: User ID for personalized selection
            enable_fallback: Enable fallback to other providers
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Available tools
            tool_choice: Tool choice strategy
            request_id: Request ID for tracking (auto-generated if None)
            
        Returns:
            Dictionary containing response and metadata
        """
        
        await self.initialize()
        
        # Generate request_id if not provided
        if request_id is None:
            request_id = str(uuid4())
        
        # Start instrumentation
        instrumentation.start_request(request_id, {
            "user_id": user_id,
            "model": model,
            "provider": provider.value if provider else None,
            "message_length": len(messages[-1].get("content", "")) if messages else 0,
            "tools_count": len(tools) if tools else 0
        })
        
        start_time = time.time()
        recommendation = None
        fallback_used = False
        
        try:
            # 1. If no model specified, use default
            if not model:
                model = global_config.get_default_model()
                logger.info(f"No model specified, using default: {model}")
                record_stage(request_id, "default_model_selected", metadata={"model": model})
            
            # 2. Handle forced provider/model selection (skip intelligence)
            if force_provider:
                selection_start = time.time()
                if model and not provider:
                    provider = await self.registry.find_provider_for_model(model)
                    if not provider:
                        raise ValueError(f"No provider found for model: {model}")
                elif provider and not model:
                    # Use the first available model from the specified provider
                    all_models = await self.registry.get_all_models()
                    if provider in all_models and all_models[provider]:
                        model = all_models[provider][0].id
                    else:
                        raise ValueError(f"No models available for provider: {provider.value}")
                
                selection_duration = (time.time() - selection_start) * 1000
                logger.info(f"Force-selected model: {model} from {provider.value} (intelligence disabled)")
                record_stage(request_id, "force_provider_selection", selection_duration, {
                    "model": model,
                    "provider": provider.value,
                    "intelligence_disabled": True
                })
                recommendation = None
            
            # 3. Get model recommendation if intelligence enabled and no explicit model
            elif not force_provider and global_config.enable_auto_selection:
                message_text = messages[-1].get("content", "") if messages else ""
                recommendation = await instrument_async_operation(
                    request_id,
                    "intelligent_model_selection",
                    self.selector.select_model(
                        message=message_text,
                        context_type=context_type,
                        priority=priority,
                        user_id=user_id,
                        max_response_time_ms=max_response_time_ms,
                        preferred_provider=provider,
                        required_capabilities=required_capabilities or []
                    )
                )
                model = recommendation.model_id
                provider = recommendation.provider
                logger.info(f"Auto-selected model: {model} from {provider.value}")
                record_stage(request_id, "intelligent_selection_complete", metadata={
                    "model": model,
                    "provider": provider.value,
                    "reasoning": recommendation.reasoning
                })
            
            # 4. Use explicit model without intelligence (default behavior)
            else:
                # Find provider for specified model
                provider = provider or await self.registry.find_provider_for_model(model)
                if not provider:
                    raise ValueError(f"No provider found for model: {model}")
                recommendation = None
                logger.info(f"Using model: {model} from {provider.value} (single model mode)")
                record_stage(request_id, "explicit_model_selection", metadata={
                    "model": model,
                    "provider": provider.value,
                    "intelligence_disabled": False
                })
            
            # 2. Convert messages to LLM format / create request
            def _invalid_message(detail: str) -> None:
                instrumentation.complete_request(request_id, {
                    "provider": provider.value if provider else None,
                    "model": model,
                    "success": False,
                    "error": f"invalid_request_payload: {detail}"
                })
                raise HTTPException(status_code=400, detail=f"Invalid chat message format: {detail}")

            llm_messages = []
            for msg in messages:
                if not isinstance(msg, dict):
                    _invalid_message(f"Message must be a dict, received {type(msg).__name__}")

                missing_fields = [field for field in ("role", "content") if field not in msg]
                if missing_fields:
                    _invalid_message(f"Missing fields: {', '.join(missing_fields)}")

                content = msg["content"]
                if not isinstance(content, str):
                    _invalid_message(f"Message content must be a string, received {type(content).__name__}")

                llm_messages.append(
                    LLMMessage(
                        role=msg["role"],
                        content=content,
                        tool_calls=msg.get("tool_calls"),
                        tool_call_id=msg.get("tool_call_id")
                    )
                )

            try:
                llm_request = LLMRequest(
                    messages=llm_messages,
                    model=model,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    tool_choice=tool_choice,
                    user_id=user_id,
                    user_email=user_email,
                    metadata={
                        "start_time": start_time,
                        "request_id": request_id
                    }
                )
            except (TypeError, ValueError) as e:
                error_detail = f"Invalid LLM request payload: {str(e)}"
                record_stage(request_id, "invalid_request_payload", metadata={"error": error_detail})
                instrumentation.complete_request(request_id, {
                    "provider": provider.value if provider else None,
                    "model": model,
                    "success": False,
                    "error": error_detail
                })
                raise HTTPException(status_code=400, detail=error_detail)

            # 4. Get provider and make request
            provider_instance = await self.registry.get_provider(provider)
            record_stage(request_id, "provider_request_start", metadata={
                "provider": provider.value,
                "model": model
            })

            response = await instrument_async_operation(
                request_id,
                "provider_api_call",
                provider_instance.chat_completion(llm_request)
            )

            # 5. Record success metrics
            self.registry.record_request(
                provider=provider,
                tokens_used=response.usage.get("total_tokens", 0),
                cost=self._calculate_cost(response, recommendation),
                response_time_ms=response.response_time_ms or 0,
                error=False
            )

            # 6. Return formatted response
            final_response = {
                "response": response.content,
                "provider": provider.value,
                "model": model,
                "usage": response.usage,
                "response_time_ms": response.response_time_ms,
                "reasoning": recommendation.reasoning if recommendation else f"Explicit model selection: {model}",
                "fallback_used": fallback_used,
                "tool_calls": response.tool_calls,
                "finish_reason": response.finish_reason,
                "request_id": request_id
            }

            # Complete instrumentation
            instrumentation.complete_request(request_id, {
                "provider": provider.value,
                "model": model,
                "success": True,
                "token_count": response.usage.get("total_tokens", 0),
                "fallback_used": fallback_used
            })

            return final_response
            
        except LLMProviderError as e:
            logger.error(f"Provider error with {provider.value}: {str(e)}")
            
            # Record error
            self.registry.record_request(
                provider=provider,
                error=True
            )
            
            record_stage(request_id, "provider_error", metadata={
                "provider": provider.value,
                "error": str(e)
            })
            
            # Try fallback if enabled
            if enable_fallback and not fallback_used and e.error_code != "invalid_request_payload":
                logger.info("Attempting fallback to alternative provider")
                fallback_used = True
                
                # Get alternative recommendation
                try:
                    message_text = messages[-1].get("content", "") if messages else ""
                    
                    # Get provider recommendations with proper await
                    get_recommendations_coro = self.selector.get_provider_recommendations({
                        "message": message_text,
                        "context_type": context_type,
                        "priority": priority,
                        "max_response_time_ms": max_response_time_ms,
                        "required_capabilities": required_capabilities or []
                    })
                    
                    recommendations = await instrument_async_operation(
                        request_id,
                        "fallback_provider_selection",
                        get_recommendations_coro
                    )
                    
                    # Try each recommendation until one works
                    for rec in recommendations:
                        if rec.provider != provider:  # Skip the failed provider
                            try:
                                record_stage(request_id, "fallback_attempt", metadata={
                                    "fallback_provider": rec.provider.value,
                                    "fallback_model": rec.model_id
                                })
                                
                                return await self.chat_completion(
                                    messages=messages,
                                    system_prompt=system_prompt,
                                    model=rec.model_id,
                                    provider=rec.provider,
                                    enable_fallback=False,  # Prevent infinite recursion
                                    temperature=temperature,
                                    max_tokens=max_tokens,
                                    tools=tools,
                                    tool_choice=tool_choice,
                                    request_id=request_id  # Pass through request_id
                                )
                            except Exception as fallback_error:
                                logger.warning(f"Fallback to {rec.provider.value} failed: {str(fallback_error)}")
                                record_stage(request_id, "fallback_failed", metadata={
                                    "fallback_provider": rec.provider.value,
                                    "error": str(fallback_error)
                                })
                                continue
                                
                except Exception as fallback_selection_error:
                    logger.error(f"Fallback selection failed: {str(fallback_selection_error)}")
                    record_stage(request_id, "fallback_selection_failed", metadata={
                        "error": str(fallback_selection_error)
                    })
            
            # Complete instrumentation with error
            instrumentation.complete_request(request_id, {
                "provider": provider.value if provider else "unknown",
                "success": False,
                "error": str(e),
                "fallback_used": fallback_used
            })
            
            # If all fallbacks failed, raise the original error
            status_code = 400 if e.error_code == "invalid_request_payload" else 500
            raise HTTPException(status_code=status_code, detail=f"Chat completion failed ({e.error_code or 'provider_error'}): {str(e)}")

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Unexpected error in chat completion: {str(e)}")
            
            # Complete instrumentation with error
            instrumentation.complete_request(request_id, {
                "success": False,
                "error": str(e),
                "unexpected_error": True
            })
            
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[LLMProvider] = None,
        priority: Optional[ModelPriority] = None,
        context_type: Optional[ContextType] = None,
        max_response_time_ms: Optional[int] = None,
        required_capabilities: Optional[List[ModelCapability]] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        enable_fallback: bool = True,
        force_provider: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate a streaming chat completion
        """
        
        await self.initialize()
        
        # Generate request_id if not provided
        if request_id is None:
            request_id = str(uuid4())
        
        # Start instrumentation
        instrumentation.start_request(request_id, {
            "user_id": user_id,
            "model": model,
            "provider": provider.value if provider else None,
            "message_length": len(messages[-1].get("content", "")) if messages else 0,
            "tools_count": len(tools) if tools else 0,
            "streaming": True
        })
        
        start_time = time.time()
        recommendation = None
        fallback_used = False
        
        try:
            # 1. If no model specified, use default
            if not model:
                model = global_config.get_default_model()
                logger.info(f"No model specified, using default: {model}")
            
            # 2. Handle forced provider/model selection (skip intelligence)
            if force_provider:
                if model and not provider:
                    provider = await self.registry.find_provider_for_model(model)
                    if not provider:
                        raise ValueError(f"No provider found for model: {model}")
                elif provider and not model:
                    # Use the first available model from the specified provider
                    all_models = await self.registry.get_all_models()
                    if provider in all_models and all_models[provider]:
                        model = all_models[provider][0].id
                    else:
                        raise ValueError(f"No models available for provider: {provider.value}")
                
                yield {
                    "type": "model_selection",
                    "model": model,
                    "provider": provider.value,
                    "reasoning": f"Force-selected: {model} (intelligence disabled)"
                }
            
            # 3. Get model recommendation if intelligence enabled
            elif not force_provider and global_config.enable_auto_selection:
                message_text = messages[-1].get("content", "") if messages else ""
                recommendation = await self.selector.select_model(
                    message=message_text,
                    context_type=context_type,
                    priority=priority,
                    user_id=user_id,
                    max_response_time_ms=max_response_time_ms,
                    preferred_provider=provider,
                    required_capabilities=required_capabilities or []
                )
                model = recommendation.model_id
                provider = recommendation.provider
                
                # Yield selection info
                yield {
                    "type": "model_selection",
                    "model": model,
                    "provider": provider.value,
                    "reasoning": recommendation.reasoning
                }
            
            # 4. Use explicit model without intelligence (default behavior)
            else:
                # Find provider for specified model
                provider = provider or await self.registry.find_provider_for_model(model)
                if not provider:
                    raise ValueError(f"No provider found for model: {model}")
                
                yield {
                    "type": "model_selection", 
                    "model": model,
                    "provider": provider.value,
                    "reasoning": f"Default model: {model} (single model mode)"
                }
            
            # 2. Convert messages to LLM format
            llm_messages = [
                LLMMessage(
                    role=msg["role"],
                    content=msg["content"],
                    tool_calls=msg.get("tool_calls"),
                    tool_call_id=msg.get("tool_call_id")
                )
                for msg in messages
            ]
            
            # 3. Create LLM request
            llm_request = LLMRequest(
                messages=llm_messages,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                tools=tools,
                tool_choice=tool_choice,
                user_id=user_id,
                user_email=user_email, # Pass user_email here
                metadata={
                    "start_time": start_time,
                    "request_id": request_id
                }
            )
            
            # 4. Get provider and stream response
            provider_instance = await self.registry.get_provider(provider)
            
            total_tokens = 0
            async for chunk in provider_instance.chat_completion_stream(llm_request):
                # Convert StreamChunk to dict
                chunk_data = {
                    "type": "content",
                    "content": chunk.content,
                    "provider": chunk.provider.value,
                    "model": model
                }
                
                if chunk.finish_reason:
                    chunk_data["finish_reason"] = chunk.finish_reason
                
                if chunk.tool_calls:
                    chunk_data["tool_calls"] = chunk.tool_calls
                
                if chunk.usage:
                    chunk_data["usage"] = chunk.usage
                    total_tokens = chunk.usage.get("total_tokens", 0)
                
                yield chunk_data
            
            # 5. Record success metrics
            response_time_ms = int((time.time() - start_time) * 1000)
            self.registry.record_request(
                provider=provider,
                tokens_used=total_tokens,
                cost=self._calculate_cost_estimate(model, total_tokens),
                response_time_ms=response_time_ms,
                error=False
            )
            
            # 6. Yield final metadata
            yield {
                "type": "metadata",
                "response_time_ms": response_time_ms,
                "fallback_used": fallback_used,
                "total_tokens": total_tokens
            }
            
        except LLMProviderError as e:
            logger.error(f"Provider error with {provider.value}: {str(e)}")
            
            # Record error
            self.registry.record_request(provider=provider, error=True)
            
            # Yield error but continue if fallback is possible
            yield {
                "type": "error",
                "error": str(e),
                "provider": provider.value if provider else "unknown",
                "fallback_available": enable_fallback and not fallback_used
            }
            
            # Try fallback if enabled
            if enable_fallback and not fallback_used:
                yield {"type": "fallback_attempt", "message": "Attempting fallback to alternative provider"}
                
                try:
                    message_text = messages[-1].get("content", "") if messages else ""
                    recommendations = await self.selector.get_provider_recommendations({
                        "message": message_text,
                        "context_type": context_type,
                        "priority": priority,
                        "max_response_time_ms": max_response_time_ms,
                        "required_capabilities": required_capabilities or []
                    })
                    
                    # Try first alternative
                    for rec in recommendations:
                        if rec.provider != provider:
                            try:
                                async for fallback_chunk in self.chat_completion_stream(
                                    messages=messages,
                                    system_prompt=system_prompt,
                                    model=rec.model_id,
                                    provider=rec.provider,
                                    enable_fallback=False,
                                    temperature=temperature,
                                    max_tokens=max_tokens,
                                    tools=tools,
                                    tool_choice=tool_choice,
                                    request_id=request_id  # Pass through request_id
                                ):
                                    fallback_chunk["fallback_used"] = True
                                    yield fallback_chunk
                                return
                            except Exception:
                                continue
                                
                    # If no fallback worked
                    yield {
                        "type": "error",
                        "error": "All fallback attempts failed",
                        "fallback_used": True
                    }
                    
                except Exception as fallback_error:
                    yield {
                        "type": "error", 
                        "error": f"Fallback selection failed: {str(fallback_error)}",
                        "fallback_used": True
                    }
            
        except Exception as e:
            logger.error(f"Unexpected error in streaming chat: {str(e)}")
            yield {
                "type": "error",
                "error": f"Internal error: {str(e)}"
            }
    
    def _calculate_cost(self, response: LLMResponse, recommendation: Optional[ModelRecommendation]) -> float:
        """Calculate cost for a completed response"""
        if recommendation:
            return recommendation.estimated_cost
        
        # Fallback cost calculation
        usage = response.usage or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        # Use rough estimates if model info not available
        input_cost = input_tokens * 0.000003  # Rough average
        output_cost = output_tokens * 0.000015  # Rough average
        
        return input_cost + output_cost
    
    def _calculate_cost_estimate(self, model: str, total_tokens: int) -> float:
        """Estimate cost based on model and token count"""
        # This would ideally use model-specific pricing
        return total_tokens * 0.000006  # Rough average per token

# Global chat service instance
chat_service = MultiProviderChatService()
