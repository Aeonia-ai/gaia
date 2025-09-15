"""
Orchestration Examples

Examples of using the custom orchestration system for various use cases.
"""
import asyncio
from app.services.chat.custom_orchestration import CustomOrchestrator, SimpleOrchestrator
from app.services.chat.orchestrated_chat import OrchestrationPatterns


async def example_direct_orchestration():
    """Example: Let the orchestrator decide how to handle a request"""
    
    orchestrator = CustomOrchestrator()
    
    # Simple request - should answer directly
    result = await orchestrator.orchestrate(
        "What is the capital of France?"
    )
    print(f"Simple request: {result.tasks_executed} agents used")
    print(f"Response: {result.response}\n")
    
    # Complex request - should spawn agents
    result = await orchestrator.orchestrate(
        "Research the latest developments in quantum computing, analyze their implications for cryptography, and write a summary report"
    )
    print(f"Complex request: {result.tasks_executed} agents used")
    print(f"Response: {result.response[:200]}...")
    print(f"Task details: {result.task_details}\n")


async def example_simple_orchestration():
    """Example: Directly specify which agents to run"""
    
    simple = SimpleOrchestrator()
    
    # Run specific agents with dependencies
    agents = [
        {
            "role": "researcher",
            "task": "Research current Python web frameworks and their pros/cons",
            "parallel": True
        },
        {
            "role": "analyst",
            "task": "Analyze which framework would be best for a startup",
            "parallel": False,
            "depends_on": [0]  # Wait for researcher
        },
        {
            "role": "writer",
            "task": "Write a recommendation report with clear justification",
            "parallel": False,
            "depends_on": [1]  # Wait for analyst
        }
    ]
    
    result = await simple.run_agents(agents)
    
    print(f"Executed {result['count']} agents")
    print(f"Success: {result['success']}")
    
    # Show individual results
    for idx, agent_result in result['results'].items():
        print(f"\nAgent {idx} ({agent_result['role']}):")
        print(f"Task: {agent_result['task']}")
        print(f"Result: {agent_result['result'][:200]}...")


async def example_patterns():
    """Example: Use pre-defined orchestration patterns"""
    
    simple = SimpleOrchestrator()
    
    # Use the code review pattern
    code_review_agents = OrchestrationPatterns.code_review_pattern()
    
    # Customize the tasks
    code_review_agents[0]["task"] = "Analyze the Python code in src/main.py for issues"
    code_review_agents[1]["task"] = "Check for security vulnerabilities and performance problems"
    code_review_agents[2]["task"] = "Suggest refactoring improvements"
    
    result = await simple.run_agents(code_review_agents)
    
    print("Code Review Results:")
    for idx, agent_result in result['results'].items():
        print(f"\n{agent_result['role'].upper()}:")
        print(agent_result['result'][:300] + "...")


async def example_parallel_research():
    """Example: Parallel research on multiple topics"""
    
    orchestrator = CustomOrchestrator()
    
    # Research multiple topics in parallel
    result = await orchestrator.orchestrate(
        """I need comprehensive research on three topics:
        1. The current state of renewable energy technology
        2. Recent breakthroughs in medical AI
        3. Emerging trends in sustainable agriculture
        
        For each topic, provide key developments, challenges, and future outlook."""
    )
    
    print(f"Parallel research used {result.tasks_executed} agents")
    print(f"Total time: {result.total_time:.2f}s")
    
    # Show which agents ran in parallel
    for task in result.task_details:
        print(f"- {task['role']}: {task['description'][:50]}... ({task['execution_time']:.2f}s)")


async def example_error_handling():
    """Example: How orchestration handles errors"""
    
    orchestrator = CustomOrchestrator()
    
    # Request that might cause some agents to fail
    result = await orchestrator.orchestrate(
        "Access the file /restricted/secret.txt, analyze its contents, and write a summary",
        timeout=10.0  # Short timeout
    )
    
    print(f"Success: {result.success}")
    print(f"Errors: {result.errors}")
    print(f"Response: {result.response}")


async def example_custom_agents():
    """Example: Create custom agent configurations"""
    
    simple = SimpleOrchestrator()
    
    # Custom agent setup for a specific workflow
    agents = [
        {
            "role": "researcher",
            "task": "Find the latest statistics on remote work adoption post-2020",
            "parallel": True
        },
        {
            "role": "researcher",  # Multiple researchers in parallel
            "task": "Research the impact of remote work on productivity",
            "parallel": True
        },
        {
            "role": "researcher",
            "task": "Find case studies of successful remote-first companies",
            "parallel": True
        },
        {
            "role": "analyst",
            "task": "Synthesize all research findings and identify key trends",
            "parallel": False,
            "depends_on": [0, 1, 2]  # Wait for all researchers
        },
        {
            "role": "writer",
            "task": "Create an executive summary with actionable insights",
            "parallel": False,
            "depends_on": [3]
        }
    ]
    
    result = await simple.run_agents(agents)
    
    # Show execution flow
    print("Execution flow:")
    print("- Phase 1: 3 researchers in parallel")
    print("- Phase 2: 1 analyst (after all research)")
    print("- Phase 3: 1 writer (after analysis)")
    print(f"\nFinal report:\n{result['results'][4]['result']}")


# Performance comparison example
async def example_performance_comparison():
    """Compare performance of different approaches"""
    
    import time
    
    test_request = "Explain the concept of machine learning and provide three practical examples"
    
    # Test 1: Custom Orchestrator (let it decide)
    orchestrator = CustomOrchestrator()
    start = time.time()
    result1 = await orchestrator.orchestrate(test_request)
    time1 = time.time() - start
    
    # Test 2: Simple Orchestrator (direct specification)
    simple = SimpleOrchestrator()
    start = time.time()
    result2 = await simple.run_agents([
        {"role": "writer", "task": test_request, "parallel": True}
    ])
    time2 = time.time() - start
    
    print("Performance Comparison:")
    print(f"Custom Orchestrator: {time1:.2f}s ({result1.tasks_executed} agents)")
    print(f"Simple Orchestrator: {time2:.2f}s (1 agent)")
    print(f"Overhead: {time1 - time2:.2f}s")


if __name__ == "__main__":
    # Run examples
    async def main():
        print("=== Custom Orchestration Examples ===\n")
        
        print("1. Direct Orchestration")
        await example_direct_orchestration()
        
        print("\n2. Simple Orchestration")
        await example_simple_orchestration()
        
        print("\n3. Using Patterns")
        await example_patterns()
        
        print("\n4. Parallel Research")
        await example_parallel_research()
        
        print("\n5. Error Handling")
        await example_error_handling()
        
        print("\n6. Custom Agents")
        await example_custom_agents()
        
        print("\n7. Performance Comparison")
        await example_performance_comparison()
    
    asyncio.run(main())