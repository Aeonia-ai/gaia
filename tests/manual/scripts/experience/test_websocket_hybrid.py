#!/usr/bin/env python3
"""
Hybrid Test: Use HTTP to trigger action, WebSocket to receive world_update event
This separates action execution from event listening
"""

import asyncio
import json
import sys
import requests
import websockets

async def test_hybrid(token: str):
    """Test using HTTP for action, WebSocket for events."""
    print("=" * 70)
    print("Hybrid Test: HTTP Action + WebSocket Events")
    print("=" * 70)
    print()

    # Start WebSocket listener first
    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience=wylding-woods"

    async with websockets.connect(ws_url) as websocket:
        # Welcome
        welcome = json.loads(await websocket.recv())
        user_id = welcome['user_id']
        print(f"✅ WebSocket connected: {user_id}")
        print()

        # Now trigger action via HTTP
        print("🍾 Triggering collection via HTTP endpoint...")
        http_url = "http://localhost:8001/experience/interact"
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "experience": "wylding-woods",
            "message": "collect dream bottle from spawn_zone_1"
        }

        response = requests.post(http_url, json=data, headers=headers, timeout=10)
        print(f"   HTTP Response: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(f"   Message: {result.get('narrative', '')[:80]}...")
        print()

        # Now listen on WebSocket for world_update event
        print("⏳ Listening on WebSocket for world_update event (10 seconds)...")

        events = []
        try:
            for i in range(20):  # Listen for up to 20 messages
                msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(msg)
                events.append(data)

                msg_type = data.get('type')
                print(f"   [{i+1}] {msg_type}")

                if msg_type == 'world_update':
                    print()
                    print("=" * 70)
                    print("🎉 WORLD UPDATE v0.4 RECEIVED VIA WEBSOCKET!")
                    print("=" * 70)
                    print(json.dumps(data, indent=2))
                    print("=" * 70)
                    print()

                    # Validate
                    assert data['version'] == '0.4'
                    assert 'base_version' in data
                    assert 'snapshot_version' in data
                    assert isinstance(data['changes'], list)

                    print("✅ v0.4 FORMAT VALIDATED!")
                    print(f"   version: {data['version']}")
                    print(f"   base_version: {data['base_version']}")
                    print(f"   snapshot_version: {data['snapshot_version']}")
                    print(f"   changes: {len(data['changes'])} items")

                    return True

        except asyncio.TimeoutError:
            print("   ⏱️  Timeout")

        print(f"\n📊 Total events received: {len(events)}")
        for event in events:
            print(f"   - {event.get('type')}")

        return False


async def main():
    with open("/tmp/jwt_token.txt", 'r') as f:
        token = f.read().strip()

    try:
        success = await test_hybrid(token)
        if success:
            print("\n✅ TEST PASSED!")
            sys.exit(0)
        else:
            print("\n⚠️  No world_update received")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
