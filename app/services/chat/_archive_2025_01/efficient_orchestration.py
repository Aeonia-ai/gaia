"""
Efficient Custom Orchestration - Best Ideas, Minimal Overhead

Taking the best patterns without the bloat
"""
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import time

from anthropic import Anthropic


class AgentType(str, Enum):
    """Keep it simple - just the roles we actually need"""
    MAIN = "main"
    TOOL_USER = "tool_user"  # Uses MCP tools
    ANALYZER = "analyzer"    # Analyzes data/code
    WRITER = "writer"        # Creates content
    REVIEWER = "reviewer"    # QA/validation


@dataclass
class Task:
    """Lightweight task definition"""
    id: str
    type: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    status: str = "pending"  # pending, running, completed, failed


class EfficientOrchestrator:
    """
    Minimal orchestrator that:
    1. Lets the main LLM decide when to spawn sub-tasks
    2. Runs them efficiently
    3. Aggregates results
    4. No unnecessary abstractions
    """
    
    def __init__(self):
        self.anthropic = Anthropic()
        self.tasks: Dict[str, Task] = {}
        self.shared_context: Dict[str, Any] = {}
        
        # Simple sub-agent prompts
        self.agent_prompts = {
            AgentType.TOOL_USER: "You are a tool specialist. Execute the requested tools efficiently and return results.",
            AgentType.ANALYZER: "You are an analyzer. Analyze the provided data and return insights.",
            AgentType.WRITER: "You are a writer. Create the requested content clearly and concisely.",
            AgentType.REVIEWER: "You are a reviewer. Review the provided work and identify any issues."
        }
        
        # The ONLY tool the main agent needs
        self.spawn_task_tool = {
            "name": "spawn_task",
            "description": "Spawn a sub-task to be executed by a specialist",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "enum": ["tool_user", "analyzer", "writer", "reviewer"]
                    },
                    "description": {"type": "string"},
                    "context": {"type": "object"},
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs that must complete first"
                    }
                },
                "required": ["task_type", "description"]
            }
        }
    
    async def process(self, message: str) -> Dict[str, Any]:
        """
        Process message with optional sub-task spawning
        """
        start_time = time.time()
        
        # Main agent decides what to do
        main_response = self.anthropic.messages.create(
            model="claude-sonnet-4-5",
            messages=[{
                "role": "system",
                "content": """You are an AI assistant that can spawn specialized sub-tasks when needed.

For simple questions, just answer directly.
For complex tasks, break them down and spawn sub-tasks.

Examples:
- "What is 2+2?" → Just answer
- "Analyze this code and write documentation" → Spawn analyzer and writer tasks
- "Research X and create report" → Spawn tool_user for research, then writer

Be efficient - only spawn tasks when it truly adds value."""
            }, {
                "role": "user",
                "content": message
            }],
            tools=[self.spawn_task_tool],
            max_tokens=2000
        )
        
        # Extract any spawned tasks
        spawned_tasks = []
        main_content = ""
        
        for block in main_response.content:
            if block.type == "text":
                main_content += block.text
            elif block.type == "tool_use" and block.name == "spawn_task":
                task_id = f"task_{len(self.tasks)}"
                task = Task(
                    id=task_id,
                    type=block.input["task_type"],
                    description=block.input["description"],
                    context=block.input.get("context", {}),
                    dependencies=block.input.get("dependencies", [])
                )
                self.tasks[task_id] = task
                spawned_tasks.append(task_id)
        
        # Execute spawned tasks efficiently
        if spawned_tasks:
            await self._execute_tasks(spawned_tasks)
            
            # Get final response incorporating results
            final_response = await self._get_final_response(
                message, 
                main_content, 
                spawned_tasks
            )
        else:
            final_response = main_content
        
        execution_time = time.time() - start_time
        
        return {
            "response": final_response,
            "tasks_spawned": len(spawned_tasks),
            "execution_time": execution_time,
            "task_details": {
                tid: {
                    "type": self.tasks[tid].type,
                    "status": self.tasks[tid].status,
                    "description": self.tasks[tid].description[:50] + "..."
                }
                for tid in spawned_tasks
            } if spawned_tasks else None
        }
    
    async def _execute_tasks(self, task_ids: List[str]):
        """Execute tasks with dependency management"""
        completed = set()
        
        while len(completed) < len(task_ids):
            # Find ready tasks
            ready = []
            for tid in task_ids:
                if tid not in completed:
                    task = self.tasks[tid]
                    # Check dependencies
                    if all(dep in completed for dep in task.dependencies):
                        ready.append(tid)
            
            if not ready:
                break  # Circular dependency or error
            
            # Execute ready tasks in parallel
            await asyncio.gather(*[
                self._execute_single_task(tid) for tid in ready
            ])
            
            completed.update(ready)
    
    async def _execute_single_task(self, task_id: str):
        """Execute a single task"""
        task = self.tasks[task_id]
        task.status = "running"
        
        try:
            # Get appropriate prompt
            system_prompt = self.agent_prompts.get(
                AgentType(task.type),
                "You are a specialist. Complete the requested task."
            )
            
            # Include dependency results in context
            context = task.context.copy()
            for dep_id in task.dependencies:
                if dep_id in self.tasks and self.tasks[dep_id].result:
                    context[f"result_from_{dep_id}"] = self.tasks[dep_id].result
            
            # Execute
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-5",  # Could use Haiku for speed
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Task: {task.description}\n\nContext: {json.dumps(context)}"
                    }
                ],
                max_tokens=2000
            )
            
            task.result = response.content[0].text
            task.status = "completed"
            
        except Exception as e:
            task.result = f"Error: {str(e)}"
            task.status = "failed"
    
    async def _get_final_response(
        self, 
        original_message: str,
        initial_response: str,
        task_ids: List[str]
    ) -> str:
        """Synthesize final response from all results"""
        
        # Collect results
        results = {}
        for tid in task_ids:
            task = self.tasks[tid]
            results[tid] = {
                "type": task.type,
                "description": task.description,
                "result": task.result
            }
        
        # Have main agent synthesize
        synthesis = self.anthropic.messages.create(
            model="claude-sonnet-4-5",
            messages=[{
                "role": "system",
                "content": "Synthesize the task results into a final response for the user."
            }, {
                "role": "user",
                "content": f"""Original request: {original_message}

Initial thoughts: {initial_response}

Task results:
{json.dumps(results, indent=2)}

Provide a unified, coherent response."""
            }],
            max_tokens=2000
        )
        
        return synthesis.content[0].text


# Even simpler: Direct task spawning without heavy abstractions
class UltraLightOrchestrator:
    """
    The absolute minimal version - just parallel task execution
    """
    
    def __init__(self):
        self.anthropic = Anthropic()
    
    async def parallel_process(
        self, 
        main_prompt: str,
        subtasks: List[Dict[str, str]]  # [{"role": "analyzer", "task": "..."}]
    ) -> Dict[str, Any]:
        """
        Super simple: Main task + parallel subtasks
        """
        
        # Execute all in parallel
        tasks = [self._run_main(main_prompt)]
        tasks.extend([
            self._run_subtask(st["role"], st["task"]) 
            for st in subtasks
        ])
        
        results = await asyncio.gather(*tasks)
        
        # First result is main, rest are subtasks
        main_result = results[0]
        subtask_results = results[1:]
        
        # Simple synthesis
        return {
            "main_response": main_result,
            "subtask_results": [
                {"role": subtasks[i]["role"], "result": r}
                for i, r in enumerate(subtask_results)
            ]
        }
    
    async def _run_main(self, prompt: str) -> str:
        response = self.anthropic.messages.create(
            model="claude-sonnet-4-5",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        return response.content[0].text
    
    async def _run_subtask(self, role: str, task: str) -> str:
        prompts = {
            "analyzer": "You are an analyst. ",
            "researcher": "You are a researcher. ",
            "writer": "You are a writer. "
        }
        
        response = self.anthropic.messages.create(
            model="claude-sonnet-4-5",  # Or Haiku for speed
            messages=[{
                "role": "user",
                "content": prompts.get(role, "") + task
            }],
            max_tokens=1000
        )
        return response.content[0].text


# Usage examples
async def example_usage():
    # Efficient orchestrator - LLM decides
    orchestrator = EfficientOrchestrator()
    result = await orchestrator.process(
        "Analyze the Python code in main.py and write documentation for it"
    )
    
    # Ultra-light - you decide the tasks
    ultra = UltraLightOrchestrator()
    result = await ultra.parallel_process(
        main_prompt="I need help improving my Python web app",
        subtasks=[
            {"role": "analyzer", "task": "Analyze common Python web app performance issues"},
            {"role": "researcher", "task": "Research latest Python web frameworks"},
            {"role": "writer", "task": "Write best practices for Python web apps"}
        ]
    )