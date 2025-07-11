"""
Multi-provider model selector for optimal LLM selection
"""
import logging
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from .base import LLMProvider, ModelInfo, ModelCapability
from .registry import get_registry, LLMProviderRegistry

logger = logging.getLogger(__name__)

class ModelPriority(Enum):
    """Model selection priorities"""
    SPEED = "speed"           # Fastest response time
    QUALITY = "quality"       # Best response quality  
    BALANCED = "balanced"     # Balance of speed/quality
    VR_OPTIMIZED = "vr"      # VR/AR specific optimization
    COST_EFFICIENT = "cost"   # Lowest cost per token

class ContextType(Enum):
    """Context types for model selection"""
    GREETING = "greeting"
    CONVERSATION = "conversation"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    VR_INTERACTION = "vr"
    EMERGENCY = "emergency"
    MULTIMODAL = "multimodal"

@dataclass
class ModelRecommendation:
    """Model recommendation with reasoning"""
    model_id: str
    provider: LLMProvider
    model_info: ModelInfo
    confidence: float  # 0.0-1.0
    reasoning: str
    fallback_models: List[str]
    estimated_cost: float
    estimated_response_time_ms: int

class MultiProviderModelSelector:
    """Enhanced model selector supporting multiple LLM providers"""
    
    def __init__(self):
        self.registry: Optional[LLMProviderRegistry] = None
        self.user_preferences: Dict[str, Dict] = {}
        self.performance_history: Dict[str, List] = {}
        
        # Context-based preferences - now provider-agnostic
        self.context_preferences = {
            ContextType.GREETING: {
                "priority": ModelPriority.SPEED,
                "max_response_time_ms": 500,
                "preferred_capabilities": [ModelCapability.CHAT],
                "reason": "Greetings need fast response, simple content"
            },
            ContextType.VR_INTERACTION: {
                "priority": ModelPriority.VR_OPTIMIZED,
                "max_response_time_ms": 700,
                "preferred_capabilities": [ModelCapability.CHAT, ModelCapability.STREAMING],
                "reason": "VR requires sub-700ms response times"
            },
            ContextType.CONVERSATION: {
                "priority": ModelPriority.BALANCED,
                "max_response_time_ms": 2000,
                "preferred_capabilities": [ModelCapability.CHAT, ModelCapability.STREAMING],
                "reason": "Balanced quality/speed for normal chat"
            },
            ContextType.TECHNICAL: {
                "priority": ModelPriority.QUALITY,
                "max_response_time_ms": 3000,
                "preferred_capabilities": [ModelCapability.CHAT, ModelCapability.TOOL_CALLING, ModelCapability.CODE_GENERATION],
                "reason": "Technical queries need highest reasoning quality"
            },
            ContextType.CREATIVE: {
                "priority": ModelPriority.QUALITY,
                "max_response_time_ms": 3000,
                "preferred_capabilities": [ModelCapability.CHAT, ModelCapability.LONG_CONTEXT],
                "reason": "Creative tasks benefit from advanced capabilities"
            },
            ContextType.EMERGENCY: {
                "priority": ModelPriority.SPEED,
                "max_response_time_ms": 300,
                "preferred_capabilities": [ModelCapability.CHAT],
                "reason": "Emergency situations need fastest possible response"
            },
            ContextType.MULTIMODAL: {
                "priority": ModelPriority.QUALITY,
                "max_response_time_ms": 5000,
                "preferred_capabilities": [ModelCapability.CHAT, ModelCapability.VISION, ModelCapability.MULTIMODAL],
                "reason": "Multimodal tasks require vision and advanced capabilities"
            }
        }
    
    async def initialize(self):
        """Initialize the selector with registry"""
        if not self.registry:
            self.registry = await get_registry()
    
    async def select_model(
        self,
        message: str,
        context_type: Optional[ContextType] = None,
        priority: Optional[ModelPriority] = None,
        user_id: Optional[str] = None,
        activity: Optional[str] = None,
        max_response_time_ms: Optional[int] = None,
        preferred_provider: Optional[LLMProvider] = None,
        required_capabilities: Optional[List[ModelCapability]] = None
    ) -> ModelRecommendation:
        """
        Select the optimal model based on context and requirements
        
        Args:
            message: The user message content
            context_type: Type of interaction context
            priority: Performance priority (speed/quality/balanced/cost)
            user_id: User identifier for personalized selection
            activity: Activity context (e.g., "vr", "chat", "technical")
            max_response_time_ms: Maximum acceptable response time
            preferred_provider: Preferred LLM provider
            required_capabilities: Required model capabilities
            
        Returns:
            ModelRecommendation with selected model and reasoning
        """
        
        await self.initialize()
        
        # 1. Check user preferences first
        if user_id and user_id in self.user_preferences:
            user_pref = self.user_preferences[user_id]
            if "preferred_model" in user_pref:
                model_info = await self.registry.get_model_info(user_pref["preferred_model"])
                if model_info:
                    logger.info(f"Using user {user_id} preferred model: {user_pref['preferred_model']}")
                    return ModelRecommendation(
                        model_id=user_pref["preferred_model"],
                        provider=model_info.provider,
                        model_info=model_info,
                        confidence=1.0,
                        reasoning=f"User {user_id} preference",
                        fallback_models=[],
                        estimated_cost=self._estimate_cost(model_info, message),
                        estimated_response_time_ms=model_info.avg_response_time_ms
                    )
        
        # 2. Auto-detect context if not provided
        if context_type is None:
            context_type = self._detect_context(message, activity)
        
        # 3. Get context requirements
        context_prefs = self.context_preferences.get(context_type, {})
        
        # 4. Override with explicit parameters
        if priority is None:
            priority = context_prefs.get("priority", ModelPriority.BALANCED)
        
        if max_response_time_ms is None:
            max_response_time_ms = context_prefs.get("max_response_time_ms", 2000)
        
        if required_capabilities is None:
            required_capabilities = context_prefs.get("preferred_capabilities", [ModelCapability.CHAT])
        
        # 5. Get all available models
        all_models = await self.registry.get_all_models()
        
        # 6. Filter models based on requirements
        candidate_models = []
        
        for provider, models in all_models.items():
            # Skip if preferred provider specified and this isn't it
            if preferred_provider and provider != preferred_provider:
                continue
            
            for model in models:
                # Check if model meets capability requirements
                if not all(cap in model.capabilities for cap in required_capabilities):
                    continue
                
                # Check response time requirement
                if model.avg_response_time_ms > max_response_time_ms:
                    continue
                
                # Check if provider is healthy
                health_status = self.registry.get_health_status(provider)
                if provider in health_status and health_status[provider].status != "healthy":
                    continue
                
                candidate_models.append(model)
        
        if not candidate_models:
            # Fallback: relax constraints and try again
            logger.warning(f"No models meet strict requirements for {context_type.value}, relaxing constraints")
            candidate_models = []
            
            for provider, models in all_models.items():
                for model in models:
                    if ModelCapability.CHAT in model.capabilities:
                        candidate_models.append(model)
        
        if not candidate_models:
            raise ValueError("No suitable models available")
        
        # 7. Score and rank models
        scored_models = []
        for model in candidate_models:
            score = self._calculate_model_score(model, priority, context_type, message)
            scored_models.append((score, model))
        
        # Sort by score (highest first)
        scored_models.sort(key=lambda x: x[0], reverse=True)
        
        # 8. Select best model
        best_score, best_model = scored_models[0]
        
        # 9. Get fallback models
        fallback_models = [model.id for _, model in scored_models[1:4]]  # Top 3 alternatives
        
        # 10. Build recommendation
        return ModelRecommendation(
            model_id=best_model.id,
            provider=best_model.provider,
            model_info=best_model,
            confidence=min(best_score, 1.0),
            reasoning=self._build_reasoning(best_model, priority, context_type, best_score),
            fallback_models=fallback_models,
            estimated_cost=self._estimate_cost(best_model, message),
            estimated_response_time_ms=best_model.avg_response_time_ms
        )
    
    def _detect_context(self, message: str, activity: Optional[str] = None) -> ContextType:
        """Auto-detect context type from message content and activity"""
        message_lower = message.lower()
        
        # Check activity first
        if activity:
            if activity in ["vr", "ar", "xr", "metaverse"]:
                return ContextType.VR_INTERACTION
            elif activity in ["technical", "coding", "programming"]:
                return ContextType.TECHNICAL
            elif activity in ["creative", "writing", "art"]:
                return ContextType.CREATIVE
        
        # Check for multimodal indicators
        multimodal_words = ["image", "picture", "photo", "visual", "see", "look", "show"]
        if any(word in message_lower for word in multimodal_words):
            return ContextType.MULTIMODAL
        
        # Analyze message content
        greeting_words = ["hi", "hello", "hey", "good morning", "good afternoon", "greetings"]
        if any(word in message_lower for word in greeting_words) and len(message.split()) <= 5:
            return ContextType.GREETING
            
        technical_words = ["code", "debug", "error", "function", "algorithm", "api", "database", "programming"]
        if any(word in message_lower for word in technical_words):
            return ContextType.TECHNICAL
            
        creative_words = ["write", "story", "poem", "creative", "imagine", "design", "art", "compose"]
        if any(word in message_lower for word in creative_words):
            return ContextType.CREATIVE
            
        emergency_words = ["urgent", "emergency", "critical", "help!", "asap", "immediately"]
        if any(word in message_lower for word in emergency_words):
            return ContextType.EMERGENCY
        
        # Default to conversation
        return ContextType.CONVERSATION
    
    def _calculate_model_score(self, model: ModelInfo, priority: ModelPriority, 
                             context_type: ContextType, message: str) -> float:
        """Calculate a score for model selection"""
        score = 0.0
        
        # Base score from model quality
        score += model.quality_score * 0.4
        
        # Speed score (invert response time)
        max_time = 3000  # 3 seconds as reference
        speed_score = max(0, (max_time - model.avg_response_time_ms) / max_time)
        score += speed_score * 0.3
        
        # Priority-based scoring
        if priority == ModelPriority.SPEED:
            score += model.speed_score * 0.5
        elif priority == ModelPriority.QUALITY:
            score += model.quality_score * 0.5
        elif priority == ModelPriority.COST_EFFICIENT:
            # Lower cost = higher score
            max_cost = 0.00006  # Reference cost per token
            cost_score = max(0, (max_cost - model.cost_per_input_token) / max_cost)
            score += cost_score * 0.5
        elif priority == ModelPriority.VR_OPTIMIZED:
            if model.avg_response_time_ms < 700:
                score += 0.5
            if ModelCapability.STREAMING in model.capabilities:
                score += 0.2
        
        # Context-specific bonuses
        if context_type == ContextType.TECHNICAL:
            if ModelCapability.CODE_GENERATION in model.capabilities:
                score += 0.2
            if ModelCapability.TOOL_CALLING in model.capabilities:
                score += 0.2
        elif context_type == ContextType.CREATIVE:
            if ModelCapability.LONG_CONTEXT in model.capabilities:
                score += 0.2
        elif context_type == ContextType.MULTIMODAL:
            if ModelCapability.VISION in model.capabilities:
                score += 0.5
            if ModelCapability.MULTIMODAL in model.capabilities:
                score += 0.3
        
        # Provider preference (slight bonus for proven providers)
        if model.provider == LLMProvider.CLAUDE:
            score += 0.1  # Slight bonus for Claude (proven track record)
        
        return score
    
    def _build_reasoning(self, model: ModelInfo, priority: ModelPriority, 
                        context_type: ContextType, score: float) -> str:
        """Build human-readable reasoning for model selection"""
        reasons = []
        
        reasons.append(f"Selected {model.name} from {model.provider.value}")
        reasons.append(f"Context: {context_type.value}, Priority: {priority.value}")
        reasons.append(f"Quality score: {model.quality_score:.1f}/1.0")
        reasons.append(f"Expected response time: {model.avg_response_time_ms}ms")
        
        if priority == ModelPriority.SPEED:
            reasons.append("Optimized for fastest response")
        elif priority == ModelPriority.QUALITY:
            reasons.append("Optimized for highest quality output")
        elif priority == ModelPriority.COST_EFFICIENT:
            reasons.append(f"Cost-efficient at ${model.cost_per_input_token:.6f}/token")
        elif priority == ModelPriority.VR_OPTIMIZED:
            if model.avg_response_time_ms < 700:
                reasons.append("Meets VR response time requirements")
        
        # Add capability highlights
        special_caps = [cap for cap in model.capabilities if cap not in [ModelCapability.CHAT, ModelCapability.STREAMING]]
        if special_caps:
            reasons.append(f"Capabilities: {', '.join(cap.value for cap in special_caps)}")
        
        return "; ".join(reasons)
    
    def _estimate_cost(self, model: ModelInfo, message: str) -> float:
        """Estimate cost for processing message"""
        # Rough token estimation: 1 token ≈ 4 characters
        input_tokens = len(message) // 4
        output_tokens = input_tokens * 0.5  # Assume 50% output ratio
        
        input_cost = input_tokens * model.cost_per_input_token
        output_cost = output_tokens * model.cost_per_output_token
        
        return input_cost + output_cost
    
    async def get_provider_recommendations(self, requirements: Dict[str, Any]) -> List[ModelRecommendation]:
        """Get recommendations from all providers based on requirements"""
        await self.initialize()
        
        context_type = requirements.get("context_type", ContextType.CONVERSATION)
        priority = requirements.get("priority", ModelPriority.BALANCED)
        message = requirements.get("message", "")
        max_response_time = requirements.get("max_response_time_ms", 2000)
        required_capabilities = requirements.get("required_capabilities", [ModelCapability.CHAT])
        
        recommendations = []
        
        # Get recommendations from each provider
        for provider in await self.registry.get_available_providers():
            try:
                rec = await self.select_model(
                    message=message,
                    context_type=context_type,
                    priority=priority,
                    max_response_time_ms=max_response_time,
                    preferred_provider=provider,
                    required_capabilities=required_capabilities
                )
                recommendations.append(rec)
            except Exception as e:
                logger.warning(f"Could not get recommendation from {provider.value}: {str(e)}")
        
        # Sort by confidence
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return recommendations
    
    def set_user_preference(self, user_id: str, preferred_model: str, 
                          preferred_provider: Optional[LLMProvider] = None):
        """Set user's model preferences"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        self.user_preferences[user_id]["preferred_model"] = preferred_model
        if preferred_provider:
            self.user_preferences[user_id]["preferred_provider"] = preferred_provider
        
        logger.info(f"Set user {user_id} preference to {preferred_model}")
    
    async def get_model_comparison(self, model_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple models across different criteria"""
        await self.initialize()
        
        models = []
        for model_id in model_ids:
            model_info = await self.registry.get_model_info(model_id)
            if model_info:
                models.append(model_info)
        
        if not models:
            return {"error": "No valid models found"}
        
        comparison = {
            "models": {},
            "best_for": {
                "speed": None,
                "quality": None,
                "cost": None,
                "overall": None
            },
            "summary": {}
        }
        
        for model in models:
            comparison["models"][model.id] = {
                "name": model.name,
                "provider": model.provider.value,
                "quality_score": model.quality_score,
                "speed_score": model.speed_score,
                "avg_response_time_ms": model.avg_response_time_ms,
                "cost_per_input_token": model.cost_per_input_token,
                "cost_per_output_token": model.cost_per_output_token,
                "capabilities": [cap.value for cap in model.capabilities],
                "context_window": model.context_window,
                "max_tokens": model.max_tokens
            }
        
        # Find best models for each criterion
        comparison["best_for"]["speed"] = min(models, key=lambda m: m.avg_response_time_ms).id
        comparison["best_for"]["quality"] = max(models, key=lambda m: m.quality_score).id
        comparison["best_for"]["cost"] = min(models, key=lambda m: m.cost_per_input_token).id
        
        # Calculate overall best (balanced score)
        best_overall = max(models, key=lambda m: (m.quality_score + m.speed_score) / 2)
        comparison["best_for"]["overall"] = best_overall.id
        
        return comparison

# Global multi-provider selector instance
multi_provider_selector = MultiProviderModelSelector()