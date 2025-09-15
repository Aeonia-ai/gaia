"""
Hybrid MCP Strategy - Best of Both Worlds

Use the right tool for the right job:
1. No tools needed → Direct LLM (fastest)
2. Simple tools → Direct MCP (fast)
3. Complex workflows → mcp-agent (powerful)
"""
from typing import List, Optional
from enum import Enum

class ChatComplexity(Enum):
    SIMPLE = "simple"          # No tools needed
    TOOLS = "tools"            # Basic tool usage
    WORKFLOW = "workflow"      # Multi-agent/complex

class HybridMCPRouter:
    """Routes requests to appropriate handler based on complexity"""
    
    @staticmethod
    def analyze_request(
        message: str,
        requested_tools: List[str],
        workflow_type: Optional[str] = None
    ) -> ChatComplexity:
        """Determine optimal processing path"""
        
        # No tools = simple chat
        if not requested_tools and not workflow_type:
            return ChatComplexity.SIMPLE
        
        # Workflow requested = use mcp-agent
        if workflow_type in ["research", "code_review", "data_pipeline"]:
            return ChatComplexity.WORKFLOW
        
        # Complex tool combinations = use mcp-agent
        complex_combinations = [
            {"github", "filesystem", "terminal"},  # Code development
            {"postgres", "s3", "python"},          # Data processing
            {"kubernetes", "prometheus", "slack"}   # DevOps
        ]
        
        if any(set(requested_tools) >= combo for combo in complex_combinations):
            return ChatComplexity.WORKFLOW
        
        # Simple tool usage = direct MCP
        return ChatComplexity.TOOLS
    
    async def route_request(self, request):
        """Route to appropriate handler"""
        complexity = self.analyze_request(
            request.message,
            request.tools or [],
            request.workflow_type
        )
        
        if complexity == ChatComplexity.SIMPLE:
            # Direct to LLM - 2s average
            return await self.direct_llm_handler(request)
            
        elif complexity == ChatComplexity.TOOLS:
            # Direct MCP integration - 3-4s average
            return await self.direct_mcp_handler(request)
            
        else:  # WORKFLOW
            # mcp-agent for complex cases - 5-10s
            return await self.mcp_agent_handler(request)


# Example endpoint structure:
"""
POST /api/v1/chat
{
    "message": "What is 2+2?",
    "tools": [],                    # → Direct LLM (2s)
}

POST /api/v1/chat
{
    "message": "List my GitHub PRs",
    "tools": ["github"],            # → Direct MCP (3s)
}

POST /api/v1/chat
{
    "message": "Review my code and fix issues",
    "tools": ["github", "filesystem", "terminal"],
    "workflow_type": "code_review"  # → mcp-agent (8s)
}
"""