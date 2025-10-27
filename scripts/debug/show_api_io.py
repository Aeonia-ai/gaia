#!/usr/bin/env python3
"""Show all API inputs and outputs in one run."""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def api_call(name: str, payload: dict):
    print(f"\n{'='*70}")
    print(f"TEST #{name}")
    print(f"{'='*70}")
    print("\n📤 INPUT:")
    print(json.dumps(payload, indent=2))

    response = requests.post(
        f"{BASE_URL}/game/test/simple-command",
        headers=HEADERS,
        json=payload
    )

    print("\n📥 OUTPUT:")
    print(json.dumps(response.json(), indent=2))

print("╔═══════════════════════════════════════════════════════════════════╗")
print("║           INSTANCE MANAGEMENT: INPUTS & OUTPUTS                   ║")
print("╚═══════════════════════════════════════════════════════════════════╝")

# Test 1: Look
api_call("1 - Look at shelf_1", {
    "action": "look",
    "sublocation": "shelf_1",
    "experience": "wylding-woods",
    "waypoint": "waypoint_28a"
})

# Test 2: Collect
api_call("2 - Collect dream_bottle", {
    "action": "collect",
    "target": "dream_bottle",
    "sublocation": "shelf_1",
    "experience": "wylding-woods",
    "waypoint": "waypoint_28a"
})

# Test 3: Inventory
api_call("3 - Check inventory", {
    "action": "inventory",
    "experience": "wylding-woods",
    "waypoint": "waypoint_28a"
})

# Test 4: Wrong house
api_call("4 - Return to WRONG house", {
    "action": "return",
    "target": "dream_bottle",
    "destination": "fairy_door_2",
    "sublocation": "fairy_door_2",
    "experience": "wylding-woods",
    "waypoint": "waypoint_28a"
})

# Test 5: Correct house
api_call("5 - Return to CORRECT house", {
    "action": "return",
    "target": "dream_bottle",
    "destination": "fairy_door_1",
    "sublocation": "fairy_door_1",
    "experience": "wylding-woods",
    "waypoint": "waypoint_28a"
})

# Test 6: Final inventory
api_call("6 - Final inventory", {
    "action": "inventory",
    "experience": "wylding-woods",
    "waypoint": "waypoint_28a"
})

print("\n" + "="*70)
print("✅ COMPLETE")
print("="*70)
