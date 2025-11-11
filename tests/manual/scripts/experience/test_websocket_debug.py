#!/usr/bin/env python3
"""Debug WebSocket - Find the real issue"""

import asyncio
import json
import websockets

async def test_debug(token: str):
    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience=wylding-woods"

    print("Connecting...")
    async with websockets.connect(ws_url) as ws:
        print("✅ Connected\n")

        # Welcome
        msg1 = await ws.recv()
        print(f"1. Welcome: {json.loads(msg1)['type']}\n")

        # Ping
        print("Sending ping...")
        await ws.send(json.dumps({"type": "ping"}))
        msg2 = await ws.recv()
        print(f"2. Pong: {json.loads(msg2)['type']}\n")

        # Action with LONG timeout (60 seconds)
        print("Sending collect action...")
        print("(Waiting up to 60 seconds for response...)\n")

        await ws.send(json.dumps({
            "type": "action",
            "action": "collect",
            "target": "bottle"
        }))

        try:
            msg3 = await asyncio.wait_for(ws.recv(), timeout=60.0)
            data = json.loads(msg3)
            print(f"✅ RESPONSE RECEIVED!")
            print(f"   Type: {data.get('type')}")
            print(f"   Success: {data.get('success')}")
            print(f"   Message: {data.get('message', '')[:100]}")
            print(f"\n   Full response:")
            print(json.dumps(data, indent=2))

        except asyncio.TimeoutError:
            print("❌ TIMEOUT after 60 seconds")
            print("   This indicates a real problem - responses should come faster")


asyncio.run(test_debug(open("/tmp/jwt_token.txt").read().strip()))
