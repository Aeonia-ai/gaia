#!/usr/bin/env python3
"""
Test Game Commands via Natural Language Chat Interface

Tests the /game/command endpoint that uses LLM to process natural language.
This is the REAL game interface players will use.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def send_command(command: str, user_context: dict, session_state: dict = None):
    """Send a natural language command to the game."""
    payload = {
        "command": command,
        "experience": "wylding-woods",
        "user_context": user_context,
        "session_state": session_state or {}
    }

    print(f"\n{'='*70}")
    print(f"🎮 PLAYER SAYS: \"{command}\"")
    print(f"{'='*70}")
    print("\n📤 REQUEST:")
    print(f"POST {BASE_URL}/game/command")
    print(json.dumps(payload, indent=2))

    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/game/command",
        headers=HEADERS,
        json=payload
    )
    elapsed = time.time() - start_time

    result = response.json()

    print(f"\n📥 RESPONSE (took {elapsed:.2f}s):")
    print(json.dumps(result, indent=2))

    # Extract narrative for easy reading
    if result.get("success") and result.get("narrative"):
        print(f"\n📖 GAME SAYS:")
        print(f"   {result['narrative']}")

    return result


def main():
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║           WYLDING WOODS: NATURAL LANGUAGE GAME TEST               ║")
    print("║                   (via LLM Chat Interface)                        ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")

    # Set up player context
    user_context = {
        "waypoint": "waypoint_28a",
        "sublocation": "shelf_1",
        "role": "player",
        "experience_state": {}
    }

    session_state = {}

    # Test 1: Look around
    print("\n" + "="*70)
    print("TEST 1: Natural Language - Look Around")
    print("="*70)
    result = send_command(
        "Look at the shelf in front of me",
        user_context,
        session_state
    )

    input("\n[Press Enter to continue...]")

    # Test 2: Pick up bottle
    print("\n" + "="*70)
    print("TEST 2: Natural Language - Pick Up Item")
    print("="*70)
    result = send_command(
        "Pick up the glowing bottle with the spiral symbol",
        user_context,
        session_state
    )

    input("\n[Press Enter to continue...]")

    # Test 3: Check inventory
    print("\n" + "="*70)
    print("TEST 3: Natural Language - Check Inventory")
    print("="*70)
    result = send_command(
        "What am I carrying?",
        user_context,
        session_state
    )

    input("\n[Press Enter to continue...]")

    # Test 4: Try wrong house
    print("\n" + "="*70)
    print("TEST 4: Natural Language - Try Wrong House")
    print("="*70)
    user_context["sublocation"] = "fairy_door_2"
    result = send_command(
        "Put the bottle I'm carrying into this fairy house",
        user_context,
        session_state
    )

    input("\n[Press Enter to continue...]")

    # Test 5: Go to correct house and return
    print("\n" + "="*70)
    print("TEST 5: Natural Language - Return to Correct House")
    print("="*70)
    user_context["sublocation"] = "fairy_door_1"
    result = send_command(
        "Return the spiral bottle to this house",
        user_context,
        session_state
    )

    input("\n[Press Enter to continue...]")

    # Test 6: Check final state
    print("\n" + "="*70)
    print("TEST 6: Natural Language - Check Final State")
    print("="*70)
    result = send_command(
        "Check my inventory please",
        user_context,
        session_state
    )

    print("\n" + "="*70)
    print("✅ NATURAL LANGUAGE GAME TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️  Game interrupted by player.")
    except Exception as e:
        print(f"\n❌ Game error: {e}")
        import traceback
        traceback.print_exc()
