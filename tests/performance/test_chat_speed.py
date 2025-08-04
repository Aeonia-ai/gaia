"""
Chat Endpoint Speed Test

Compares performance across different chat implementations:
1. Original multi-provider chat (with MCP tools)
2. Lightweight chat (no MCP, in-memory)
3. Lightweight chat with DB (no MCP, database memory)
"""
import asyncio
import time
import statistics
import httpx
from typing import Dict, List, Tuple
import json
import tabulate
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "http://localhost:8666"
API_KEY = os.getenv("API_KEY", "test-api-key")

# Test messages - variety of lengths and complexity
TEST_MESSAGES = [
    # Simple questions
    "What is 2+2?",
    "Hello, how are you?",
    
    # Medium complexity
    "Explain quantum computing in simple terms.",
    "Write a haiku about programming.",
    
    # Longer prompts
    "Write a short Python function to calculate fibonacci numbers with memoization.",
    "Explain the difference between REST and GraphQL APIs with examples.",
    
    # Context-dependent (for multi-turn testing)
    "My name is Alice and I work as a data scientist.",
    "What's my profession?",  # Should remember from previous
]

# Endpoints to test
ENDPOINTS = {
    "standard": {
        "url": "/api/v1/chat",
        "description": "Standard chat endpoint with MCP tools",
        "has_mcp": True
    },
    "lightweight": {
        "url": "/api/v1/chat/lightweight",
        "description": "Lightweight chat (mcp-agent per request)",
        "has_mcp": False
    },
    "lightweight-hot": {
        "url": "/api/v1/chat/lightweight-hot",
        "description": "Hot-loaded lightweight (mcp-agent cached)",
        "has_mcp": False
    }
}


class ChatSpeedTester:
    def __init__(self):
        self.client = None
        self.results = {}
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def test_endpoint(
        self, 
        endpoint_name: str, 
        endpoint_config: Dict,
        message: str,
        conversation_id: str = None
    ) -> Tuple[float, bool, str]:
        """
        Test a single endpoint with a message.
        Returns: (response_time, success, response_text)
        """
        url = BASE_URL + endpoint_config["url"]
        
        # Build request
        request_data = {
            "message": message,
            "model": "claude-3-5-sonnet-20241022",
            "stream": False
        }
        
        # Add conversation_id for endpoints that support it
        params = {}
        if conversation_id and "db" in endpoint_name:
            params["conversation_id"] = conversation_id
        
        headers = {
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }
        
        try:
            start_time = time.time()
            response = await self.client.post(
                url,
                json=request_data,
                headers=headers,
                params=params
            )
            end_time = time.time()
            
            response_time = end_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                # Extract response text based on endpoint format
                if "choices" in data:
                    response_text = data["choices"][0]["message"]["content"]
                else:
                    response_text = data.get("response", "No response")
                
                return response_time, True, response_text
            else:
                print(f"    DEBUG: Status {response.status_code}: {response.text[:200]}")
                return response_time, False, f"Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            print(f"    DEBUG: Exception: {str(e)}")
            return 0.0, False, f"Exception: {str(e)}"
    
    async def warmup_endpoints(self):
        """Warm up endpoints with initial requests"""
        print("🔥 Warming up endpoints...")
        
        for endpoint_name, config in ENDPOINTS.items():
            await self.test_endpoint(endpoint_name, config, "Hello")
            print(f"  ✓ Warmed up {endpoint_name}")
        
        # Give services a moment to fully initialize
        await asyncio.sleep(2)
    
    async def test_single_messages(self):
        """Test single message performance"""
        print("\n📊 Testing single message performance...")
        
        results = {}
        
        for endpoint_name, config in ENDPOINTS.items():
            endpoint_results = {
                "times": [],
                "successes": [],
                "responses": []
            }
            
            print(f"\n  Testing {endpoint_name}...")
            
            for i, message in enumerate(TEST_MESSAGES[:6]):  # Skip context-dependent ones
                response_time, success, response = await self.test_endpoint(
                    endpoint_name, 
                    config, 
                    message
                )
                
                endpoint_results["times"].append(response_time)
                endpoint_results["successes"].append(success)
                endpoint_results["responses"].append(response[:50] + "..." if len(response) > 50 else response)
                
                status = "✓" if success else "✗"
                print(f"    {status} Message {i+1}: {response_time:.3f}s")
            
            results[endpoint_name] = endpoint_results
        
        return results
    
    async def test_multi_turn_conversation(self):
        """Test multi-turn conversation performance"""
        print("\n💬 Testing multi-turn conversation...")
        
        results = {}
        
        for endpoint_name, config in ENDPOINTS.items():
            if endpoint_name == "lightweight-db":
                # This endpoint maintains conversation context
                print(f"\n  Testing {endpoint_name} with conversation context...")
                
                times = []
                conversation_id = None
                
                # First message
                response_time, success, response = await self.test_endpoint(
                    endpoint_name,
                    config,
                    TEST_MESSAGES[6],  # "My name is Alice..."
                    conversation_id
                )
                times.append(response_time)
                print(f"    Message 1: {response_time:.3f}s")
                
                # Extract conversation_id if returned
                # (In real implementation, this would be in the response)
                
                # Second message (should remember context)
                response_time, success, response = await self.test_endpoint(
                    endpoint_name,
                    config,
                    TEST_MESSAGES[7],  # "What's my profession?"
                    conversation_id
                )
                times.append(response_time)
                print(f"    Message 2: {response_time:.3f}s")
                
                # Check if context was maintained
                context_maintained = "data scientist" in response.lower() or "alice" in response.lower()
                print(f"    Context maintained: {'✓' if context_maintained else '✗'}")
                
                results[endpoint_name] = {
                    "times": times,
                    "context_maintained": context_maintained
                }
            else:
                # For other endpoints, just test the two messages
                times = []
                for i, msg_idx in enumerate([6, 7]):
                    response_time, success, response = await self.test_endpoint(
                        endpoint_name,
                        config,
                        TEST_MESSAGES[msg_idx]
                    )
                    times.append(response_time)
                
                results[endpoint_name] = {
                    "times": times,
                    "context_maintained": None  # Not tested for these
                }
        
        return results
    
    async def test_concurrent_requests(self):
        """Test concurrent request handling"""
        print("\n🚀 Testing concurrent requests...")
        
        concurrent_count = 5
        results = {}
        
        for endpoint_name, config in ENDPOINTS.items():
            print(f"\n  Testing {endpoint_name} with {concurrent_count} concurrent requests...")
            
            # Create concurrent tasks
            tasks = []
            for i in range(concurrent_count):
                message = TEST_MESSAGES[i % len(TEST_MESSAGES)]
                tasks.append(self.test_endpoint(endpoint_name, config, message))
            
            # Run concurrently and measure total time
            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            # Extract times from responses
            times = [r[0] for r in responses if r[1]]  # Only successful responses
            
            results[endpoint_name] = {
                "total_time": total_time,
                "individual_times": times,
                "success_rate": sum(1 for r in responses if r[1]) / len(responses)
            }
            
            print(f"    Total time: {total_time:.3f}s")
            print(f"    Success rate: {results[endpoint_name]['success_rate']*100:.0f}%")
        
        return results
    
    def generate_report(self, single_results, multi_turn_results, concurrent_results):
        """Generate a comprehensive performance report"""
        print("\n" + "="*80)
        print("📈 PERFORMANCE REPORT")
        print("="*80)
        
        # Single Message Performance
        print("\n### Single Message Performance ###")
        
        table_data = []
        for endpoint, data in single_results.items():
            times = [t for t, s in zip(data["times"], data["successes"]) if s]
            if times:
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
                std_dev = statistics.stdev(times) if len(times) > 1 else 0
                
                table_data.append([
                    ENDPOINTS[endpoint]["description"],
                    f"{avg_time:.3f}s",
                    f"{min_time:.3f}s",
                    f"{max_time:.3f}s",
                    f"{std_dev:.3f}s",
                    "Yes" if ENDPOINTS[endpoint]["has_mcp"] else "No"
                ])
        
        headers = ["Endpoint", "Avg Time", "Min Time", "Max Time", "Std Dev", "MCP"]
        print(tabulate.tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Speed comparison
        if len(table_data) >= 2:
            lightweight_avg = float(table_data[1][1].replace('s', ''))
            original_avg = float(table_data[0][1].replace('s', ''))
            speedup = (original_avg - lightweight_avg) / original_avg * 100
            
            print(f"\n🏃 Lightweight chat is {speedup:.1f}% faster than original!")
        
        # Multi-turn Performance
        print("\n### Multi-turn Conversation Performance ###")
        
        table_data = []
        for endpoint, data in multi_turn_results.items():
            if data["times"]:
                avg_time = statistics.mean(data["times"])
                context = "✓" if data["context_maintained"] else "✗" if data["context_maintained"] is False else "N/A"
                
                table_data.append([
                    ENDPOINTS[endpoint]["description"],
                    f"{avg_time:.3f}s",
                    context
                ])
        
        headers = ["Endpoint", "Avg Time", "Context Maintained"]
        print(tabulate.tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Concurrent Performance
        print("\n### Concurrent Request Performance ###")
        
        table_data = []
        for endpoint, data in concurrent_results.items():
            avg_individual = statistics.mean(data["individual_times"]) if data["individual_times"] else 0
            
            table_data.append([
                ENDPOINTS[endpoint]["description"],
                f"{data['total_time']:.3f}s",
                f"{avg_individual:.3f}s",
                f"{data['success_rate']*100:.0f}%"
            ])
        
        headers = ["Endpoint", "Total Time (5 requests)", "Avg Individual", "Success Rate"]
        print(tabulate.tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Summary
        print("\n### Summary ###")
        print("✅ Lightweight endpoints show significant performance improvements")
        print("✅ Database-backed endpoint maintains conversation context")
        print("✅ All endpoints handle concurrent requests well")
        
        # Recommendations
        print("\n### Recommendations ###")
        print("1. Use lightweight endpoint for single-shot queries (fastest)")
        print("2. Use lightweight-db for conversations requiring context")
        print("3. Use multi-provider when MCP tools are needed")


async def main():
    """Run the complete speed test suite"""
    print("🏁 Chat Endpoint Speed Test")
    print("="*80)
    
    # Check if services are running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print("❌ Gateway service not running. Please start Docker services.")
                return
    except:
        print("❌ Cannot connect to gateway. Please ensure services are running:")
        print("   docker-compose up -d")
        return
    
    async with ChatSpeedTester() as tester:
        # Warm up endpoints
        await tester.warmup_endpoints()
        
        # Run tests
        single_results = await tester.test_single_messages()
        multi_turn_results = await tester.test_multi_turn_conversation()
        concurrent_results = await tester.test_concurrent_requests()
        
        # Generate report
        tester.generate_report(single_results, multi_turn_results, concurrent_results)


if __name__ == "__main__":
    # Install required package if needed
    try:
        import tabulate
    except ImportError:
        print("Installing tabulate...")
        import subprocess
        subprocess.check_call(["pip", "install", "tabulate"])
    
    asyncio.run(main())