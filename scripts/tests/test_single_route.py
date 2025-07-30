#!/usr/bin/env python3
"""Test a single routing decision."""

import requests
import json
import sys

message = sys.argv[1] if len(sys.argv) > 1 else "Hello!"

response = requests.post(
    "http://localhost:8666/api/v1/chat",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"
    },
    json={"message": message, "stream": False},
    timeout=10
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    metadata = result.get("_metadata", {})
    print(f"Route: {metadata.get('route_type', 'unknown')}")
    if metadata.get("reasoning"):
        print(f"Reasoning: {metadata['reasoning']}")
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    print(f"Response: {content[:100]}...")
else:
    print(f"Error: {response.text}")