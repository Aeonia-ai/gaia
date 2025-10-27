"""
Semantic MCP Router - Using LLM for Intelligent Routing

Instead of brittle string matching, use the LLM itself to understand intent
"""
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio

from anthropic import Anthropic
from pydantic import BaseModel

class RouteDecision(BaseModel):
    """LLM's routing decision"""
    route: str  # "direct_llm", "direct_mcp", "mcp_agent"
    confidence: float
    reasoning: str
    required_tools: List[str]
    is_multi_step: bool
    needs_state: bool
    estimated_complexity: int  # 1-10 scale

class ToolCapability(BaseModel):
    """What each tool can do"""
    name: str
    description: str
    examples: List[str]
    typical_use_cases: List[str]

class SemanticMCPRouter:
    """Use LLM to make intelligent routing decisions"""
    
    def __init__(self):
        self.anthropic = Anthropic()
        self.routing_model = "claude-3-haiku-20240307"  # Fast, cheap model for routing
        
        # Tool catalog with semantic descriptions
        self.tool_catalog = {
            "filesystem": ToolCapability(
                name="filesystem",
                description="Read, write, create, delete files and directories",
                examples=[
                    "List files in a directory",
                    "Read file contents", 
                    "Save data to a file",
                    "Create folder structure"
                ],
                typical_use_cases=[
                    "Code analysis",
                    "Data persistence",
                    "File manipulation"
                ]
            ),
            "github": ToolCapability(
                name="github",
                description="Interact with GitHub repositories, PRs, issues",
                examples=[
                    "List pull requests",
                    "Create issues",
                    "Review code changes",
                    "Check notifications"
                ],
                typical_use_cases=[
                    "Code review",
                    "Project management",
                    "Collaboration"
                ]
            ),
            "postgres": ToolCapability(
                name="postgres",
                description="Query and manage PostgreSQL databases",
                examples=[
                    "Run SQL queries",
                    "View table schemas",
                    "Insert/update data",
                    "Create migrations"
                ],
                typical_use_cases=[
                    "Data analysis",
                    "Database management",
                    "Reporting"
                ]
            ),
            "kubernetes": ToolCapability(
                name="kubernetes",
                description="Manage Kubernetes clusters and deployments",
                examples=[
                    "Check pod status",
                    "Scale deployments",
                    "View logs",
                    "Apply configurations"
                ],
                typical_use_cases=[
                    "DevOps",
                    "Container orchestration",
                    "Infrastructure management"
                ]
            )
        }
        
        # Build routing prompt
        self.routing_prompt = self._build_routing_prompt()
        
    def _build_routing_prompt(self) -> str:
        """Build the system prompt for routing decisions"""
        tool_descriptions = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in self.tool_catalog.items()
        ])
        
        return f"""You are a routing assistant that determines how to handle user requests.

Available tools:
{tool_descriptions}

Routing options:
1. "direct_llm" - Simple questions, no tools needed
2. "direct_mcp" - Single or simple tool usage, stateless operations
3. "mcp_agent" - Complex multi-step workflows, needs coordination or state

Analyze the user's request and respond with a JSON object containing:
- route: The chosen route
- confidence: 0.0-1.0 confidence in decision
- reasoning: Brief explanation
- required_tools: List of tools needed (empty if none)
- is_multi_step: Whether this requires multiple sequential steps
- needs_state: Whether this needs to remember context between steps
- estimated_complexity: 1-10 scale

Examples:
- "What is 2+2?" → direct_llm (no tools)
- "List files in /home" → direct_mcp (simple filesystem)
- "Analyze my codebase, fix bugs, test, and create PR" → mcp_agent (complex workflow)
"""

    async def route_request(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        user_preferences: Optional[Dict] = None
    ) -> Tuple[str, RouteDecision]:
        """
        Use LLM to make routing decision
        
        Returns: (route, decision_details)
        """
        # Build messages for routing LLM
        messages = [
            {"role": "system", "content": self.routing_prompt},
            {"role": "user", "content": f"Route this request: {user_message}"}
        ]
        
        # Add conversation context if relevant
        if conversation_history:
            # Include last few messages for context
            context = "Recent conversation:\n"
            for msg in conversation_history[-3:]:
                context += f"{msg['role']}: {msg['content'][:100]}...\n"
            messages.insert(1, {"role": "system", "content": context})
        
        # Get routing decision from LLM
        response = self.anthropic.messages.create(
            model=self.routing_model,
            messages=messages,
            max_tokens=500,
            temperature=0.1  # Low temperature for consistent routing
        )
        
        # Parse JSON response
        try:
            decision_text = response.content[0].text
            # Extract JSON from response
            json_start = decision_text.find('{')
            json_end = decision_text.rfind('}') + 1
            decision_json = json.loads(decision_text[json_start:json_end])
            
            decision = RouteDecision(**decision_json)
            
            # Apply user preferences overrides
            if user_preferences:
                if user_preferences.get("prefer_fast") and decision.route == "mcp_agent":
                    # User prefers speed over capabilities
                    if decision.estimated_complexity < 7:
                        decision.route = "direct_mcp"
                        decision.reasoning += " (Downgraded for speed preference)"
                
            return decision.route, decision
            
        except Exception as e:
            # Fallback to simple routing
            return self._fallback_routing(user_message)
    
    def _fallback_routing(self, message: str) -> Tuple[str, RouteDecision]:
        """Simple fallback if LLM routing fails"""
        # Very basic keyword detection as fallback
        message_lower = message.lower()
        
        tool_keywords = {
            "filesystem": ["file", "directory", "folder", "read", "write", "save"],
            "github": ["github", "pr", "pull request", "issue", "repository"],
            "postgres": ["database", "sql", "query", "table"],
            "kubernetes": ["k8s", "pod", "deployment", "container"]
        }
        
        detected_tools = []
        for tool, keywords in tool_keywords.items():
            if any(kw in message_lower for kw in keywords):
                detected_tools.append(tool)
        
        if not detected_tools:
            route = "direct_llm"
        elif len(detected_tools) == 1:
            route = "direct_mcp"
        else:
            route = "mcp_agent"
        
        return route, RouteDecision(
            route=route,
            confidence=0.5,
            reasoning="Fallback routing based on keywords",
            required_tools=detected_tools,
            is_multi_step=len(detected_tools) > 1,
            needs_state=False,
            estimated_complexity=len(detected_tools) * 2
        )


class HybridRouter:
    """
    Combines semantic routing with caching and fast paths
    """
    
    def __init__(self):
        self.semantic_router = SemanticMCPRouter()
        self.route_cache = {}  # Cache routing decisions
        self.fast_patterns = {
            # Very common patterns that don't need LLM routing
            "direct_llm": [
                r"^(what|who|when|where|why|how) (is|are|was|were)",
                r"^(explain|describe|tell me about)",
                r"^(hello|hi|hey|thanks|thank you)",
            ],
            "direct_mcp": [
                r"^(list|show|display) files",
                r"^(read|cat|open) .+\.(py|js|txt|md)",
                r"^(my |list )?(github )?(prs?|pull requests?|issues?)",
            ]
        }
    
    async def route(
        self, 
        message: str,
        use_cache: bool = True,
        force_semantic: bool = False
    ) -> Tuple[str, RouteDecision]:
        """
        Route with multiple strategies:
        1. Fast pattern matching for common cases
        2. Cache lookup for repeated queries
        3. Semantic LLM routing for complex cases
        """
        # 1. Try fast patterns first (unless forced to use semantic)
        if not force_semantic:
            for route, patterns in self.fast_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, message.lower()):
                        return route, RouteDecision(
                            route=route,
                            confidence=0.9,
                            reasoning="Matched fast pattern",
                            required_tools=[],
                            is_multi_step=False,
                            needs_state=False,
                            estimated_complexity=1
                        )
        
        # 2. Check cache
        cache_key = hash(message.lower())
        if use_cache and cache_key in self.route_cache:
            cached = self.route_cache[cache_key]
            cached.reasoning += " (cached)"
            return cached.route, cached
        
        # 3. Semantic routing for everything else
        route, decision = await self.semantic_router.route_request(message)
        
        # Cache the decision
        if use_cache:
            self.route_cache[cache_key] = decision
            # Limit cache size
            if len(self.route_cache) > 1000:
                # Remove oldest entries
                self.route_cache = dict(list(self.route_cache.items())[-500:])
        
        return route, decision


# Alternative: Function Calling for Routing
class FunctionCallRouter:
    """
    Use function calling to let the LLM decide routing
    """
    
    def __init__(self):
        self.anthropic = Anthropic()
        
        # Define routing as a tool
        self.routing_tool = {
            "name": "route_request",
            "description": "Determine how to route a user request",
            "input_schema": {
                "type": "object",
                "properties": {
                    "route": {
                        "type": "string",
                        "enum": ["direct_llm", "direct_mcp", "mcp_agent"],
                        "description": "The routing decision"
                    },
                    "tools_needed": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of MCP tools needed"
                    },
                    "complexity_factors": {
                        "type": "object",
                        "properties": {
                            "multi_step": {"type": "boolean"},
                            "needs_state": {"type": "boolean"},
                            "requires_coordination": {"type": "boolean"}
                        }
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    }
                },
                "required": ["route", "tools_needed", "complexity_factors", "confidence"]
            }
        }
    
    async def route_with_function_call(self, message: str) -> Dict[str, Any]:
        """Let the LLM route using function calling"""
        
        response = self.anthropic.messages.create(
            model="claude-sonnet-4-5",
            messages=[{
                "role": "user", 
                "content": f"Route this request: {message}"
            }],
            tools=[self.routing_tool],
            tool_choice={"type": "tool", "name": "route_request"},
            max_tokens=500
        )
        
        # Extract routing decision from tool use
        for content in response.content:
            if content.type == "tool_use" and content.name == "route_request":
                return content.input
        
        # Shouldn't reach here
        raise ValueError("No routing decision returned")


# Usage example
async def example_usage():
    # Hybrid router with multiple strategies
    router = HybridRouter()
    
    test_messages = [
        "What is the capital of France?",
        "List all Python files in the src directory",
        "Review my latest PR, fix any security issues, test the changes, and merge if tests pass",
        "Check database performance and optimize slow queries"
    ]
    
    for msg in test_messages:
        route, decision = await router.route(msg)
        print(f"\nMessage: {msg}")
        print(f"Route: {route}")
        print(f"Confidence: {decision.confidence}")
        print(f"Tools: {decision.required_tools}")
        print(f"Reasoning: {decision.reasoning}")