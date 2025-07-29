#!/usr/bin/env python3
"""Quick test of routing improvements."""

import requests
import json

def test_message(message):
    """Test a single message."""
    response = requests.post(
        "http://localhost:8666/api/v1/chat",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"
        },
        json={"message": message, "stream": False},
        timeout=15
    )
    
    if response.status_code == 200:
        result = response.json()
        metadata = result.get("_metadata", {})
        route = metadata.get("route_type", "unknown")
        reasoning = metadata.get("reasoning", "")
        return route, reasoning
    return "error", f"HTTP {response.status_code}"

# Test cases
tests = [
    ("Hello!", "direct"),
    ("What is 2+2?", "direct"),
    ("What's the capital of France?", "direct"),
    ("Explain quantum computing", "direct"),
    ("What files are in the current directory?", "tool"),
    ("Search my KB for Python", "tool"),
]

print("🧪 Testing Improved Routing")
print("=" * 50)

for message, expected in tests:
    print(f"\n'{message}'")
    print(f"Expected: {expected}")
    
    route, reasoning = test_message(message)
    
    if (expected == "direct" and route == "direct") or \
       (expected == "tool" and route != "direct"):
        print(f"✅ Got: {route}")
    else:
        print(f"❌ Got: {route}")
    
    if reasoning and route != "direct":
        print(f"   Reasoning: {reasoning}")
    
    import time
    time.sleep(1)  # Rate limit