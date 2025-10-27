"""
Custom Multi-Agent Orchestration System

Lightweight, efficient orchestration taking the best ideas without the bloat.
Built for Gaia's specific needs.
"""
import asyncio
import uuid
import time
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

from anthropic import Anthropic
from app.shared.config import GaiaSettings as Settings

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Focused set of agent roles for real use cases"""
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    CODER = "coder"
    REVIEWER = "reviewer"
    TOOL_USER = "tool_user"


@dataclass
class Task:
    """Lightweight task definition"""
    id: str
    role: AgentRole
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    parallel_ok: bool = True
    result: Optional[Any] = None
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None
    execution_time: Optional[float] = None


@dataclass
class OrchestrationResult:
    """Result of orchestrated execution"""
    success: bool
    response: str
    tasks_executed: int
    total_time: float
    task_details: List[Dict[str, Any]]
    errors: List[str] = field(default_factory=list)


class CustomOrchestrator:
    """
    Efficient orchestrator optimized for Gaia's needs
    
    Key features:
    - LLM decides when to spawn sub-agents
    - Efficient parallel execution
    - Minimal overhead
    - Clear result aggregation
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.anthropic = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)
        self.tasks: Dict[str, Task] = {}
        
        # Agent-specific prompts
        self.agent_prompts = {
            AgentRole.RESEARCHER: "You are a research specialist. Gather accurate, relevant information and cite sources.",
            AgentRole.ANALYST: "You are an analyst. Analyze data, identify patterns, and provide insights.",
            AgentRole.WRITER: "You are a writer. Create clear, engaging content appropriate for the audience.",
            AgentRole.CODER: "You are a coding specialist. Write clean, efficient, well-documented code.",
            AgentRole.REVIEWER: "You are a reviewer. Check quality, identify issues, and suggest improvements.",
            AgentRole.TOOL_USER: "You are a tool specialist. Execute tools efficiently and handle errors gracefully."
        }
        
        # Tool for spawning sub-agents
        self.spawn_agent_tool = {
            "name": "spawn_agent",
            "description": "Spawn a specialized sub-agent for a specific task",
            "input_schema": {
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "enum": [r.value for r in AgentRole if r != AgentRole.ORCHESTRATOR],
                        "description": "Type of specialist agent"
                    },
                    "description": {
                        "type": "string",
                        "description": "What the agent should do"
                    },
                    "context": {
                        "type": "object",
                        "description": "Any context the agent needs"
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs that must complete first"
                    },
                    "parallel_ok": {
                        "type": "boolean",
                        "default": True,
                        "description": "Can run in parallel with other tasks"
                    }
                },
                "required": ["role", "description"]
            }
        }
    
    async def orchestrate(
        self,
        request: str,
        max_agents: int = 10,
        timeout: float = 60.0
    ) -> OrchestrationResult:
        """
        Main orchestration method
        
        The orchestrator LLM analyzes the request and decides:
        1. Can I answer this directly?
        2. Do I need to spawn specialized agents?
        3. What agents and in what order?
        """
        start_time = time.time()
        
        try:
            # Phase 1: Planning
            logger.info(f"Orchestrating request: {request[:100]}...")
            
            system_prompt = """You are an AI orchestrator that can spawn specialized sub-agents.

For simple questions, answer directly.
For complex tasks, break them down and spawn appropriate agents.

Available agent types:
- researcher: Gathers information, finds sources
- analyst: Analyzes data, identifies patterns  
- writer: Creates content, documentation
- coder: Writes and reviews code
- reviewer: Quality checks, validation
- tool_user: Executes MCP tools

Be efficient - only spawn agents when they add real value.
When spawning agents, think about:
- What order do they need to run in?
- Can any run in parallel?
- What context does each need?

Examples:
- "What is Python?" → Just answer directly
- "Analyze this code and write docs" → Spawn analyst then writer
- "Research X, analyze findings, write report" → Spawn researcher, analyst, writer in sequence"""

            # Get orchestration plan
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request}
            ]
            
            response = await self._call_llm(
                messages=messages,
                tools=[self.spawn_agent_tool],
                model="claude-sonnet-4-5"
            )
            
            # Phase 2: Execute spawned agents
            spawned_tasks = await self._extract_and_create_tasks(response)
            
            if not spawned_tasks:
                # No agents spawned, direct answer
                return OrchestrationResult(
                    success=True,
                    response=self._extract_text_content(response),
                    tasks_executed=0,
                    total_time=time.time() - start_time,
                    task_details=[]
                )
            
            # Execute tasks with timeout
            await asyncio.wait_for(
                self._execute_tasks(spawned_tasks),
                timeout=timeout
            )
            
            # Phase 3: Synthesize results
            final_response = await self._synthesize_results(
                request,
                self._extract_text_content(response),
                spawned_tasks
            )
            
            # Prepare detailed results
            task_details = [
                {
                    "id": task_id,
                    "role": self.tasks[task_id].role.value,
                    "description": self.tasks[task_id].description[:100] + "...",
                    "status": self.tasks[task_id].status,
                    "execution_time": self.tasks[task_id].execution_time,
                    "error": self.tasks[task_id].error
                }
                for task_id in spawned_tasks
            ]
            
            errors = [
                f"Task {tid}: {self.tasks[tid].error}"
                for tid in spawned_tasks
                if self.tasks[tid].error
            ]
            
            return OrchestrationResult(
                success=len(errors) == 0,
                response=final_response,
                tasks_executed=len(spawned_tasks),
                total_time=time.time() - start_time,
                task_details=task_details,
                errors=errors
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Orchestration timeout after {timeout}s")
            return OrchestrationResult(
                success=False,
                response="Request timed out",
                tasks_executed=len(self.tasks),
                total_time=timeout,
                task_details=[],
                errors=["Orchestration timeout"]
            )
        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            return OrchestrationResult(
                success=False,
                response=f"Orchestration failed: {str(e)}",
                tasks_executed=0,
                total_time=time.time() - start_time,
                task_details=[],
                errors=[str(e)]
            )
    
    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        model: str = "claude-sonnet-4-5",
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 2000
    ) -> Any:
        """Call Anthropic API with error handling"""
        try:
            if tools:
                return self.anthropic.messages.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    max_tokens=max_tokens
                )
            else:
                return self.anthropic.messages.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens
                )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    async def _extract_and_create_tasks(self, response: Any) -> List[str]:
        """Extract spawned agent tasks from LLM response"""
        task_ids = []
        
        for content in response.content:
            if content.type == "tool_use" and content.name == "spawn_agent":
                task_id = str(uuid.uuid4())[:8]  # Short ID for readability
                
                task = Task(
                    id=task_id,
                    role=AgentRole(content.input["role"]),
                    description=content.input["description"],
                    context=content.input.get("context", {}),
                    dependencies=content.input.get("dependencies", []),
                    parallel_ok=content.input.get("parallel_ok", True)
                )
                
                self.tasks[task_id] = task
                task_ids.append(task_id)
                
                logger.info(f"Created task {task_id}: {task.role.value} - {task.description[:50]}...")
        
        return task_ids
    
    async def _execute_tasks(self, task_ids: List[str]):
        """Execute tasks with dependency management"""
        completed = set()
        
        while len(completed) < len(task_ids):
            # Find ready tasks
            ready = []
            for tid in task_ids:
                if tid not in completed:
                    task = self.tasks[tid]
                    # Check if dependencies are satisfied
                    if all(dep in completed for dep in task.dependencies):
                        ready.append(tid)
            
            if not ready:
                # No tasks ready, might be circular dependency
                logger.error("No tasks ready to execute - possible circular dependency")
                break
            
            # Group by parallel_ok
            parallel_tasks = [t for t in ready if self.tasks[t].parallel_ok]
            sequential_tasks = [t for t in ready if not self.tasks[t].parallel_ok]
            
            # Execute parallel tasks
            if parallel_tasks:
                await asyncio.gather(*[
                    self._execute_single_task(tid) for tid in parallel_tasks
                ])
                completed.update(parallel_tasks)
            
            # Execute sequential tasks one by one
            for tid in sequential_tasks:
                await self._execute_single_task(tid)
                completed.add(tid)
    
    async def _execute_single_task(self, task_id: str):
        """Execute a single agent task"""
        task = self.tasks[task_id]
        task.status = "running"
        start = time.time()
        
        try:
            logger.info(f"Executing task {task_id}: {task.role.value}")
            
            # Get role-specific prompt
            system_prompt = self.agent_prompts.get(
                task.role,
                "You are a specialist. Complete the requested task efficiently."
            )
            
            # Build context including dependency results
            context = task.context.copy()
            for dep_id in task.dependencies:
                if dep_id in self.tasks and self.tasks[dep_id].result:
                    context[f"result_from_{dep_id}"] = self.tasks[dep_id].result
            
            # Execute with appropriate model (could use Haiku for simple tasks)
            model = "claude-sonnet-4-5"
            if task.role in [AgentRole.RESEARCHER, AgentRole.REVIEWER]:
                model = "claude-3-haiku-20240307"  # Faster for simpler tasks
            
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Task: {task.description}\n\nContext: {json.dumps(context, indent=2)}"
                }
            ]
            
            response = await self._call_llm(messages=messages, model=model)
            
            task.result = self._extract_text_content(response)
            task.status = "completed"
            task.execution_time = time.time() - start
            
            logger.info(f"Task {task_id} completed in {task.execution_time:.2f}s")
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.execution_time = time.time() - start
            logger.error(f"Task {task_id} failed: {e}")
    
    async def _synthesize_results(
        self,
        original_request: str,
        orchestrator_response: str,
        task_ids: List[str]
    ) -> str:
        """Synthesize final response from all agent results"""
        
        # Collect successful results
        results = []
        for tid in task_ids:
            task = self.tasks[tid]
            if task.status == "completed" and task.result:
                results.append({
                    "role": task.role.value,
                    "task": task.description,
                    "result": task.result
                })
        
        if not results:
            return orchestrator_response
        
        # Have orchestrator synthesize
        synthesis_prompt = """Synthesize the results from your sub-agents into a coherent final response.
Focus on answering the original request completely.
Be concise but thorough."""
        
        messages = [
            {"role": "system", "content": synthesis_prompt},
            {
                "role": "user",
                "content": f"""Original request: {original_request}

Your initial analysis: {orchestrator_response}

Sub-agent results:
{json.dumps(results, indent=2)}

Provide a unified response that best answers the original request."""
            }
        ]
        
        response = await self._call_llm(messages=messages)
        return self._extract_text_content(response)
    
    def _extract_text_content(self, response: Any) -> str:
        """Extract text content from Anthropic response"""
        if hasattr(response, 'content') and response.content:
            return response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
        return ""


# Simple interface for direct use
class SimpleOrchestrator:
    """Even simpler interface when you know what agents you need"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.anthropic = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)
    
    async def run_agents(
        self,
        agents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run specific agents in parallel or sequence
        
        Example:
        agents = [
            {"role": "researcher", "task": "Find Python best practices", "parallel": True},
            {"role": "coder", "task": "Implement the function", "parallel": False, "depends_on": [0]},
            {"role": "reviewer", "task": "Review the code", "parallel": False, "depends_on": [1]}
        ]
        """
        results = {}
        
        # Group by dependency level
        levels = self._group_by_dependency_level(agents)
        
        for level in levels:
            # Run all agents at this level in parallel
            tasks = []
            for idx in level:
                agent = agents[idx]
                
                # Build context from dependencies
                context = {}
                for dep_idx in agent.get("depends_on", []):
                    if dep_idx in results:
                        context[f"previous_{dep_idx}"] = results[dep_idx]
                
                task = self._run_single_agent(
                    agent["role"],
                    agent["task"],
                    context
                )
                tasks.append((idx, task))
            
            # Execute level
            level_results = await asyncio.gather(*[t[1] for t in tasks])
            
            # Store results
            for (idx, _), result in zip(tasks, level_results):
                results[idx] = result
        
        return {
            "success": all(r.get("success", False) for r in results.values()),
            "results": results,
            "count": len(agents)
        }
    
    async def _run_single_agent(
        self,
        role: str,
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a single agent"""
        try:
            prompts = {
                "researcher": "You are a research specialist. Find accurate, relevant information.",
                "coder": "You are a coding specialist. Write clean, efficient code.",
                "analyst": "You are an analyst. Analyze and provide insights.",
                "writer": "You are a writer. Create clear, engaging content.",
                "reviewer": "You are a reviewer. Check quality and suggest improvements."
            }
            
            system_prompt = prompts.get(role, "You are a specialist. Complete the task efficiently.")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Task: {task}\n\nContext: {json.dumps(context, indent=2) if context else 'None'}"
                }
            ]
            
            # Use Haiku for simple roles, Sonnet for complex ones
            model = "claude-3-haiku-20240307" if role in ["researcher", "reviewer"] else "claude-sonnet-4-5"
            
            response = self.anthropic.messages.create(
                model=model,
                messages=messages,
                max_tokens=1500
            )
            
            return {
                "success": True,
                "role": role,
                "task": task,
                "result": response.content[0].text
            }
            
        except Exception as e:
            return {
                "success": False,
                "role": role,
                "task": task,
                "error": str(e)
            }
    
    def _group_by_dependency_level(self, agents: List[Dict]) -> List[List[int]]:
        """Group agents by dependency level for parallel execution"""
        levels = []
        processed = set()
        
        while len(processed) < len(agents):
            level = []
            for idx, agent in enumerate(agents):
                if idx not in processed:
                    deps = agent.get("depends_on", [])
                    if all(d in processed for d in deps):
                        level.append(idx)
            
            if not level:
                # Circular dependency or error
                remaining = [i for i in range(len(agents)) if i not in processed]
                level = remaining  # Process remaining as final level
            
            levels.append(level)
            processed.update(level)
        
        return levels