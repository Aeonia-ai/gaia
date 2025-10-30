#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def game_cmd(command, role="admin"):
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
    print(json.dumps(result, indent=2))
    return result

# Test admin command
print("=== Testing Admin Command: @stats ===")
game_cmd("@stats", role="admin")

print("\n=== Testing Admin Command: @list waypoints ===")
game_cmd("@list waypoints", role="admin")
