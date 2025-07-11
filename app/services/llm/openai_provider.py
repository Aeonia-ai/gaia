import os
import time
import json
from typing import Optional, List, Dict, Any, AsyncGenerator, Union
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
import logging
from datetime import datetime

from app.shared.instrumentation import instrumentation

from .base import (
    LLMProvider,
    ModelCapability,
    ModelInfo,
    LLMMessage,
    LLMResponse,
    LLMRequest,
    StreamChunk,
    LLMProviderError,
    LLMProviderInterface,
    LLMProviderFactory
)

logger = logging.getLogger(__name__)

class OpenAIProvider(LLMProviderInterface):
    """OpenAI provider implementation using the new interface"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=self.api_key)
        self.async_client = AsyncOpenAI(api_key=self.api_key)
    
    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.OPENAI
    
    @property
    def available_models(self) -> List[ModelInfo]:
        """Return list of available OpenAI models"""
        return [
            ModelInfo(
                id="gpt-4o",
                name="GPT-4o",
                provider=LLMProvider.OPENAI,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.STREAMING,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.MULTIMODAL
                ],
                max_tokens=4096,
                context_window=128000,
                cost_per_input_token=0.000005,
                cost_per_output_token=0.000015,
                avg_response_time_ms=800,
                quality_score=0.95,
                speed_score=0.8,
                description="Most capable GPT-4 model with vision and multimodal capabilities",
                supports_system_prompt=True,
                supports_temperature=True,
                supports_streaming=True
            ),
            ModelInfo(
                id="gpt-4o-mini",
                name="GPT-4o Mini",
                provider=LLMProvider.OPENAI,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.STREAMING,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.MULTIMODAL
                ],
                max_tokens=16384,
                context_window=128000,
                cost_per_input_token=0.00000015,
                cost_per_output_token=0.0000006,
                avg_response_time_ms=500,
                quality_score=0.8,
                speed_score=0.9,
                description="Faster, more affordable version of GPT-4o",
                supports_system_prompt=True,
                supports_temperature=True,
                supports_streaming=True
            ),
            ModelInfo(
                id="gpt-4-turbo",
                name="GPT-4 Turbo",
                provider=LLMProvider.OPENAI,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.STREAMING,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.MULTIMODAL,
                    ModelCapability.LONG_CONTEXT
                ],
                max_tokens=4096,
                context_window=128000,
                cost_per_input_token=0.00001,
                cost_per_output_token=0.00003,
                avg_response_time_ms=1200,
                quality_score=0.9,
                speed_score=0.6,
                description="High-performance GPT-4 model with large context window",
                supports_system_prompt=True,
                supports_temperature=True,
                supports_streaming=True
            ),
            ModelInfo(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider=LLMProvider.OPENAI,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.STREAMING,
                    ModelCapability.CODE_GENERATION
                ],
                max_tokens=4096,
                context_window=16385,
                cost_per_input_token=0.000001,
                cost_per_output_token=0.000002,
                avg_response_time_ms=400,
                quality_score=0.7,
                speed_score=1.0,
                description="Fast and affordable model for simple tasks",
                supports_system_prompt=True,
                supports_temperature=True,
                supports_streaming=True
            ),
            ModelInfo(
                id="gpt-4",
                name="GPT-4",
                provider=LLMProvider.OPENAI,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.STREAMING,
                    ModelCapability.CODE_GENERATION
                ],
                max_tokens=4096,
                context_window=8192,
                cost_per_input_token=0.00003,
                cost_per_output_token=0.00006,
                avg_response_time_ms=2000,
                quality_score=0.85,
                speed_score=0.4,
                description="Original GPT-4 model with high quality reasoning",
                supports_system_prompt=True,
                supports_temperature=True,
                supports_streaming=True,
                is_deprecated=True
            )
        ]
    
    async def validate_config(self) -> bool:
        """Validate provider configuration"""
        try:
            # Make a minimal request to validate API key
            response = await self.async_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI API key validation failed: {str(e)}")
            return False
    
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        models = self.available_models
        for model in models:
            if model.id == model_id:
                return model
        return None
    
    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage objects to OpenAI format"""
        converted = []
        for msg in messages:
            openai_msg = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id
            converted.append(openai_msg)
        return converted
    
    def _convert_tools(self, tools: List[Union[Dict[str, Any], Any]]) -> List[Dict[str, Any]]:
        """Convert tools to OpenAI format"""
        converted_tools = []
        for tool in tools:
            # Handle both dictionary and Tool object formats
            if hasattr(tool, 'model_dump'):
                # It's a Pydantic model (Tool object), convert to dict
                tool_dict = tool.model_dump()
            else:
                # It's already a dictionary
                tool_dict = tool
            converted_tools.append(tool_dict)
        return converted_tools
    
    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Generate a chat completion"""
        start_time = time.time()
        
        # Start provider timing if request has metadata with request_id
        provider_timing = None
        if hasattr(request, 'metadata') and request.metadata and 'request_id' in request.metadata:
            timing_id = instrumentation.start_provider_timing(
                request.metadata['request_id'], 
                "openai", 
                request.model
            )
            provider_timing = instrumentation.get_provider_timing(timing_id)
        
        try:
            # Build request parameters
            params = {
                "model": request.model,
                "messages": self._convert_messages(request.messages),
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            }
            
            # OpenAI handles system prompts as messages, not separate parameter
            if request.system_prompt:
                system_msg = {"role": "system", "content": request.system_prompt}
                params["messages"] = [system_msg] + params["messages"]
            
            if request.tools:
                params["tools"] = self._convert_tools(request.tools)
            
            if request.tool_choice:
                params["tool_choice"] = request.tool_choice
            
            # Record request sent
            if provider_timing:
                provider_timing.record_request_sent()
            
            # Make the API call
            response = await self.async_client.chat.completions.create(**params)
            
            # Record first token (for non-streaming)
            if provider_timing:
                provider_timing.record_first_token()
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract content and tool calls
            content = response.choices[0].message.content or ""
            tool_calls = None
            
            if response.choices[0].message.tool_calls:
                tool_calls = []
                for tool_call in response.choices[0].message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
            
            # Record completion with token counts
            if provider_timing:
                provider_timing.record_completion(
                    input_tokens=response.usage.prompt_tokens if response.usage else 0,
                    output_tokens=response.usage.completion_tokens if response.usage else 0
                )
            
            return LLMResponse(
                content=content,
                model=request.model,
                provider=LLMProvider.OPENAI,
                usage={
                    "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                tool_calls=tool_calls,
                finish_reason=response.choices[0].finish_reason,
                response_time_ms=response_time_ms,
                metadata=request.metadata or {}
            )
            
        except Exception as e:
            error_msg = str(e)
            error_code = "unknown_error"
            
            if "authentication" in error_msg.lower():
                error_code = "auth_error"
            elif "rate limit" in error_msg.lower():
                error_code = "rate_limit"
            elif "connection" in error_msg.lower():
                error_code = "connection_error"
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                error_code = "model_not_found"
            
            raise LLMProviderError(f"OpenAI API error: {error_msg}", LLMProvider.OPENAI, error_code)
    
    async def chat_completion_stream(self, request: LLMRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate a streaming chat completion"""
        try:
            # Build request parameters
            params = {
                "model": request.model,
                "messages": self._convert_messages(request.messages),
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": True
            }
            
            # OpenAI handles system prompts as messages, not separate parameter
            if request.system_prompt:
                system_msg = {"role": "system", "content": request.system_prompt}
                params["messages"] = [system_msg] + params["messages"]
            
            if request.tools:
                params["tools"] = self._convert_tools(request.tools)
            
            if request.tool_choice:
                params["tool_choice"] = request.tool_choice
            
            # Stream response
            stream = await self.async_client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    
                    # Handle content delta
                    if choice.delta.content:
                        yield StreamChunk(
                            content=choice.delta.content,
                            model=request.model,
                            provider=LLMProvider.OPENAI,
                            metadata=request.metadata or {}
                        )
                    
                    # Handle tool calls
                    if choice.delta.tool_calls:
                        tool_calls = []
                        for tool_call in choice.delta.tool_calls:
                            tool_calls.append({
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": {
                                    "name": tool_call.function.name if tool_call.function else "",
                                    "arguments": tool_call.function.arguments if tool_call.function else ""
                                }
                            })
                        
                        yield StreamChunk(
                            content="",
                            model=request.model,
                            provider=LLMProvider.OPENAI,
                            tool_calls=tool_calls,
                            metadata=request.metadata or {}
                        )
                    
                    # Handle finish reason
                    if choice.finish_reason:
                        yield StreamChunk(
                            content="",
                            model=request.model,
                            provider=LLMProvider.OPENAI,
                            finish_reason=choice.finish_reason,
                            metadata=request.metadata or {}
                        )
                
                # Handle usage information
                if hasattr(chunk, 'usage') and chunk.usage:
                    yield StreamChunk(
                        content="",
                        model=request.model,
                        provider=LLMProvider.OPENAI,
                        usage={
                            "input_tokens": chunk.usage.prompt_tokens,
                            "output_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        },
                        metadata=request.metadata or {}
                    )
                        
        except Exception as e:
            error_msg = str(e)
            error_code = "unknown_error"
            
            if "authentication" in error_msg.lower():
                error_code = "auth_error"
            elif "rate limit" in error_msg.lower():
                error_code = "rate_limit"
            elif "connection" in error_msg.lower():
                error_code = "connection_error"
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                error_code = "model_not_found"
            
            raise LLMProviderError(f"OpenAI streaming error: {error_msg}", LLMProvider.OPENAI, error_code)
    
    async def count_tokens(self, text: str, model: str) -> int:
        """Count tokens in text for the specified model"""
        try:
            import tiktoken
            
            # Get encoder for the model
            if model.startswith("gpt-4"):
                encoder = tiktoken.encoding_for_model("gpt-4")
            elif model.startswith("gpt-3.5"):
                encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
            else:
                # Fallback to cl100k_base encoding
                encoder = tiktoken.get_encoding("cl100k_base")
            
            return len(encoder.encode(text))
        except ImportError:
            # Fallback if tiktoken is not available
            # Use a rough approximation: 1 token ≈ 4 characters for English text
            return len(text) // 4
        except Exception:
            # Fallback approximation
            return len(text) // 4
    
    def is_model_available(self, model_id: str) -> bool:
        """Check if a model is available for this provider"""
        return any(model.id == model_id for model in self.available_models)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the provider"""
        try:
            start_time = time.time()
            
            # Make a minimal request
            response = await self.async_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "provider": "openai",
                "status": "healthy",
                "response_time_ms": response_time,
                "available_models": len(self.available_models),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "provider": "openai",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Register the provider
LLMProviderFactory.register_provider(LLMProvider.OPENAI, OpenAIProvider)