"""
Unit tests for the model selector service.
Tests intelligent model selection based on context and performance.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.services.model_selector import (
    ModelSelector, ModelPriority, ContextType
)


class TestModelSelector:
    """Test the ModelSelector service"""
    
    @pytest.fixture
    def selector(self):
        """Create a fresh ModelSelector instance"""
        return ModelSelector()
    
    def test_init_default_values(self, selector):
        """Test ModelSelector initializes with correct defaults"""
        # Verify model performance data
        assert len(selector.model_performance) == 4
        assert "claude-3-haiku-20240307" in selector.model_performance
        assert "claude-3-5-sonnet-20241022" in selector.model_performance
        
        # Verify context preferences
        assert len(selector.context_preferences) == 6
        assert ContextType.GREETING in selector.context_preferences
        assert ContextType.VR_INTERACTION in selector.context_preferences
        
        # Verify empty user preferences
        assert selector.user_preferences == {}
        assert selector.performance_history == {}
    
    def test_select_model_with_user_preference(self, selector):
        """Test model selection honors user preferences"""
        # Set user preference
        selector.set_user_preference("user123", "claude-3-5-sonnet-20241022")
        
        # User preference should override everything else
        selected = selector.select_model(
            message="Hi there",
            context_type=ContextType.GREETING,  # Would normally use haiku
            user_id="user123"
        )
        
        assert selected == "claude-3-5-sonnet-20241022"
    
    def test_select_model_by_context_type(self, selector):
        """Test model selection based on context type"""
        # Test greeting context
        selected = selector.select_model(
            message="Hello!",
            context_type=ContextType.GREETING
        )
        assert selected == "claude-3-haiku-20240307"
        
        # Test technical context
        selected = selector.select_model(
            message="How do I implement a binary search?",
            context_type=ContextType.TECHNICAL
        )
        assert selected == "claude-3-5-sonnet-20241022"
        
        # Test VR context
        selected = selector.select_model(
            message="Show me that object",
            context_type=ContextType.VR_INTERACTION
        )
        assert selected == "claude-3-haiku-20240307"
    
    def test_select_model_by_priority(self, selector):
        """Test model selection based on priority"""
        # Test speed priority
        selected = selector.select_model(
            message="Quick response needed",
            priority=ModelPriority.SPEED
        )
        assert selected == "claude-3-haiku-20240307"  # Fastest model
        
        # Test quality priority
        selected = selector.select_model(
            message="Complex analysis needed",
            priority=ModelPriority.QUALITY
        )
        assert selected == "claude-3-5-sonnet-20241022"  # Highest quality
        
        # Test balanced priority
        selected = selector.select_model(
            message="General conversation",
            priority=ModelPriority.BALANCED
        )
        # Should select based on balance calculation
        assert selected in selector.model_performance
    
    def test_select_model_with_max_response_time(self, selector):
        """Test model selection with response time constraint"""
        # Strict constraint - only haiku meets it
        selected = selector.select_model(
            message="Need fast response",
            max_response_time_ms=700
        )
        assert selected == "claude-3-haiku-20240307"
        
        # Relaxed constraint - multiple models meet it
        selected = selector.select_model(
            message="Normal speed ok",
            max_response_time_ms=1200
        )
        assert selector.model_performance[selected]["avg_ttft_ms"] <= 1200
        
        # Impossible constraint - should use fastest
        selected = selector.select_model(
            message="Impossible speed",
            max_response_time_ms=100
        )
        assert selected == "claude-3-haiku-20240307"
    
    def test_detect_context_from_message(self, selector):
        """Test automatic context detection from message"""
        # Test greeting detection
        assert selector._detect_context("Hi there") == ContextType.GREETING
        assert selector._detect_context("Hello!") == ContextType.GREETING
        assert selector._detect_context("Good morning") == ContextType.GREETING
        
        # Test technical detection
        assert selector._detect_context("Debug this code for me") == ContextType.TECHNICAL
        assert selector._detect_context("How do I use this API?") == ContextType.TECHNICAL
        
        # Test creative detection
        assert selector._detect_context("Write a story about dragons") == ContextType.CREATIVE
        assert selector._detect_context("Design a logo for me") == ContextType.CREATIVE
        
        # Test emergency detection
        assert selector._detect_context("URGENT: Need help!") == ContextType.EMERGENCY
        assert selector._detect_context("Critical issue asap") == ContextType.EMERGENCY
        
        # Test default conversation
        assert selector._detect_context("What's the weather like?") == ContextType.CONVERSATION
    
    def test_detect_context_from_activity(self, selector):
        """Test context detection from activity parameter"""
        # VR activities
        assert selector._detect_context("Show me", activity="vr") == ContextType.VR_INTERACTION
        assert selector._detect_context("Look at that", activity="ar") == ContextType.VR_INTERACTION
        
        # Technical activities
        assert selector._detect_context("Help me", activity="coding") == ContextType.TECHNICAL
        assert selector._detect_context("Explain this", activity="programming") == ContextType.TECHNICAL
        
        # Creative activities
        assert selector._detect_context("Make something", activity="creative") == ContextType.CREATIVE
        assert selector._detect_context("Create this", activity="art") == ContextType.CREATIVE
    
    def test_get_fastest_model(self, selector):
        """Test getting the fastest model"""
        fastest = selector._get_fastest_model()
        assert fastest == "claude-3-haiku-20240307"
        
        # Verify it's actually the fastest
        fastest_ttft = selector.model_performance[fastest]["avg_ttft_ms"]
        for model_id, perf in selector.model_performance.items():
            assert perf["avg_ttft_ms"] >= fastest_ttft
    
    def test_get_highest_quality_model(self, selector):
        """Test getting the highest quality model"""
        best = selector._get_highest_quality_model()
        assert best == "claude-3-5-sonnet-20241022"
        
        # Verify it's actually the highest quality
        best_quality = selector.model_performance[best]["quality_score"]
        for model_id, perf in selector.model_performance.items():
            assert perf["quality_score"] <= best_quality
    
    def test_get_balanced_model(self, selector):
        """Test getting the best balanced model"""
        balanced = selector._get_balanced_model()
        
        # Should return a valid model
        assert balanced in selector.model_performance
        
        # Calculate and verify balance score
        def balance_score(model_id):
            perf = selector.model_performance[model_id]
            speed_score = 2000 / perf["avg_ttft_ms"]
            quality_score = perf["quality_score"]
            return speed_score + quality_score
        
        balanced_score = balance_score(balanced)
        for model_id in selector.model_performance:
            assert balance_score(model_id) <= balanced_score
    
    def test_set_and_get_user_preference(self, selector):
        """Test setting and retrieving user preferences"""
        # Set preference
        selector.set_user_preference(
            "user456",
            "claude-3-sonnet-20240229",
            priority=ModelPriority.BALANCED
        )
        
        # Verify stored correctly
        assert "user456" in selector.user_preferences
        assert selector.user_preferences["user456"]["preferred_model"] == "claude-3-sonnet-20240229"
        assert selector.user_preferences["user456"]["priority"] == ModelPriority.BALANCED
        
        # Test model selection uses preference
        selected = selector.select_model("Any message", user_id="user456")
        assert selected == "claude-3-sonnet-20240229"
    
    def test_get_model_info(self, selector):
        """Test getting model information"""
        # Valid model
        info = selector.get_model_info("claude-3-haiku-20240307")
        assert info["name"] == "Claude 3 Haiku"
        assert info["avg_ttft_ms"] == 633
        assert info["vr_suitable"] is True
        
        # Invalid model
        info = selector.get_model_info("invalid-model")
        assert info == {}
    
    def test_list_available_models(self, selector):
        """Test listing all available models"""
        models = selector.list_available_models()
        
        assert len(models) == 4
        
        # Check structure
        for model in models:
            assert "model_id" in model
            assert "name" in model
            assert "avg_ttft_ms" in model
            assert "tokens_per_sec" in model
            assert "quality_score" in model
            assert "vr_suitable" in model
            assert "best_for" in model
    
    def test_track_performance(self, selector):
        """Test performance tracking updates model stats"""
        model_id = "claude-3-haiku-20240307"
        original_ttft = selector.model_performance[model_id]["avg_ttft_ms"]
        
        # Track 10 performances with faster times
        for i in range(10):
            selector.track_performance(model_id, 500.0, quality_rating=8)
        
        # Should update average
        updated_ttft = selector.model_performance[model_id]["avg_ttft_ms"]
        assert updated_ttft == 500.0
        assert updated_ttft < original_ttft
        
        # Check history is maintained
        assert len(selector.performance_history[model_id]) == 10
        assert all(r["ttft_ms"] == 500.0 for r in selector.performance_history[model_id])
    
    def test_track_performance_limits_history(self, selector):
        """Test performance history is limited to 100 records"""
        model_id = "claude-3-haiku-20240307"
        
        # Track 150 performances
        for i in range(150):
            selector.track_performance(model_id, float(i))
        
        # Should only keep last 100
        assert len(selector.performance_history[model_id]) == 100
        
        # Verify it kept the most recent ones
        assert selector.performance_history[model_id][0]["ttft_ms"] == 50.0
        assert selector.performance_history[model_id][-1]["ttft_ms"] == 149.0
    
    def test_recommend_model_for_vr(self, selector):
        """Test VR-specific model recommendation"""
        recommendation = selector.recommend_model_for_vr()
        
        assert recommendation["recommended_model"] == "claude-3-haiku-20240307"
        assert recommendation["model_name"] == "Claude 3 Haiku"
        assert recommendation["vr_suitable"] is True
        assert recommendation["confidence"] == "high"  # Because <700ms
        assert recommendation["expected_ttft_ms"] == 633
    
    def test_recommend_model_for_vr_no_suitable(self, selector):
        """Test VR recommendation when no suitable models"""
        # Make all models non-VR suitable
        for model_id in selector.model_performance:
            selector.model_performance[model_id]["vr_suitable"] = False
        
        recommendation = selector.recommend_model_for_vr()
        
        # Should recommend fastest model with low confidence
        assert recommendation["recommended_model"] == "claude-3-haiku-20240307"
        assert recommendation["vr_suitable"] is False
        assert recommendation["confidence"] == "low"
        assert "note" in recommendation
    
    def test_model_selection_integration(self, selector):
        """Test complete model selection flow"""
        # Scenario 1: VR user needs fast response
        selected = selector.select_model(
            message="Show me that building",
            activity="vr",
            priority=ModelPriority.VR_OPTIMIZED
        )
        assert selected == "claude-3-haiku-20240307"
        
        # Scenario 2: Developer needs help with complex code
        selected = selector.select_model(
            message="Debug this recursive algorithm implementation",
            priority=ModelPriority.QUALITY
        )
        assert selected == "claude-3-5-sonnet-20241022"
        
        # Scenario 3: Regular chat with time constraint
        selected = selector.select_model(
            message="Tell me about the weather",
            max_response_time_ms=1000
        )
        assert selector.model_performance[selected]["avg_ttft_ms"] <= 1000
    
    @patch('app.services.model_selector.logger')
    def test_logging(self, mock_logger, selector):
        """Test that appropriate logging occurs"""
        # Test user preference logging
        selector.set_user_preference("user789", "claude-3-haiku-20240307")
        mock_logger.info.assert_called()
        
        # Test model selection logging
        selector.select_model(
            message="Test message",
            context_type=ContextType.TECHNICAL
        )
        # Should log the selection reason
        assert mock_logger.info.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])