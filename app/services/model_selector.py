"""
Dynamic model selection service for optimal performance

TODO: This is Tech Debt, remove
This service uses outdated string-based context detection and duplicates
functionality better handled by intelligent_router.py with LLM-based classification.
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class ModelPriority(Enum):
    """Model selection priorities"""
    SPEED = "speed"           # Fastest response time
    QUALITY = "quality"       # Best response quality  
    BALANCED = "balanced"     # Balance of speed/quality
    VR_OPTIMIZED = "vr"      # VR/AR specific optimization

class ContextType(Enum):
    """Context types for model selection"""
    GREETING = "greeting"
    CONVERSATION = "conversation"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    VR_INTERACTION = "vr"
    EMERGENCY = "emergency"

class ModelSelector:
    """Intelligent model selection based on context and performance"""
    
    def __init__(self):
        # Model performance data from our testing
        self.model_performance = {
            "claude-3-haiku-20240307": {
                "name": "Claude 3 Haiku",
                "avg_ttft_ms": 633,
                "tokens_per_sec": 7.5,
                "quality_score": 7,
                "cost_factor": 1.0,
                "vr_suitable": True,
                "best_for": ["speed", "vr", "simple_queries"]
            },
            "claude-3-sonnet-20240229": {
                "name": "Claude 3 Sonnet", 
                "avg_ttft_ms": 999,
                "tokens_per_sec": 7.9,
                "quality_score": 8,
                "cost_factor": 3.0,
                "vr_suitable": False,
                "best_for": ["balanced", "general"]
            },
            "claude-3-5-haiku-20241022": {
                "name": "Claude 3.5 Haiku",
                "avg_ttft_ms": 1106,
                "tokens_per_sec": 7.1,
                "quality_score": 7.5,
                "cost_factor": 1.0,
                "vr_suitable": False,
                "best_for": ["newer_features", "simple_queries"]
            },
            "claude-3-5-sonnet-20241022": {
                "name": "Claude 3.5 Sonnet",
                "avg_ttft_ms": 1575,
                "tokens_per_sec": 2.4,
                "quality_score": 9,
                "cost_factor": 3.0,
                "vr_suitable": False,
                "best_for": ["quality", "complex_reasoning", "creative"]
            }
        }
        
        # Context-based model preferences
        self.context_preferences = {
            ContextType.GREETING: {
                "primary": "claude-3-haiku-20240307",
                "fallback": "claude-3-sonnet-20240229",
                "reason": "Greetings need fast response, simple content"
            },
            ContextType.VR_INTERACTION: {
                "primary": "claude-3-haiku-20240307", 
                "fallback": "claude-3-sonnet-20240229",
                "reason": "VR requires sub-700ms response times"
            },
            ContextType.CONVERSATION: {
                "primary": "claude-3-sonnet-20240229",
                "fallback": "claude-3-haiku-20240307", 
                "reason": "Balanced quality/speed for normal chat"
            },
            ContextType.TECHNICAL: {
                "primary": "claude-3-5-sonnet-20241022",
                "fallback": "claude-3-sonnet-20240229",
                "reason": "Technical queries need highest reasoning quality"
            },
            ContextType.CREATIVE: {
                "primary": "claude-3-5-sonnet-20241022",
                "fallback": "claude-3-sonnet-20240229", 
                "reason": "Creative tasks benefit from advanced capabilities"
            },
            ContextType.EMERGENCY: {
                "primary": "claude-3-haiku-20240307",
                "fallback": "claude-3-5-haiku-20241022",
                "reason": "Emergency situations need fastest possible response"
            }
        }
        
        # User preference overrides
        self.user_preferences: Dict[str, Dict] = {}
        
        # Model performance tracking
        self.performance_history: Dict[str, List] = {}
        
    def select_model(
        self, 
        message: str,
        context_type: Optional[ContextType] = None,
        priority: Optional[ModelPriority] = None,
        user_id: Optional[str] = None,
        activity: Optional[str] = None,
        max_response_time_ms: Optional[int] = None
    ) -> str:
        """
        Select the optimal model based on context and requirements
        
        Args:
            message: The user message content
            context_type: Type of interaction context
            priority: Performance priority (speed/quality/balanced)
            user_id: User identifier for personalized selection
            activity: Activity context (e.g., "vr", "chat", "technical")
            max_response_time_ms: Maximum acceptable response time
            
        Returns:
            Model ID string
        """
        
        # 1. Check user preferences first
        if user_id and user_id in self.user_preferences:
            user_pref = self.user_preferences[user_id]
            if "preferred_model" in user_pref:
                logger.info(f"Using user {user_id} preferred model: {user_pref['preferred_model']}")
                return user_pref["preferred_model"]
        
        # 2. Auto-detect context if not provided
        if context_type is None:
            context_type = self._detect_context(message, activity)
        
        # 3. Handle max response time requirement
        if max_response_time_ms:
            suitable_models = [
                model_id for model_id, perf in self.model_performance.items()
                if perf["avg_ttft_ms"] <= max_response_time_ms
            ]
            if suitable_models:
                # Pick fastest among suitable models
                selected = min(suitable_models, 
                             key=lambda m: self.model_performance[m]["avg_ttft_ms"])
                logger.info(f"Selected {selected} for max response time {max_response_time_ms}ms")
                return selected
            else:
                logger.warning(f"No models meet {max_response_time_ms}ms requirement, using fastest")
                return self._get_fastest_model()
        
        # 4. Handle priority-based selection
        if priority:
            selected = self._select_by_priority(priority)
            logger.info(f"Selected {selected} for priority {priority.value}")
            return selected
            
        # 5. Use context-based selection
        context_pref = self.context_preferences.get(context_type)
        if context_pref:
            selected = context_pref["primary"]
            logger.info(f"Selected {selected} for context {context_type.value}: {context_pref['reason']}")
            return selected
        
        # 6. Default fallback
        default = "claude-3-haiku-20240307"  # Fastest model as default
        logger.info(f"Using default model: {default}")
        return default
    
    def _detect_context(self, message: str, activity: Optional[str] = None) -> ContextType:
        """
        Default context detection - always returns CONVERSATION.
        
        String-based context detection is unreliable and language-dependent.
        For proper context classification, use the intelligent_router from chat service
        which provides LLM-based classification with function calling.
        
        Args:
            message: User message (not used in current implementation)
            activity: Activity context (not used in current implementation)
            
        Returns:
            Always returns ContextType.CONVERSATION for safe defaults
        """
        # Always default to conversation - no string matching
        # TODO: Integrate with app.services.chat.intelligent_router for LLM-based classification
        return ContextType.CONVERSATION
    
    def _select_by_priority(self, priority: ModelPriority) -> str:
        """Select model based on priority"""
        if priority == ModelPriority.SPEED or priority == ModelPriority.VR_OPTIMIZED:
            return self._get_fastest_model()
        elif priority == ModelPriority.QUALITY:
            return self._get_highest_quality_model()
        elif priority == ModelPriority.BALANCED:
            return self._get_balanced_model()
        else:
            return "claude-3-haiku-20240307"  # Default
    
    def _get_fastest_model(self) -> str:
        """Get the fastest responding model"""
        return min(self.model_performance.keys(), 
                  key=lambda m: self.model_performance[m]["avg_ttft_ms"])
    
    def _get_highest_quality_model(self) -> str:
        """Get the highest quality model"""
        return max(self.model_performance.keys(),
                  key=lambda m: self.model_performance[m]["quality_score"])
    
    def _get_balanced_model(self) -> str:
        """Get the best balanced model (speed/quality ratio)"""
        # Calculate speed/quality score (higher is better)
        def balance_score(model_id: str) -> float:
            perf = self.model_performance[model_id]
            # Invert TTFT (lower is better) and combine with quality
            speed_score = 2000 / perf["avg_ttft_ms"]  # Higher is better
            quality_score = perf["quality_score"]
            return speed_score + quality_score
        
        return max(self.model_performance.keys(), key=balance_score)
    
    def set_user_preference(
        self, 
        user_id: str, 
        preferred_model: str,
        priority: Optional[ModelPriority] = None
    ):
        """Set user's preferred model"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
            
        self.user_preferences[user_id]["preferred_model"] = preferred_model
        if priority:
            self.user_preferences[user_id]["priority"] = priority
            
        logger.info(f"Set user {user_id} preference to {preferred_model}")
    
    def get_model_info(self, model_id: str) -> Dict:
        """Get detailed information about a model"""
        return self.model_performance.get(model_id, {})
    
    def list_available_models(self) -> List[Dict]:
        """List all available models with their performance characteristics"""
        return [
            {
                "model_id": model_id,
                "name": perf["name"],
                "avg_ttft_ms": perf["avg_ttft_ms"],
                "tokens_per_sec": perf["tokens_per_sec"],
                "quality_score": perf["quality_score"],
                "vr_suitable": perf["vr_suitable"],
                "best_for": perf["best_for"]
            }
            for model_id, perf in self.model_performance.items()
        ]
    
    def track_performance(self, model_id: str, ttft_ms: float, quality_rating: Optional[int] = None):
        """Track actual performance for model optimization"""
        if model_id not in self.performance_history:
            self.performance_history[model_id] = []
            
        record = {
            "timestamp": datetime.utcnow(),
            "ttft_ms": ttft_ms,
            "quality_rating": quality_rating
        }
        
        self.performance_history[model_id].append(record)
        
        # Keep only last 100 records per model
        self.performance_history[model_id] = self.performance_history[model_id][-100:]
        
        # Update model performance if we have enough data
        if len(self.performance_history[model_id]) >= 10:
            recent_avg = sum(r["ttft_ms"] for r in self.performance_history[model_id][-10:]) / 10
            self.model_performance[model_id]["avg_ttft_ms"] = recent_avg
            logger.debug(f"Updated {model_id} average TTFT to {recent_avg:.0f}ms")
    
    def recommend_model_for_vr(self) -> Dict:
        """Get specific recommendation for VR applications"""
        vr_models = [
            (model_id, perf) for model_id, perf in self.model_performance.items()
            if perf["vr_suitable"]
        ]
        
        if vr_models:
            # Get fastest VR-suitable model
            best_model_id, best_perf = min(vr_models, key=lambda x: x[1]["avg_ttft_ms"])
            
            return {
                "recommended_model": best_model_id,
                "model_name": best_perf["name"],
                "expected_ttft_ms": best_perf["avg_ttft_ms"],
                "vr_suitable": True,
                "confidence": "high" if best_perf["avg_ttft_ms"] < 700 else "medium"
            }
        else:
            # No VR-suitable models, recommend fastest
            fastest_id = self._get_fastest_model()
            fastest_perf = self.model_performance[fastest_id]
            
            return {
                "recommended_model": fastest_id,
                "model_name": fastest_perf["name"], 
                "expected_ttft_ms": fastest_perf["avg_ttft_ms"],
                "vr_suitable": False,
                "confidence": "low",
                "note": "No models consistently achieve <500ms. Consider response pre-generation."
            }

# Global model selector instance
model_selector = ModelSelector()