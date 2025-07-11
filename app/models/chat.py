from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal, Union

class Message(BaseModel):
    role: Literal["system", "user", "assistant", "function"] = Field(
        description="The role of the message sender"
    )
    content: str = Field(description="The content of the message")
    name: Optional[str] = Field(None, description="Name of the function that was called")

class FunctionDefinition(BaseModel):
    """Definition of a function tool."""
    name: str = Field(description="The name of the function")
    description: str = Field(description="A description of what the function does")
    parameters: Dict[str, Any] = Field(description="The parameters schema for the function")

class Tool(BaseModel):
    """A tool that can be used by the LLM."""
    type: Literal["function"] = Field(description="The type of tool (currently only 'function' is supported)")
    function: FunctionDefinition = Field(description="The function definition for this tool")

class ChatRequest(BaseModel):
    message: str = Field(description="The message to process")
    stream: Optional[bool] = Field(
        default=False,
        description="Whether to stream the response using Server-Sent Events (SSE). Compatible with OpenAI and Anthropic streaming format."
    )
    provider: Optional[Literal["claude", "openai", "gemini", "mistral"]] = Field(
        default=None,
        description="The LLM provider to use. If not specified, auto-selection will be used"
    )
    activity: Optional[str] = Field(
        default="generic",
        description="The activity context for tool selection"
    )
    persona_id: Optional[str] = Field(
        default="default",
        description="The persona ID to use for this chat"
    )
    model: Optional[str] = Field(
        default=None,
        description="Specific model to use (e.g. claude-3-haiku-20240307, gpt-4o-mini)"
    )
    auto_select_model: Optional[bool] = Field(
        default=False,
        description="Whether to use automatic model selection when model is not specified"
    )
    force_provider: Optional[bool] = Field(
        default=True,
        description="Force the use of specified provider/model without intelligent switching"
    )
    priority: Optional[Literal["speed", "quality", "balanced", "vr", "cost"]] = Field(
        default=None,
        description="Model selection priority: speed, quality, balanced, vr, cost"
    )
    context_type: Optional[Literal["greeting", "conversation", "technical", "creative", "vr", "emergency", "multimodal"]] = Field(
        default=None,
        description="Context type for intelligent model selection"
    )
    max_response_time_ms: Optional[int] = Field(
        default=None,
        description="Maximum acceptable response time in milliseconds"
    )
    required_capabilities: Optional[List[str]] = Field(
        default=None,
        description="Required model capabilities (e.g. ['vision', 'tool_calling'])"
    )
    force_model_override: Optional[bool] = Field(
        default=False,
        description="Force model selection even if user has preferences set"
    )
    enable_fallback: Optional[bool] = Field(
        default=True,
        description="Enable automatic fallback to other providers on failure"
    )

class ChatResponse(BaseModel):
    response: str = Field(description="The generated chat response")
    provider: str = Field(description="The LLM provider that generated the response")
    model: str = Field(description="The specific model that generated the response")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage information")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    reasoning: Optional[str] = Field(None, description="Model selection reasoning")
    fallback_used: Optional[bool] = Field(None, description="Whether fallback was used")

class ModelSelectionRequest(BaseModel):
    """Request for model selection without generating a response"""
    message: str = Field(description="The message to analyze for model selection")
    provider: Optional[Literal["claude", "openai", "gemini", "mistral"]] = Field(
        default=None,
        description="Preferred LLM provider"
    )
    priority: Optional[Literal["speed", "quality", "balanced", "vr", "cost"]] = Field(
        default="balanced",
        description="Model selection priority"
    )
    context_type: Optional[Literal["greeting", "conversation", "technical", "creative", "vr", "emergency", "multimodal"]] = Field(
        default=None,
        description="Context type for intelligent model selection"
    )
    max_response_time_ms: Optional[int] = Field(
        default=None,
        description="Maximum acceptable response time in milliseconds"
    )
    required_capabilities: Optional[List[str]] = Field(
        default=None,
        description="Required model capabilities"
    )

class ModelRecommendationResponse(BaseModel):
    """Response containing model recommendation"""
    recommended_model: str = Field(description="Recommended model ID")
    provider: str = Field(description="Provider for the recommended model")
    confidence: float = Field(description="Confidence score (0.0-1.0)")
    reasoning: str = Field(description="Human-readable reasoning for the selection")
    alternatives: List[Dict[str, Any]] = Field(description="Alternative model options")
    estimated_cost: float = Field(description="Estimated cost for the request")
    estimated_response_time_ms: int = Field(description="Estimated response time")
    model_info: Dict[str, Any] = Field(description="Detailed model information")