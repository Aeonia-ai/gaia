#!/usr/bin/env python3
"""
Test all chat endpoints with performance measurements
"""
import asyncio
import aiohttp
import time
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import statistics

# Configuration
BASE_URL = os.getenv("GAIA_BASE_URL", "http://localhost:8666")
API_KEY = os.getenv("GAIA_API_KEY", "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE")

# Test queries of varying complexity
TEST_QUERIES = {
    "simple": "What is 2+2?",
    "medium": "Explain the concept of recursion with an example",
    "complex": "Compare the pros and cons of microservices vs monolithic architecture",
    "multi_step": "Research Python web frameworks, analyze their strengths, and recommend one for a startup"
}

# All endpoints to test
ENDPOINTS = {
    "v1-chat": "/api/v1/chat",  # Routes to /chat/unified
    "v0.3-chat": "/api/v0.3/chat",  # Clean API format
    # Note: v0.2 API and /api/v1/chat/completions have been removed for cleanup.
    # All chat requests now go through intelligent routing.
}


@dataclass
class TestResult:
    endpoint: str
    query_type: str
    query: str
    success: bool
    response_time: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    response_preview: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatEndpointTester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        self.results: List[TestResult] = []
    
    async def test_endpoint(
        self, 
        session: aiohttp.ClientSession,
        endpoint_name: str,
        endpoint_path: str,
        query_type: str,
        query: str
    ) -> TestResult:
        """Test a single endpoint with a query"""
        url = f"{self.base_url}{endpoint_path}"
        
        # Prepare request - all endpoints now use standard format
        payload = {
            "message": query,
            "model": "claude-sonnet-4-5"
        }
        
        start_time = time.time()
        
        try:
            async with session.post(
                url, 
                json=payload, 
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                response_time = time.time() - start_time
                response_data = await response.json()
                
                # Extract response text
                response_text = response_data.get("response", "")
                
                # Extract metadata if available
                metadata = response_data.get("metadata", {})
                
                return TestResult(
                    endpoint=endpoint_name,
                    query_type=query_type,
                    query=query,
                    success=response.status == 200,
                    response_time=response_time,
                    status_code=response.status,
                    response_preview=response_text[:100] + "..." if response_text else None,
                    metadata=metadata
                )
                
        except asyncio.TimeoutError:
            return TestResult(
                endpoint=endpoint_name,
                query_type=query_type,
                query=query,
                success=False,
                response_time=60.0,
                error="Timeout after 60s"
            )
        except Exception as e:
            return TestResult(
                endpoint=endpoint_name,
                query_type=query_type,
                query=query,
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def test_all_endpoints(self):
        """Test all endpoints with all query types"""
        async with aiohttp.ClientSession() as session:
            # Test each endpoint with each query type
            tasks = []
            for endpoint_name, endpoint_path in ENDPOINTS.items():
                for query_type, query in TEST_QUERIES.items():
                    task = self.test_endpoint(
                        session,
                        endpoint_name,
                        endpoint_path,
                        query_type,
                        query
                    )
                    tasks.append(task)
            
            # Run tests in parallel
            print(f"Running {len(tasks)} tests in parallel...")
            results = await asyncio.gather(*tasks)
            self.results.extend(results)
    
    def print_results(self):
        """Print formatted test results"""
        print("\n" + "="*80)
        print("CHAT ENDPOINT TEST RESULTS")
        print("="*80)
        
        # Group results by endpoint
        by_endpoint = {}
        for result in self.results:
            if result.endpoint not in by_endpoint:
                by_endpoint[result.endpoint] = []
            by_endpoint[result.endpoint].append(result)
        
        # Print results for each endpoint
        for endpoint_name, results in by_endpoint.items():
            print(f"\n{endpoint_name.upper()} Endpoint ({ENDPOINTS.get(endpoint_name, 'unknown')})")
            print("-" * 60)
            
            for result in results:
                if result.query_type == "warmup":
                    continue
                    
                status = "✓" if result.success else "✗"
                print(f"{status} {result.query_type:12} | {result.response_time:6.2f}s", end="")
                
                if result.error:
                    print(f" | ERROR: {result.error}")
                elif result.metadata and endpoint_name == "orchestrated":
                    orch_info = result.metadata.get("orchestration", {})
                    if orch_info:
                        print(f" | Agents: {orch_info.get('agents_used', 0)}")
                    else:
                        print()
                else:
                    print()
            
            # Calculate average response time
            valid_times = [r.response_time for r in results if r.success and r.query_type != "warmup"]
            if valid_times:
                avg_time = statistics.mean(valid_times)
                print(f"Average response time: {avg_time:.2f}s")
    
    def print_performance_summary(self):
        """Print performance comparison"""
        print("\n" + "="*80)
        print("PERFORMANCE SUMMARY")
        print("="*80)
        
        # Calculate average times by endpoint
        endpoint_times = {}
        for result in self.results:
            if result.success and result.query_type != "warmup":
                if result.endpoint not in endpoint_times:
                    endpoint_times[result.endpoint] = []
                endpoint_times[result.endpoint].append(result.response_time)
        
        # Sort by average time
        sorted_endpoints = sorted(
            [(ep, statistics.mean(times)) for ep, times in endpoint_times.items()],
            key=lambda x: x[1]
        )
        
        print("\nEndpoints ranked by speed (fastest to slowest):")
        print("-" * 50)
        for i, (endpoint, avg_time) in enumerate(sorted_endpoints, 1):
            print(f"{i}. {endpoint:15} | {avg_time:6.2f}s average")
        
        # Show query complexity impact
        print("\nResponse time by query complexity:")
        print("-" * 50)
        for query_type in TEST_QUERIES:
            times_by_endpoint = {}
            for result in self.results:
                if result.success and result.query_type == query_type:
                    if result.endpoint not in times_by_endpoint:
                        times_by_endpoint[result.endpoint] = []
                    times_by_endpoint[result.endpoint].append(result.response_time)
            
            if times_by_endpoint:
                print(f"\n{query_type.upper()} queries:")
                for endpoint, times in sorted(times_by_endpoint.items()):
                    avg = statistics.mean(times)
                    print(f"  {endpoint:15} | {avg:6.2f}s")
    
    def save_results(self, filename: str = "endpoint_test_results.json"):
        """Save results to JSON file"""
        data = {
            "test_time": datetime.now().isoformat(),
            "endpoints_tested": list(ENDPOINTS.keys()),
            "queries_tested": TEST_QUERIES,
            "results": [
                {
                    "endpoint": r.endpoint,
                    "query_type": r.query_type,
                    "success": r.success,
                    "response_time": r.response_time,
                    "error": r.error,
                    "status_code": r.status_code
                }
                for r in self.results
            ]
        }
        
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"\nResults saved to {filename}")


async def main():
    print("Starting Gaia Chat Endpoint Tests")
    print(f"Base URL: {BASE_URL}")
    print(f"Testing {len(ENDPOINTS)} endpoints with {len(TEST_QUERIES)} query types each")
    print()
    
    tester = ChatEndpointTester(BASE_URL, API_KEY)
    
    # Run all tests
    start_time = time.time()
    await tester.test_all_endpoints()
    total_time = time.time() - start_time
    
    # Print results
    tester.print_results()
    tester.print_performance_summary()
    tester.save_results()
    
    print(f"\nTotal test time: {total_time:.2f}s")
    print(f"Total tests run: {len(tester.results)}")


if __name__ == "__main__":
    asyncio.run(main())