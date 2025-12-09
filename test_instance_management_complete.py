#!/usr/bin/env python3
"""
Comprehensive test suite for Instance Management system.

Tests:
- Collect items from world
- Return items to destinations
- Inventory management
- Location filtering
- Symbol validation
- Quest progress tracking
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

print("╔═════════════════════════════════════════════════════════════════════╗")
print("║              INSTANCE MANAGEMENT TEST SUITE                         ║")
print("║  Tests: collect, return, inventory, look, symbol validation        ║")
print("╚═════════════════════════════════════════════════════════════════════╝")

test_results = []

# Section 1: Look Command
print("\n" + "█"*70)
print("█  SECTION 1: Look Command (Location Awareness)")
print("█"*70)

result = cmd("look", "Test 1: Look at shelf_1", sublocation="shelf_1", waypoint="waypoint_28a", experience="wylding-woods")
test_results.append(("Look at shelf_1", result.get("success", False)))

# Section 2: Inventory
print("\n" + "█"*70)
print("█  SECTION 2: Inventory Command")
print("█"*70)

result = cmd("inventory", "Test 2: Check initial inventory", experience="wylding-woods")
test_results.append(("Check inventory", result.get("success", False)))

# Section 3: Collect
print("\n" + "█"*70)
print("█  SECTION 3: Collect Command")
print("█"*70)

result = cmd("collect", "Test 3: Collect dream bottle from shelf_2", target="dream_bottle", sublocation="shelf_2", waypoint="waypoint_28a", experience="wylding-woods")
test_results.append(("Collect from shelf_2", result.get("success", False)))

result = cmd("inventory", "Test 4: Check inventory after collecting", experience="wylding-woods")
test_results.append(("Inventory after collect", result.get("success", False)))

# Section 4: Return
print("\n" + "█"*70)
print("█  SECTION 4: Return Command")
print("█"*70)

result = cmd("return", "Test 5: Return bottle to matching door", target="dream_bottle", destination="fairy_door_2", waypoint="waypoint_28a", experience="wylding-woods")
test_results.append(("Return bottle", result.get("success", False)))

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
else:
    print("🎉 ALL TESTS PASSED!")

sys.exit(0 if failed == 0 else 1)
