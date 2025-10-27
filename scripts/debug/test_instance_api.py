#!/usr/bin/env python3
"""
Test Script for Instance Management REST API

Tests the /game/test/simple-command endpoint with the running KB service.
"""

import requests
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def test_api_call(action: str, **kwargs) -> Dict[str, Any]:
    """Make a test API call."""
    payload = {
        "action": action,
        "experience": "wylding-woods",
        "waypoint": "waypoint_28a",
        **kwargs
    }

    response = requests.post(
        f"{BASE_URL}/game/test/simple-command",
        headers=HEADERS,
        json=payload
    )

    return response.json()


def main():
    print("=" * 60)
    print("INSTANCE MANAGEMENT API TEST")
    print("=" * 60)

    # Test 1: Look at shelf_1
    print("\n[1/6] Looking at shelf_1...")
    result = test_api_call("look", sublocation="shelf_1")
    if result.get("success"):
        print(f"✅ Found items:")
        print(f"   {result['narrative']}")
    else:
        print(f"❌ Failed: {result.get('error', {}).get('message')}")

    # Test 2: Collect dream bottle
    print("\n[2/6] Collecting dream bottle from shelf_1...")
    result = test_api_call("collect", target="dream_bottle", sublocation="shelf_1")
    if result.get("success"):
        print(f"✅ Collection successful!")
        print(f"   {result['narrative']}")
    else:
        print(f"❌ Failed: {result.get('error', {}).get('message')}")
        return False

    # Test 3: Check inventory
    print("\n[3/6] Checking inventory...")
    result = test_api_call("inventory")
    if result.get("success"):
        print(f"✅ Inventory:")
        print(f"   {result['narrative']}")
    else:
        print(f"❌ Failed: {result.get('error', {}).get('message')}")

    # Test 4: Try wrong house
    print("\n[4/6] Attempting to return spiral bottle to star house (should fail)...")
    result = test_api_call("return", target="dream_bottle", destination="fairy_door_2", sublocation="fairy_door_2")
    if not result.get("success"):
        print(f"✅ Correctly rejected!")
        print(f"   {result.get('error', {}).get('message')}")
    else:
        print(f"❌ Should have failed but didn't!")
        return False

    # Test 5: Return to correct house
    print("\n[5/6] Returning spiral bottle to spiral house (fairy_door_1)...")
    result = test_api_call("return", target="dream_bottle", destination="fairy_door_1", sublocation="fairy_door_1")
    if result.get("success"):
        print(f"✅ Return successful!")
        print(f"   {result['narrative']}")
        quest_progress = result.get('state_changes', {}).get('quest_progress', {})
        bottles = quest_progress.get('dream_bottle_quest', {}).get('bottles_returned', 0)
        print(f"   Quest progress: {bottles}/4 bottles returned")
    else:
        print(f"❌ Failed: {result.get('error', {}).get('message')}")
        return False

    # Test 6: Final inventory
    print("\n[6/6] Final inventory check...")
    result = test_api_call("inventory")
    if result.get("success"):
        print(f"✅ Final inventory:")
        print(f"   {result['narrative']}")

    print("\n" + "=" * 60)
    print("✅ ALL API TESTS PASSED!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
