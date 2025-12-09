#!/usr/bin/env python3
"""
Test the get_commands WebSocket introspection endpoint.

Usage:
    # Set JWT token and run test
    export TEST_JWT_TOKEN=$(python3 tests/manual/get_test_jwt.py admin@aeonia.ai <password> 2>/dev/null | head -1)
    python3 tests/manual/test_get_commands.py

    # Or in one command
    TEST_JWT_TOKEN=$(python3 tests/manual/get_test_jwt.py admin@aeonia.ai <password> 2>/dev/null | head -1) python3 tests/manual/test_get_commands.py
"""
import asyncio
import json
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    import websockets
except ImportError:
    print("❌ websockets package not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


async def test_get_commands():
    """Test the get_commands endpoint."""

    # Get JWT token
    print("=" * 70)
    print("Testing Command Discovery (get_commands)")
    print("=" * 70)
    print()

    # Get JWT token from environment variable
    token = os.getenv("TEST_JWT_TOKEN")
    if not token:
        print("❌ TEST_JWT_TOKEN environment variable not set")
        print("Get token with: export TEST_JWT_TOKEN=$(python3 tests/manual/get_test_jwt.py admin@aeonia.ai <password>)")
        sys.exit(1)

    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience=wylding-woods"

    print(f"Connecting to WebSocket...")

    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected!")
            print()

            # Wait for connected message
            connected_msg = await websocket.recv()
            connected_data = json.loads(connected_msg)
            print(f"📨 Received: {connected_data.get('type')}")
            print()

            # Send get_commands request
            print("📤 Sending get_commands request...")
            request = {
                "type": "get_commands"
            }
            await websocket.send(json.dumps(request))

            # Receive response
            response_msg = await websocket.recv()
            response_data = json.loads(response_msg)

            print(f"📨 Received: {response_data.get('type')}")
            print()

            if response_data.get('type') == 'commands_schema':
                print("✅ Command discovery successful!")
                print()
                print(f"Schema Version: {response_data.get('schema_version')}")
                print(f"Number of commands: {len(response_data.get('commands', {}))}")
                print()

                print("Available Commands:")
                print("-" * 70)
                for cmd_name, cmd_schema in response_data.get('commands', {}).items():
                    title = cmd_schema.get('title', cmd_name)
                    desc = cmd_schema.get('description', 'No description')
                    metadata = cmd_schema.get('metadata', {})
                    avg_time = metadata.get('avg_response_time_ms', 'N/A')

                    print(f"  {cmd_name}")
                    print(f"    Title: {title}")
                    print(f"    Description: {desc}")
                    print(f"    Avg Response Time: {avg_time}ms")

                    # Show required fields
                    required = cmd_schema.get('required', [])
                    print(f"    Required Fields: {', '.join(required)}")
                    print()

                # Show full schema for one command as example
                print()
                print("Example: Full schema for 'collect_item' command:")
                print("-" * 70)
                collect_schema = response_data['commands'].get('collect_item', {})
                print(json.dumps(collect_schema, indent=2))

            else:
                print(f"❌ Unexpected response type: {response_data.get('type')}")
                print(json.dumps(response_data, indent=2))

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed: {e}")
        print("Make sure KB service is running: docker compose up kb-service")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_get_commands())
