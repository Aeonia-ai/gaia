#!/usr/bin/env python3
"""
Test script to verify world_update events during quest flow.

Captures and logs all WebSocket events to verify:
- Items added to inventory (collect)
- Items removed from inventory (give)
- Quest progression tracking
- Event payload structure
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import websockets

async def get_jwt_token() -> str:
    """Get JWT token from test script."""
    import subprocess
    result = subprocess.run(
        ["python3", str(Path(__file__).parent.parent.parent / "tests/manual/get_test_jwt.py")],
        capture_output=True,
        text=True
    )
    return result.stdout.strip().split('\n')[-1]


async def test_quest_with_events():
    """Run quest test and capture all event messages."""

    print("=" * 80)
    print("Quest Event Message Test")
    print("=" * 80)
    print()

    # Get JWT
    print("🔐 Getting JWT token...")
    token = await get_jwt_token()
    print("   ✅ Token obtained")
    print()

    # Connect to WebSocket
    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience=wylding-woods"
    print(f"🔌 Connecting to WebSocket...")

    async with websockets.connect(ws_url) as ws:
        print("   ✅ Connected")
        print()

        # Receive initial state
        initial = await ws.recv()
        initial_data = json.loads(initial)
        print(f"📥 Received: {initial_data.get('type')}")
        print()

        # Navigate to main_room
        print("📍 Navigating to main_room...")
        await ws.send(json.dumps({"type": "action", "action": "go to main room"}))
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get("type") == "action_response":
                print(f"   ✅ {data.get('message', 'Arrived')}")
                break
        print()

        # Collect first bottle and examine events
        print("=" * 80)
        print("TEST 1: Collecting bottle_mystery")
        print("=" * 80)
        print()

        await ws.send(json.dumps({"type": "action", "action": "collect bottle_mystery"}))

        collect_events = []
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            msg_type = data.get("type")

            if msg_type == "world_update":
                collect_events.append(data)
                print(f"📥 world_update event:")
                print(f"   Updates: {json.dumps(data.get('updates', {}), indent=2)}")
                print()
            elif msg_type == "action_response":
                print(f"✅ Action response: {data.get('message')}")
                print()
                break

        print(f"Total world_update events during collection: {len(collect_events)}")
        print()

        # Give first bottle and examine events
        print("=" * 80)
        print("TEST 2: Giving bottle_mystery to Louisa")
        print("=" * 80)
        print()

        await ws.send(json.dumps({"type": "action", "action": "give bottle_mystery to louisa"}))

        give_events = []
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            msg_type = data.get("type")

            if msg_type == "world_update":
                give_events.append(data)
                print(f"📥 world_update event #{len(give_events)}:")
                updates = data.get('updates', {})

                # Check for inventory changes
                if 'inventory' in updates:
                    print(f"   📦 Inventory update: {updates['inventory']}")

                # Check for quest updates
                if 'npcs' in updates and 'louisa' in updates.get('npcs', {}):
                    louisa = updates['npcs']['louisa']
                    if 'state' in louisa:
                        print(f"   🎯 Louisa state: {louisa['state']}")

                # Check for global state
                if 'global_state' in updates:
                    print(f"   🌍 Global state: {updates['global_state']}")

                print(f"   Full updates: {json.dumps(updates, indent=2)}")
                print()
            elif msg_type == "action_response":
                response_data = data.get('data', {})
                print(f"✅ Action response:")
                print(f"   Dialogue: {response_data.get('dialogue')}")
                if 'quest_updates' in response_data:
                    print(f"   Quest updates: {response_data['quest_updates']}")
                print()
                break

        print(f"Total world_update events during give: {len(give_events)}")
        print()

        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ Collection events: {len(collect_events)}")
        print(f"✅ Give events: {len(give_events)}")
        print()
        print("Event verification:")
        print(f"  - Inventory updates during collection: {'✅' if any('inventory' in e.get('updates', {}) for e in collect_events) else '❌'}")
        print(f"  - Inventory updates during give: {'✅' if any('inventory' in e.get('updates', {}) for e in give_events) else '❌'}")
        print(f"  - Quest state updates: {'✅' if any('npcs' in e.get('updates', {}) for e in give_events) else '❌'}")


if __name__ == "__main__":
    asyncio.run(test_quest_with_events())
