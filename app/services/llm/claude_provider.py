import os
import time
import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator, Union
from anthropic import Anthropic, APIError, APIConnectionError, AuthenticationError
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

class ClaudeProvider(LLMProviderInterface):
    """Claude provider implementation using the new interface"""
    
    # Class-level connection pool
    _client_pool = []
    _pool_size = 3
    _initialized = False
    
    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        # Initialize client pool on first use
        if not ClaudeProvider._initialized:
            self._init_connection_pool()
            
        # Get client from pool
        self.client = self._get_pooled_client()
    
    @classmethod
    def _init_connection_pool(cls):
        """Initialize connection pool with pre-established clients"""
        logger.info(f"Initializing Claude connection pool with {cls._pool_size} connections")
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        for i in range(cls._pool_size):
            client = Anthropic(api_key=api_key)
            cls._client_pool.append(client)
            logger.debug(f"Created pooled client {i+1}/{cls._pool_size}")
        
        cls._initialized = True
        logger.info("Claude connection pool initialized")
    
    def _get_pooled_client(self):
        """Get a client from the pool (round-robin)"""
        if not ClaudeProvider._client_pool:
            raise RuntimeError("Connection pool not initialized")
        
        # Simple round-robin selection
        import threading
        if not hasattr(ClaudeProvider, '_pool_index'):
            ClaudeProvider._pool_index = 0
            ClaudeProvider._pool_lock = threading.Lock()
        
        with ClaudeProvider._pool_lock:
            client = ClaudeProvider._client_pool[ClaudeProvider._pool_index]
            ClaudeProvider._pool_index = (ClaudeProvider._pool_index + 1) % len(ClaudeProvider._client_pool)
        
        return client
    
    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.CLAUDE
    
    @property
    def available_models(self) -> List[ModelInfo]:
        """Return list of available Claude models"""
        return [
            ModelInfo(
                id="claude-3-haiku-20240307",
                name="Claude 3 Haiku",
                provider=LLMProvider.CLAUDE,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.STREAMING,
                    ModelCapability.CODE_GENERATION
                ],
                max_tokens=4096,
                context_window=200000,
                cost_per_input_token=0.00000025,
                cost_per_output_token=0.00000125,
                avg_response_time_ms=633,
                quality_score=0.75,
                speed_score=1.0,
                description="Fastest Claude model, optimal for VR and real-time applications",
                supports_system_prompt=True,
                supports_temperature=True,
                supports_streaming=True
            ),
            ModelInfo(
                id="claude-3-sonnet-20240229",
                name="Claude 3 Sonnet",
                provider=LLMProvider.CLAUDE,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.STREAMING,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.MULTIMODAL
                ],
                max_tokens=4096,
                context_window=200000,
                cost_per_input_token=0.000003,
                cost_per_output_token=0.000015,
                avg_response_time_ms=999,
                quality_score=0.85,
                speed_score=0.7,
                description="Balanced performance and quality, good for most applications",
                supports_system_prompt=True,
                supports_temperature=True,
                supports_streaming=True
            ),
            ModelInfo(
                id="claude-3-5-haiku-20241022",
                name="Claude 3.5 Haiku",
                provider=LLMProvider.CLAUDE,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.STREAMING,
                    ModelCapability.CODE_GENERATION
                ],
                max_tokens=8192,
                context_window=200000,
                cost_per_input_token=0.000001,
                cost_per_output_token=0.000005,
                avg_response_time_ms=1106,
                quality_score=0.8,
                speed_score=0.85,
                description="Improved version of Haiku with better performance",
                supports_system_prompt=True,
                supports_temperature=True,
                supports_streaming=True
            ),
            ModelInfo(
                id="claude-haiku-4-5",
                name="Claude Haiku 4.5",
                provider=LLMProvider.CLAUDE,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.STREAMING,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.LONG_CONTEXT
                ],
                max_tokens=64000,
                context_window=200000,
                cost_per_input_token=0.000001,
                cost_per_output_token=0.000005,
                avg_response_time_ms=800,
                quality_score=0.9,
                speed_score=1.0,
                description="Latest Haiku with near-frontier intelligence, fastest Claude model",
                supports_system_prompt=True,
                supports_temperature=True,
                supports_streaming=True
            ),
            ModelInfo(
                id="claude-3-5-sonnet-20241022",
                name="Claude 3.5 Sonnet",
                provider=LLMProvider.CLAUDE,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.STREAMING,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.MULTIMODAL,
                    ModelCapability.LONG_CONTEXT
                ],
                max_tokens=8192,
                context_window=200000,
                cost_per_input_token=0.000003,
                cost_per_output_token=0.000015,
                avg_response_time_ms=1575,
                quality_score=1.0,
                speed_score=0.5,
                description="Highest quality Claude model with advanced reasoning capabilities",
                supports_system_prompt=True,
                supports_temperature=True,
                supports_streaming=True
            )
        ]
    
    async def validate_config(self) -> bool:
        """Validate provider configuration"""
        try:
            # Make a minimal request to validate API key
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1
            )
            return True
        except AuthenticationError:
            logger.error("Invalid Anthropic API key")
            return False
        except Exception as e:
            logger.warning(f"API key validation warning: {str(e)}")
            return False
    
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        models = self.available_models
        for model in models:
            if model.id == model_id:
                return model
        return None
    
    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage objects to Claude format (excluding system messages)"""
        converted = []
        for msg in messages:
            # Skip system messages - they should be handled via system parameter
            if msg.role == "system":
                continue
                
            claude_msg = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.tool_calls:
                claude_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                claude_msg["tool_call_id"] = msg.tool_call_id
            converted.append(claude_msg)
        return converted
    
    def _convert_tools(self, tools: List[Union[Dict[str, Any], Any]]) -> List[Dict[str, Any]]:
        """Convert tools to Claude format"""
        claude_tools = []
        for tool in tools:
            # Handle both dictionary and Tool object formats
            if hasattr(tool, 'model_dump'):
                # It's a Pydantic model (Tool object), convert to dict
                tool_dict = tool.model_dump()
            else:
                # It's already a dictionary
                tool_dict = tool
            
            if tool_dict.get("type") == "function":
                claude_tools.append({
                    "name": tool_dict["function"]["name"],
                    "description": tool_dict["function"].get("description", ""),
                    "input_schema": tool_dict["function"].get("parameters", {})
                })
        return claude_tools
    
    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Generate a chat completion"""
        start_time = time.time()
        
        # Start provider timing if request has metadata with request_id
        provider_timing = None
        if hasattr(request, 'metadata') and request.metadata and 'request_id' in request.metadata:
            timing_id = instrumentation.start_provider_timing(
                request.metadata['request_id'], 
                "claude", 
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
            
            if request.system_prompt:
                params["system"] = request.system_prompt
            
            if request.tools:
                params["tools"] = self._convert_tools(request.tools)
            
            if request.tool_choice:
                params["tool_choice"] = request.tool_choice
            
            # Record request sent
            if provider_timing:
                provider_timing.record_request_sent()
            
            # Make the API call
            response = self.client.messages.create(**params)
            
            # Record first token (for non-streaming)
            if provider_timing:
                provider_timing.record_first_token()
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract content
            content = ""
            tool_calls = []
            
            logger.info(f"Claude response blocks: {len(response.content)}")
            for i, block in enumerate(response.content):
                logger.info(f"Block {i}: type={block.type}")
                if block.type == "text":
                    logger.info(f"Text block content length: {len(block.text)}")
                    if len(block.text) > 0:
                        logger.info(f"Text block content preview: {block.text[:100]}...")
                    content += block.text
                elif block.type == "tool_use":
                    logger.info(f"Tool use block: {block.name}")
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": block.input
                        }
                    })
            
            logger.info(f"Final content length: {len(content)}")
            
            # Record completion with token counts
            if provider_timing:
                provider_timing.record_completion(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens
                )
            
            return LLMResponse(
                content=content,
                model=request.model,
                provider=LLMProvider.CLAUDE,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                tool_calls=tool_calls if tool_calls else None,
                finish_reason=response.stop_reason,
                response_time_ms=response_time_ms,
                metadata=request.metadata or {}
            )
            
        except AuthenticationError as e:
            raise LLMProviderError(f"Authentication error: {str(e)}", LLMProvider.CLAUDE, "auth_error")
        except APIConnectionError as e:
            raise LLMProviderError(f"Connection error: {str(e)}", LLMProvider.CLAUDE, "connection_error")
        except APIError as e:
            raise LLMProviderError(f"API error: {str(e)}", LLMProvider.CLAUDE, "api_error")
        except Exception as e:
            raise LLMProviderError(f"Unexpected error: {str(e)}", LLMProvider.CLAUDE, "unknown_error")
    
    async def chat_completion_stream(self, request: LLMRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate a streaming chat completion"""
        # Start provider timing if request has metadata with request_id
        provider_timing = None
        if hasattr(request, 'metadata') and request.metadata and 'request_id' in request.metadata:
            timing_id = instrumentation.start_provider_timing(
                request.metadata['request_id'], 
                "claude", 
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
            
            if request.system_prompt:
                params["system"] = request.system_prompt
            
            if request.tools:
                params["tools"] = self._convert_tools(request.tools)
            
            if request.tool_choice:
                params["tool_choice"] = request.tool_choice
            
            # Record request sent
            if provider_timing:
                provider_timing.record_request_sent()
            
            # Stream response
            with self.client.messages.stream(**params) as stream:
                current_tool_call = None
                tool_calls = []
                first_token_received = False
                
                for chunk in stream:
                    if chunk.type == "message_start":
                        continue
                    elif chunk.type == "content_block_start":
                        if chunk.content_block.type == "tool_use":
                            current_tool_call = {
                                "id": chunk.content_block.id,
                                "type": "function",
                                "function": {
                                    "name": chunk.content_block.name,
                                    "arguments": ""
                                }
                            }
                    elif chunk.type == "content_block_delta":
                        if chunk.delta.type == "text_delta":
                            # Record first token timing
                            if not first_token_received and provider_timing:
                                provider_timing.record_first_token()
                                first_token_received = True
                            
                            yield StreamChunk(
                                content=chunk.delta.text,
                                model=request.model,
                                provider=LLMProvider.CLAUDE,
                                metadata=request.metadata or {}
                            )
                        elif chunk.delta.type == "input_json_delta" and current_tool_call:
                            current_tool_call["function"]["arguments"] += chunk.delta.partial_json
                    elif chunk.type == "content_block_stop":
                        if current_tool_call:
                            tool_calls.append(current_tool_call)
                            current_tool_call = None
                    elif chunk.type == "message_delta":
                        if chunk.delta.stop_reason:
                            yield StreamChunk(
                                content="",
                                model=request.model,
                                provider=LLMProvider.CLAUDE,
                                finish_reason=chunk.delta.stop_reason,
                                tool_calls=tool_calls if tool_calls else None,
                                metadata=request.metadata or {}
                            )
                    elif chunk.type == "message_stop":
                        if hasattr(chunk, 'usage') and chunk.usage:
                            # Record completion with token counts
                            if provider_timing:
                                provider_timing.record_completion(
                                    input_tokens=chunk.usage.input_tokens,
                                    output_tokens=chunk.usage.output_tokens
                                )
                            
                            yield StreamChunk(
                                content="",
                                model=request.model,
                                provider=LLMProvider.CLAUDE,
                                usage={
                                    "input_tokens": chunk.usage.input_tokens,
                                    "output_tokens": chunk.usage.output_tokens,
                                    "total_tokens": chunk.usage.input_tokens + chunk.usage.output_tokens
                                },
                                metadata=request.metadata or {}
                            )
                        
        except AuthenticationError as e:
            raise LLMProviderError(f"Authentication error: {str(e)}", LLMProvider.CLAUDE, "auth_error")
        except APIConnectionError as e:
            raise LLMProviderError(f"Connection error: {str(e)}", LLMProvider.CLAUDE, "connection_error")
        except APIError as e:
            raise LLMProviderError(f"API error: {str(e)}", LLMProvider.CLAUDE, "api_error")
        except Exception as e:
            raise LLMProviderError(f"Unexpected error: {str(e)}", LLMProvider.CLAUDE, "unknown_error")
    
    async def count_tokens(self, text: str, model: str) -> int:
        """Count tokens in text for the specified model"""
        # Claude doesn't provide a direct token counting API
        # Use a rough approximation: 1 token ≈ 4 characters for English text
        return len(text) // 4
    
    def is_model_available(self, model_id: str) -> bool:
        """Check if a model is available for this provider"""
        return any(model.id == model_id for model in self.available_models)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the provider"""
        try:
            start_time = time.time()
            
            # Make a minimal request
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "provider": "claude",
                "status": "healthy",
                "response_time_ms": response_time,
                "available_models": len(self.available_models),
                "pool_size": len(self._client_pool),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "provider": "claude",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Register the provider
LLMProviderFactory.register_provider(LLMProvider.CLAUDE, ClaudeProvider)