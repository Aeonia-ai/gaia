#!/usr/bin/env python3
"""
Manual WebSocket Test Client for Experience Endpoint

Tests the /ws/experience WebSocket endpoint with:
- JWT authentication
- Bottle collection actions
- NATS world update events
- Quest progress tracking

Usage:
    # Local testing (requires running Docker services)
    python tests/manual/test_websocket_experience.py

    # With custom JWT token
    python tests/manual/test_websocket_experience.py --token <jwt_token>

Author: GAIA Platform Team
Created: 2025-11-05 (AEO-65 Demo Testing)
"""

import asyncio
import json
import sys
import os
import argparse
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    import websockets
except ImportError:
    print("❌ websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


async def test_websocket_connection(
    url: str,
    token: str,
    experience: str = "wylding-woods"
):
    """
    Test WebSocket connection and bottle collection flow.

    Args:
        url: WebSocket URL (e.g., ws://localhost:8000/ws/experience)
        token: JWT authentication token
        experience: Experience ID (default: wylding-woods)
    """
    print(f"🔗 Connecting to WebSocket: {url}")
    print(f"🎮 Experience: {experience}")
    print(f"🔑 Token: {token[:20]}..." if len(token) > 20 else f"🔑 Token: {token}")
    print()

    # Add token and experience to URL as query params
    ws_url = f"{url}?token={token}&experience={experience}"

    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully!")
            print()

            # Wait for welcome message
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 Welcome message received:")
            print(f"   Type: {welcome_data.get('type')}")
            print(f"   Connection ID: {welcome_data.get('connection_id')}")
            print(f"   User ID: {welcome_data.get('user_id')}")
            print()

            # Test 1: Send ping
            print("🏓 Sending ping...")
            ping_msg = {
                "type": "ping",
                "timestamp": int(datetime.utcnow().timestamp() * 1000)
            }
            await websocket.send(json.dumps(ping_msg))

            pong_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            pong_data = json.loads(pong_response)
            print(f"✅ Pong received: {pong_data.get('type')}")
            print()

            # Test 2: Collect first bottle
            print("🍾 Collecting first bottle (bottle_of_joy_1)...")
            collect_msg = {
                "type": "action",
                "action": "collect_bottle",
                "item_id": "bottle_of_joy_1",
                "spot_id": "woander_store.shelf_a.slot_1"
            }
            await websocket.send(json.dumps(collect_msg))

            # Wait for responses (action_response, world_update, quest_update)
            print("⏳ Waiting for responses...")
            for i in range(3):  # Expect 3 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    msg_type = response_data.get('type')

                    if msg_type == "action_response":
                        print(f"   ✅ Action response: success={response_data.get('success')}")
                    elif msg_type == "world_update":
                        print(f"   🌍 World update received (version {response_data.get('version')})")
                    elif msg_type == "quest_update":
                        print(f"   🎯 Quest update: {response_data.get('bottles_collected')}/{response_data.get('bottles_total')} bottles")
                    elif msg_type == "error":
                        print(f"   ❌ Error: {response_data.get('message')}")
                    else:
                        print(f"   📨 {msg_type}: {response_data}")

                except asyncio.TimeoutError:
                    print(f"   ⚠️ Timeout waiting for response {i+1}")
                    break

            print()

            # Test 3: Collect more bottles (simulate progress)
            for bottle_num in range(2, 8):  # Collect bottles 2-7
                print(f"🍾 Collecting bottle {bottle_num}...")
                collect_msg = {
                    "type": "action",
                    "action": "collect_bottle",
                    "item_id": f"bottle_of_joy_{bottle_num}",
                    "spot_id": f"woander_store.shelf_b.slot_{bottle_num}"
                }
                await websocket.send(json.dumps(collect_msg))

                # Wait for quest update
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)

                    # Skip action_response, wait for quest_update
                    if response_data.get('type') != 'quest_update':
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)

                    if response_data.get('type') == 'quest_update':
                        bottles_collected = response_data.get('bottles_collected')
                        bottles_total = response_data.get('bottles_total')
                        status = response_data.get('status')
                        print(f"   🎯 Progress: {bottles_collected}/{bottles_total} (status: {status})")

                        # Check for win condition
                        if bottles_collected >= bottles_total:
                            # Wait for quest_complete message
                            complete_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            complete_data = json.loads(complete_msg)
                            if complete_data.get('type') == 'quest_complete':
                                print(f"   🎉 {complete_data.get('message')}")
                                break

                except asyncio.TimeoutError:
                    print(f"   ⚠️ Timeout waiting for quest update")

                await asyncio.sleep(0.5)  # Small delay between collections

            print()
            print("✅ All tests completed successfully!")
            print()

            # Keep connection open briefly to see any NATS events
            print("⏳ Listening for NATS events (5 seconds)...")
            try:
                for _ in range(5):
                    event = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    event_data = json.loads(event)
                    print(f"   📨 NATS event: {event_data.get('type')}")
            except asyncio.TimeoutError:
                print("   ℹ️  No additional events received")

            print()
            print("👋 Closing WebSocket connection...")

    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def main():
    """Main entry point for WebSocket testing."""
    parser = argparse.ArgumentParser(description="Test WebSocket Experience Endpoint")
    parser.add_argument(
        "--url",
        default="ws://localhost:8000/ws/experience",
        help="WebSocket URL (default: ws://localhost:8000/ws/experience)"
    )
    parser.add_argument(
        "--token",
        default=os.getenv("TEST_JWT_TOKEN", ""),
        help="JWT token for authentication (or set TEST_JWT_TOKEN env var)"
    )
    parser.add_argument(
        "--experience",
        default="wylding-woods",
        help="Experience ID (default: wylding-woods)"
    )

    args = parser.parse_args()

    if not args.token:
        print("❌ No JWT token provided!")
        print()
        print("Options:")
        print("  1. Set TEST_JWT_TOKEN environment variable")
        print("  2. Pass --token <jwt_token> argument")
        print()
        print("To get a test token:")
        print("  ./scripts/manage-users.sh list")
        print("  # Use JWT from user record")
        sys.exit(1)

    print("=" * 60)
    print("WebSocket Experience Endpoint Test")
    print("=" * 60)
    print()

    # Run async test
    success = asyncio.run(test_websocket_connection(
        url=args.url,
        token=args.token,
        experience=args.experience
    ))

    if success:
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ TESTS FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
