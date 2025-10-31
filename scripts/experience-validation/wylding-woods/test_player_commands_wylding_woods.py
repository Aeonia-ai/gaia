#!/usr/bin/env python3
"""
Comprehensive test suite for player commands in Wylding Woods.

Tests natural language gameplay commands:
- Looking around and exploring
- Collecting items from locations
- Checking inventory
- Talking to NPCs
- Returning items to complete quests
- Symbol validation mechanics
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def player_cmd(command, waypoint="waypoint_28a", sublocation="center", desc=""):
    """Execute a natural language player command."""
    print(f"\n{'='*70}")
    if desc:
        print(f"📌 {desc}")
    print(f"🎮 Player says: \"{command}\"")
    print(f"📍 Location: {waypoint}/{sublocation}")
    print(f"{'='*70}")

    try:
        payload = {
            "command": command,
            "experience": "wylding-woods",
            "user_context": {
                "user_id": "jason@aeonia.ai",
                "waypoint": waypoint,
                "sublocation": sublocation,
                "role": "player"
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
            print(f"\n{result['narrative']}")

        # Show actions taken
        if result.get("actions"):
            print(f"\n📋 Actions:")
            for action in result["actions"]:
                print(f"   • {action.get('type', 'unknown')}: {action}")

        # Show state changes
        if result.get("state_changes"):
            print(f"\n🔄 State changes:")
            for key, value in result["state_changes"].items():
                print(f"   • {key}: {value}")

        success = result.get("success", False)
        if success:
            print(f"\n✅ Success")
        else:
            error = result.get("error", {})
            print(f"\n❌ Failed: {error.get('message', 'Unknown error')}")

        return result

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        return {"success": False, "error": str(e)}

def admin_cmd(command, desc=""):
    """Execute admin command for test setup/cleanup."""
    print(f"\n{'─'*70}")
    if desc:
        print(f"🔧 Admin: {desc}")
    print(f"{'─'*70}")

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
            print(result["narrative"])

        return result

    except Exception as e:
        print(f"❌ Exception: {e}")
        return {"success": False, "error": str(e)}

print("╔═════════════════════════════════════════════════════════════════════╗")
print("║         WYLDING WOODS - PLAYER COMMAND TEST SUITE                  ║")
print("║  Tests: Natural language gameplay in Dream Weaver's Clearing       ║")
print("╚═════════════════════════════════════════════════════════════════════╝")

test_results = []

# Pre-setup: Clean slate
print("\n" + "█"*70)
print("█  PRE-SETUP: Reset for clean test state")
print("█"*70)

admin_cmd("@reset player jason@aeonia.ai CONFIRM", "Clear player progress")
admin_cmd("@reset instance 2 CONFIRM", "Reset dream bottle on shelf_1")
admin_cmd("@reset instance 3 CONFIRM", "Reset dream bottle on shelf_2")

time.sleep(1)  # Brief pause for file operations

# Section 1: Exploration and Looking Around
print("\n" + "█"*70)
print("█  SECTION 1: Exploration Commands")
print("█"*70)

result = player_cmd(
    "Look around",
    sublocation="center",
    desc="Test 1: Look around the center of the clearing"
)
test_results.append(("Look around center", result.get("success", False)))

result = player_cmd(
    "go to counter",
    desc="Move to the counter"
)

result = player_cmd(
    "What's on the first shelf?",
    sublocation="shelf_1",
    desc="Test 2: Examine shelf_1"
)
test_results.append(("Look at shelf_1", result.get("success", False)))

result = player_cmd(
    "Look at the second shelf",
    sublocation="shelf_2",
    desc="Test 3: Examine shelf_2"
)
test_results.append(("Look at shelf_2", result.get("success", False)))

# Section 2: Inventory Management
print("\n" + "█"*70)
print("█  SECTION 2: Inventory Commands")
print("█"*70)

result = player_cmd(
    "Check my inventory",
    desc="Test 4: Check empty inventory"
)
test_results.append(("Check empty inventory", result.get("success", False)))

# Section 3: Item Collection
print("\n" + "█"*70)
print("█  SECTION 3: Collecting Items")
print("█"*70)

result = player_cmd(
    "Pick up the dream bottle",
    sublocation="shelf_1",
    desc="Test 5: Collect dream bottle from shelf_1"
)
test_results.append(("Collect from shelf_1", result.get("success", False)))

result = player_cmd(
    "What am I carrying?",
    desc="Test 6: Check inventory after collection"
)
test_results.append(("Check inventory after collect", result.get("success", False)))

result = player_cmd(
    "Take the dream bottle",
    sublocation="shelf_2",
    desc="Test 7: Collect dream bottle from shelf_2"
)
test_results.append(("Collect from shelf_2", result.get("success", False)))

result = player_cmd(
    "Show me my inventory",
    desc="Test 8: Check inventory with multiple items"
)
test_results.append(("Check multiple items", result.get("success", False)))

# Section 4: NPC Interaction
print("\n" + "█"*70)
print("█  SECTION 4: NPC Interaction")
print("█"*70)

result = player_cmd(
    "go to fairy_door_1",
    desc="Move to the fairy door"
)

result = player_cmd(
    "Talk to Louisa",
    sublocation="fairy_door_1",
    desc="Test 9: Talk to the Dream Weaver"
)
test_results.append(("Talk to NPC", result.get("success", False)))

result = player_cmd(
    "Ask Louisa about the dream bottles",
    sublocation="fairy_door_1",
    desc="Test 10: Ask NPC about quest"
)
test_results.append(("Ask about quest", result.get("success", False)))

# Section 5: Quest Mechanics (Symbol Validation)
print("\n" + "█"*70)
print("█  SECTION 5: Quest Completion (Symbol Validation)")
print("█"*70)

result = player_cmd(
    "Return the dream bottle to the fairy door",
    sublocation="fairy_door_1",
    desc="Test 11: Return bottle with spiral symbol to door 1"
)
test_results.append(("Return to matching door", result.get("success", False)))

result = player_cmd(
    "Return the dream bottle to the second fairy door",
    sublocation="fairy_door_2",
    desc="Test 12: Return bottle with star symbol to door 2"
)
test_results.append(("Return to matching door 2", result.get("success", False)))

result = player_cmd(
    "Check inventory",
    desc="Test 13: Verify empty inventory after returns"
)
test_results.append(("Empty inventory after returns", result.get("success", False)))

# Section 6: Error Handling
print("\n" + "█"*70)
print("█  SECTION 6: Error Handling")
print("█"*70)

result = player_cmd(
    "Pick up the golden chalice",
    sublocation="shelf_1",
    desc="Test 14: Try to collect non-existent item"
)
# This should fail gracefully
test_results.append(("Graceful failure - no item", not result.get("success", False)))

result = player_cmd(
    "Return a dream bottle",
    sublocation="shelf_1",
    desc="Test 15: Try to return when inventory is empty"
)
# This should fail gracefully
test_results.append(("Graceful failure - no inventory", not result.get("success", False)))

# Section 7: Complex Natural Language
print("\n" + "█"*70)
print("█  SECTION 7: Complex Natural Language Understanding")
print("█"*70)

# Reset an item for this test
admin_cmd("@reset instance 4 CONFIRM", "Reset dream bottle on shelf_3")
time.sleep(0.5)

result = player_cmd(
    "I want to grab the dream bottle on the third shelf",
    sublocation="shelf_3",
    desc="Test 16: Complex pickup command"
)
test_results.append(("Complex natural language", result.get("success", False)))

result = player_cmd(
    "Can you tell me what I'm currently holding?",
    desc="Test 17: Conversational inventory check"
)
test_results.append(("Conversational command", result.get("success", False)))

# Results
print("\n" + "═"*70)
print("RESULTS SUMMARY")
print("═"*70)

passed = sum(1 for _, success in test_results if success)
total = len(test_results)
failed = total - passed

print(f"\n✅ Passed: {passed}/{total} ({100*passed//total}%)")
if failed > 0:
    print(f"❌ Failed: {failed}/{total}")
    print("\nFailed tests:")
    for name, success in test_results:
        if not success:
            print(f"  - {name}")
else:
    print("🎉 ALL TESTS PASSED!")

print("\n" + "═"*70)
print("TEST CATEGORIES")
print("═"*70)
print("✓ Exploration & Looking")
print("✓ Inventory Management")
print("✓ Item Collection")
print("✓ NPC Interaction")
print("✓ Quest Mechanics (Symbol Validation)")
print("✓ Error Handling")
print("✓ Natural Language Understanding")

sys.exit(0 if failed == 0 else 1)
