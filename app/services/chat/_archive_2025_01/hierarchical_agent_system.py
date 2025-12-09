"""
Hierarchical Agent System - Main Chat Can Spawn Specialized Sub-Agents

The main chat acts as an orchestrator that can:
- Spawn specialized agents for specific tasks
- Run them in parallel sub-threads
- Aggregate results
- Maintain separate conversation contexts
"""
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

from anthropic import Anthropic
from pydantic import BaseModel


class AgentType(Enum):
    MAIN = "main"                    # Orchestrator
    RESEARCHER = "researcher"        # Information gathering
    CODER = "coder"                 # Code analysis/generation
    ANALYZER = "analyzer"           # Data analysis
    WRITER = "writer"               # Content creation
    REVIEWER = "reviewer"           # Quality checking
    TOOL_SPECIALIST = "tool_specialist"  # MCP tool usage


class AgentStatus(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentContext:
    """Context for a sub-agent"""
    agent_id: str
    agent_type: AgentType
    parent_id: Optional[str]
    task_description: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    message_history: List[Dict[str, str]] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SubAgent:
    """A specialized sub-agent that can be spawned by the main chat"""
    
    def __init__(
        self,
        agent_type: AgentType,
        context: AgentContext,
        llm_model: str = "claude-sonnet-4-5"
    ):
        self.agent_type = agent_type
        self.context = context
        self.llm_model = llm_model
        self.anthropic = Anthropic()
        
    def get_system_prompt(self) -> str:
        """Get specialized system prompt based on agent type"""
        prompts = {
            AgentType.RESEARCHER: """You are a research specialist. Your role is to:
- Gather relevant information
- Verify facts and sources
- Summarize findings clearly
- Identify knowledge gaps
Focus on accuracy and completeness.""",

            AgentType.CODER: """You are a coding specialist. Your role is to:
- Analyze code structure and quality
- Write clean, efficient code
- Debug and fix issues
- Follow best practices
Focus on correctness and maintainability.""",

            AgentType.ANALYZER: """You are a data analysis specialist. Your role is to:
- Analyze patterns and trends
- Perform calculations
- Create insights from data
- Identify anomalies
Focus on accuracy and actionable insights.""",

            AgentType.WRITER: """You are a content writing specialist. Your role is to:
- Create clear, engaging content
- Adapt tone to audience
- Structure information logically
- Ensure readability
Focus on clarity and engagement.""",

            AgentType.REVIEWER: """You are a quality review specialist. Your role is to:
- Check for errors and inconsistencies
- Verify requirements are met
- Suggest improvements
- Ensure standards compliance
Focus on thoroughness and constructive feedback.""",

            AgentType.TOOL_SPECIALIST: """You are a tool usage specialist. Your role is to:
- Execute tools efficiently
- Chain tool operations effectively
- Handle errors gracefully
- Optimize tool usage
Focus on reliability and efficiency."""
        }
        
        base_prompt = prompts.get(self.agent_type, "You are a specialized assistant.")
        
        # Add task-specific context
        if self.context.task_description:
            base_prompt += f"\n\nYour specific task: {self.context.task_description}"
        
        # Add constraints
        if self.context.constraints:
            base_prompt += f"\n\nConstraints: {json.dumps(self.context.constraints, indent=2)}"
        
        return base_prompt
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the agent's task"""
        self.context.status = AgentStatus.THINKING
        
        try:
            # Build messages including any context from parent
            messages = [
                {"role": "system", "content": self.get_system_prompt()}
            ]
            
            # Add message history if any
            messages.extend(self.context.message_history)
            
            # If no specific messages, use task description
            if len(messages) == 1:
                messages.append({
                    "role": "user",
                    "content": self.context.task_description
                })
            
            # Call LLM with appropriate tools if available
            self.context.status = AgentStatus.EXECUTING
            
            if self.context.available_tools and self.agent_type == AgentType.TOOL_SPECIALIST:
                # Tool specialist gets actual tool definitions
                response = await self._execute_with_tools(messages)
            else:
                # Other agents just get LLM access
                response = self.anthropic.messages.create(
                    model=self.llm_model,
                    messages=messages,
                    max_tokens=2000
                )
                response = {"content": response.content[0].text}
            
            self.context.status = AgentStatus.COMPLETED
            self.context.results = {
                "success": True,
                "response": response,
                "agent_type": self.agent_type.value,
                "execution_time": (datetime.now() - self.context.created_at).total_seconds()
            }
            
            return self.context.results
            
        except Exception as e:
            self.context.status = AgentStatus.FAILED
            self.context.results = {
                "success": False,
                "error": str(e),
                "agent_type": self.agent_type.value
            }
            return self.context.results
    
    async def _execute_with_tools(self, messages: List[Dict]) -> Dict[str, Any]:
        """Execute with MCP tools for tool specialist"""
        # This would integrate with the MCP system
        # For now, simulate tool execution
        return {
            "content": "Executed tools successfully",
            "tools_used": self.context.available_tools
        }


class HierarchicalAgentOrchestrator:
    """
    Main orchestrator that can spawn and manage sub-agents
    """
    
    def __init__(self):
        self.anthropic = Anthropic()
        self.active_agents: Dict[str, SubAgent] = {}
        self.completed_agents: Dict[str, SubAgent] = {}
        self.main_context = AgentContext(
            agent_id=str(uuid.uuid4()),
            agent_type=AgentType.MAIN,
            parent_id=None,
            task_description="Main orchestrator"
        )
        
        # Define the spawning tool for the main agent
        self.agent_spawning_tool = {
            "name": "spawn_agent",
            "description": "Spawn a specialized sub-agent for a specific task",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "enum": [t.value for t in AgentType if t != AgentType.MAIN],
                        "description": "Type of specialist agent to spawn"
                    },
                    "task_description": {
                        "type": "string",
                        "description": "Detailed description of what the agent should do"
                    },
                    "constraints": {
                        "type": "object",
                        "description": "Any constraints or parameters for the agent"
                    },
                    "provide_context": {
                        "type": "boolean",
                        "description": "Whether to share current conversation context"
                    },
                    "run_parallel": {
                        "type": "boolean",
                        "description": "Whether this can run in parallel with other agents"
                    }
                },
                "required": ["agent_type", "task_description"]
            }
        }
        
        # Tool for checking agent status
        self.agent_status_tool = {
            "name": "check_agents",
            "description": "Check status of spawned agents",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific agent IDs to check (empty for all)"
                    }
                }
            }
        }
        
        # Tool for aggregating results
        self.aggregate_results_tool = {
            "name": "aggregate_results",
            "description": "Aggregate results from multiple agents",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "aggregation_type": {
                        "type": "string",
                        "enum": ["summary", "detailed", "comparison"]
                    }
                }
            }
        }
    
    async def process_with_spawning(
        self,
        message: str,
        max_parallel_agents: int = 5
    ) -> Dict[str, Any]:
        """
        Process a message where the main agent can spawn sub-agents
        """
        
        # Main agent system prompt
        system_prompt = """You are an orchestrator AI that can spawn specialized sub-agents for complex tasks.

You can:
1. Spawn specialized agents (researcher, coder, analyzer, writer, reviewer, tool_specialist)
2. Run multiple agents in parallel for efficiency
3. Check on agent progress
4. Aggregate results from multiple agents

When you receive a complex request, think about:
- Can this be broken down into specialized subtasks?
- Which agents would be best for each part?
- Can any parts run in parallel?
- How should results be combined?

Example decompositions:
- "Review and fix code" → spawn coder for analysis, then reviewer for QA
- "Research and write article" → spawn researcher and writer in sequence
- "Analyze system performance" → spawn multiple analyzers in parallel

Always explain your orchestration strategy."""

        # Process with spawning tools
        response = self.anthropic.messages.create(
            model="claude-sonnet-4-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            tools=[
                self.agent_spawning_tool,
                self.agent_status_tool,
                self.aggregate_results_tool
            ],
            max_tokens=2000
        )
        
        # Track spawned agents
        spawned_agents = []
        parallel_tasks = []
        
        # Process tool calls
        for content in response.content:
            if content.type == "tool_use":
                if content.name == "spawn_agent":
                    agent_id = await self._spawn_agent(content.input)
                    spawned_agents.append(agent_id)
                    
                    if content.input.get("run_parallel", True):
                        # Start execution immediately
                        task = asyncio.create_task(
                            self._execute_agent(agent_id)
                        )
                        parallel_tasks.append(task)
                
                elif content.name == "check_agents":
                    # Check agent status
                    status = self._get_agent_status(content.input.get("agent_ids", []))
                    # Would continue conversation with status
                
                elif content.name == "aggregate_results":
                    # Aggregate results
                    results = self._aggregate_results(
                        content.input["agent_ids"],
                        content.input.get("aggregation_type", "summary")
                    )
        
        # Wait for parallel agents if any
        if parallel_tasks:
            await asyncio.gather(*parallel_tasks)
        
        # Execute sequential agents
        for agent_id in spawned_agents:
            if agent_id in self.active_agents:
                await self._execute_agent(agent_id)
        
        # Get final aggregated response
        final_response = await self._get_orchestrated_response(
            response.content[0].text if response.content else "",
            spawned_agents
        )
        
        return {
            "response": final_response,
            "agents_spawned": len(spawned_agents),
            "agent_details": [
                {
                    "id": aid,
                    "type": self.completed_agents[aid].agent_type.value,
                    "status": self.completed_agents[aid].context.status.value,
                    "results": self.completed_agents[aid].context.results
                }
                for aid in spawned_agents if aid in self.completed_agents
            ]
        }
    
    async def _spawn_agent(self, config: Dict[str, Any]) -> str:
        """Spawn a new sub-agent"""
        agent_id = str(uuid.uuid4())
        
        context = AgentContext(
            agent_id=agent_id,
            agent_type=AgentType(config["agent_type"]),
            parent_id=self.main_context.agent_id,
            task_description=config["task_description"],
            constraints=config.get("constraints", {})
        )
        
        # Add context if requested
        if config.get("provide_context"):
            context.message_history = self.main_context.message_history[-5:]
        
        # Add tools for tool specialist
        if context.agent_type == AgentType.TOOL_SPECIALIST:
            context.available_tools = config.get("tools", ["filesystem", "github"])
        
        agent = SubAgent(context.agent_type, context)
        self.active_agents[agent_id] = agent
        
        return agent_id
    
    async def _execute_agent(self, agent_id: str):
        """Execute a specific agent"""
        if agent_id not in self.active_agents:
            return
        
        agent = self.active_agents[agent_id]
        await agent.execute()
        
        # Move to completed
        self.completed_agents[agent_id] = agent
        del self.active_agents[agent_id]
    
    def _get_agent_status(self, agent_ids: List[str]) -> Dict[str, Any]:
        """Get status of agents"""
        if not agent_ids:
            agent_ids = list(self.active_agents.keys()) + list(self.completed_agents.keys())
        
        status = {}
        for aid in agent_ids:
            if aid in self.active_agents:
                status[aid] = {
                    "status": self.active_agents[aid].context.status.value,
                    "type": self.active_agents[aid].agent_type.value
                }
            elif aid in self.completed_agents:
                status[aid] = {
                    "status": "completed",
                    "type": self.completed_agents[aid].agent_type.value,
                    "has_results": bool(self.completed_agents[aid].context.results)
                }
        
        return status
    
    def _aggregate_results(self, agent_ids: List[str], aggregation_type: str) -> Dict[str, Any]:
        """Aggregate results from multiple agents"""
        results = {}
        
        for aid in agent_ids:
            if aid in self.completed_agents:
                agent = self.completed_agents[aid]
                results[aid] = {
                    "type": agent.agent_type.value,
                    "task": agent.context.task_description,
                    "results": agent.context.results
                }
        
        if aggregation_type == "summary":
            # Create summary of key findings
            return {"summary": "Aggregated findings from agents", "details": results}
        elif aggregation_type == "detailed":
            return results
        elif aggregation_type == "comparison":
            # Compare results across agents
            return {"comparison": "Comparative analysis", "details": results}
    
    async def _get_orchestrated_response(
        self,
        initial_response: str,
        agent_ids: List[str]
    ) -> str:
        """Get final orchestrated response combining all agent outputs"""
        
        # Collect all results
        agent_results = []
        for aid in agent_ids:
            if aid in self.completed_agents:
                agent = self.completed_agents[aid]
                if agent.context.results.get("success"):
                    agent_results.append({
                        "agent_type": agent.agent_type.value,
                        "task": agent.context.task_description,
                        "result": agent.context.results.get("response", {}).get("content", "")
                    })
        
        # Have the main agent synthesize
        synthesis_response = self.anthropic.messages.create(
            model="claude-sonnet-4-5",
            messages=[
                {
                    "role": "system",
                    "content": "Synthesize the results from your sub-agents into a coherent response."
                },
                {
                    "role": "user",
                    "content": f"""Initial orchestration: {initial_response}

Sub-agent results:
{json.dumps(agent_results, indent=2)}

Please provide a unified response that incorporates all agent findings."""
                }
            ],
            max_tokens=2000
        )
        
        return synthesis_response.content[0].text


# Example usage showing complex orchestration
async def example_hierarchical_execution():
    orchestrator = HierarchicalAgentOrchestrator()
    
    # Complex request that benefits from multiple specialists
    result = await orchestrator.process_with_spawning(
        """I need help with my Python web application:
        1. Review the code in src/ for security issues
        2. Analyze the database performance 
        3. Write documentation for the API endpoints
        4. Create a deployment guide
        
        Please handle this comprehensively."""
    )
    
    print(f"Agents spawned: {result['agents_spawned']}")
    print(f"Final response: {result['response']}")
    
    # Show agent details
    for agent in result['agent_details']:
        print(f"\nAgent {agent['id']} ({agent['type']}):")
        print(f"  Status: {agent['status']}")
        print(f"  Results: {agent['results']}")


# Advanced: Agent communication and coordination
class InterAgentCommunication:
    """Allow agents to communicate with each other"""
    
    def __init__(self):
        self.message_queue: Dict[str, List[Dict]] = {}
        self.agent_dependencies: Dict[str, List[str]] = {}
    
    async def send_message(self, from_agent: str, to_agent: str, message: Dict):
        """Send message from one agent to another"""
        if to_agent not in self.message_queue:
            self.message_queue[to_agent] = []
        
        self.message_queue[to_agent].append({
            "from": from_agent,
            "message": message,
            "timestamp": datetime.now()
        })
    
    async def get_messages(self, agent_id: str) -> List[Dict]:
        """Get messages for an agent"""
        messages = self.message_queue.get(agent_id, [])
        self.message_queue[agent_id] = []  # Clear after reading
        return messages
    
    def add_dependency(self, agent_id: str, depends_on: str):
        """Add dependency between agents"""
        if agent_id not in self.agent_dependencies:
            self.agent_dependencies[agent_id] = []
        self.agent_dependencies[agent_id].append(depends_on)