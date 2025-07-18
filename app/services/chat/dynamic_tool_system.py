"""
Dynamic Tool System - LLM-Driven Tool Selection with State Navigation

Tools are dynamically injected based on:
- Current state in a workflow
- User permissions/roles
- System capabilities
- Context requirements
"""
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
from abc import ABC, abstractmethod

from anthropic import Anthropic
from pydantic import BaseModel


class ToolAvailability(Enum):
    ALWAYS = "always"
    CONDITIONAL = "conditional"
    STATE_DEPENDENT = "state_dependent"
    PERMISSION_BASED = "permission_based"


@dataclass
class Tool:
    """Base tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    availability: ToolAvailability = ToolAvailability.ALWAYS
    required_permissions: Set[str] = field(default_factory=set)
    required_state: Optional[str] = None
    cost_tokens: int = 0  # Estimated token cost
    execution_time_ms: int = 1000  # Estimated execution time
    
    # The actual implementation
    execute: Optional[Callable] = None
    
    # Conditions for availability
    is_available: Optional[Callable] = None


@dataclass
class WorkflowState:
    """Current state in a workflow/conversation"""
    current_node: str
    completed_nodes: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    user_permissions: Set[str] = field(default_factory=set)
    system_capabilities: Set[str] = field(default_factory=set)


class StateNode:
    """Node in a state tree with available tools"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.tools: List[Tool] = []
        self.transitions: Dict[str, 'StateNode'] = {}
        self.entry_conditions: List[Callable] = []
        self.exit_conditions: List[Callable] = []
    
    def add_tool(self, tool: Tool):
        """Add a tool available in this state"""
        self.tools.append(tool)
    
    def add_transition(self, trigger: str, target_node: 'StateNode'):
        """Add a state transition"""
        self.transitions[trigger] = target_node


class DynamicToolSystem:
    """
    Dynamic tool system where LLM decides what tools to use
    based on current state and context
    """
    
    def __init__(self):
        self.anthropic = Anthropic()
        self.global_tools: List[Tool] = []  # Always available
        self.conditional_tools: List[Tool] = []  # Conditionally available
        self.state_tree: Dict[str, StateNode] = {}
        self.current_state: Optional[WorkflowState] = None
        
        # Tool implementations registry
        self.tool_implementations: Dict[str, Callable] = {}
        
        # Initialize with base tools
        self._initialize_base_tools()
        
    def _initialize_base_tools(self):
        """Initialize always-available tools"""
        
        # Navigation tool - always available
        self.global_tools.append(Tool(
            name="navigate_state",
            description="Navigate to a different state in the workflow",
            input_schema={
                "type": "object",
                "properties": {
                    "target_state": {"type": "string"},
                    "reason": {"type": "string"}
                }
            },
            availability=ToolAvailability.ALWAYS,
            cost_tokens=10,
            execution_time_ms=100
        ))
        
        # Context inspection tool
        self.global_tools.append(Tool(
            name="inspect_context",
            description="Inspect current workflow context and state",
            input_schema={"type": "object", "properties": {}},
            availability=ToolAvailability.ALWAYS,
            cost_tokens=5,
            execution_time_ms=50
        ))
    
    def create_state_tree_example(self):
        """Example: Create a code review workflow state tree"""
        
        # Initial state
        initial = StateNode("initial", "Starting point")
        initial.add_tool(Tool(
            name="analyze_request",
            description="Analyze what the user wants to do",
            input_schema={
                "type": "object",
                "properties": {
                    "request_type": {"type": "string"},
                    "complexity": {"type": "integer", "minimum": 1, "maximum": 10}
                }
            }
        ))
        
        # Code analysis state
        code_analysis = StateNode("code_analysis", "Analyzing code")
        code_analysis.add_tool(Tool(
            name="list_files",
            description="List files in repository",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}}
            },
            required_permissions={"filesystem_read"}
        ))
        code_analysis.add_tool(Tool(
            name="read_file",
            description="Read a specific file",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}}
            },
            required_permissions={"filesystem_read"}
        ))
        code_analysis.add_tool(Tool(
            name="run_linter",
            description="Run code linter",
            input_schema={
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}}
                }
            },
            required_permissions={"code_analysis"}
        ))
        
        # Bug fixing state
        bug_fixing = StateNode("bug_fixing", "Fixing identified issues")
        bug_fixing.add_tool(Tool(
            name="edit_file",
            description="Edit a file to fix issues",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "changes": {"type": "array"}
                }
            },
            required_permissions={"filesystem_write"}
        ))
        bug_fixing.add_tool(Tool(
            name="run_tests",
            description="Run tests to verify fixes",
            input_schema={
                "type": "object",
                "properties": {"test_files": {"type": "array"}}
            },
            required_permissions={"code_execution"}
        ))
        
        # Review complete state
        review_complete = StateNode("review_complete", "Review completed")
        review_complete.add_tool(Tool(
            name="generate_report",
            description="Generate review report",
            input_schema={
                "type": "object",
                "properties": {
                    "include_metrics": {"type": "boolean"},
                    "format": {"type": "string", "enum": ["markdown", "json"]}
                }
            }
        ))
        
        # Set up transitions
        initial.add_transition("start_analysis", code_analysis)
        code_analysis.add_transition("issues_found", bug_fixing)
        code_analysis.add_transition("no_issues", review_complete)
        bug_fixing.add_transition("fixes_complete", review_complete)
        
        # Add to state tree
        self.state_tree = {
            "initial": initial,
            "code_analysis": code_analysis,
            "bug_fixing": bug_fixing,
            "review_complete": review_complete
        }
    
    def get_available_tools(self, state: Optional[WorkflowState] = None) -> List[Tool]:
        """Get all tools available in current state"""
        if state is None:
            state = self.current_state
        
        available = []
        
        # 1. Global tools (always available)
        available.extend(self.global_tools)
        
        # 2. State-specific tools
        if state and state.current_node in self.state_tree:
            node = self.state_tree[state.current_node]
            for tool in node.tools:
                # Check permissions
                if tool.required_permissions.issubset(state.user_permissions):
                    # Check custom availability
                    if tool.is_available is None or tool.is_available(state):
                        available.append(tool)
        
        # 3. Conditional tools based on context
        for tool in self.conditional_tools:
            if self._check_tool_conditions(tool, state):
                available.append(tool)
        
        return available
    
    def _check_tool_conditions(self, tool: Tool, state: WorkflowState) -> bool:
        """Check if a conditional tool should be available"""
        # Check permissions
        if not tool.required_permissions.issubset(state.user_permissions):
            return False
        
        # Check required state
        if tool.required_state and state.current_node != tool.required_state:
            return False
        
        # Check custom availability function
        if tool.is_available and not tool.is_available(state):
            return False
        
        return True
    
    async def process_with_dynamic_tools(
        self,
        message: str,
        initial_state: Optional[WorkflowState] = None
    ) -> Dict[str, Any]:
        """
        Process a message with dynamically available tools
        
        The LLM can:
        1. Use available tools in current state
        2. Navigate to different states
        3. Discover what tools become available in each state
        """
        if initial_state:
            self.current_state = initial_state
        elif not self.current_state:
            # Start with initial state
            self.current_state = WorkflowState(
                current_node="initial",
                user_permissions={"filesystem_read", "code_analysis"}  # Example
            )
        
        # Get available tools for current state
        available_tools = self.get_available_tools()
        
        # Build tool descriptions for LLM
        tool_descriptions = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "metadata": {
                    "cost_tokens": tool.cost_tokens,
                    "execution_time_ms": tool.execution_time_ms,
                    "state_required": tool.required_state
                }
            }
            for tool in available_tools
        ]
        
        # Create state-aware system prompt
        system_prompt = f"""You are an AI assistant navigating a workflow.

Current State: {self.current_state.current_node}
State Description: {self.state_tree[self.current_state.current_node].description if self.current_state.current_node in self.state_tree else 'Unknown'}

Available transitions from this state:
{self._format_transitions()}

Context:
{json.dumps(self.current_state.context, indent=2)}

You have access to tools that change based on your current state. 
Use navigate_state to move between states and unlock different capabilities.
Always explain why you're navigating to a new state.
"""
        
        # LLM call with dynamic tools
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            tools=tool_descriptions,
            max_tokens=2000
        )
        
        # Process tool calls
        tool_results = []
        state_changed = False
        
        for content in response.content:
            if content.type == "tool_use":
                result = await self._execute_tool(
                    content.name,
                    content.input
                )
                tool_results.append(result)
                
                # Check if state changed
                if content.name == "navigate_state":
                    state_changed = True
                    new_state = content.input["target_state"]
                    self.current_state.current_node = new_state
                    self.current_state.completed_nodes.append(new_state)
        
        # If state changed, offer to show new tools
        if state_changed:
            new_tools = self.get_available_tools()
            tool_names = [t.name for t in new_tools]
            
            # Continue conversation with new state info
            continuation = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": f"You've navigated to {self.current_state.current_node}. Available tools now: {tool_names}"}
                ],
                tools=[t for t in tool_descriptions if t["name"] in tool_names],
                max_tokens=1000
            )
            
            return {
                "response": continuation.content[0].text,
                "state": self.current_state.current_node,
                "tools_used": [r["tool"] for r in tool_results],
                "available_tools": tool_names
            }
        
        return {
            "response": response.content[0].text if response.content else "",
            "state": self.current_state.current_node,
            "tools_used": [r["tool"] for r in tool_results],
            "tool_results": tool_results
        }
    
    def _format_transitions(self) -> str:
        """Format available transitions for current state"""
        if self.current_state.current_node not in self.state_tree:
            return "No transitions available"
        
        node = self.state_tree[self.current_state.current_node]
        if not node.transitions:
            return "No transitions available"
        
        lines = []
        for trigger, target in node.transitions.items():
            lines.append(f"- {trigger} → {target.name}: {target.description}")
        
        return "\n".join(lines)
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return results"""
        # Special handling for navigation
        if tool_name == "navigate_state":
            return {
                "tool": tool_name,
                "success": True,
                "result": f"Navigated to state: {args['target_state']}"
            }
        
        # Look up implementation
        if tool_name in self.tool_implementations:
            try:
                result = await self.tool_implementations[tool_name](args, self.current_state)
                return {
                    "tool": tool_name,
                    "success": True,
                    "result": result
                }
            except Exception as e:
                return {
                    "tool": tool_name,
                    "success": False,
                    "error": str(e)
                }
        
        return {
            "tool": tool_name,
            "success": False,
            "error": "Tool not implemented"
        }
    
    def register_tool_implementation(self, tool_name: str, implementation: Callable):
        """Register a tool implementation"""
        self.tool_implementations[tool_name] = implementation


# Example: Dynamic tool injection based on discovered context
class ContextAwareToolInjector:
    """Inject tools based on discovered context"""
    
    def __init__(self, tool_system: DynamicToolSystem):
        self.tool_system = tool_system
    
    async def inject_tools_from_context(self, context: Dict[str, Any]):
        """Dynamically inject tools based on context"""
        
        # Example: If we discover a database connection
        if "database_url" in context:
            self.tool_system.conditional_tools.append(Tool(
                name="execute_sql",
                description="Execute SQL queries on discovered database",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}}
                },
                required_permissions={"database_access"},
                is_available=lambda state: "database_url" in state.context
            ))
        
        # Example: If we discover Kubernetes config
        if "kubeconfig" in context:
            self.tool_system.conditional_tools.extend([
                Tool(
                    name="kubectl_get",
                    description="Get Kubernetes resources",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "resource": {"type": "string"},
                            "namespace": {"type": "string"}
                        }
                    },
                    required_permissions={"kubernetes_read"}
                ),
                Tool(
                    name="kubectl_apply",
                    description="Apply Kubernetes configuration",
                    input_schema={
                        "type": "object",
                        "properties": {"manifest": {"type": "string"}}
                    },
                    required_permissions={"kubernetes_write"}
                )
            ])
        
        # Example: If we're in a git repository
        if "git_repo" in context:
            self.tool_system.conditional_tools.append(Tool(
                name="git_operations",
                description="Perform git operations",
                input_schema={
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["status", "diff", "commit", "push"]},
                        "args": {"type": "object"}
                    }
                },
                required_permissions={"git_access"}
            ))


# Usage example
async def example_dynamic_workflow():
    # Create the dynamic tool system
    system = DynamicToolSystem()
    system.create_state_tree_example()
    
    # Set initial permissions
    initial_state = WorkflowState(
        current_node="initial",
        user_permissions={"filesystem_read", "code_analysis", "filesystem_write", "code_execution"}
    )
    
    # Process a complex request
    result = await system.process_with_dynamic_tools(
        "Review the Python files in src/, fix any bugs you find, and generate a report",
        initial_state
    )
    
    print(f"Final state: {result['state']}")
    print(f"Tools used: {result['tools_used']}")
    print(f"Response: {result['response']}")