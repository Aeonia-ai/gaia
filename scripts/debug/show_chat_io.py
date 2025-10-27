#!/usr/bin/env python3
"""Show complete inputs and outputs for natural language game commands."""

import requests
import json
import time

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def show_io(test, command, sublocation):
    payload = {
        "command": command,
        "experience": "wylding-woods",
        "user_context": {
            "waypoint": "waypoint_28a",
            "sublocation": sublocation,
            "role": "player"
        },
        "session_state": {}
    }

    print(f"\n{'='*70}")
    print(f"{test}: \"{command}\"")
    print(f"{'='*70}")
    print("\n📤 INPUT:")
    print(json.dumps(payload, indent=2))

    start = time.time()
    response = requests.post(f"{BASE_URL}/game/command", headers=HEADERS, json=payload, timeout=60)
    elapsed = time.time() - start

    print(f"\n📥 OUTPUT ({elapsed:.2f}s):")
    print(json.dumps(response.json(), indent=2))

print("╔═══════════════════════════════════════════════════════════════════╗")
print("║         Natural Language Game Commands: Full I/O                  ║")
print("╚═══════════════════════════════════════════════════════════════════╝")

show_io("TEST 1", "Look around", "shelf_1")
show_io("TEST 2", "Pick up the dream bottle", "shelf_1")
show_io("TEST 3", "What's in my inventory?", "shelf_1")
show_io("TEST 4", "Return the bottle to the spiral fairy house", "fairy_door_1")
show_io("TEST 5", "Check my inventory", "fairy_door_1")

print("\n" + "="*70)
print("✅ COMPLETE")
print("="*70)
