"""
Intelligent Chat Router using LLM Function Calling

Uses LLM function calling to quickly classify incoming messages and route them
to the appropriate endpoint (fast path for simple dialog, orchestrated for complex).
"""
import logging
import time
from typing import Dict, Any, Optional, Literal
from enum import Enum
import json

from app.services.llm.multi_provider_selector import multi_provider_selector
from app.services.llm import LLMProvider

logger = logging.getLogger(__name__)


class ChatComplexity(str, Enum):
    """Classification of chat message complexity"""
    SIMPLE = "simple"       # Direct dialog, greetings, simple Q&A
    MODERATE = "moderate"   # Single domain, some analysis needed
    COMPLEX = "complex"     # Multi-domain, orchestration needed


class IntelligentRouter:
    """
    Routes chat messages to appropriate handlers based on complexity analysis.
    Uses LLM function calling for fast, accurate classification.
    """
    
    def __init__(self):
        self.classification_cache: Dict[str, ChatComplexity] = {}
        self._routing_metrics = {
            "simple": 0,
            "moderate": 0, 
            "complex": 0,
            "total_classifications": 0,
            "avg_classification_time_ms": 0
        }
    
    async def classify_message(
        self, 
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify message complexity using LLM function calling.
        
        Returns:
            Dict with:
            - complexity: ChatComplexity enum value
            - reasoning: Why this classification was chosen
            - suggested_endpoint: Which endpoint to use
            - estimated_response_time: Expected response time
        """
        start_time = time.time()
        
        # Define the classification function for the LLM
        classification_function = {
            "name": "classify_chat_complexity",
            "description": "Classify the complexity of a chat message to determine optimal routing",
            "parameters": {
                "type": "object",
                "properties": {
                    "complexity": {
                        "type": "string",
                        "enum": ["simple", "moderate", "complex"],
                        "description": "Complexity level of the message"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why this complexity was chosen"
                    },
                    "requires_tools": {
                        "type": "boolean",
                        "description": "Whether this message likely needs tool usage"
                    },
                    "requires_multiagent": {
                        "type": "boolean",
                        "description": "Whether this needs multiple specialist agents"
                    },
                    "domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Which domains/topics are involved"
                    }
                },
                "required": ["complexity", "reasoning", "requires_tools", "requires_multiagent", "domains"]
            }
        }
        
        # Create classification prompt
        system_prompt = """You are a chat complexity classifier. Analyze messages and determine:

SIMPLE (use for ~70% of messages):
- Greetings, farewells, small talk
- Simple questions with straightforward answers
- Basic information requests
- Casual conversation
- Single-turn responses

MODERATE (use for ~20% of messages):
- Questions requiring some research or analysis
- Requests needing tool usage (search, calculations)
- Technical questions in a single domain
- Multi-step but straightforward tasks

COMPLEX (use for ~10% of messages):
- Multi-domain questions requiring expertise
- Creative tasks (worldbuilding, storytelling)
- Complex problem-solving needing multiple perspectives
- Requests explicitly asking for multiple viewpoints
- Tasks requiring coordination of multiple specialists

Be biased towards SIMPLE for conversational messages."""
        
        # Prepare messages for classification
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Classify this message: {message}"}
        ]
        
        try:
            # Use fastest available model for classification (e.g., Claude Haiku)
            provider = LLMProvider.ANTHROPIC
            model = "claude-3-haiku-20240307"  # Fastest model for classification
            
            # Make the classification call with function
            response = await multi_provider_selector.chat_completion(
                messages=messages,
                model=model,
                provider=provider,
                tools=[{"type": "function", "function": classification_function}],
                tool_choice={"type": "function", "function": {"name": "classify_chat_complexity"}},
                temperature=0.3,  # Low temperature for consistent classification
                max_tokens=200
            )
            
            # Parse function call response
            if response.get("tool_calls"):
                function_args = json.loads(response["tool_calls"][0]["function"]["arguments"])
                complexity = ChatComplexity(function_args["complexity"])
                
                # Update metrics
                self._routing_metrics[complexity.value] += 1
                self._routing_metrics["total_classifications"] += 1
                classification_time = (time.time() - start_time) * 1000
                
                # Update rolling average
                avg = self._routing_metrics["avg_classification_time_ms"]
                total = self._routing_metrics["total_classifications"]
                self._routing_metrics["avg_classification_time_ms"] = (
                    (avg * (total - 1) + classification_time) / total
                )
                
                # Determine endpoint and estimated time
                routing_decision = self._determine_routing(
                    complexity, 
                    function_args.get("requires_tools", False),
                    function_args.get("requires_multiagent", False)
                )
                
                logger.info(
                    f"Classified message as {complexity.value} in {classification_time:.0f}ms - "
                    f"routing to {routing_decision['endpoint']}"
                )
                
                return {
                    "complexity": complexity,
                    "reasoning": function_args.get("reasoning", ""),
                    "domains": function_args.get("domains", []),
                    "requires_tools": function_args.get("requires_tools", False),
                    "requires_multiagent": function_args.get("requires_multiagent", False),
                    **routing_decision,
                    "classification_time_ms": classification_time
                }
                
            else:
                # Fallback if no function call (shouldn't happen with tool_choice)
                logger.warning("No function call in response, defaulting to simple")
                return self._default_simple_routing()
                
        except Exception as e:
            logger.error(f"Classification error: {e}, defaulting to simple")
            return self._default_simple_routing()
    
    def _determine_routing(
        self, 
        complexity: ChatComplexity,
        requires_tools: bool,
        requires_multiagent: bool
    ) -> Dict[str, Any]:
        """Determine the best endpoint and estimated response time"""
        
        if complexity == ChatComplexity.SIMPLE and not requires_tools:
            return {
                "suggested_endpoint": "/chat/direct",
                "estimated_response_time": "~1s",
                "use_streaming": True
            }
        elif complexity == ChatComplexity.MODERATE or requires_tools:
            return {
                "suggested_endpoint": "/chat/mcp-agent-hot",
                "estimated_response_time": "~2-3s",
                "use_streaming": True
            }
        else:  # COMPLEX or requires_multiagent
            return {
                "suggested_endpoint": "/chat/mcp-agent",
                "estimated_response_time": "~3-5s",
                "use_streaming": True
            }
    
    def _default_simple_routing(self) -> Dict[str, Any]:
        """Default routing for when classification fails"""
        return {
            "complexity": ChatComplexity.SIMPLE,
            "reasoning": "Default fallback classification",
            "domains": [],
            "requires_tools": False,
            "requires_multiagent": False,
            "suggested_endpoint": "/chat/direct",
            "estimated_response_time": "~1s",
            "use_streaming": True,
            "classification_time_ms": 0
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get routing metrics for monitoring"""
        total = self._routing_metrics["total_classifications"]
        if total == 0:
            return self._routing_metrics
            
        return {
            **self._routing_metrics,
            "distribution": {
                "simple": f"{(self._routing_metrics['simple'] / total * 100):.1f}%",
                "moderate": f"{(self._routing_metrics['moderate'] / total * 100):.1f}%",
                "complex": f"{(self._routing_metrics['complex'] / total * 100):.1f}%"
            }
        }


# Global router instance
intelligent_router = IntelligentRouter()