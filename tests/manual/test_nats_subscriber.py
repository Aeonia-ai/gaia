#!/usr/bin/env python3
"""
NATS Subscriber Test Script

Purpose: Validate that KB Service is publishing world_update events to NATS
after state changes (Phase 1 implementation).

Usage:
    # Terminal 1: Run this script
    python tests/manual/test_nats_subscriber.py

    # Terminal 2: Trigger state changes
    ./scripts/test.sh --local chat "take dream bottle"

Expected Output:
    ✅ Connected to NATS at nats://localhost:4222
    📡 Subscribed to: world.updates.user.*

    [2025-11-02 14:23:45] Received world_update
    Subject: world.updates.user.player@example.com
    Experience: wylding-woods
    Changes: {"world": {...}, "player": {...}}
    ---

Requirements:
    - Docker services running (docker compose up)
    - NATS container accessible at localhost:4222
    - KB Service publishing world_update events (Phase 1 complete)

Validation:
    ✅ Events arrive within sub-100ms of state change
    ✅ Event payload matches WorldUpdateEvent schema
    ✅ Subject includes correct user_id
    ✅ Changes delta contains expected state updates
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import nats
    from nats.aio.client import Client as NATSClient
except ImportError:
    print("❌ Error: nats-py package not installed")
    print("Install with: pip install nats-py")
    sys.exit(1)


class WorldUpdateSubscriber:
    """Subscribes to NATS world_update events and prints them in readable format."""

    def __init__(self, nats_url: str = "nats://localhost:4222"):
        self.nats_url = nats_url
        self.nc: NATSClient = None
        self.event_count = 0

    async def connect(self):
        """Connect to NATS server."""
        try:
            self.nc = await nats.connect(self.nats_url)
            print(f"✅ Connected to NATS at {self.nats_url}")
        except Exception as e:
            print(f"❌ Failed to connect to NATS at {self.nats_url}")
            print(f"   Error: {e}")
            print("\n📝 Troubleshooting:")
            print("   1. Ensure Docker services are running: docker compose up")
            print("   2. Check NATS container: docker compose ps nats")
            print("   3. Check NATS logs: docker compose logs nats")
            raise

    async def message_handler(self, msg):
        """Handle received NATS messages."""
        self.event_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Parse message data
        try:
            data = json.loads(msg.data.decode())
        except json.JSONDecodeError as e:
            print(f"❌ [{timestamp}] Invalid JSON in message: {e}")
            print(f"   Raw data: {msg.data.decode()}")
            return

        # Print formatted event
        print(f"\n[{timestamp}] Received world_update")
        print(f"Subject: {msg.subject}")
        print(f"Experience: {data.get('experience', 'N/A')}")
        print(f"User ID: {data.get('user_id', 'N/A')}")
        print(f"Timestamp: {data.get('timestamp', 'N/A')}")

        # Print changes (pretty format)
        changes = data.get('changes', {})
        if changes:
            print(f"Changes:")
            print(json.dumps(changes, indent=2))
        else:
            print(f"Changes: (empty)")

        # Print metadata if present
        metadata = data.get('metadata', {})
        if metadata:
            print(f"Metadata: {json.dumps(metadata)}")

        print("---")

    async def subscribe(self, subject: str = "world.updates.user.*"):
        """Subscribe to world update events."""
        if not self.nc:
            raise RuntimeError("Not connected to NATS. Call connect() first.")

        try:
            await self.nc.subscribe(subject, cb=self.message_handler)
            print(f"📡 Subscribed to: {subject}")
            print(f"\n🎧 Listening for world_update events...")
            print(f"   Press Ctrl+C to stop\n")
        except Exception as e:
            print(f"❌ Failed to subscribe to {subject}")
            print(f"   Error: {e}")
            raise

    async def run(self):
        """Main run loop - keeps subscriber alive until interrupted."""
        try:
            await self.connect()
            await self.subscribe()

            # Keep subscriber alive
            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print(f"\n\n✋ Received interrupt signal")
            print(f"📊 Total events received: {self.event_count}")
        finally:
            if self.nc:
                await self.nc.drain()
                print("✅ Disconnected from NATS")


async def main():
    """Entry point for the subscriber script."""
    print("=" * 60)
    print("NATS World Update Subscriber")
    print("=" * 60)
    print()

    # Get NATS URL from environment or use default
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")

    subscriber = WorldUpdateSubscriber(nats_url)
    await subscriber.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
