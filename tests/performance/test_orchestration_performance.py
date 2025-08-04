"""
Test orchestration performance with real timings
"""
import asyncio
import time
import os
from typing import List, Dict, Any

# Set up environment
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")

from app.services.chat.custom_orchestration import CustomOrchestrator, SimpleOrchestrator


async def test_direct_response():
    """Test simple question that shouldn't spawn agents"""
    orchestrator = CustomOrchestrator()
    
    start = time.time()
    result = await orchestrator.orchestrate("What is 2+2?")
    end = time.time()
    
    return {
        "type": "direct_response",
        "time": end - start,
        "agents_spawned": result.tasks_executed,
        "response_preview": result.response[:100]
    }


async def test_single_agent():
    """Test spawning a single agent"""
    orchestrator = CustomOrchestrator()
    
    start = time.time()
    result = await orchestrator.orchestrate(
        "Write a haiku about Python programming"
    )
    end = time.time()
    
    return {
        "type": "single_agent",
        "time": end - start,
        "agents_spawned": result.tasks_executed,
        "response_preview": result.response[:100]
    }


async def test_sequential_agents():
    """Test sequential agent execution"""
    orchestrator = CustomOrchestrator()
    
    start = time.time()
    result = await orchestrator.orchestrate(
        "Research the history of Python, then write a short summary about its creator"
    )
    end = time.time()
    
    return {
        "type": "sequential_agents",
        "time": end - start,
        "agents_spawned": result.tasks_executed,
        "task_details": result.task_details
    }


async def test_parallel_agents():
    """Test parallel agent execution"""
    orchestrator = CustomOrchestrator()
    
    start = time.time()
    result = await orchestrator.orchestrate(
        "I need three things done independently: 1) List 5 Python best practices, 2) Explain what REST APIs are, 3) Describe the MVC pattern"
    )
    end = time.time()
    
    return {
        "type": "parallel_agents",
        "time": end - start,
        "agents_spawned": result.tasks_executed,
        "task_details": result.task_details
    }


async def test_complex_workflow():
    """Test complex multi-agent workflow"""
    orchestrator = CustomOrchestrator()
    
    start = time.time()
    result = await orchestrator.orchestrate(
        "Analyze the pros and cons of microservices architecture, research real-world case studies, and write a recommendation for a startup"
    )
    end = time.time()
    
    return {
        "type": "complex_workflow",
        "time": end - start,
        "agents_spawned": result.tasks_executed,
        "task_details": result.task_details
    }


async def test_simple_orchestrator():
    """Test the SimpleOrchestrator with known agents"""
    simple = SimpleOrchestrator()
    
    agents = [
        {"role": "writer", "task": "Write a joke about programming", "parallel": True}
    ]
    
    start = time.time()
    result = await simple.run_agents(agents)
    end = time.time()
    
    return {
        "type": "simple_orchestrator",
        "time": end - start,
        "agents_count": len(agents),
        "success": result["success"]
    }


async def test_haiku_model():
    """Test using Haiku for simple tasks"""
    simple = SimpleOrchestrator()
    
    # This should use Haiku (faster/cheaper)
    agents = [
        {"role": "researcher", "task": "Name 3 popular Python frameworks", "parallel": True}
    ]
    
    start = time.time()
    result = await simple.run_agents(agents)
    end = time.time()
    
    return {
        "type": "haiku_model",
        "time": end - start,
        "response_preview": str(result["results"][0]["result"])[:100] if result["success"] else "Failed"
    }


async def main():
    print("=== Orchestration Performance Tests ===\n")
    print("Running real performance tests...\n")
    
    # Run tests
    tests = [
        ("Direct Response (no agents)", test_direct_response),
        ("Single Agent", test_single_agent),
        ("Sequential Agents", test_sequential_agents),
        ("Parallel Agents", test_parallel_agents),
        ("Complex Workflow", test_complex_workflow),
        ("Simple Orchestrator", test_simple_orchestrator),
        ("Haiku Model Test", test_haiku_model)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running: {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"✓ Completed in {result['time']:.2f}s\n")
        except Exception as e:
            print(f"✗ Failed: {e}\n")
            results.append((test_name, {"error": str(e)}))
    
    # Summary
    print("\n=== Performance Summary ===\n")
    for test_name, result in results:
        if "error" in result:
            print(f"{test_name}: ERROR - {result['error']}")
        else:
            print(f"{test_name}: {result['time']:.2f}s")
            if "agents_spawned" in result:
                print(f"  - Agents spawned: {result['agents_spawned']}")
            if "task_details" in result:
                for task in result["task_details"]:
                    print(f"  - {task['role']}: {task['execution_time']:.2f}s")
        print()
    
    # Calculate averages
    valid_times = [r[1]["time"] for r in results if "time" in r[1] and "error" not in r[1]]
    if valid_times:
        print(f"Average time: {sum(valid_times) / len(valid_times):.2f}s")
        print(f"Min time: {min(valid_times):.2f}s")
        print(f"Max time: {max(valid_times):.2f}s")


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it to run performance tests")
    else:
        asyncio.run(main())