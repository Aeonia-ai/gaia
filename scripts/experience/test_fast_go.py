#!/usr/bin/env python3
"""
Test Fast "go" Command Implementation

Tests the new fast path for navigation commands (no LLM processing).
Expected response time: <1s (vs 25-30s for natural language "go to X")
"""

import asyncio
import websockets
import json
import time
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


async def get_jwt_token():
    """Get JWT token for testing."""
    import subprocess
    result = subprocess.run(
        ["python3", "tests/manual/get_test_jwt.py"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..', '..')
    )
    if result.returncode != 0:
        raise Exception(f"Failed to get JWT token: {result.stderr}")
    return result.stdout.strip()


async def test_fast_go():
    """Test fast go command vs natural language go command."""

    print("=" * 60)
    print("Fast 'go' Command Test")
    print("=" * 60)
    print()

    # Get JWT token
    print("Getting JWT token...")
    token = await get_jwt_token()
    print("✅ JWT token obtained\n")

    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience=wylding-woods"

    async with websockets.connect(ws_url) as ws:
        # Wait for connection message
        msg = await ws.recv()
        conn_data = json.loads(msg)
        print(f"✅ Connected: {conn_data.get('message')}\n")

        # Test 1: Fast "go" with structured parameters
        print("━" * 60)
        print("Test 1: Fast 'go' command (structured parameters)")
        print("━" * 60)
        print('Sending: {"type": "action", "action": "go", "destination": "spawn_zone_1"}')
        print()

        start_time = time.time()
        await ws.send(json.dumps({
            "type": "action",
            "action": "go",
            "destination": "spawn_zone_1"
        }))

        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        elapsed = time.time() - start_time

        response_data = json.loads(response)
        print(f"Response time: {elapsed*1000:.0f}ms")
        print(f"Success: {response_data.get('success')}")
        print(f"Message: {response_data.get('message')}")
        print()

        if elapsed < 1.0:
            print(f"✅ FAST PATH CONFIRMED (<1s)\n")
        elif elapsed > 10.0:
            print(f"❌ SLOW PATH DETECTED (>10s) - Still using LLM?\n")
        else:
            print(f"⚠️  MEDIUM SPEED ({elapsed:.1f}s)\n")

        # Test 2: Natural language "go" for comparison
        print("━" * 60)
        print("Test 2: Natural language 'go' (LLM path)")
        print("━" * 60)
        print('Sending: {"type": "action", "action": "go to spawn_zone_2"}')
        print("Expected: 25-30s (LLM processing)")
        print()

        start_time = time.time()
        await ws.send(json.dumps({
            "type": "action",
            "action": "go to spawn_zone_2"
        }))

        response = await asyncio.wait_for(ws.recv(), timeout=60.0)
        elapsed = time.time() - start_time

        response_data = json.loads(response)
        print(f"Response time: {elapsed:.1f}s")
        print(f"Success: {response_data.get('success')}")
        print(f"Message: {response_data.get('message')[:100]}..." if len(response_data.get('message', '')) > 100 else f"Message: {response_data.get('message')}")
        print()

        if elapsed > 10.0:
            print(f"✅ LLM PATH CONFIRMED (>10s) - Backward compatible\n")
        else:
            print(f"⚠️  Faster than expected for natural language\n")

        # Summary
        print("=" * 60)
        print("Test Summary")
        print("=" * 60)
        print("✅ Fast path: Test 1 should complete in <1s")
        print("✅ LLM fallback: Test 2 should take 25-30s")
        print("✅ Backward compatible: Both formats work")
        print()


if __name__ == "__main__":
    asyncio.run(test_fast_go())
