#!/usr/bin/env python3
"""Realistic natural language game test - look first, then interact."""

import requests
import json
import time

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def cmd(test, command, sublocation="shelf_1"):
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
    print(f"{test}")
    print(f"🎮 \"{command}\" (at {sublocation})")
    print(f"{'='*70}")

    start = time.time()
    response = requests.post(f"{BASE_URL}/game/command", headers=HEADERS, json=payload, timeout=60)
    elapsed = time.time() - start

    result = response.json()
    print(f"⏱️  {elapsed:.2f}s | Model: {result.get('model_used', 'unknown')}")

    if result.get("narrative"):
        print(f"\n📖 {result['narrative']}")

    if not result.get("success"):
        print(f"\n❌ Error: {result.get('error', {}).get('message')}")

    return result

print("╔═══════════════════════════════════════════════════════════════════╗")
print("║    WYLDING WOODS: Realistic Natural Language Gameplay             ║")
print("╚═══════════════════════════════════════════════════════════════════╝")

# Realistic flow: Look, then interact
cmd("TEST 1", "Look around", "shelf_1")
cmd("TEST 2", "Pick up the dream bottle", "shelf_1")
cmd("TEST 3", "What's in my inventory?", "shelf_1")
cmd("TEST 4", "Go to the star fairy house and try to return the bottle", "fairy_door_2")
cmd("TEST 5", "Go to the spiral fairy house and return the dream bottle", "fairy_door_1")
cmd("TEST 6", "Check inventory", "fairy_door_1")

print("\n" + "="*70)
print("✅ COMPLETE")
print("="*70)
