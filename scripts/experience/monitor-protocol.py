#!/usr/bin/env python3
"""
WebSocket Protocol Monitor - Real-time visibility into client-server exchanges

Connects to WebSocket, sends commands, captures all events, displays in readable format.
Useful for debugging Unity integration and protocol issues.

Usage:
    ./monitor-protocol.py                    # Interactive mode
    ./monitor-protocol.py --auto             # Auto-run test sequence
    ./monitor-protocol.py --command "collect bottle_mystery"  # Single command
"""

import asyncio
import websockets
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import argparse
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def get_jwt_token() -> str:
    """Get JWT token from test script."""
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent.parent / "tests/manual/get_test_jwt.py")],
        capture_output=True,
        text=True
    )
    return result.stdout.strip().split('\n')[-1]


def print_header(text: str, color=Fore.CYAN):
    """Print formatted header."""
    print()
    print(color + "=" * 80)
    print(color + text)
    print(color + "=" * 80)
    print()


def print_message(msg_type: str, data: Dict[str, Any], msg_num: int):
    """Pretty-print a WebSocket message."""

    # Color by message type
    colors = {
        "world_update": Fore.GREEN,
        "action_response": Fore.YELLOW,
        "quest_update": Fore.MAGENTA,
        "connected": Fore.CYAN,
        "error": Fore.RED,
    }
    color = colors.get(msg_type, Fore.WHITE)

    print(f"\n{color}{'─' * 80}")
    print(f"{color}Message #{msg_num}: {msg_type.upper()}")
    print(f"{color}{'─' * 80}{Style.RESET_ALL}")

    # Special formatting for different message types
    if msg_type == "world_update":
        print(f"  Version: {data.get('version')}")
        print(f"  Base Version: {data.get('base_version')}")
        print(f"  Snapshot Version: {data.get('snapshot_version')}")

        changes = data.get('changes', [])
        print(f"  Changes: {len(changes)} item(s)")

        for i, change in enumerate(changes, 1):
            print(f"\n  Change {i}:")
            print(f"    Operation: {change.get('operation')}")
            print(f"    Area ID: {change.get('area_id')}")
            print(f"    Instance ID: {change.get('instance_id')}")
            print(f"    Path: {change.get('path')}")

            if change.get('item'):
                item = change['item']
                print(f"    Item:")
                print(f"      instance_id: {item.get('instance_id')}")
                print(f"      template_id: {item.get('template_id')}")
                print(f"      semantic_name: {item.get('semantic_name')}")

    elif msg_type == "action_response":
        print(f"  Action: {data.get('action')}")
        print(f"  Success: {data.get('success')}")
        print(f"  Message: {data.get('message')}")
        print(f"  Item ID: {data.get('item_id', '(none)')}")

        if data.get('metadata'):
            print(f"  Metadata:")
            for key, value in data['metadata'].items():
                print(f"    {key}: {value}")

    elif msg_type == "quest_update":
        print(f"  Quest ID: {data.get('quest_id')}")
        print(f"  Status: {data.get('status')}")
        print(f"  Progress: {data.get('bottles_collected', 0)}/{data.get('bottles_total', 0)}")

    else:
        # Generic formatting
        for key, value in data.items():
            if key != 'type':
                print(f"  {key}: {value}")

    print()


async def monitor_session(
    experience: str = "wylding-woods",
    commands: List[str] = None,
    auto: bool = False
):
    """Monitor WebSocket session with interactive or automated commands."""

    print_header("WebSocket Protocol Monitor", Fore.CYAN)
    print(f"Experience: {experience}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Mode: {'Auto' if auto else 'Interactive'}")

    # Get JWT
    print("\n🔐 Authenticating...")
    token = await get_jwt_token()
    print("   ✅ Token obtained")

    # Connect
    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience={experience}"
    print(f"\n🔌 Connecting to WebSocket...")

    async with websockets.connect(ws_url) as ws:
        # Receive connected message
        connected_msg = await ws.recv()
        connected_data = json.loads(connected_msg)
        print(f"   ✅ Connected: {connected_data.get('message')}")

        message_count = 0

        # Auto-run test sequence if requested
        if auto:
            print_header("Auto-Running Test Sequence", Fore.YELLOW)
            commands = [
                "@reset experience CONFIRM",
                "go to main room",
                '{"type": "action", "action": "collect_item", "instance_id": "bottle_mystery"}',
                '{"type": "action", "action": "give_item", "instance_id": "bottle_mystery", "target_npc_id": "louisa"}',
            ]

        # Process commands
        if commands:
            for cmd in commands:
                print_header(f"Command: {cmd}", Fore.BLUE)

                # Parse command format
                if cmd.startswith('{'):
                    # JSON command
                    await ws.send(cmd)
                else:
                    # Text command
                    await ws.send(json.dumps({"type": "action", "action": cmd}))

                # Collect responses (wait up to 2 seconds)
                print("\n📥 Receiving responses...\n")

                for _ in range(10):
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        data = json.loads(msg)
                        message_count += 1

                        print_message(data.get('type'), data, message_count)

                    except asyncio.TimeoutError:
                        break

                # Pause between commands
                if len(commands) > 1:
                    await asyncio.sleep(1)

        else:
            # Interactive mode
            print_header("Interactive Mode - Enter Commands", Fore.YELLOW)
            print("Examples:")
            print("  collect_item bottle_mystery")
            print("  {\"type\": \"action\", \"action\": \"collect_item\", \"instance_id\": \"bottle_mystery\"}")
            print("  go to main room")
            print("  quit")
            print()

            # Start background task to receive messages
            async def receive_messages():
                nonlocal message_count
                while True:
                    try:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        message_count += 1
                        print_message(data.get('type'), data, message_count)
                    except Exception as e:
                        print(f"Error receiving: {e}")
                        break

            receive_task = asyncio.create_task(receive_messages())

            # Interactive command loop
            try:
                while True:
                    cmd = input(f"{Fore.GREEN}> {Style.RESET_ALL}")

                    if cmd.lower() in ['quit', 'exit', 'q']:
                        break

                    if not cmd.strip():
                        continue

                    # Send command
                    if cmd.startswith('{'):
                        await ws.send(cmd)
                    else:
                        await ws.send(json.dumps({"type": "action", "action": cmd}))

            except KeyboardInterrupt:
                print("\n\nExiting...")
            finally:
                receive_task.cancel()

        print_header("Session Complete", Fore.CYAN)
        print(f"Total messages: {message_count}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Monitor WebSocket protocol exchanges")
    parser.add_argument("experience", nargs="?", default="wylding-woods",
                       help="Experience ID (default: wylding-woods)")
    parser.add_argument("--auto", action="store_true",
                       help="Auto-run test sequence")
    parser.add_argument("--command", "-c",
                       help="Single command to run")

    args = parser.parse_args()

    commands = [args.command] if args.command else None

    asyncio.run(monitor_session(
        experience=args.experience,
        commands=commands,
        auto=args.auto
    ))


if __name__ == "__main__":
    main()
