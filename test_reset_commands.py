#!/usr/bin/env python3
"""
Test suite for @reset admin commands.

Tests:
- @reset instance <id> CONFIRM - Reset single instance
- @reset player <user_id> CONFIRM - Delete player progress
- @reset experience CONFIRM - Nuclear reset
- CONFIRM safety mechanism
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def cmd(action, desc="", **kwargs):
    """Execute simple command via test endpoint."""
    print(f"\n{'='*70}")
    if desc:
        print(f"📌 {desc}")
    print(f"💻 Action: {action}")
    if kwargs:
        print(f"   Params: {kwargs}")
    print(f"{'='*70}")

    try:
        payload = {
            "action": action,
            **kwargs
        }

        response = requests.post(
            f"{BASE_URL}/game/test/simple-command",
            headers=HEADERS,
            json=payload,
            timeout=30
        )

        result = response.json()

        if result.get("narrative"):
            print(f"{result['narrative']}")

        success = result.get("success", False)
        if success:
            print(f"✅ Success")
        else:
            error = result.get("error", {})
            print(f"❌ Failed: {error.get('message', 'Unknown error')}")

        return result

    except Exception as e:
        print(f"❌ Exception: {e}")
        return {"success": False, "error": str(e)}

def admin_cmd(command, desc=""):
    """Execute admin command via game command endpoint."""
    print(f"\n{'='*70}")
    if desc:
        print(f"📌 {desc}")
    print(f"💻 Admin: {command}")
    print(f"{'='*70}")

    try:
        payload = {
            "command": command,
            "experience": "wylding-woods",
            "user_context": {
                "user_id": "jason@aeonia.ai",
                "waypoint": "waypoint_28a",
                "role": "admin"
            }
        }

        response = requests.post(
            f"{BASE_URL}/game/command",
            headers=HEADERS,
            json=payload,
            timeout=30
        )

        result = response.json()

        if result.get("narrative"):
            print(f"{result['narrative']}")

        success = result.get("success", False)
        if success:
            print(f"✅ Success")
        else:
            error = result.get("error", {})
            print(f"❌ Failed: {error.get('message', 'Unknown error')}")

        return result

    except Exception as e:
        print(f"❌ Exception: {e}")
        return {"success": False, "error": str(e)}

print("╔═════════════════════════════════════════════════════════════════════╗")
print("║              @RESET COMMAND TEST SUITE                              ║")
print("║  Tests: instance reset, player reset, experience reset, safety     ║")
print("╚═════════════════════════════════════════════════════════════════════╝")

test_results = []

# Pre-setup: Reset instance to ensure clean state
print("\n" + "█"*70)
print("█  PRE-SETUP: Ensure clean test state")
print("█"*70)

admin_cmd("@reset instance 2 CONFIRM", "Pre-setup: Reset instance #2 to clean state")

# Setup: Collect an item so we have state to reset
print("\n" + "█"*70)
print("█  SETUP: Create state to reset")
print("█"*70)

result = cmd("collect", "Setup: Collect dream bottle from shelf_1",
             target="dream_bottle", sublocation="shelf_1",
             waypoint="waypoint_28a", experience="wylding-woods")
test_results.append(("Setup: Collect item", result.get("success", False)))

result = cmd("inventory", "Setup: Verify item in inventory",
             experience="wylding-woods")
test_results.append(("Setup: Verify inventory", result.get("success", False)))

# Section 1: Safety Mechanism (without CONFIRM)
print("\n" + "█"*70)
print("█  SECTION 1: CONFIRM Safety Mechanism")
print("█"*70)

result = admin_cmd("@reset instance 2", "Test 1: Try reset without CONFIRM")
# Should fail and show usage - check for "CONFIRM" in narrative or error
has_confirm_warning = "CONFIRM" in result.get("narrative", "") or \
                      "CONFIRM" in result.get("error", {}).get("message", "") or \
                      not result.get("success", True)
test_results.append(("Safety: Reset without CONFIRM warns", has_confirm_warning))

# Section 2: Reset Single Instance
print("\n" + "█"*70)
print("█  SECTION 2: Reset Single Instance")
print("█"*70)

result = admin_cmd("@reset instance 2 CONFIRM", "Test 2: Reset instance #2")
test_results.append(("Reset instance", result.get("success", False)))

# Verify instance was reset by trying to collect again
result = cmd("collect", "Test 3: Verify instance reset (can collect again)",
             target="dream_bottle", sublocation="shelf_1",
             waypoint="waypoint_28a", experience="wylding-woods")
test_results.append(("Verify instance reset", result.get("success", False)))

# Section 3: Reset Player Progress
print("\n" + "█"*70)
print("█  SECTION 3: Reset Player Progress")
print("█"*70)

# First ensure we have something in inventory
result = cmd("inventory", "Setup: Check current inventory",
             experience="wylding-woods")

result = admin_cmd("@reset player jason@aeonia.ai CONFIRM",
                   "Test 4: Reset player progress")
test_results.append(("Reset player", result.get("success", False)))

# Verify player progress was reset
result = cmd("inventory", "Test 5: Verify empty inventory after reset",
             experience="wylding-woods")
# Check if inventory is empty (no items listed)
has_empty_inventory = "not carrying" in result.get("narrative", "").lower() or \
                      "don't have" in result.get("narrative", "").lower() or \
                      "inventory is empty" in result.get("narrative", "").lower() or \
                      "inventory: []" in str(result).lower()
test_results.append(("Verify player reset", has_empty_inventory))

# Section 4: Experience Reset (commented out - too destructive)
print("\n" + "█"*70)
print("█  SECTION 4: Experience Reset (Preview Only)")
print("█"*70)

result = admin_cmd("@reset experience", "Test 6: Try experience reset without CONFIRM")
# Should fail and show usage requiring CONFIRM
requires_confirm = not result.get("success", True) or "CONFIRM" in result.get("narrative", "") or \
                   "CONFIRM" in result.get("error", {}).get("message", "")
test_results.append(("Experience reset safety", requires_confirm))

# NOTE: Not testing actual "@reset experience CONFIRM" as it's too destructive for automated tests

# Results
print("\n" + "═"*70)
print("RESULTS SUMMARY")
print("═"*70)

passed = sum(1 for _, success in test_results if success)
total = len(test_results)
failed = total - passed

print(f"\n✅ Passed: {passed}/{total}")
if failed > 0:
    print(f"❌ Failed: {failed}/{total}")
    print("\nFailed tests:")
    for name, success in test_results:
        if not success:
            print(f"  - {name}")
else:
    print("🎉 ALL TESTS PASSED!")

sys.exit(0 if failed == 0 else 1)
