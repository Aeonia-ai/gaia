#!/usr/bin/env python3
"""
Comprehensive test suite for admin commands.

Tests the core world-building commands:
- @create waypoint/location/sublocation
- @connect / @disconnect
- @edit waypoint/location/sublocation
- @inspect
- @delete (with CONFIRM)
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def admin_cmd(command, desc=""):
    """Execute an admin command."""
    print(f"\n{'='*70}")
    if desc:
        print(f"📌 {desc}")
    print(f"💻 Admin says: \"{command}\"")
    print(f"{'='*70}")

    try:
        payload = {
            "command": command,
            "experience": "wylding-woods",
            "user_context": {
                "user_id": "admin@aeonia.ai",
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
            print(f"\n{result['narrative']}")

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

print("╔═════════════════════════════════════════════════════════════════════╗")
print("║         ADMIN COMMANDS - FULL TEST SUITE                         ║")
print("║  Tests: @create, @connect, @edit, @inspect, @delete              ║")
print("╚═════════════════════════════════════════════════════════════════════╝")

test_results = []

# --- Test Data ---
TEST_WP = "test_waypoint"
TEST_LOC = "test_location"
TEST_SUBLOC_A = "test_subloc_a"
TEST_SUBLOC_B = "test_subloc_b"

# --- Cleanup: Ensure test data doesn't exist from a previous failed run ---
print("\n" + "█"*70)
print("█  PRE-SETUP: Clean up any previous test data")
print("█"*70)
admin_cmd(f"@delete waypoint {TEST_WP} CONFIRM", "Cleanup: Deleting test waypoint if it exists")
time.sleep(1)

# --- Section 1: @create Commands ---
print("\n" + "█"*70)
print("█  SECTION 1: @create Commands")
print("█"*70)

result = admin_cmd(f"@create waypoint {TEST_WP} Test Waypoint", "Test 1: Create a new waypoint")
test_results.append(("Create waypoint", result.get("success", False)))

result = admin_cmd(f"@create location {TEST_WP} {TEST_LOC} Test Location", "Test 2: Create a new location")
test_results.append(("Create location", result.get("success", False)))

result = admin_cmd(f"@create sublocation {TEST_WP} {TEST_LOC} {TEST_SUBLOC_A} Test Sublocation A", "Test 3: Create sublocation A")
test_results.append(("Create sublocation A", result.get("success", False)))

result = admin_cmd(f"@create sublocation {TEST_WP} {TEST_LOC} {TEST_SUBLOC_B} Test Sublocation B", "Test 4: Create sublocation B")
test_results.append(("Create sublocation B", result.get("success", False)))

# --- Section 2: @connect and @disconnect Commands ---
print("\n" + "█"*70)
print("█  SECTION 2: @connect and @disconnect Commands")
print("█"*70)

result = admin_cmd(f"@connect {TEST_WP} {TEST_LOC} {TEST_SUBLOC_A} {TEST_SUBLOC_B} north", "Test 5: Connect two sublocations")
test_results.append(("Connect sublocations", result.get("success", False)))

# Verify connection with @inspect
result = admin_cmd(f"@inspect sublocation {TEST_WP} {TEST_LOC} {TEST_SUBLOC_A}", "Test 6: Verify connection on sublocation A")
test_results.append(("Verify connection A", result.get("success", False) and TEST_SUBLOC_B in result.get("narrative", "")))

result = admin_cmd(f"@disconnect {TEST_WP} {TEST_LOC} {TEST_SUBLOC_A} {TEST_SUBLOC_B}", "Test 7: Disconnect two sublocations")
test_results.append(("Disconnect sublocations", result.get("success", False)))

# Verify disconnection with @inspect
result = admin_cmd(f"@inspect sublocation {TEST_WP} {TEST_LOC} {TEST_SUBLOC_A}", "Test 8: Verify disconnection on sublocation A")
test_results.append(("Verify disconnection A", result.get("success", False) and TEST_SUBLOC_B not in result.get("narrative", "")))

# --- Section 3: @edit Commands ---
print("\n" + "█"*70)
print("█  SECTION 3: @edit Commands")
print("█"*70)

result = admin_cmd(f"@edit waypoint {TEST_WP} name Updated Waypoint Name", "Test 9: Edit waypoint name")
test_results.append(("Edit waypoint name", result.get("success", False)))

result = admin_cmd(f"@edit location {TEST_WP} {TEST_LOC} description A new description", "Test 10: Edit location description")
test_results.append(("Edit location description", result.get("success", False)))

result = admin_cmd(f"@edit sublocation {TEST_WP} {TEST_LOC} {TEST_SUBLOC_A} interactable false", "Test 11: Edit sublocation property")
test_results.append(("Edit sublocation property", result.get("success", False)))

# Verify edits with @inspect
result = admin_cmd(f"@inspect waypoint {TEST_WP}", "Test 12: Verify waypoint edit")
test_results.append(("Verify waypoint edit", result.get("success", False) and "Updated Waypoint Name" in result.get("narrative", "")))

# --- Section 4: @delete Commands ---
print("\n" + "█"*70)
print("█  SECTION 4: @delete Commands (Cleanup)")
print("█"*70)

result = admin_cmd(f"@delete sublocation {TEST_WP} {TEST_LOC} {TEST_SUBLOC_A}", "Test 13: Try to delete without CONFIRM")
test_results.append(("Delete safety check", not result.get("success", True)))

result = admin_cmd(f"@delete sublocation {TEST_WP} {TEST_LOC} {TEST_SUBLOC_A} CONFIRM", "Test 14: Delete sublocation A")
test_results.append(("Delete sublocation A", result.get("success", False)))

result = admin_cmd(f"@delete location {TEST_WP} {TEST_LOC} CONFIRM", "Test 15: Delete location (cascading)")
test_results.append(("Delete location", result.get("success", False)))

result = admin_cmd(f"@delete waypoint {TEST_WP} CONFIRM", "Test 16: Delete waypoint (cascading)")
test_results.append(("Delete waypoint", result.get("success", False)))

# --- Results ---
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

sys.exit(0 if failed == 0 else 1)
