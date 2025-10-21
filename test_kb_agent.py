#!/usr/bin/env python3
"""Test KB intelligent agent functionality"""

import json
import requests

def test_kb_agent():
    url = "http://localhost:8666/api/v0.3/chat"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
    }

    # Test with a KB-related query
    data = {
        "message": "What information do you have about the Wylding Woods experience?",
        "stream": False,
        "context": {
            "kb_enabled": True
        }
    }

    print("Testing KB intelligent agent...")
    print("-" * 50)

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        print(response.text)
        return

    result = response.json()
    print(f"Response: {result.get('response', 'No response')[:500]}...")
    print(f"Conversation ID: {result.get('conversation_id')}")

    # Check if KB was used
    if "Wylding" in result.get('response', '') or "forest" in result.get('response', ''):
        print("✅ KB agent appears to be working - found relevant content")
    else:
        print("⚠️  KB agent may not be working - no relevant content found")

if __name__ == "__main__":
    test_kb_agent()