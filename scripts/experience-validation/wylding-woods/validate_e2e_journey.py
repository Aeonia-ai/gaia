#!/usr/bin/env python3
"""
Realistic journey test for Wylding Woods unified experience system.

This test simulates a player's journey at Woander's Magical Shop:
- Exploring the shop (entrance, counter, back room)
- Talking to Woander the shopkeeper
- Checking inventory
- Natural language interactions

Note: This is a single-location test focused on sublocation navigation
and NPC interaction within one venue.
"""

import requests
import json
import sys
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

# Use a unique user for clean test
TEST_USER = f"journey-test-{int(time.time())}@aeonia.ai"


def send_command(message: str) -> Dict[str, Any]:
    """Send a game command."""
    payload = {
        "experience": "wylding-woods",
        "message": message,
        "user_id": TEST_USER
    }

    try:
        response = requests.post(
            f"{BASE_URL}/experience/interact",
            headers=HEADERS,
            json=payload,
            timeout=30
        )
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def display_result(result: Dict[str, Any], step_name: str):
    """Display command result."""
    print(f"\n{'='*70}")
    print(f"🎮 {step_name}")
    print(f"{'='*70}")

    if not result.get("success"):
        error = result.get("error", {})
        if isinstance(error, dict):
            print(f"❌ Failed: {error.get('message', 'Unknown error')}")
            if error.get('code'):
                print(f"   Error code: {error['code']}")
        else:
            print(f"❌ Failed: {error}")
        return False

    narrative = result.get("narrative", "")
    print(f"\n📖 {narrative[:300]}...")

    metadata = result.get("metadata", {})
    if metadata.get("location"):
        print(f"\n📍 Location: {metadata.get('location')}/{metadata.get('sublocation', 'center')}")

    actions = result.get("available_actions", [])
    if actions:
        print(f"\n⚡ Available actions ({len(actions)}):")
        for action in actions[:5]:
            print(f"   • {action}")
        if len(actions) > 5:
            print(f"   ... and {len(actions) - 5} more")

    return True


def run_realistic_journey():
    """Run a realistic player journey through Dream Weaver's Clearing."""
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║    WYLDING WOODS - DREAM WEAVER'S CLEARING JOURNEY TEST             ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print(f"\n🆔 Test User: {TEST_USER}")
    print("📝 Simulates a player's journey at Dream Weaver's Clearing (waypoint_28a)")
    print("📍 Single waypoint test - player physically at GPS location\n")

    steps = []

    # CHAPTER 1: ARRIVING AT THE CLEARING
    print("\n" + "="*70)
    print("📖 CHAPTER 1: ARRIVING AT THE DREAM WEAVER'S CLEARING")
    print("="*70)

    steps.append(("👀 Step 1: Look around at center", "look around"))
    steps.append(("📦 Step 2: Check starting inventory", "check my inventory"))

    # CHAPTER 2: EXPLORING THE SHELVES
    print("\n" + "="*70)
    print("📖 CHAPTER 2: EXPLORING THE MUSHROOM SHELVES")
    print("="*70)

    steps.append(("🍄 Step 3: Go to first shelf", "go to shelf 1"))
    steps.append(("👁️  Step 4: Look at shelf 1", "look around"))
    steps.append(("✋ Step 5: Take dream bottle", "take the dream bottle"))
    steps.append(("🍄 Step 6: Go to second shelf", "go to shelf 2"))
    steps.append(("👁️  Step 7: Look at shelf 2", "look around"))
    steps.append(("✋ Step 8: Take dream bottle", "take the dream bottle"))
    steps.append(("🍄 Step 9: Go to third shelf", "go to shelf 3"))
    steps.append(("👁️  Step 10: Look at shelf 3", "look around"))
    steps.append(("✋ Step 11: Take dream bottle", "take the dream bottle"))
    steps.append(("🎒 Step 12: Check inventory", "what do I have"))

    # CHAPTER 3: MEETING THE DREAM WEAVER
    print("\n" + "="*70)
    print("📖 CHAPTER 3: MEETING LOUISA THE DREAM WEAVER")
    print("="*70)

    steps.append(("🚪 Step 13: Go to fairy door", "go to fairy door 1"))
    steps.append(("👁️  Step 14: Look around", "look around"))
    steps.append(("🧚 Step 15: Talk to Louisa", "talk to Louisa"))
    steps.append(("💬 Step 16: Ask about quest", "ask about the dream bottles"))

    # CHAPTER 4: RETURNING THE BOTTLES
    print("\n" + "="*70)
    print("📖 CHAPTER 4: RETURNING THE DREAM BOTTLES")
    print("="*70)

    steps.append(("🎁 Step 17: Return first bottle", "give dream bottle to Louisa"))
    steps.append(("🎁 Step 18: Return second bottle", "give another dream bottle to Louisa"))
    steps.append(("🎁 Step 19: Return third bottle", "give the last dream bottle to Louisa"))
    steps.append(("✨ Step 20: Final inventory check", "check inventory"))

    # Execute journey
    passed = 0
    failed = 0

    for step_name, command in steps:
        result = send_command(command)
        success = display_result(result, step_name)

        if success:
            passed += 1
        else:
            failed += 1
            # Continue even on failure to see what happens next

        time.sleep(0.5)  # Small delay between commands for readability

    # Summary
    print(f"\n{'='*70}")
    print(f"📊 JOURNEY SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Successful steps: {passed}/{len(steps)}")
    print(f"❌ Failed steps: {failed}/{len(steps)}")

    if failed == 0:
        print(f"\n🎉 Perfect journey! All steps completed successfully!")
    elif failed < len(steps) / 2:
        print(f"\n👍 Good journey! Most steps worked, but some need attention.")
    else:
        print(f"\n⚠️  Journey had significant issues. Review failed steps.")

    print(f"{'='*70}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_realistic_journey()
    sys.exit(0 if success else 1)
