#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def game_cmd(command, role="player"):
    """Execute game command."""
    response = requests.post(
        f"{BASE_URL}/game/command",
        headers=HEADERS,
        json={
            "command": command,
            "experience": "wylding-woods",
            "user_context": {
                "role": role,
                "user_id": f"{role}@test.com"
            }
        },
        timeout=30
    )
    result = response.json()
    print(f"Response time: {response.elapsed.total_seconds():.2f}s")
    print(f"Narrative: {result.get('narrative', 'N/A')[:200]}...")
    return result

# Test player command (natural language)
print("=== Testing Player Command: 'look around' ===")
game_cmd("look around", role="player")
