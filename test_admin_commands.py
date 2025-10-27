#!/usr/bin/env python3
"""Test admin commands (@list, @stats, etc.)."""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def test_admin_cmd(desc, command):
    print(f"\n{'='*70}")
    print(f"{desc}")
    print(f"Command: \"{command}\"")
    print(f"{'='*70}")

    payload = {
        "command": command,
        "experience": "wylding-woods",
        "user_context": {"role": "admin", "user_id": "admin@gaia.dev"}
    }

    try:
        response = requests.post(
            f"{BASE_URL}/game/command",
            headers=HEADERS,
            json=payload,
            timeout=30
        )
        result = response.json()

        print(json.dumps(result, indent=2))

        if result.get("narrative"):
            print(f"\n📋 {result['narrative']}")

    except Exception as e:
        print(f"❌ Error: {e}")

print("╔═══════════════════════════════════════════════════════════════════╗")
print("║              Admin Commands Test Suite                            ║")
print("╚═══════════════════════════════════════════════════════════════════╝")

# Test @stats
test_admin_cmd("TEST 1: Get world statistics", "@stats")

# Test @list commands
test_admin_cmd("TEST 2: List all waypoints", "@list waypoints")

test_admin_cmd("TEST 3: List locations in waypoint", "@list locations waypoint_28a")

test_admin_cmd("TEST 4: List sublocations", "@list sublocations waypoint_28a clearing")

test_admin_cmd("TEST 5: List all items", "@list items")

test_admin_cmd("TEST 6: List items at specific location", "@list items at waypoint_28a clearing shelf_1")

test_admin_cmd("TEST 7: List all templates", "@list templates")

test_admin_cmd("TEST 8: List item templates only", "@list templates items")

# Test invalid commands
test_admin_cmd("TEST 9: Unknown command (should fail gracefully)", "@unknown")

test_admin_cmd("TEST 10: List with missing args (should show usage)", "@list locations")

# Test permission check with player role
print(f"\n{'='*70}")
print("TEST 11: Player trying admin command (should be denied)")
print(f"{'='*70}")
payload = {
    "command": "@stats",
    "experience": "wylding-woods",
    "user_context": {"role": "player", "user_id": "player@test.com"}
}
try:
    response = requests.post(
        f"{BASE_URL}/game/command",
        headers=HEADERS,
        json=payload,
        timeout=30
    )
    result = response.json()
    print(json.dumps(result, indent=2))
    if result.get("narrative"):
        print(f"\n📋 {result['narrative']}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("✅ ADMIN COMMAND TESTS COMPLETE")
print("="*70)
