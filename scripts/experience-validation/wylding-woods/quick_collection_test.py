#!/usr/bin/env python3
"""
Quick manual collection test - just the collection step
Assumes reset has already been done and player is at spawn_zone_3
"""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

TEST_USER = "collection-test@aeonia.ai"

def send_command(message):
    payload = {
        "experience": "wylding-woods",
        "message": message,
        "user_id": TEST_USER
    }

    print(f"\n{'='*70}")
    print(f"🎮 Command: \"{message}\"")
    print(f"{'='*70}")

    try:
        response = requests.post(
            f"{BASE_URL}/experience/interact",
            headers=HEADERS,
            json=payload,
            timeout=60  # Increased timeout
        )

        result = response.json()

        print(f"\n📖 Response:")
        print(result.get("narrative", "")[:400])

        # Check state_updates for correct path
        state_updates = result.get("state_updates", {})
        if state_updates:
            print(f"\n📝 State Updates:")
            world = state_updates.get("world", {})
            if world:
                path = world.get("path", "")
                operation = world.get("operation", "")
                item_id = world.get("item_id", "")

                print(f"   World: {operation} at {path}")
                print(f"   Item: {item_id}")

                # CRITICAL CHECK
                if "sublocations" in path:
                    print(f"\n✅ SUCCESS! Path includes 'sublocations'")
                    print(f"   Full path: {path}")
                    print(f"\n🎉 BUG IS FIXED!")
                else:
                    print(f"\n❌ FAILURE! Missing 'sublocations' in path")
                    print(f"   Path: {path}")
                    print(f"   This would cause duplication!")

        if result.get("success"):
            print(f"\n✅ Command succeeded")
        else:
            error = result.get("error", {})
            print(f"\n❌ Command failed: {error}")

        return result

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        return None

print("="*70)
print("QUICK COLLECTION TEST")
print("="*70)
print(f"User: {TEST_USER}")
print("Testing collection with sublocation path fix...")

# Step 1: Navigate
print("\n\nSTEP 1: Navigate to spawn_zone_3")
send_command("go to spawn_zone_3")

# Step 2: Look
print("\n\nSTEP 2: Look around")
send_command("look around")

# Step 3: Collect
print("\n\nSTEP 3: Collect the dream bottle")
result = send_command("take the dream bottle")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
