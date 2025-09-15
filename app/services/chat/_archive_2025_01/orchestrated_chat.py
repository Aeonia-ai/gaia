"""
Orchestrated Chat Service

Integrates custom orchestration with the chat service for intelligent
request handling and multi-agent workflows.
"""
import asyncio
import time
from typing import Dict, List, Any, Optional
import logging

from fastapi import HTTPException
from anthropic import Anthropic

from app.shared.config import GaiaSettings as Settings
from app.services.chat.custom_orchestration import CustomOrchestrator, SimpleOrchestrator
from app.services.chat.semantic_mcp_router import HybridRouter

logger = logging.getLogger(__name__)


class OrchestratedChatService:
    """
    Enhanced chat service with multi-agent orchestration
    
    Features:
    - Intelligent routing (direct LLM, MCP tools, multi-agent)
    - Dynamic agent spawning
    - Efficient parallel execution
    - Seamless fallback to standard chat
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.anthropic = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)
        
        # Initialize components
        self.router = HybridRouter()
        self.orchestrator = CustomOrchestrator(settings)
        self.simple_orchestrator = SimpleOrchestrator(settings)
        
        # Performance tracking
        self.metrics = {
            "total_requests": 0,
            "direct_llm": 0,
            "mcp_requests": 0,
            "orchestrated": 0,
            "avg_response_time": 0
        }
    
    async def process_chat(
        self,
        request: Dict[str, Any],
        auth_principal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point for orchestrated chat
        
        1. Route the request
        2. Execute with appropriate strategy
        3. Return unified response
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # Extract message from standard format
            message = request.get("message")
            if not message:
                raise HTTPException(status_code=400, detail="No message provided")
            
            # Convert to messages array for internal use
            messages = [{"role": "user", "content": message}]
            latest_message = message
            
            # Route the request
            route, decision = await self.router.route(latest_message)
            logger.info(f"Routed to: {route} (confidence: {decision.confidence})")
            
            # Execute based on route
            if route == "direct_llm":
                response = await self._handle_direct_llm(messages)
                self.metrics["direct_llm"] += 1
                
            elif route == "direct_mcp":
                response = await self._handle_direct_mcp(messages, decision.required_tools)
                self.metrics["mcp_requests"] += 1
                
            elif route == "mcp_agent":
                response = await self._handle_orchestrated(latest_message, messages)
                self.metrics["orchestrated"] += 1
                
            else:
                # Fallback to direct LLM
                response = await self._handle_direct_llm(messages)
                self.metrics["direct_llm"] += 1
            
            # Track performance
            execution_time = time.time() - start_time
            self._update_avg_response_time(execution_time)
            
            # Format response
            return self._format_response(response, execution_time, route)
            
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _handle_direct_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Handle simple direct LLM requests"""
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            max_tokens=2000
        )
        
        return {
            "content": response.content[0].text,
            "type": "direct_llm",
            "model": response.model
        }
    
    async def _handle_direct_mcp(
        self,
        messages: List[Dict[str, str]],
        required_tools: List[str]
    ) -> Dict[str, Any]:
        """Handle requests that need MCP tools"""
        # This would integrate with the MCP system
        # For now, simulate tool usage
        
        tool_descriptions = self._get_tool_descriptions(required_tools)
        
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            tools=tool_descriptions,
            max_tokens=2000
        )
        
        # Process tool calls
        tool_results = []
        final_content = ""
        
        for content in response.content:
            if content.type == "text":
                final_content += content.text
            elif content.type == "tool_use":
                # Would execute actual MCP tool here
                tool_results.append({
                    "tool": content.name,
                    "input": content.input,
                    "result": f"Simulated result for {content.name}"
                })
        
        return {
            "content": final_content,
            "type": "mcp_tools",
            "tools_used": [r["tool"] for r in tool_results],
            "tool_results": tool_results
        }
    
    async def _handle_orchestrated(
        self,
        message: str,
        full_messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Handle complex requests with orchestration"""
        
        # Add context from conversation history
        context = ""
        if len(full_messages) > 1:
            # Include last few messages for context
            recent = full_messages[-3:-1]  # Exclude the current message
            context = "\n\nRecent conversation:\n"
            for msg in recent:
                role = msg["role"]
                content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
                context += f"{role}: {content}\n"
        
        full_request = message + context
        
        # Orchestrate
        result = await self.orchestrator.orchestrate(
            request=full_request,
            max_agents=5,
            timeout=30.0
        )
        
        return {
            "content": result.response,
            "type": "orchestrated",
            "agents_used": result.tasks_executed,
            "task_details": result.task_details,
            "success": result.success,
            "errors": result.errors
        }
    
    def _get_tool_descriptions(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        """Get tool descriptions for requested tools"""
        # This would come from the MCP registry
        # For now, return mock tools
        
        available_tools = {
            "filesystem": {
                "name": "read_file",
                "description": "Read contents of a file",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"]
                }
            },
            "github": {
                "name": "list_prs",
                "description": "List pull requests",
                "input_schema": {
                    "type": "object",
                    "properties": {"repo": {"type": "string"}},
                    "required": ["repo"]
                }
            }
        }
        
        return [available_tools.get(name) for name in tool_names if name in available_tools]
    
    def _format_response(
        self,
        response: Dict[str, Any],
        execution_time: float,
        route: str
    ) -> Dict[str, Any]:
        """Format the final response"""
        
        # LLM Platform compatible response
        formatted = {
            "id": f"msg_{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": response.get("model", "claude-3-5-sonnet-20241022"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response["content"]
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 100,  # Would calculate actual tokens
                "completion_tokens": 200,
                "total_tokens": 300
            }
        }
        
        # Add orchestration metadata if available
        if response["type"] == "orchestrated":
            formatted["metadata"] = {
                "orchestration": {
                    "agents_used": response.get("agents_used", 0),
                    "success": response.get("success", True),
                    "task_details": response.get("task_details", [])
                }
            }
        elif response["type"] == "mcp_tools":
            formatted["metadata"] = {
                "tools": {
                    "used": response.get("tools_used", []),
                    "results": response.get("tool_results", [])
                }
            }
        
        # Add performance data
        formatted["metadata"] = formatted.get("metadata", {})
        formatted["metadata"]["performance"] = {
            "route": route,
            "execution_time": round(execution_time, 3),
            "type": response["type"]
        }
        
        return formatted
    
    def _update_avg_response_time(self, new_time: float):
        """Update rolling average response time"""
        current_avg = self.metrics["avg_response_time"]
        total_requests = self.metrics["total_requests"]
        
        # Calculate new average
        self.metrics["avg_response_time"] = (
            (current_avg * (total_requests - 1) + new_time) / total_requests
        )
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            **self.metrics,
            "route_distribution": {
                "direct_llm": self.metrics["direct_llm"] / max(self.metrics["total_requests"], 1),
                "mcp": self.metrics["mcp_requests"] / max(self.metrics["total_requests"], 1),
                "orchestrated": self.metrics["orchestrated"] / max(self.metrics["total_requests"], 1)
            }
        }


# Example: Pre-configured orchestration patterns
class OrchestrationPatterns:
    """Common orchestration patterns for reuse"""
    
    @staticmethod
    def research_and_write() -> List[Dict[str, Any]]:
        """Research topic then write about it"""
        return [
            {"role": "researcher", "task": "Research the topic thoroughly", "parallel": True},
            {"role": "writer", "task": "Write comprehensive content based on research", "depends_on": [0]}
        ]
    
    @staticmethod
    def code_review_pattern() -> List[Dict[str, Any]]:
        """Analyze code, identify issues, suggest fixes"""
        return [
            {"role": "coder", "task": "Analyze code structure and patterns", "parallel": True},
            {"role": "analyst", "task": "Identify potential issues and bugs", "parallel": True},
            {"role": "reviewer", "task": "Provide improvement suggestions", "depends_on": [0, 1]}
        ]
    
    @staticmethod
    def full_analysis_pattern() -> List[Dict[str, Any]]:
        """Comprehensive analysis with multiple perspectives"""
        return [
            {"role": "researcher", "task": "Gather all relevant information", "parallel": True},
            {"role": "analyst", "task": "Analyze data and patterns", "parallel": True},
            {"role": "reviewer", "task": "Critical evaluation", "depends_on": [0, 1]},
            {"role": "writer", "task": "Synthesize findings into report", "depends_on": [2]}
        ]