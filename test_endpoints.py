#!/usr/bin/env python3
"""
Gaia Platform Endpoint Testing Script
Tests all major endpoints without requiring manual curl commands.
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuration
GATEWAY_URL = "http://localhost:8666"
API_KEY = "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def test_endpoint(method: str, url: str, data: Dict[str, Any] = None, headers: Dict[str, str] = None) -> tuple[bool, str, Dict]:
    """Test a single endpoint and return results."""
    try:
        if headers is None:
            headers = HEADERS
            
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return False, f"Unsupported method: {method}", {}
            
        success = response.status_code < 400
        return success, f"{response.status_code}", response.json() if response.headers.get('content-type', '').startswith('application/json') else {"raw": response.text}
        
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {e}", {}
    except Exception as e:
        return False, f"Error: {e}", {}

def main():
    """Run all endpoint tests."""
    print("🚀 Testing Gaia Platform Endpoints")
    print("=" * 50)
    
    tests = [
        # Health checks and version info
        ("GET", f"{GATEWAY_URL}/health", None, "Gateway health"),
        ("GET", f"{GATEWAY_URL}/", None, "Root endpoint (version info)"),
        
        # v0.2 API tests (recommended API)
        ("GET", f"{GATEWAY_URL}/api/v0.2/", None, "v0.2 API info"),
        ("GET", f"{GATEWAY_URL}/api/v0.2/health", None, "v0.2 health check"),
        ("GET", f"{GATEWAY_URL}/api/v0.2/chat/status", None, "v0.2 chat status"),
        ("POST", f"{GATEWAY_URL}/api/v0.2/chat", {"message": "Hello v0.2!"}, "v0.2 chat completion"),
        ("GET", f"{GATEWAY_URL}/api/v0.2/providers", None, "v0.2 list providers"),
        ("GET", f"{GATEWAY_URL}/api/v0.2/providers/claude", None, "v0.2 get provider"),
        ("GET", f"{GATEWAY_URL}/api/v0.2/models", None, "v0.2 list models"),
        ("POST", f"{GATEWAY_URL}/api/v0.2/models/recommend", {"message": "Need a fast model", "priority": "speed"}, "v0.2 model recommendation"),
        ("DELETE", f"{GATEWAY_URL}/api/v0.2/chat/history", None, "v0.2 clear chat history"),
        
        # v1 API tests (legacy support)
        ("GET", f"{GATEWAY_URL}/api/v1/chat/status", None, "v1 chat status"),
        ("POST", f"{GATEWAY_URL}/api/v1/chat", {"message": "Hello v1 test"}, "v1 chat completion"),
        ("POST", f"{GATEWAY_URL}/api/v1/chat/completions", {"message": "OpenAI format test"}, "v1 chat completions (OpenAI format)"),
        ("DELETE", f"{GATEWAY_URL}/api/v1/chat/history", None, "v1 clear chat history"),
        
        # Asset endpoints
        ("GET", f"{GATEWAY_URL}/api/v1/assets", None, "Assets list"),
    ]
    
    results = []
    for method, url, data, description in tests:
        print(f"\n📝 Testing: {description}")
        print(f"   {method} {url}")
        
        success, status, response = test_endpoint(method, url, data)
        
        if success:
            print(f"   ✅ {status} - Success")
            # Show key response fields for successful requests
            if response:
                if "response" in response:
                    print(f"   📄 Chat response: {response['response'][:100]}...")
                elif "assets" in response:
                    print(f"   📄 Asset count: {response.get('total', 'unknown')}")
                elif "message_count" in response:
                    print(f"   📄 Chat status: {response['message_count']} messages, history: {response['has_history']}")
                elif "status" in response and response["status"] == "success":
                    print(f"   📄 Operation: {response}")
                elif "version" in response:
                    print(f"   📄 Version: {response['version']}")
                elif "versions" in response:
                    print(f"   📄 API versions: {list(response['versions'].keys())}")
                elif len(str(response)) < 150:
                    print(f"   📄 Response: {response}")
        else:
            print(f"   ❌ {status} - Failed")
            if response:
                print(f"   📄 Error: {response}")
        
        results.append((description, success, status, response))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success, _, _ in results if success)
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed")
        
        print("\nFailed tests:")
        for description, success, status, response in results:
            if not success:
                print(f"  - {description}: {status}")
        
        sys.exit(1)

if __name__ == "__main__":
    main()