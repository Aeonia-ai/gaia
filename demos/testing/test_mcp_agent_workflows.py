"""
Test MCP-Agent Endpoint with Real Workflows

Tests our existing mcp-agent endpoints with the workflow patterns
to understand which works best for MMOIRL sub-500ms requirements.
"""
import asyncio
import time
import json
import httpx
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8666"  # Gateway
API_KEY = "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"

class MCPAgentEndpointTester:
    """Test our mcp-agent endpoints with different workflow patterns"""
    
    def __init__(self):
        self.headers = {
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        }
    
    async def test_endpoint(self, endpoint: str, message: str, description: str) -> Dict[str, Any]:
        """Test a specific endpoint with timing"""
        print(f"\n🧪 Testing {description}")
        print(f"Endpoint: {endpoint}")
        print(f"Message: {message}")
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{BASE_URL}{endpoint}",
                    headers=self.headers,
                    json={"message": message}
                )
                
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract response content
                    if "choices" in result and result["choices"]:
                        content = result["choices"][0]["message"]["content"]
                    else:
                        content = str(result)
                    
                    print(f"✅ Success ({elapsed:.2f}s)")
                    print(f"Response: {content[:150]}...")
                    
                    return {
                        "success": True,
                        "elapsed": elapsed,
                        "response": content,
                        "full_result": result
                    }
                else:
                    print(f"❌ Failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "elapsed": elapsed,
                        "error": f"{response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ Exception: {e}")
            return {
                "success": False,
                "elapsed": elapsed,
                "error": str(e)
            }
    
    async def compare_mcp_agent_endpoints(self):
        """Compare our different mcp-agent endpoint implementations"""
        
        # Test message that benefits from MCP tools
        test_message = "List the files in the current directory and tell me about this project"
        
        endpoints_to_test = [
            ("/api/v1/chat/lightweight", "Lightweight MCP-Agent (no tools)"),
            ("/api/v1/chat/lightweight-db", "Lightweight MCP-Agent with DB"),
            ("/api/v1/chat/mcp-agent", "Standard MCP-Agent"),
            ("/api/v1/chat/mcp-agent-hot", "Hot-loaded MCP-Agent"),
        ]
        
        print("🔬 MCP-Agent Endpoint Comparison")
        print("=" * 60)
        
        results = {}
        
        for endpoint, description in endpoints_to_test:
            result = await self.test_endpoint(endpoint, test_message, description)
            results[description] = result
            
            # Brief pause between tests
            await asyncio.sleep(1)
        
        # Performance summary
        print("\n📊 Performance Summary")
        print("=" * 40)
        
        successful_results = {k: v for k, v in results.items() if v["success"]}
        
        if successful_results:
            # Sort by speed
            sorted_results = sorted(successful_results.items(), key=lambda x: x[1]["elapsed"])
            
            print("Rankings (fastest to slowest):")
            for i, (name, result) in enumerate(sorted_results, 1):
                print(f"{i}. {name}: {result['elapsed']:.2f}s")
            
            fastest = sorted_results[0]
            print(f"\n🏆 Fastest: {fastest[0]} ({fastest[1]['elapsed']:.2f}s)")
            
            # Check sub-500ms requirement
            sub_500ms = [name for name, result in successful_results.items() if result["elapsed"] < 0.5]
            if sub_500ms:
                print(f"⚡ Sub-500ms capable: {', '.join(sub_500ms)}")
            else:
                print("⚠️  None achieved sub-500ms (MMOIRL requirement)")
        
        # Failed tests
        failed_results = {k: v for k, v in results.items() if not v["success"]}
        if failed_results:
            print(f"\n❌ Failed tests: {', '.join(failed_results.keys())}")
    
    async def test_workflow_patterns(self):
        """Test different types of messages to understand routing needs"""
        
        workflow_tests = [
            # Simple questions (should be fast)
            ("What is 2+2?", "Simple Math", "Should route to lightweight/fast endpoint"),
            
            # Conversational (needs context)
            ("Continue our previous conversation about microservices", "Conversation", "Should route to DB endpoint"),
            
            # Tool-requiring tasks
            ("List files in the current directory", "File System", "Should route to MCP-agent"),
            
            # Complex multi-step
            ("Analyze the codebase structure and write a summary", "Complex Analysis", "Should route to hot MCP-agent"),
            
            # Creative tasks
            ("Write a haiku about programming", "Creative", "Could use lightweight"),
        ]
        
        print("\n🎭 Workflow Pattern Testing")
        print("=" * 50)
        
        # Test with our fastest endpoint from previous test
        endpoint = "/api/v1/chat/mcp-agent"  # Standard endpoint
        
        for message, task_type, expected_routing in workflow_tests:
            print(f"\n📝 {task_type} Task:")
            result = await self.test_endpoint(endpoint, message, f"{task_type} - {expected_routing}")
            
            if result["success"]:
                # Analyze response characteristics
                response_len = len(result["response"])
                print(f"   Response length: {response_len} chars")
                print(f"   Speed tier: {'⚡ Fast' if result['elapsed'] < 1 else '🐌 Slow'}")
    
    async def test_concurrent_requests(self):
        """Test how endpoints handle concurrent requests (MMOIRL requirement)"""
        print("\n🚀 Concurrent Request Testing")
        print("=" * 40)
        
        endpoint = "/api/v1/chat/mcp-agent"
        concurrent_messages = [
            "What is the capital of France?",
            "Calculate 15 * 23",
            "Explain REST APIs briefly", 
            "What is Python?",
            "Name 3 colors"
        ]
        
        print(f"Sending {len(concurrent_messages)} concurrent requests...")
        
        start_time = time.time()
        
        # Send all requests concurrently
        tasks = []
        for i, message in enumerate(concurrent_messages):
            task = self.test_endpoint(endpoint, message, f"Concurrent #{i+1}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_elapsed = time.time() - start_time
        
        # Analyze concurrent performance
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
        
        print(f"\n📊 Concurrent Results:")
        print(f"Total time: {total_elapsed:.2f}s")
        print(f"Successful: {len(successful)}/{len(concurrent_messages)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            avg_time = sum(r["elapsed"] for r in successful) / len(successful)
            max_time = max(r["elapsed"] for r in successful)
            min_time = min(r["elapsed"] for r in successful)
            
            print(f"Response times - Avg: {avg_time:.2f}s, Min: {min_time:.2f}s, Max: {max_time:.2f}s")
            
            # MMOIRL assessment
            if max_time < 0.5:
                print("✅ All responses under 500ms - MMOIRL ready!")
            elif avg_time < 0.5:
                print("⚠️  Average under 500ms, but some slower - Needs optimization")
            else:
                print("❌ Too slow for MMOIRL requirements")

async def main():
    """Run comprehensive mcp-agent endpoint testing"""
    tester = MCPAgentEndpointTester()
    
    print("🔬 MCP-Agent Endpoint Testing Suite")
    print("Testing for MMOIRL sub-500ms requirements")
    print("=" * 60)
    
    try:
        # Test 1: Compare our different implementations
        await tester.compare_mcp_agent_endpoints()
        
        # Test 2: Different workflow patterns
        await tester.test_workflow_patterns()
        
        # Test 3: Concurrent request handling
        await tester.test_concurrent_requests()
        
        print("\n✅ All tests completed!")
        print("\n🎯 Recommendations:")
        print("1. Use fastest endpoint for simple MMOIRL queries")
        print("2. Implement smart routing based on request complexity")
        print("3. Consider hot-loading for complex agent tasks")
        print("4. Monitor response times in production")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())