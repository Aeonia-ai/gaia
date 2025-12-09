#!/usr/bin/env python3
"""Compare natural language vs admin command execution."""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def test_command(desc, command, role="admin"):
    print(f"\n{'='*70}")
    print(f"{desc}")
    print(f"Role: {role}")
    print(f"Command: '{command}'")
    print(f"{'='*70}")
    
    payload = {
        "command": command,
        "experience": "wylding-woods",
        "user_context": {"role": role, "user_id": f"{role}@test.com"}
    }
    
    response = requests.post(f"{BASE_URL}/game/command", headers=HEADERS, json=payload, timeout=30)
    result = response.json()
    
    if result.get("success"):
        print(f"✅ Success: {result['success']}")
        if result.get("narrative"):
            print(f"\n📖 {result['narrative']}")
    else:
        print(f"❌ Failed: {result.get('error', {}).get('message', 'Unknown error')}")

print("╔═══════════════════════════════════════════════════════════════════╗")
print("║           Natural Language vs Admin Commands Test                ║")
print("╚═══════════════════════════════════════════════════════════════════╝")

# Test 1: Admin command with admin role (should work)
test_command(
    "TEST 1: Admin using @list command",
    "@list items at waypoint_28a clearing shelf_1",
    role="admin"
)

# Test 2: Player trying admin command (should fail)
test_command(
    "TEST 2: Player trying @list command (should be denied)",
    "@list items",
    role="player"
)

# Test 3: Player using natural language (should work via LLM)
test_command(
    "TEST 3: Player using natural language",
    "look at shelf_1",
    role="player"
)

# Test 4: Show the navigation graph
test_command(
    "TEST 4: Display sublocation navigation graph",
    "@list sublocations waypoint_28a clearing",
    role="admin"
)

print(f"\n{'='*70}")
print("✅ COMPARISON TESTS COMPLETE")
print(f"{'='*70}")
