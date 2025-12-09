#!/usr/bin/env python3
"""
Test WebSocket messages to see EXACTLY what Unity receives.
Captures both action_response and world_update events.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

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


async def test_ws_messages():
    """Capture exact WebSocket messages."""

    print("=" * 80)
    print("WebSocket Message Capture Test")
    print("=" * 80)
    print()

    # Get JWT
    token = await get_jwt_token()

    # Connect
    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience=wylding-woods"

    async with websockets.connect(ws_url) as ws:
        # Receive initial messages
        msg = await ws.recv()
        print(f"1. {json.loads(msg).get('type')}: {msg[:100]}...")
        print()

        # Navigate
        await ws.send(json.dumps({"type": "action", "action": "go to main room"}))
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get("type") == "action_response":
                break

        print("=" * 80)
        print("TEST: collect bottle_mystery")
        print("=" * 80)
        print()

        # Send collect action
        await ws.send(json.dumps({
            "type": "action",
            "action": "collect bottle_mystery"
        }))

        # Capture ALL messages received
        messages = []
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(msg)
                messages.append(data)

                if data.get("type") == "action_response":
                    break  # Stop after action_response
            except asyncio.TimeoutError:
                break

        # Display all messages
        print(f"📥 Received {len(messages)} message(s):")
        print()

        for i, msg in enumerate(messages, 1):
            print(f"Message {i}: {msg.get('type')}")
            print(json.dumps(msg, indent=2))
            print()

        # Check what Unity needs
        print("=" * 80)
        print("UNITY EXPECTATIONS vs REALITY")
        print("=" * 80)
        print()

        action_response = next((m for m in messages if m.get("type") == "action_response"), None)
        world_updates = [m for m in messages if m.get("type") == "world_update"]

        if action_response:
            print("action_response:")
            print(f"  ✅ type: {action_response.get('type')}")
            print(f"  ✅ success: {action_response.get('success')}")
            print(f"  ✅ message: {action_response.get('message')[:50]}...")
            print(f"  metadata: {action_response.get('metadata', {})}")

            # Unity expects item_id field
            item_id = action_response.get("item_id")
            meta_instance_id = action_response.get("metadata", {}).get("instance_id")

            if item_id:
                print(f"  ✅ item_id: {item_id} (Unity needs this!)")
            else:
                print(f"  ❌ item_id: MISSING (Unity expects this)")
                if meta_instance_id:
                    print(f"  ⚠️  Found in metadata.instance_id: {meta_instance_id}")
        print()

        if world_updates:
            for i, wu in enumerate(world_updates, 1):
                print(f"world_update #{i}:")
                updates = wu.get("updates", {})
                if updates:
                    print(f"  ✅ updates: {json.dumps(updates, indent=4)}")
                else:
                    print(f"  ❌ updates: EMPTY (Unity can't see state changes)")
        else:
            print("world_update:")
            print("  ❌ NO world_update events received")

        print()


if __name__ == "__main__":
    asyncio.run(test_ws_messages())
