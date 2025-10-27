#!/usr/bin/env python3
"""Test location extraction from natural language."""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def test_cmd(desc, command):
    print(f"\n{'='*70}")
    print(f"{desc}")
    print(f"Command: \"{command}\"")
    print(f"{'='*70}")

    payload = {
        "command": command,
        "experience": "wylding-woods",
        "user_context": {"role": "player"}
    }

    response = requests.post(f"{BASE_URL}/game/command", headers=HEADERS, json=payload, timeout=30)
    result = response.json()

    print(json.dumps(result, indent=2))

    if result.get("narrative"):
        print(f"\n📖 {result['narrative']}")

print("Testing Location Extraction from Natural Language")

test_cmd("TEST 1", "look at shelf_1 in waypoint_28a")
test_cmd("TEST 2", "pick up the dream bottle from shelf_1")
test_cmd("TEST 3", "check my inventory")
test_cmd("TEST 4", "return the dream bottle to fairy_door_1")

print("\n" + "="*70)
print("DONE")
