from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import json

class LLMProvider(str, Enum):
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    MISTRAL = "mistral"

class ModelCapability(str, Enum):
    CHAT = "chat"
    TOOL_CALLING = "tool_calling"
    VISION = "vision"
    CODE_GENERATION = "code_generation"
    MULTIMODAL = "multimodal"
    STREAMING = "streaming"
    LONG_CONTEXT = "long_context"

@dataclass
class ModelInfo:
    id: str
    name: str
    provider: LLMProvider
    capabilities: List[ModelCapability]
    max_tokens: int
    context_window: int
    cost_per_input_token: float
    cost_per_output_token: float
    avg_response_time_ms: int
    quality_score: float  # 0.0-1.0
    speed_score: float    # 0.0-1.0
    description: str
    is_deprecated: bool = False
    supports_system_prompt: bool = True
    supports_temperature: bool = True
    supports_streaming: bool = True

@dataclass
class LLMMessage:
    role: str  # "user", "assistant", "system"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    timestamp: Optional[datetime] = None

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: LLMProvider
    usage: Dict[str, Any]
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    response_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = None

@dataclass
class LLMRequest:
    messages: List[LLMMessage]
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    system_prompt: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class StreamChunk:
    content: str
    model: str
    provider: LLMProvider
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

class LLMProviderError(Exception):
    def __init__(self, message: str, provider: LLMProvider, error_code: Optional[str] = None):
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code

class LLMProviderInterface(ABC):
    """Base interface for all LLM providers"""
    
    @property
    @abstractmethod
    def provider_name(self) -> LLMProvider:
        """Return the provider name"""
        pass
    
    @property
    @abstractmethod
    def available_models(self) -> List[ModelInfo]:
        """Return list of available models for this provider"""
        pass
    
    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate provider configuration (API keys, etc.)"""
        pass
    
    @abstractmethod
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        pass
    
    @abstractmethod
    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Generate a chat completion"""
        pass
    
    @abstractmethod
    async def chat_completion_stream(self, request: LLMRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate a streaming chat completion"""
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str, model: str) -> int:
        """Count tokens in text for the specified model"""
        pass
    
    @abstractmethod
    def is_model_available(self, model_id: str) -> bool:
        """Check if a model is available for this provider"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the provider"""
        pass

class LLMProviderFactory:
    """Factory for creating LLM provider instances"""
    
    _providers: Dict[LLMProvider, type] = {}
    _instances: Dict[LLMProvider, LLMProviderInterface] = {}
    
    @classmethod
    def register_provider(cls, provider: LLMProvider, provider_class: type):
        """Register a new provider class"""
        cls._providers[provider] = provider_class
    
    @classmethod
    async def get_provider(cls, provider: LLMProvider) -> LLMProviderInterface:
        """Get provider instance (singleton)"""
        if provider not in cls._instances:
            if provider not in cls._providers:
                raise ValueError(f"Provider {provider} not registered")
            cls._instances[provider] = cls._providers[provider]()
        return cls._instances[provider]
    
    @classmethod
    def get_available_providers(cls) -> List[LLMProvider]:
        """Get list of registered providers"""
        return list(cls._providers.keys())
    
    @classmethod
    def reset_instances(cls):
        """Reset all provider instances (for testing)"""
        cls._instances.clear()
