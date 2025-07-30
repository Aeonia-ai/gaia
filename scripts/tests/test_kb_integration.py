#!/usr/bin/env python3
"""Test KB integration in chat."""

import requests
import json

def test_kb_search(message):
    """Test KB search through chat."""
    response = requests.post(
        "http://localhost:8666/api/v1/chat",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"
        },
        json={"message": message, "stream": False},
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        metadata = result.get("_metadata", {})
        print(f"Route: {metadata.get('route_type', 'unknown')}")
        if metadata.get("tools_used"):
            print(f"Tools used: {metadata['tools_used']}")
        
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"Response preview: {content[:200]}...")
        print(f"\nFull metadata: {json.dumps(metadata, indent=2)}")
    else:
        print(f"Error: {response.text}")

# Test cases
print("🧪 Testing KB Integration")
print("=" * 50)

print("\n1. Testing explicit KB search:")
test_kb_search("Search my knowledge base for Python tutorials")

print("\n" + "=" * 50)
print("\n2. Testing file search question:")
test_kb_search("What's in my notes about machine learning?")

print("\n" + "=" * 50)
print("\n3. Testing general knowledge (should NOT use KB):")
test_kb_search("What is the capital of France?")