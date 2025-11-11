#!/usr/bin/env python3
"""v0.4 Test - Using Exact Command Format"""

import asyncio
import json
import websockets

async def test():
    token = open("/tmp/jwt_token.txt").read().strip()
    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience=wylding-woods"

    print("v0.4 WorldUpdate Test")
    print("=" * 70)

    async with websockets.connect(ws_url) as ws:
        # Welcome
        welcome = json.loads(await ws.recv())
        print(f"✅ Connected\n")

        # Look to see where we are
        print("1. Looking around...")
        await ws.send(json.dumps({"type": "action", "action": "look"}))
        r1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
        print(f"   {r1.get('message', '')[:100]}...\n")

        # Go to spawn_zone_1
        print("2. Going to spawn_zone_1...")
        await ws.send(json.dumps({"type": "action", "action": "go to spawn_zone_1"}))
        r2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
        print(f"   Success: {r2.get('success')}")
        print(f"   {r2.get('message', '')[:100]}...\n")

        if not r2.get('success'):
            print("❌ Couldn't move to spawn_zone_1")
            print("   Available actions:", r2.get('metadata', {}).get('available_actions'))
            return False

        # Collect dream bottle
        print("3. Collecting dream bottle...")
        await ws.send(json.dumps({"type": "action", "action": "collect dream bottle"}))

        # Listen for responses
        print("   Waiting for responses...\n")
        events = []

        for i in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=60)
                data = json.loads(msg)
                events.append(data)

                print(f"   [{len(events)}] {data.get('type')}")

                if data.get('type') == 'world_update':
                    print("\n" + "=" * 70)
                    print("🎉 WORLD UPDATE v0.4!")
                    print("=" * 70)
                    print(json.dumps(data, indent=2))
                    print("=" * 70)

                    assert data['version'] == '0.4'
                    assert 'base_version' in data
                    assert 'snapshot_version' in data
                    assert isinstance(data['changes'], list)

                    print("\n✅ v0.4 VALIDATED!")
                    return True

            except asyncio.TimeoutError:
                break

        print(f"\n⚠️  No world_update ({len(events)} events received)")
        return False


if asyncio.run(test()):
    print("\n✅ SUCCESS")
else:
    print("\n⚠️  INCOMPLETE")
