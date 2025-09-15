"""
Production Multi-Agent Orchestration System

Incorporates best practices from AutoGPT, LangGraph, CrewAI, and Anthropic's research
"""
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Set, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import networkx as nx
from abc import ABC, abstractmethod

from anthropic import Anthropic
from pydantic import BaseModel


# Core Components based on best practices

class AgentRole(Enum):
    """Expanded agent roles for diverse use cases"""
    # Core roles
    ORCHESTRATOR = "orchestrator"
    SUPERVISOR = "supervisor"
    
    # Research & Analysis
    RESEARCHER = "researcher"
    FACT_CHECKER = "fact_checker"
    DATA_ANALYST = "data_analyst"
    MARKET_ANALYST = "market_analyst"
    
    # Creative & Content
    WRITER = "writer"
    EDITOR = "editor"
    DESIGNER = "designer"
    TRANSLATOR = "translator"
    
    # Technical
    CODER = "coder"
    ARCHITECT = "architect"
    DEBUGGER = "debugger"
    DEVOPS = "devops"
    
    # Business & Operations
    PROJECT_MANAGER = "project_manager"
    FINANCIAL_ANALYST = "financial_analyst"
    LEGAL_REVIEWER = "legal_reviewer"
    STRATEGIST = "strategist"
    
    # Specialized Tools
    TOOL_SPECIALIST = "tool_specialist"
    API_INTEGRATOR = "api_integrator"
    DATABASE_ADMIN = "database_admin"
    
    # Quality & Safety
    QUALITY_CHECKER = "quality_checker"
    SAFETY_MONITOR = "safety_monitor"
    COMPLIANCE_OFFICER = "compliance_officer"


@dataclass
class SharedContext:
    """Shared memory/context following best practices"""
    # Core context
    task_id: str
    original_request: str
    current_phase: str
    
    # Accumulated knowledge
    facts: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    
    # Agent communications
    messages: List[Dict[str, Any]] = field(default_factory=list)
    pending_questions: List[str] = field(default_factory=list)
    
    # State tracking
    completed_subtasks: Set[str] = field(default_factory=set)
    active_agents: Set[str] = field(default_factory=set)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Governance
    human_approvals_needed: List[Dict[str, Any]] = field(default_factory=list)
    audit_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_message(self, from_agent: str, to_agent: str, content: Any):
        """Add inter-agent message"""
        self.messages.append({
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_fact(self, key: str, value: Any, source: str):
        """Add verified fact to shared knowledge"""
        self.facts[key] = {
            "value": value,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
    
    def log_audit(self, agent: str, action: str, details: Any):
        """Add to audit log for governance"""
        self.audit_log.append({
            "agent": agent,
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })


class BaseAgent(ABC):
    """Base agent following CrewAI/LangGraph patterns"""
    
    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        capabilities: Set[str],
        model: str = "claude-3-5-sonnet-20241022"
    ):
        self.agent_id = agent_id
        self.role = role
        self.capabilities = capabilities
        self.model = model
        self.anthropic = Anthropic()
        self.status = "idle"
        
    @abstractmethod
    def get_system_prompt(self, context: SharedContext) -> str:
        """Get role-specific system prompt"""
        pass
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any], context: SharedContext) -> Dict[str, Any]:
        """Execute assigned task with shared context"""
        pass
    
    async def communicate(self, target_agent: str, message: Any, context: SharedContext):
        """Send message to another agent via shared context"""
        context.add_message(self.agent_id, target_agent, message)
    
    def log_action(self, action: str, details: Any, context: SharedContext):
        """Log action for audit trail"""
        context.log_audit(self.agent_id, action, details)


class GraphOrchestrator:
    """
    LangGraph-inspired orchestration using directed graphs
    """
    
    def __init__(self):
        self.workflow_graph = nx.DiGraph()
        self.agents: Dict[str, BaseAgent] = {}
        self.shared_context: Optional[SharedContext] = None
        self.execution_history: List[Dict[str, Any]] = []
        
    def add_agent_node(self, agent: BaseAgent, dependencies: List[str] = None):
        """Add agent as node in workflow graph"""
        self.agents[agent.agent_id] = agent
        self.workflow_graph.add_node(agent.agent_id, agent=agent)
        
        # Add edges for dependencies
        if dependencies:
            for dep in dependencies:
                self.workflow_graph.add_edge(dep, agent.agent_id)
    
    def add_conditional_edge(
        self, 
        from_agent: str, 
        to_agent: str, 
        condition: Callable[[SharedContext], bool]
    ):
        """Add conditional edge between agents"""
        self.workflow_graph.add_edge(
            from_agent, 
            to_agent, 
            condition=condition
        )
    
    async def execute_workflow(
        self, 
        initial_request: str,
        parallel: bool = True
    ) -> Dict[str, Any]:
        """Execute workflow following graph structure"""
        
        # Initialize shared context
        self.shared_context = SharedContext(
            task_id=str(uuid.uuid4()),
            original_request=initial_request,
            current_phase="initialization"
        )
        
        # Topological sort for execution order
        try:
            execution_order = list(nx.topological_sort(self.workflow_graph))
        except nx.NetworkXError:
            # Has cycles, use BFS instead
            execution_order = list(nx.bfs_tree(self.workflow_graph, source=list(self.workflow_graph.nodes)[0]))
        
        # Execute agents
        if parallel:
            await self._execute_parallel(execution_order)
        else:
            await self._execute_sequential(execution_order)
        
        return self._compile_results()
    
    async def _execute_parallel(self, execution_order: List[str]):
        """Execute agents in parallel where possible"""
        completed = set()
        
        while len(completed) < len(execution_order):
            # Find agents ready to execute
            ready = []
            for agent_id in execution_order:
                if agent_id not in completed:
                    # Check if all dependencies completed
                    deps = list(self.workflow_graph.predecessors(agent_id))
                    if all(d in completed for d in deps):
                        ready.append(agent_id)
            
            # Execute ready agents in parallel
            if ready:
                tasks = []
                for agent_id in ready:
                    task = self._execute_agent(agent_id)
                    tasks.append(task)
                
                await asyncio.gather(*tasks)
                completed.update(ready)
            else:
                # Prevent infinite loop
                break
    
    async def _execute_agent(self, agent_id: str) -> Dict[str, Any]:
        """Execute single agent with error handling"""
        agent = self.agents[agent_id]
        
        try:
            self.shared_context.active_agents.add(agent_id)
            
            # Prepare task from context
            task = {
                "request": self.shared_context.original_request,
                "phase": self.shared_context.current_phase,
                "prior_results": self._get_prior_results(agent_id)
            }
            
            # Execute
            result = await agent.execute(task, self.shared_context)
            
            # Log execution
            self.execution_history.append({
                "agent_id": agent_id,
                "role": agent.role.value,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            self.shared_context.active_agents.remove(agent_id)
            self.shared_context.completed_subtasks.add(agent_id)
            
            return result
            
        except Exception as e:
            self.shared_context.errors.append({
                "agent_id": agent_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return {"error": str(e)}


class SwarmOrchestrator:
    """
    CrewAI-inspired swarm orchestration with team dynamics
    """
    
    def __init__(self):
        self.crews: Dict[str, List[BaseAgent]] = {}
        self.crew_leaders: Dict[str, BaseAgent] = {}
        self.shared_context = None
        
    def create_crew(
        self, 
        crew_name: str, 
        leader: BaseAgent, 
        members: List[BaseAgent]
    ):
        """Create a crew with leader and members"""
        self.crew_leaders[crew_name] = leader
        self.crews[crew_name] = members
        
        # Leader supervises all members
        for member in members:
            member.supervisor = leader.agent_id
    
    async def execute_crew_task(
        self, 
        crew_name: str, 
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute task with crew coordination"""
        
        leader = self.crew_leaders[crew_name]
        members = self.crews[crew_name]
        
        # Leader decomposes task
        subtasks = await self._leader_decompose_task(leader, task)
        
        # Assign subtasks to members
        assignments = await self._leader_assign_tasks(leader, subtasks, members)
        
        # Execute in parallel with supervision
        results = await self._execute_with_supervision(assignments, leader)
        
        # Leader aggregates results
        final_result = await self._leader_aggregate(leader, results)
        
        return final_result


class AdaptiveOrchestrator:
    """
    Production-ready orchestrator combining best practices
    """
    
    def __init__(self):
        self.anthropic = Anthropic()
        self.graph_orchestrator = GraphOrchestrator()
        self.swarm_orchestrator = SwarmOrchestrator()
        
        # Agent registry
        self.available_agents: Dict[AgentRole, List[BaseAgent]] = {}
        
        # Orchestration strategies
        self.strategies = {
            "simple": self._simple_sequential,
            "parallel": self._parallel_execution,
            "graph": self._graph_based_execution,
            "swarm": self._swarm_execution,
            "adaptive": self._adaptive_execution
        }
        
        # Monitoring
        self.metrics = {
            "tasks_completed": 0,
            "average_time": 0,
            "error_rate": 0,
            "human_interventions": 0
        }
    
    async def process_request(
        self,
        request: str,
        strategy: str = "adaptive",
        constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process request with chosen orchestration strategy
        """
        
        # Analyze request to determine best approach
        analysis = await self._analyze_request(request)
        
        # Select strategy
        if strategy == "adaptive":
            strategy = self._select_optimal_strategy(analysis)
        
        # Initialize shared context
        context = SharedContext(
            task_id=str(uuid.uuid4()),
            original_request=request,
            current_phase="planning"
        )
        
        # Execute with chosen strategy
        executor = self.strategies.get(strategy, self._adaptive_execution)
        result = await executor(request, analysis, context)
        
        # Update metrics
        self._update_metrics(context)
        
        return {
            "result": result,
            "strategy_used": strategy,
            "agents_involved": len(context.completed_subtasks),
            "execution_time": self._calculate_execution_time(context),
            "human_approvals": len(context.human_approvals_needed),
            "audit_trail": context.audit_log
        }
    
    async def _analyze_request(self, request: str) -> Dict[str, Any]:
        """Analyze request to determine complexity and requirements"""
        
        analysis_prompt = """Analyze this request and determine:
1. Complexity level (1-10)
2. Required agent roles
3. Whether it needs parallel execution
4. Whether it needs human oversight
5. Estimated subtasks
6. Domain areas involved

Request: {request}

Respond in JSON format."""

        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{
                "role": "user",
                "content": analysis_prompt.format(request=request)
            }],
            max_tokens=500
        )
        
        # Parse analysis
        try:
            analysis = json.loads(response.content[0].text)
            return analysis
        except:
            return {
                "complexity": 5,
                "roles": ["researcher", "writer"],
                "parallel": False,
                "human_oversight": False,
                "subtasks": 3,
                "domains": ["general"]
            }
    
    def _select_optimal_strategy(self, analysis: Dict[str, Any]) -> str:
        """Select optimal orchestration strategy based on analysis"""
        
        complexity = analysis.get("complexity", 5)
        parallel_needed = analysis.get("parallel", False)
        subtasks = analysis.get("subtasks", 1)
        
        if complexity <= 3 and subtasks <= 2:
            return "simple"
        elif parallel_needed and subtasks > 3:
            return "parallel"
        elif complexity > 7 and len(analysis.get("roles", [])) > 4:
            return "swarm"
        elif subtasks > 5:
            return "graph"
        else:
            return "adaptive"
    
    async def _adaptive_execution(
        self, 
        request: str, 
        analysis: Dict[str, Any], 
        context: SharedContext
    ) -> Dict[str, Any]:
        """
        Adaptive execution that can switch strategies mid-flight
        """
        
        # Start with initial strategy
        current_strategy = self._select_optimal_strategy(analysis)
        
        # Monitor and adapt
        while context.current_phase != "completed":
            # Execute current phase
            phase_result = await self._execute_phase(
                current_strategy, 
                context
            )
            
            # Check if strategy switch needed
            if self._should_switch_strategy(context):
                current_strategy = self._determine_new_strategy(context)
                context.log_audit(
                    "orchestrator", 
                    "strategy_switch", 
                    {"from": current_strategy, "to": current_strategy}
                )
            
            # Check if human intervention needed
            if context.human_approvals_needed:
                await self._handle_human_approvals(context)
            
            # Progress to next phase
            context.current_phase = self._determine_next_phase(context)
        
        return self._compile_final_results(context)


# Example specialized agents

class ResearchAgent(BaseAgent):
    """Research specialist agent"""
    
    def get_system_prompt(self, context: SharedContext) -> str:
        return """You are a research specialist. Your role:
- Gather accurate, relevant information
- Verify sources and credibility
- Identify knowledge gaps
- Summarize findings clearly
- Flag any contradictions or uncertainties

Current context: {context}"""

    async def execute(self, task: Dict[str, Any], context: SharedContext) -> Dict[str, Any]:
        # Implementation would use tools for research
        pass


class QualityAgent(BaseAgent):
    """Quality assurance agent"""
    
    def get_system_prompt(self, context: SharedContext) -> str:
        return """You are a quality assurance specialist. Your role:
- Review work from other agents
- Check for errors, inconsistencies
- Verify requirements are met
- Suggest improvements
- Ensure standards compliance"""

    async def execute(self, task: Dict[str, Any], context: SharedContext) -> Dict[str, Any]:
        # Review artifacts in context
        pass


# Usage example
async def example_production_orchestration():
    orchestrator = AdaptiveOrchestrator()
    
    # Complex multi-domain request
    result = await orchestrator.process_request(
        """I'm planning to launch a new product. I need:
        1. Market research on competitors
        2. Financial projections for 3 years
        3. Legal compliance review
        4. Marketing strategy
        5. Technical architecture if it's a software product
        
        The product is an AI-powered personal finance app.
        """,
        strategy="adaptive"
    )
    
    print(f"Strategy used: {result['strategy_used']}")
    print(f"Agents involved: {result['agents_involved']}")
    print(f"Execution time: {result['execution_time']}s")
    print(f"Human approvals needed: {result['human_approvals']}")