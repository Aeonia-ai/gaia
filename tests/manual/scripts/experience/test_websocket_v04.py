#!/usr/bin/env python3
"""Final v0.4 Test - With Proper Timeouts"""

import asyncio
import json
import websockets

async def test_v04_collection(token: str):
    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience=wylding-woods"

    print("=" * 70)
    print("v0.4 WorldUpdate Test - With Proper LLM Timeouts")
    print("=" * 70)
    print()

    async with websockets.connect(ws_url) as ws:
        # Welcome
        welcome = json.loads(await ws.recv())
        print(f"✅ Connected: {welcome['user_id']}\n")

        # Step 1: Go to spawn_zone_1 where bottles are
        print("Step 1: Moving to spawn_zone_1 (where items are)...")
        await ws.send(json.dumps({
            "type": "action",
            "action": "go to spawn_zone_1"
        }))

        response1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=60.0))
        print(f"   Response: {response1.get('type')}")
        print(f"   Success: {response1.get('success')}")
        print(f"   Message: {response1.get('message', '')[:80]}...\n")

        # Step 2: Collect dream bottle
        print("Step 2: Collecting dream bottle...")
        await ws.send(json.dumps({
            "type": "action",
            "action": "collect dream bottle"
        }))

        # Collect all responses for next 60 seconds
        print("   Listening for responses (action_response + world_update)...\n")

        events = []
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < 60:
            try:
                remaining = 60 - (asyncio.get_event_loop().time() - start_time)
                if remaining <= 0:
                    break

                msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
                data = json.loads(msg)
                events.append(data)

                msg_type = data.get('type')
                print(f"   📨 [{len(events)}] {msg_type}")

                if msg_type == 'action_response':
                    print(f"      success: {data.get('success')}")

                elif msg_type == 'world_update':
                    print()
                    print("=" * 70)
                    print("🎉 WORLD UPDATE v0.4 RECEIVED!")
                    print("=" * 70)
                    print(json.dumps(data, indent=2))
                    print("=" * 70)
                    print()

                    # Validate
                    assert data['version'] == '0.4'
                    print(f"✅ version: {data['version']}")

                    assert 'base_version' in data
                    print(f"✅ base_version: {data['base_version']}")

                    assert 'snapshot_version' in data
                    print(f"✅ snapshot_version: {data['snapshot_version']}")

                    assert isinstance(data['changes'], list)
                    print(f"✅ changes: array with {len(data['changes'])} items")

                    print("\n🎉 v0.4 FORMAT VALIDATED!")
                    return True

            except asyncio.TimeoutError:
                break

        print(f"\n📊 Total events received: {len(events)}")
        if not any(e.get('type') == 'world_update' for e in events):
            print("⚠️  No world_update received (collection may have failed due to game logic)")

        return False


async def main():
    token = open("/tmp/jwt_token.txt").read().strip()
    success = await test_v04_collection(token)
    print()
    print("=" * 70)
    if success:
        print("✅ TEST PASSED - v0.4 WorldUpdate validated!")
    else:
        print("⚠️  No world_update - check game state requirements")
    print("=" * 70)


asyncio.run(main())
