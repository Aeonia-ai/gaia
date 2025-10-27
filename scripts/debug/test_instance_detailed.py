#!/usr/bin/env python3
"""
Detailed Instance Management API Test
Shows exact inputs and outputs for each API call.
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def show_request_response(test_name: str, payload: Dict[str, Any]):
    """Make API call and show full request/response."""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")

    print("\n📤 REQUEST:")
    print(f"POST {BASE_URL}/game/test/simple-command")
    print(f"Headers: {json.dumps({'Content-Type': 'application/json', 'X-API-Key': '[REDACTED]'}, indent=2)}")
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2))

    response = requests.post(
        f"{BASE_URL}/game/test/simple-command",
        headers=HEADERS,
        json=payload
    )

    print(f"\n📥 RESPONSE:")
    print(f"Status Code: {response.status_code}")
    print(f"\nBody:")
    print(json.dumps(response.json(), indent=2))

    return response.json()


def main():
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "INSTANCE MANAGEMENT API TEST" + " "*25 + "║")
    print("║" + " "*20 + "Inputs & Outputs" + " "*32 + "║")
    print("╚" + "="*68 + "╝")

    # Test 1: Look at shelf_1
    show_request_response(
        "Look at shelf_1",
        {
            "action": "look",
            "sublocation": "shelf_1",
            "experience": "wylding-woods",
            "waypoint": "waypoint_28a"
        }
    )

    input("\nPress Enter to continue to next test...")

    # Test 2: Collect dream bottle
    show_request_response(
        "Collect dream_bottle from shelf_1",
        {
            "action": "collect",
            "target": "dream_bottle",
            "sublocation": "shelf_1",
            "experience": "wylding-woods",
            "waypoint": "waypoint_28a"
        }
    )

    input("\nPress Enter to continue to next test...")

    # Test 3: Check inventory
    show_request_response(
        "Check inventory",
        {
            "action": "inventory",
            "experience": "wylding-woods",
            "waypoint": "waypoint_28a"
        }
    )

    input("\nPress Enter to continue to next test...")

    # Test 4: Try wrong house
    show_request_response(
        "Return to WRONG house (symbol mismatch)",
        {
            "action": "return",
            "target": "dream_bottle",
            "destination": "fairy_door_2",
            "sublocation": "fairy_door_2",
            "experience": "wylding-woods",
            "waypoint": "waypoint_28a"
        }
    )

    input("\nPress Enter to continue to next test...")

    # Test 5: Return to correct house
    show_request_response(
        "Return to CORRECT house (spiral → spiral)",
        {
            "action": "return",
            "target": "dream_bottle",
            "destination": "fairy_door_1",
            "sublocation": "fairy_door_1",
            "experience": "wylding-woods",
            "waypoint": "waypoint_28a"
        }
    )

    input("\nPress Enter to continue to next test...")

    # Test 6: Final inventory
    show_request_response(
        "Final inventory check",
        {
            "action": "inventory",
            "experience": "wylding-woods",
            "waypoint": "waypoint_28a"
        }
    )

    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
