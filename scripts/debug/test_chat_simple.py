#!/usr/bin/env python3
"""Simple chat test without pauses."""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def send_command(test_num: str, command: str, sublocation: str):
    """Send command and show I/O."""
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
    print(f"TEST #{test_num}: \"{command}\"")
    print(f"{'='*70}")
    print("\n📤 INPUT:")
    print(json.dumps(payload, indent=2))

    try:
        response = requests.post(
            f"{BASE_URL}/game/command",
            headers=HEADERS,
            json=payload,
            timeout=30
        )

        print(f"\n📥 OUTPUT (Status {response.status_code}):")
        result = response.json()
        print(json.dumps(result, indent=2))

        if result.get("narrative"):
            print(f"\n📖 GAME SAYS:")
            print(f"   {result['narrative']}")

        return result
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return {"success": False, "error": str(e)}


print("╔═══════════════════════════════════════════════════════════════════╗")
print("║         WYLDING WOODS: Natural Language Game Commands             ║")
print("╚═══════════════════════════════════════════════════════════════════╝")

# Test 1: Look around
send_command("1", "Look at the shelf", "shelf_1")

# Test 2: Pick up bottle
send_command("2", "Pick up the glowing bottle with spiral symbol", "shelf_1")

# Test 3: Check inventory
send_command("3", "What am I carrying?", "shelf_1")

# Test 4: Wrong house
send_command("4", "Put the bottle into this fairy house", "fairy_door_2")

# Test 5: Correct house
send_command("5", "Return the spiral bottle to this house", "fairy_door_1")

# Test 6: Final check
send_command("6", "Check my inventory", "fairy_door_1")

print("\n" + "="*70)
print("✅ TESTS COMPLETE")
print("="*70)
