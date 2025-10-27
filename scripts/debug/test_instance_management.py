#!/usr/bin/env python3
"""
Test Script for Instance Management System

Tests the complete Zork-like dream bottle collection flow.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.kb.kb_agent import kb_agent
from app.services.kb.kb_storage_manager import KBStorageManager


async def test_instance_management():
    """Test the complete instance management flow."""

    print("=" * 60)
    print("INSTANCE MANAGEMENT SYSTEM TEST")
    print("=" * 60)

    # Initialize KB agent
    print("\n[1/6] Initializing KB agent...")
    kb_storage = KBStorageManager()
    await kb_agent.initialize(kb_storage)
    print("✅ KB agent initialized")

    # Test parameters
    experience = "wylding-woods"
    user_id = "test_player_001"
    waypoint = "waypoint_28a"

    print(f"\n📍 Experience: {experience}")
    print(f"👤 User: {user_id}")
    print(f"🗺️  Waypoint: {waypoint}\n")

    # Test 1: Look at shelf_1
    print("\n[2/6] Looking at shelf_1...")
    instances = await kb_agent._find_instances_at_location(experience, waypoint, "shelf_1")
    print(f"Found {len(instances)} instance(s):")
    for inst in instances:
        print(f"  - {inst['semantic_name']}: {inst.get('description', 'No description')}")

    # Test 2: Collect spiral bottle from shelf_1
    print("\n[3/6] Collecting dream bottle from shelf_1...")
    result = await kb_agent._collect_item(
        experience=experience,
        item_semantic_name="dream_bottle",
        user_id=user_id,
        waypoint=waypoint,
        sublocation="shelf_1"
    )

    if result["success"]:
        print(f"✅ Collection successful!")
        print(f"   Narrative: {result['narrative']}")
        print(f"   Inventory: {len(result['state_changes']['inventory'])} item(s)")
    else:
        print(f"❌ Collection failed: {result.get('error', {}).get('message', 'Unknown error')}")
        return False

    # Test 3: Check inventory
    print("\n[4/6] Checking inventory...")
    player_state = await kb_agent._load_player_state(user_id, experience)
    inventory = player_state.get("inventory", [])
    print(f"Player inventory ({len(inventory)} item(s)):")
    for item in inventory:
        symbol = item.get('symbol', 'unknown')
        print(f"  - {item['semantic_name']} ({symbol} symbol)")

    # Test 4: Try to return bottle to wrong house (should fail)
    print("\n[5/6] Attempting to return spiral bottle to star house (should fail)...")
    result = await kb_agent._return_item(
        experience=experience,
        item_semantic_name="dream_bottle",
        destination_name="fairy_door_2",  # star house (wrong!)
        user_id=user_id,
        waypoint=waypoint,
        sublocation="fairy_door_2"
    )

    if not result["success"]:
        print(f"✅ Correctly rejected (symbol mismatch)")
        print(f"   Message: {result.get('error', {}).get('message', 'No message')}")
    else:
        print(f"❌ Should have failed but didn't!")
        return False

    # Test 5: Return bottle to correct house (should succeed)
    print("\n[6/6] Returning spiral bottle to spiral house (fairy_door_1)...")
    result = await kb_agent._return_item(
        experience=experience,
        item_semantic_name="dream_bottle",
        destination_name="fairy_door_1",  # spiral house (correct!)
        user_id=user_id,
        waypoint=waypoint,
        sublocation="fairy_door_1"
    )

    if result["success"]:
        print(f"✅ Return successful!")
        print(f"   Narrative: {result['narrative']}")
        quest_progress = result['state_changes'].get('quest_progress', {})
        bottles_returned = quest_progress.get('dream_bottle_quest', {}).get('bottles_returned', 0)
        print(f"   Quest progress: {bottles_returned}/4 bottles returned")
    else:
        print(f"❌ Return failed: {result.get('error', {}).get('message', 'Unknown error')}")
        return False

    # Final inventory check
    print("\n📦 Final inventory check...")
    player_state = await kb_agent._load_player_state(user_id, experience)
    inventory = player_state.get("inventory", [])
    print(f"Player inventory: {len(inventory)} item(s)")
    if len(inventory) == 0:
        print("  (empty - bottle was successfully returned)")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)

    return True


async def cleanup_test_data():
    """Clean up test player data."""
    import os
    import shutil

    test_player_path = "/Users/jasonasbahr/Development/Aeonia/Vaults/gaia-knowledge-base/players/test_player_001"

    if os.path.exists(test_player_path):
        print(f"\n🧹 Cleaning up test data at {test_player_path}...")
        shutil.rmtree(test_player_path)
        print("✅ Test data cleaned up")


if __name__ == "__main__":
    try:
        # Run cleanup first
        asyncio.run(cleanup_test_data())

        # Run tests
        success = asyncio.run(test_instance_management())

        if success:
            print("\n✨ Instance management system is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ Tests failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
