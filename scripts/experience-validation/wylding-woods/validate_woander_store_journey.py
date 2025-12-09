#!/usr/bin/env python3
"""
Woander Store Experience Journey Test

Tests the complete in-store VPS experience at Woander's Magical Shop:
- Phase 1: Meeting Louisa at the fairy door
- Phase 2 (Full): Scavenger hunt for dream bottles with symbol matching

This simulates the actual demo experience where:
1. Player enters store with "scrying mirror" (iPad)
2. Discovers and talks to Louisa the Dream Weaver fairy
3. Learns about Neebling stealing dreams
4. Collects 4 dream bottles from spawn zones
5. Returns bottles to matching fairy houses by symbol
6. Completes quest and celebrates with fairies

Note: All content is within a single VPS-scanned location (woander_store).
The player has physically arrived at the GPS waypoint for this store.
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
TEST_USER = f"woander-test-{int(time.time())}@aeonia.ai"


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


def run_woander_store_journey():
    """Run complete Woander Store experience test."""
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║       WYLDING WOODS - WOANDER STORE EXPERIENCE TEST                  ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print(f"\n🆔 Test User: {TEST_USER}")
    print("📝 Testing complete VPS in-store experience")
    print("📍 Location: Woander's Magical Shop (single VPS waypoint)\n")

    steps = []

    # PHASE 1: MEETING LOUISA (Demo Scope)
    print("\n" + "="*70)
    print("📖 PHASE 1: DISCOVERING LOUISA AT THE FAIRY DOOR")
    print("="*70)

    steps.append(("👀 Step 1: Look around store entrance", "look around"))
    steps.append(("📦 Step 2: Check starting inventory", "check my inventory"))
    steps.append(("🚪 Step 3: Go to main fairy door", "go to fairy door main"))
    steps.append(("👁️  Step 4: Look at fairy door", "look around"))
    steps.append(("🧚 Step 5: Talk to Louisa", "talk to Louisa"))
    steps.append(("💬 Step 6: Ask about the quest", "ask about helping with dream bottles"))

    # PHASE 2: SCAVENGER HUNT
    print("\n" + "="*70)
    print("📖 PHASE 2: DREAM BOTTLE SCAVENGER HUNT")
    print("="*70)

    steps.append(("🔍 Step 7: Go to spawn zone 1", "go to display shelf"))
    steps.append(("✋ Step 8: Collect peaceful bottle (spiral)", "take the peaceful dream bottle"))
    steps.append(("🔍 Step 9: Go to spawn zone 2", "go to window display"))
    steps.append(("✋ Step 10: Collect adventurous bottle (star)", "take the adventurous dream bottle"))
    steps.append(("🔍 Step 11: Go to spawn zone 3", "go to corner nook"))
    steps.append(("✋ Step 12: Collect joyful bottle (moon)", "take the joyful dream bottle"))
    steps.append(("🔍 Step 13: Go to spawn zone 4", "go to book alcove"))
    steps.append(("✋ Step 14: Collect whimsical bottle (sun)", "take the whimsical dream bottle"))
    steps.append(("🎒 Step 15: Check collected bottles", "check my inventory"))

    # PHASE 3: RETURNING BOTTLES TO FAIRY HOUSES
    print("\n" + "="*70)
    print("📖 PHASE 3: RETURNING BOTTLES TO FAIRY HOUSES")
    print("="*70)

    steps.append(("🏠 Step 16: Go to spiral fairy house", "go to spiral fairy house"))
    steps.append(("🎁 Step 17: Return spiral bottle", "return the peaceful dream bottle"))
    steps.append(("🏠 Step 18: Go to star fairy house", "go to star fairy house"))
    steps.append(("🎁 Step 19: Return star bottle", "return the adventurous dream bottle"))
    steps.append(("🏠 Step 20: Go to moon fairy house", "go to moon fairy house"))
    steps.append(("🎁 Step 21: Return moon bottle", "return the joyful dream bottle"))
    steps.append(("🏠 Step 22: Go to sun fairy house", "go to sun fairy house"))
    steps.append(("🎁 Step 23: Return sun bottle", "return the whimsical dream bottle"))

    # PHASE 4: CELEBRATION
    print("\n" + "="*70)
    print("📖 PHASE 4: QUEST COMPLETION")
    print("="*70)

    steps.append(("🎉 Step 24: Return to Louisa", "go to fairy door main"))
    steps.append(("💬 Step 25: Talk to Louisa", "talk to Louisa"))
    steps.append(("✨ Step 26: Final inventory check", "check inventory"))

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
    success = run_woander_store_journey()
    sys.exit(0 if success else 1)
