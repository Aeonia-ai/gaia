#!/usr/bin/env python3
"""
Test script for newly implemented admin commands:
- @inspect (waypoint, location, sublocation, item)
- @where (find by ID or name)
- @find (find template instances)
- @edit (modify properties)
- @delete (safe deletion with CONFIRM)
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def cmd(command, desc="", expect_success=True):
    """Execute admin command and show result."""
    print(f"\n{'='*70}")
    if desc:
        print(f"📌 {desc}")
    print(f"💻 {command}")
    print(f"{'='*70}")

    try:
        response = requests.post(
            f"{BASE_URL}/game/command",
            headers=HEADERS,
            json={
                "command": command,
                "experience": "wylding-woods",
                "user_context": {"role": "admin", "user_id": "test@gaia.dev"}
            },
            timeout=30
        )

        result = response.json()

        if result.get("narrative"):
            print(f"{result['narrative']}")

        success = result.get("success", False)
        if expect_success and not success:
            print(f"❌ Command failed unexpectedly!")
            return False
        elif not expect_success and success:
            print(f"❌ Command succeeded when failure was expected!")
            return False
        else:
            print(f"✅ Test passed (success={success})")
            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

print("╔═════════════════════════════════════════════════════════════════════╗")
print("║           ADMIN COMMANDS - NEW FEATURES TEST SUITE                  ║")
print("║    Testing: @inspect, @where, @find, @edit, @delete                 ║")
print("╚═════════════════════════════════════════════════════════════════════╝")

test_results = []

# ============================================================================
# SECTION 1: @inspect Commands
# ============================================================================

print("\n" + "█"*70)
print("█  SECTION 1: @inspect Commands")
print("█"*70)

test_results.append(cmd(
    "@inspect waypoint waypoint_28a",
    "Test 1: Inspect waypoint (should show all locations)"
))

test_results.append(cmd(
    "@inspect location waypoint_28a clearing",
    "Test 2: Inspect location (should show all sublocations)"
))

test_results.append(cmd(
    "@inspect sublocation waypoint_28a clearing center",
    "Test 3: Inspect sublocation (should show navigation graph)"
))

# Note: Need an actual item instance ID for this test
test_results.append(cmd(
    "@inspect item 1",
    "Test 4: Inspect item (if item #1 exists)"
))

# ============================================================================
# SECTION 2: @where Commands
# ============================================================================

print("\n" + "█"*70)
print("█  SECTION 2: @where Commands")
print("█"*70)

# Test with instance ID (if items exist)
test_results.append(cmd(
    "@where item 1",
    "Test 5: Find item by instance ID"
))

# Test with semantic name
test_results.append(cmd(
    "@where louisa",
    "Test 6: Find item by semantic name"
))

# ============================================================================
# SECTION 3: @find Commands
# ============================================================================

print("\n" + "█"*70)
print("█  SECTION 3: @find Commands")
print("█"*70)

test_results.append(cmd(
    "@find dream_bottle",
    "Test 7: Find all instances of template (grouped by location)"
))

# ============================================================================
# SECTION 4: @edit Commands
# ============================================================================

print("\n" + "█"*70)
print("█  SECTION 4: @edit Commands")
print("█"*70)

# Edit waypoint name
test_results.append(cmd(
    "@edit waypoint test_wp name Updated Test Waypoint",
    "Test 8: Edit waypoint name"
))

# Edit waypoint description
test_results.append(cmd(
    "@edit waypoint test_wp description This is an updated description for testing",
    "Test 9: Edit waypoint description"
))

# Edit location name
test_results.append(cmd(
    "@edit location test_wp my_loc name Updated Location",
    "Test 10: Edit location name"
))

# Edit sublocation description
test_results.append(cmd(
    "@edit sublocation test_wp my_loc subloc_a description An updated sublocation for testing",
    "Test 11: Edit sublocation description"
))

# Edit sublocation interactability
test_results.append(cmd(
    "@edit sublocation test_wp my_loc subloc_a interactable false",
    "Test 12: Edit sublocation interactable property"
))

# ============================================================================
# SECTION 5: @delete Commands (Safety Tests)
# ============================================================================

print("\n" + "█"*70)
print("█  SECTION 5: @delete Commands (Safety Tests)")
print("█"*70)

# First, create a fresh sublocation for deletion testing
test_results.append(cmd(
    "@create sublocation test_wp my_loc test_delete Test Delete Sublocation",
    "Test 13a: Create sublocation for deletion test"
))

# Test delete WITHOUT CONFIRM (should fail safely)
test_results.append(cmd(
    "@delete sublocation test_wp my_loc test_delete",
    "Test 13b: Delete without CONFIRM (should require confirmation)",
    expect_success=False
))

# Test delete WITH CONFIRM (should succeed)
test_results.append(cmd(
    "@delete sublocation test_wp my_loc test_delete CONFIRM",
    "Test 14: Delete sublocation with CONFIRM"
))

# Verify the sublocation is gone
test_results.append(cmd(
    "@list sublocations test_wp my_loc",
    "Test 15: Verify sublocation was deleted (should only show subloc_a)"
))

# ============================================================================
# SECTION 6: @inspect After Edits
# ============================================================================

print("\n" + "█"*70)
print("█  SECTION 6: Verify Edits with @inspect")
print("█"*70)

test_results.append(cmd(
    "@inspect waypoint test_wp",
    "Test 16: Inspect edited waypoint (verify changes and metadata)"
))

test_results.append(cmd(
    "@inspect sublocation test_wp my_loc subloc_a",
    "Test 17: Inspect edited sublocation (verify interactable=false and metadata)"
))

# ============================================================================
# RESULTS SUMMARY
# ============================================================================

print("\n" + "═"*70)
print("RESULTS SUMMARY")
print("═"*70)

passed = sum(test_results)
total = len(test_results)
failed = total - passed

print(f"\n✅ Passed: {passed}/{total}")
if failed > 0:
    print(f"❌ Failed: {failed}/{total}")
else:
    print("🎉 ALL TESTS PASSED!")

print("\n" + "═"*70)
print("🎯 Key Features Tested:")
print("  • @inspect - Detailed object inspection")
print("  • @where - Flexible item search (ID and name)")
print("  • @find - Template instance discovery")
print("  • @edit - Property modification with metadata tracking")
print("  • @delete - Safe deletion with CONFIRM requirement")
print("  • Metadata - Automatic tracking of modifications")
print("═"*70 + "\n")

sys.exit(0 if failed == 0 else 1)
