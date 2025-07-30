#!/usr/bin/env python3
"""
Test tool invocation accuracy for the unified chat endpoint.

Measures:
1. False negatives: Tool-requiring requests that don't invoke tools
2. False positives: Simple messages that unnecessarily invoke tools
"""

import requests
import json
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class ExpectedRoute(Enum):
    DIRECT = "direct"
    TOOL = "tool"  # Any tool (mcp_agent, kb_service, etc.)


@dataclass
class TestCase:
    message: str
    expected: ExpectedRoute
    category: str
    description: str


# Test cases
TEST_CASES = [
    # Direct response cases (should NOT invoke tools)
    TestCase("Hello!", ExpectedRoute.DIRECT, "greeting", "Simple greeting"),
    TestCase("How are you?", ExpectedRoute.DIRECT, "greeting", "Casual greeting"), 
    TestCase("What is 2+2?", ExpectedRoute.DIRECT, "math", "Simple math"),
    TestCase("What's the capital of France?", ExpectedRoute.DIRECT, "knowledge", "General knowledge"),
    TestCase("Tell me a joke", ExpectedRoute.DIRECT, "creative", "Creative request"),
    TestCase("What do you think about AI?", ExpectedRoute.DIRECT, "opinion", "Opinion question"),
    TestCase("Explain quantum computing", ExpectedRoute.DIRECT, "explanation", "Concept explanation"),
    TestCase("Thanks for your help!", ExpectedRoute.DIRECT, "gratitude", "Gratitude expression"),
    TestCase("Can you help me?", ExpectedRoute.DIRECT, "help", "General help request"),
    TestCase("What's your name?", ExpectedRoute.DIRECT, "identity", "Identity question"),
    
    # Tool-requiring cases (SHOULD invoke tools)
    TestCase("What files are in the current directory?", ExpectedRoute.TOOL, "file_ops", "File listing"),
    TestCase("Search my knowledge base for Python tutorials", ExpectedRoute.TOOL, "kb_search", "KB search"),
    TestCase("Create a file called test.py", ExpectedRoute.TOOL, "file_ops", "File creation"),
    TestCase("Read the contents of README.md", ExpectedRoute.TOOL, "file_ops", "File reading"),
    TestCase("What's in my notes about machine learning?", ExpectedRoute.TOOL, "kb_search", "KB query"),
    TestCase("Generate an image of a sunset", ExpectedRoute.TOOL, "asset_gen", "Image generation"),
    TestCase("Search the web for latest AI news", ExpectedRoute.TOOL, "web_search", "Web search"),
    TestCase("Calculate the factorial of 20", ExpectedRoute.TOOL, "computation", "Complex calculation"),
    TestCase("What's the current time?", ExpectedRoute.TOOL, "system_info", "System information"),
    TestCase("Run ls -la in the terminal", ExpectedRoute.TOOL, "shell", "Shell command"),
]


def test_message(message: str, api_key: str = "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE") -> Dict:
    """Test a single message and return the routing result."""
    try:
        response = requests.post(
            "http://localhost:8666/api/v1/chat",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key
            },
            json={
                "message": message,
                "stream": False
            },
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            metadata = result.get("_metadata", {})
            route_type = metadata.get("route_type", "unknown")
            
            # Normalize route types
            if route_type in ["mcp_agent", "kb_service", "asset_service", "multiagent"]:
                actual_route = "tool"
            elif route_type == "direct":
                actual_route = "direct"
            else:
                actual_route = "unknown"
            
            return {
                "success": True,
                "route_type": route_type,
                "actual_route": actual_route,
                "reasoning": metadata.get("reasoning", ""),
                "routing_time_ms": metadata.get("routing_time_ms", 0)
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """Run the accuracy test suite."""
    print("🧪 Testing Tool Invocation Accuracy")
    print("=" * 60)
    
    results = {
        "correct": 0,
        "incorrect": 0,
        "false_positives": [],  # Simple messages that invoked tools
        "false_negatives": [],  # Tool requests that didn't invoke tools
        "errors": []
    }
    
    for i, test_case in enumerate(TEST_CASES):
        print(f"\n[{i+1}/{len(TEST_CASES)}] Testing: {test_case.message[:50]}...")
        print(f"   Category: {test_case.category}")
        print(f"   Expected: {test_case.expected.value}")
        
        result = test_message(test_case.message)
        
        if not result["success"]:
            print(f"   ❌ Error: {result['error']}")
            results["errors"].append((test_case, result["error"]))
            continue
        
        actual = result["actual_route"]
        expected = "tool" if test_case.expected == ExpectedRoute.TOOL else "direct"
        
        if actual == expected:
            print(f"   ✅ Correct: {result['route_type']}")
            results["correct"] += 1
        else:
            print(f"   ❌ Incorrect: Expected {expected}, got {result['route_type']}")
            results["incorrect"] += 1
            
            if test_case.expected == ExpectedRoute.DIRECT and actual == "tool":
                results["false_positives"].append((test_case, result))
            elif test_case.expected == ExpectedRoute.TOOL and actual == "direct":
                results["false_negatives"].append((test_case, result))
        
        # Show reasoning if available
        if result.get("reasoning"):
            print(f"   Reasoning: {result['reasoning']}")
        
        # Rate limiting
        time.sleep(1)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)
    
    total = results["correct"] + results["incorrect"]
    accuracy = (results["correct"] / total * 100) if total > 0 else 0
    
    print(f"Total tests: {len(TEST_CASES)}")
    print(f"Successful: {total}")
    print(f"Errors: {len(results['errors'])}")
    print(f"\nAccuracy: {accuracy:.1f}% ({results['correct']}/{total})")
    
    print(f"\n🚫 False Positives ({len(results['false_positives'])}): Simple messages that invoked tools")
    for tc, result in results["false_positives"]:
        print(f"   - \"{tc.message}\" → {result['route_type']}")
        if result.get("reasoning"):
            print(f"     Reasoning: {result['reasoning']}")
    
    print(f"\n⚠️  False Negatives ({len(results['false_negatives'])}): Tool requests that didn't invoke tools")
    for tc, result in results["false_negatives"]:
        print(f"   - \"{tc.message}\"")
        if result.get("reasoning"):
            print(f"     Reasoning: {result['reasoning']}")


if __name__ == "__main__":
    main()