"""
MCP-Agent Workflow Pattern Demos

Comprehensive examples of mcp-agent's workflow patterns:
1. Basic Agent (single LLM)
2. Orchestrator-Workers (complex task breakdown)
3. Parallel Processing (fan-out/fan-in)
4. Router (intelligent endpoint selection)
5. Swarm (collaborative agents)
6. Intent Classifier (request categorization)

Run individual demos to understand each pattern.
"""
import asyncio
import time
from typing import Dict, Any, List
import logging

from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm import RequestParams

# Import workflow patterns
from mcp_agent.workflows.orchestrator.orchestrator import Orchestrator
from mcp_agent.workflows.parallel.parallel_llm import ParallelLLM
from mcp_agent.workflows.router.router_llm_anthropic import RouterLLMAnthropic
from mcp_agent.workflows.intent_classifier.intent_classifier_llm_anthropic import IntentClassifierLLMAnthropic

# Gaia integration
from app.shared.config import settings
from app.shared.logging import configure_logging_for_service

# Configure logging
configure_logging_for_service("mcp-agent-demos")
logger = logging.getLogger(__name__)

class MCPAgentWorkflowDemos:
    """Comprehensive demos of mcp-agent workflow patterns"""
    
    def __init__(self):
        self.app = MCPApp(name="gaia_workflow_demos")
        
    async def demo_1_basic_agent(self):
        """
        Demo 1: Basic Agent Pattern
        
        Single agent with single LLM - fastest, simplest pattern.
        Best for: Direct questions, simple tasks.
        """
        print("\n🤖 Demo 1: Basic Agent Pattern")
        print("=" * 50)
        
        async with self.app.run() as mcp_app:
            # Create simple agent
            agent = Agent(
                name="basic_assistant",
                instruction="You are a helpful assistant that answers questions concisely.",
                server_names=[]  # No MCP tools for speed
            )
            
            async with agent:
                # Attach LLM
                llm = await agent.attach_llm(AnthropicAugmentedLLM)
                
                # Test basic conversation
                questions = [
                    "What is 2+2?",
                    "Explain quantum physics in one sentence.",
                    "List 3 benefits of microservices."
                ]
                
                for q in questions:
                    start_time = time.time()
                    response = await llm.generate_str(
                        message=q,
                        request_params=RequestParams(
                            model="claude-3-5-sonnet-20241022",
                            temperature=0.7,
                            maxTokens=150
                        )
                    )
                    elapsed = time.time() - start_time
                    
                    print(f"Q: {q}")
                    print(f"A: {response}")
                    print(f"⏱️  {elapsed:.2f}s\n")
    
    async def demo_2_orchestrator_workers(self):
        """
        Demo 2: Orchestrator-Workers Pattern
        
        Central orchestrator breaks down complex tasks into subtasks,
        delegates to worker agents, synthesizes results.
        Best for: Complex multi-step tasks, code changes, research.
        """
        print("\n🎭 Demo 2: Orchestrator-Workers Pattern")
        print("=" * 50)
        
        async with self.app.run() as mcp_app:
            # Create worker agents with different specializations
            research_agent = Agent(
                name="research_specialist",
                instruction="You are a research specialist. Gather and analyze information thoroughly.",
                server_names=["fetch"]  # Can browse web
            )
            
            analysis_agent = Agent(
                name="analysis_specialist", 
                instruction="You are an analysis specialist. Break down complex data and find patterns.",
                server_names=[]
            )
            
            writer_agent = Agent(
                name="writing_specialist",
                instruction="You are a writing specialist. Create clear, structured documents.",
                server_names=[]
            )
            
            # Create orchestrator
            def llm_factory(agent: Agent):
                return AnthropicAugmentedLLM(agent=agent)
            
            orchestrator = Orchestrator(
                llm_factory=llm_factory,
                available_agents=[research_agent, analysis_agent, writer_agent],
                plan_type="iterative"  # Dynamic planning
            )
            
            # Complex task requiring multiple specialists
            complex_task = """
            Research the current state of MMOIRL (Massively Multiplayer Online In Real Life) 
            gaming concepts, analyze the technical architecture needed for sub-500ms response 
            times in real-world gaming scenarios, and write a brief technical summary.
            """
            
            start_time = time.time()
            result = await orchestrator.generate_str(
                message=complex_task,
                request_params=RequestParams(
                    model="claude-3-5-sonnet-20241022",
                    maxTokens=2000,
                    max_iterations=5
                )
            )
            elapsed = time.time() - start_time
            
            print(f"Task: {complex_task}")
            print(f"Result: {result}")
            print(f"⏱️  {elapsed:.2f}s")
    
    async def demo_3_parallel_processing(self):
        """
        Demo 3: Parallel Processing Pattern
        
        Fan-out multiple tasks to different agents simultaneously,
        then fan-in results for synthesis.
        Best for: Independent parallel tasks, performance optimization.
        """
        print("\n⚡ Demo 3: Parallel Processing Pattern")
        print("=" * 50)
        
        async with self.app.run() as mcp_app:
            # Create specialized agents for parallel work
            math_agent = Agent(
                name="math_specialist",
                instruction="You solve mathematical problems quickly and accurately.",
                server_names=[]
            )
            
            code_agent = Agent(
                name="code_specialist", 
                instruction="You analyze code and provide technical insights.",
                server_names=[]
            )
            
            business_agent = Agent(
                name="business_specialist",
                instruction="You provide business analysis and strategic insights.",
                server_names=[]
            )
            
            # Tasks that can be done in parallel
            parallel_tasks = [
                ("Calculate the server costs for 1000 concurrent users", math_agent),
                ("Review this architecture: microservices with Redis caching", code_agent),
                ("Analyze market opportunity for real-time gaming platforms", business_agent)
            ]
            
            async with math_agent, code_agent, business_agent:
                # Attach LLMs to agents
                math_llm = await math_agent.attach_llm(AnthropicAugmentedLLM)
                code_llm = await code_agent.attach_llm(AnthropicAugmentedLLM) 
                business_llm = await business_agent.attach_llm(AnthropicAugmentedLLM)
                
                llms = [math_llm, code_llm, business_llm]
                
                # Execute all tasks in parallel
                start_time = time.time()
                
                tasks = []
                for (task, _), llm in zip(parallel_tasks, llms):
                    tasks.append(llm.generate_str(
                        message=task,
                        request_params=RequestParams(
                            model="claude-3-5-sonnet-20241022",
                            maxTokens=300
                        )
                    ))
                
                results = await asyncio.gather(*tasks)
                elapsed = time.time() - start_time
                
                print("Parallel Task Results:")
                for (task, agent), result in zip(parallel_tasks, results):
                    print(f"\n{agent.name}: {task}")
                    print(f"→ {result[:100]}...")
                
                print(f"\n⏱️  All 3 tasks completed in {elapsed:.2f}s")
    
    async def demo_4_intelligent_router(self):
        """
        Demo 4: Router Pattern
        
        Analyzes incoming requests and routes to appropriate specialized agents.
        Best for: Multi-capability systems, endpoint selection.
        """
        print("\n🎯 Demo 4: Intelligent Router Pattern")
        print("=" * 50)
        
        async with self.app.run() as mcp_app:
            # Create specialized agents
            chat_agent = Agent(
                name="chat_assistant",
                instruction="Friendly conversational assistant for general chat.",
                server_names=[]
            )
            
            technical_agent = Agent(
                name="technical_assistant", 
                instruction="Technical expert for coding, architecture, and system design.",
                server_names=["filesystem"]  # Can access files
            )
            
            creative_agent = Agent(
                name="creative_assistant",
                instruction="Creative assistant for writing, brainstorming, and content creation.",
                server_names=[]
            )
            
            # Create router with classification logic
            router = RouterLLMAnthropic(
                agent=Agent(
                    name="request_router",
                    instruction="Route requests to the most appropriate specialist agent."
                ),
                available_agents={
                    "chat": chat_agent,
                    "technical": technical_agent, 
                    "creative": creative_agent
                }
            )
            
            # Test requests of different types
            test_requests = [
                "How are you doing today?",  # → chat
                "Explain microservices architecture patterns",  # → technical
                "Write a haiku about programming",  # → creative
                "Debug this Python function",  # → technical
                "What's the weather like?"  # → chat
            ]
            
            for request in test_requests:
                start_time = time.time()
                
                # Router analyzes and routes the request
                route_decision = await router.route(request)
                
                # Get the selected agent and generate response
                selected_agent = router.available_agents[route_decision]
                
                async with selected_agent:
                    llm = await selected_agent.attach_llm(AnthropicAugmentedLLM)
                    response = await llm.generate_str(
                        message=request,
                        request_params=RequestParams(maxTokens=200)
                    )
                
                elapsed = time.time() - start_time
                
                print(f"Request: {request}")
                print(f"→ Routed to: {route_decision} ({selected_agent.name})")
                print(f"→ Response: {response[:100]}...")
                print(f"⏱️  {elapsed:.2f}s\n")
    
    async def demo_5_intent_classifier(self):
        """
        Demo 5: Intent Classification Pattern
        
        Classifies user intent before processing to optimize routing and response.
        Best for: Multi-domain applications, workflow optimization.
        """
        print("\n🧠 Demo 5: Intent Classification Pattern")
        print("=" * 50)
        
        async with self.app.run() as mcp_app:
            # Define intent categories
            intents = [
                "technical_question",
                "general_chat", 
                "creative_request",
                "problem_solving",
                "information_lookup"
            ]
            
            # Create intent classifier
            classifier = IntentClassifierLLMAnthropic(
                agent=Agent(
                    name="intent_classifier",
                    instruction="Classify user requests into specific intent categories."
                ),
                intents=intents
            )
            
            # Test various requests
            test_requests = [
                "How do I optimize Redis for sub-500ms responses?",
                "Tell me a joke",
                "Write a story about AI robots",
                "My application is running slowly, help me debug it",
                "What is the capital of France?",
                "Explain MMOIRL architecture patterns",
                "Can you help me brainstorm game ideas?"
            ]
            
            for request in test_requests:
                start_time = time.time()
                
                # Classify intent
                intent = await classifier.classify(request)
                confidence = getattr(intent, 'confidence', 'unknown')
                
                elapsed = time.time() - start_time
                
                print(f"Request: {request}")
                print(f"→ Intent: {intent} (confidence: {confidence})")
                print(f"⏱️  {elapsed:.2f}s\n")
    
    async def demo_6_performance_comparison(self):
        """
        Demo 6: Performance Comparison
        
        Compare response times across different workflow patterns.
        """
        print("\n📊 Demo 6: Performance Comparison")
        print("=" * 50)
        
        test_question = "Explain the benefits of microservices architecture in 2 sentences."
        
        results = {}
        
        # Test 1: Basic Agent
        async with self.app.run():
            agent = Agent(name="basic", instruction="Answer concisely.", server_names=[])
            async with agent:
                llm = await agent.attach_llm(AnthropicAugmentedLLM)
                
                start_time = time.time()
                response = await llm.generate_str(test_question)
                results["Basic Agent"] = time.time() - start_time
        
        # Test 2: With MCP Tools (slower due to tool loading)
        async with self.app.run():
            agent = Agent(name="mcp", instruction="Answer with tool access.", server_names=["filesystem"])
            async with agent:
                llm = await agent.attach_llm(AnthropicAugmentedLLM)
                
                start_time = time.time()
                response = await llm.generate_str(test_question)
                results["With MCP Tools"] = time.time() - start_time
        
        # Test 3: Router (overhead for classification)
        async with self.app.run():
            base_agent = Agent(name="routed", instruction="Answer questions.", server_names=[])
            router = RouterLLMAnthropic(
                agent=Agent(name="router", instruction="Route requests."),
                available_agents={"general": base_agent}
            )
            
            start_time = time.time()
            route = await router.route(test_question)
            async with base_agent:
                llm = await base_agent.attach_llm(AnthropicAugmentedLLM)
                response = await llm.generate_str(test_question)
            results["Router Pattern"] = time.time() - start_time
        
        # Display results
        print("Performance Comparison Results:")
        print("-" * 40)
        for pattern, elapsed in sorted(results.items(), key=lambda x: x[1]):
            print(f"{pattern:20s}: {elapsed:.2f}s")
        
        print(f"\nFastest: {min(results.items(), key=lambda x: x[1])[0]}")
        print(f"Slowest: {max(results.items(), key=lambda x: x[1])[0]}")

async def run_all_demos():
    """Run all workflow pattern demos"""
    demos = MCPAgentWorkflowDemos()
    
    print("🚀 MCP-Agent Workflow Pattern Demos")
    print("=" * 60)
    
    try:
        await demos.demo_1_basic_agent()
        await demos.demo_2_orchestrator_workers() 
        await demos.demo_3_parallel_processing()
        await demos.demo_4_intelligent_router()
        await demos.demo_5_intent_classifier()
        await demos.demo_6_performance_comparison()
        
        print("\n✅ All demos completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
        print(f"❌ Demo failed: {e}")

async def run_single_demo(demo_name: str):
    """Run a specific demo"""
    demos = MCPAgentWorkflowDemos()
    
    demo_map = {
        "basic": demos.demo_1_basic_agent,
        "orchestrator": demos.demo_2_orchestrator_workers,
        "parallel": demos.demo_3_parallel_processing, 
        "router": demos.demo_4_intelligent_router,
        "classifier": demos.demo_5_intent_classifier,
        "performance": demos.demo_6_performance_comparison
    }
    
    if demo_name in demo_map:
        await demo_map[demo_name]()
    else:
        print(f"Unknown demo: {demo_name}")
        print(f"Available demos: {', '.join(demo_map.keys())}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        demo_name = sys.argv[1]
        asyncio.run(run_single_demo(demo_name))
    else:
        print("Usage:")
        print("  python demos/mcp_agent_workflow_demos.py [demo_name]")
        print("\nAvailable demos:")
        print("  basic       - Basic agent pattern")
        print("  orchestrator - Orchestrator-workers pattern") 
        print("  parallel    - Parallel processing pattern")
        print("  router      - Intelligent router pattern")
        print("  classifier  - Intent classification pattern")
        print("  performance - Performance comparison")
        print("  (no args)   - Run all demos")
        print()
        asyncio.run(run_all_demos())