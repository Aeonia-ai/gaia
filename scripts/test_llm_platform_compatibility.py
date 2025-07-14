#!/usr/bin/env python3
"""
Test script for remote endpoints
Runs comprehensive tests against LLM platform servers
Following llm-platform testing patterns
"""

import asyncio
import json
import os
import sys
import time
from typing import Dict, List, Any, Optional
import aiohttp
import argparse
from pathlib import Path

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key, value)

# Load .env before getting environment variables
load_env()

# Test configuration
DEFAULT_URL = "https://gaia-asset-dev.fly.dev"
API_KEY = os.getenv("API_KEY")

class TestResult:
    def __init__(self, name: str, success: bool, message: str, details: Optional[Dict] = None):
        self.name = name
        self.success = success
        self.message = message
        self.details = details or {}
        self.duration = 0.0

class GaiaAssetTester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.results: List[TestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"X-API-Key": self.api_key} if self.api_key else {},
            timeout=aiohttp.ClientTimeout(total=60)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def make_request(self, method: str, endpoint: str, **kwargs) -> tuple[bool, Dict]:
        """Make HTTP request and return (success, response_data)"""
        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.content_type == 'application/json':
                    data = await response.json()
                else:
                    data = {"text": await response.text(), "content_type": response.content_type}
                
                return response.status < 400, {
                    "status": response.status,
                    "data": data,
                    "headers": dict(response.headers)
                }
        except Exception as e:
            return False, {"error": str(e)}

    async def test_health_check(self) -> TestResult:
        """Test the health check endpoint"""
        start_time = time.time()
        success, response = await self.make_request("GET", "/health")
        
        result = TestResult(
            name="Health Check",
            success=success and response.get("status") == 200,
            message="Health endpoint check",
            details=response
        )
        result.duration = time.time() - start_time
        return result

    async def test_chat_v1(self) -> TestResult:
        """Test the v1 chat endpoint"""
        start_time = time.time()
        payload = {
            "message": "Hello! This is a test message from the Gaia Asset test suite.",
            "stream": False
        }
        
        success, response = await self.make_request(
            "POST", 
            "/api/v1/chat", 
            json=payload
        )
        
        result = TestResult(
            name="Chat v1 API",
            success=success and response.get("status") == 200,
            message="Basic chat functionality test",
            details=response
        )
        result.duration = time.time() - start_time
        return result

    async def test_chat_v0_2(self) -> TestResult:
        """Test the v0.2 chat endpoint"""
        start_time = time.time()
        payload = {
            "message": "Hello! Testing v0.2 API endpoint.",
            "stream": False
        }
        
        success, response = await self.make_request(
            "POST", 
            "/api/v0.2/chat", 
            json=payload
        )
        
        result = TestResult(
            name="Chat v0.2 API",
            success=success and response.get("status") == 200,
            message="v0.2 unified chat API test",
            details=response
        )
        result.duration = time.time() - start_time
        return result

    async def test_asset_generation(self) -> TestResult:
        """Test asset generation endpoint"""
        start_time = time.time()
        payload = {
            "prompt": "A simple test asset for validation",
            "type": "image",
            "style": "digital_art"
        }
        
        success, response = await self.make_request(
            "POST", 
            "/api/v1/assets/generate", 
            json=payload
        )
        
        result = TestResult(
            name="Asset Generation",
            success=success,
            message="Asset generation endpoint test",
            details=response
        )
        result.duration = time.time() - start_time
        return result

    async def test_personas_list(self) -> TestResult:
        """Test personas listing endpoint"""
        start_time = time.time()
        success, response = await self.make_request("GET", "/api/v1/personas/")
        
        result = TestResult(
            name="Personas List",
            success=success,
            message="List available personas",
            details=response
        )
        result.duration = time.time() - start_time
        return result

    async def test_filesystem_operations(self) -> TestResult:
        """Test filesystem operations"""
        start_time = time.time()
        
        # Test directory listing
        success, response = await self.make_request("GET", "/api/v1/filesystem/files?path=/")
        
        result = TestResult(
            name="Filesystem Operations",
            success=success,
            message="Basic filesystem operations test",
            details=response
        )
        result.duration = time.time() - start_time
        return result

    async def test_providers_info(self) -> TestResult:
        """Test providers information endpoint"""
        start_time = time.time()
        success, response = await self.make_request("GET", "/api/v1/providers/")
        
        result = TestResult(
            name="Providers Info",
            success=success,
            message="Available LLM providers information",
            details=response
        )
        result.duration = time.time() - start_time
        return result

    async def run_all_tests(self) -> List[TestResult]:
        """Run all tests and collect results"""
        print(f"🚀 Starting LLM Platform Tests against {self.base_url}")
        print("=" * 60)
        
        test_methods = [
            self.test_health_check,
            self.test_chat_v1,
            self.test_chat_v0_2,
            self.test_asset_generation,
            self.test_personas_list,
            self.test_filesystem_operations,
            self.test_providers_info,
        ]
        
        for test_method in test_methods:
            try:
                print(f"Running {test_method.__name__}...", end=" ")
                result = await test_method()
                self.results.append(result)
                
                if result.success:
                    print(f"✅ PASS ({result.duration:.2f}s)")
                else:
                    print(f"❌ FAIL ({result.duration:.2f}s)")
                    
            except Exception as e:
                error_result = TestResult(
                    name=test_method.__name__,
                    success=False,
                    message=f"Exception: {str(e)}",
                    details={"exception": str(e)}
                )
                self.results.append(error_result)
                print(f"❌ ERROR ({str(e)})")
        
        return self.results

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r.success)
        failed = len(self.results) - passed
        total_time = sum(r.duration for r in self.results)
        
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/len(self.results)*100):.1f}%")
        print(f"Total Duration: {total_time:.2f}s")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result.success:
                    print(f"  • {result.name}: {result.message}")
                    if result.details.get("error"):
                        print(f"    Error: {result.details['error']}")
                    elif result.details.get("status"):
                        print(f"    Status: {result.details['status']}")
        
        print("\n✅ SUCCESSFUL TESTS:")
        for result in self.results:
            if result.success:
                print(f"  • {result.name} ({result.duration:.2f}s)")

    def save_detailed_report(self, filename: str = "gaia_test_report.json"):
        """Save detailed test report to JSON file"""
        report = {
            "test_run": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "target_url": self.base_url,
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.success),
                "failed": sum(1 for r in self.results if not r.success),
                "total_duration": sum(r.duration for r in self.results)
            },
            "results": [
                {
                    "name": r.name,
                    "success": r.success,
                    "message": r.message,
                    "duration": r.duration,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {filename}")

async def main():
    parser = argparse.ArgumentParser(description="Test LLM Platform server endpoints")
    parser.add_argument("--url", default=DEFAULT_URL, help="Base URL to test (default: gaia-asset-dev.fly.dev)")
    parser.add_argument("--api-key", default=API_KEY, help="API key for authentication")
    parser.add_argument("--report", default="test_report.json", help="Output report filename")
    parser.add_argument("--no-auth", action="store_true", help="Skip API key authentication")
    
    args = parser.parse_args()
    
    if not args.no_auth and not args.api_key:
        print("❌ Error: API_KEY environment variable not set. Use --no-auth to skip authentication.")
        sys.exit(1)
    
    api_key = None if args.no_auth else args.api_key
    
    async with GaiaAssetTester(args.url, api_key) as tester:
        await tester.run_all_tests()
        tester.print_summary()
        tester.save_detailed_report(args.report)
        
        # Return appropriate exit code
        failed_tests = sum(1 for r in tester.results if not r.success)
        sys.exit(0 if failed_tests == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())