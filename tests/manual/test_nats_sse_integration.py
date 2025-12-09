#!/usr/bin/env python3
"""
NATS + SSE Integration Test

Tests Phase 1B implementation:
1. Opens SSE stream to Chat Service
2. Monitors NATS for subscription creation
3. Optionally injects test events
4. Verifies event delivery through stream

Usage:
    python tests/manual/test_nats_sse_integration.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path
import httpx

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test configuration
CHAT_SERVICE_URL = "http://localhost:8002"
NATS_MONITOR_URL = "http://localhost:8222"
# This API key resolves to user_id: a7f4370e-0af5-40eb-bb18-fcc10538b041
TEST_USER_ID = "a7f4370e-0af5-40eb-bb18-fcc10538b041"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"


async def check_nats_subscriptions():
    """Check current NATS subscriptions."""
    async with httpx.AsyncClient() as client:
        try:
            # Use subs=1 parameter to include subscription details
            response = await client.get(f"{NATS_MONITOR_URL}/connz?subs=1")
            data = response.json()

            print("\n📊 NATS Connection Status:")
            print(f"   Total connections: {len(data.get('connections', []))}")

            subscriptions = []
            for conn in data.get('connections', []):
                subs = conn.get('subscriptions_list', [])
                if subs:
                    subscriptions.extend(subs)
                    print(f"   Connection {conn.get('cid')}: {len(subs)} subscriptions")
                    for sub in subs:
                        print(f"      - {sub}")

            return subscriptions
        except Exception as e:
            print(f"❌ Failed to check NATS: {e}")
            return []


async def stream_chat_request(message: str, duration: int = 10):
    """
    Send chat request and keep SSE stream open.

    Args:
        message: Chat message to send
        duration: How long to keep stream open (seconds)
    """
    print(f"\n🚀 Starting SSE stream...")
    print(f"   Message: {message}")
    print(f"   Duration: {duration}s")
    print(f"   User: {TEST_USER_ID}")

    url = f"{CHAT_SERVICE_URL}/chat/unified"
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    payload = {
        "message": message,
        "user_id": TEST_USER_ID,
        "stream": True  # Enable streaming mode
    }

    start_time = time.time()
    chunks_received = 0
    nats_events_received = 0

    async with httpx.AsyncClient(timeout=duration + 5) as client:
        try:
            async with client.stream('POST', url, json=payload, headers=headers) as response:
                print(f"✅ SSE connection established (status: {response.status_code})")
                print(f"\n📥 Streaming events:")

                async for line in response.aiter_lines():
                    if not line or line.startswith(':'):
                        continue

                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            chunks_received += 1

                            # Check if this is a NATS event
                            event_type = data.get('type', 'unknown')
                            if event_type == 'world_update':
                                nats_events_received += 1
                                print(f"   🌍 NATS EVENT: {data}")
                            elif event_type == 'metadata':
                                print(f"   📋 Metadata: conversation_id={data.get('conversation_id')}")
                            elif event_type == 'done':
                                print(f"   ✅ Stream complete: {data.get('finish_reason')}")
                                break
                            else:
                                # LLM content chunk
                                content = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                if content:
                                    print(f"   💬 Content: {content[:50]}...")
                        except json.JSONDecodeError:
                            print(f"   ⚠️ Non-JSON data: {data_str[:50]}")

                    # Keep stream open for specified duration
                    elapsed = time.time() - start_time
                    if elapsed > duration:
                        print(f"\n⏱️ Duration reached ({duration}s), closing stream...")
                        break

        except httpx.ReadTimeout:
            print(f"\n⏱️ Stream timed out after {duration}s")
        except Exception as e:
            print(f"\n❌ Stream error: {e}")

    elapsed = time.time() - start_time
    print(f"\n📊 Stream Summary:")
    print(f"   Duration: {elapsed:.2f}s")
    print(f"   Total chunks: {chunks_received}")
    print(f"   NATS events: {nats_events_received}")

    return {
        'duration': elapsed,
        'chunks': chunks_received,
        'nats_events': nats_events_received
    }


async def test_nats_subscription_lifecycle():
    """
    Test complete NATS subscription lifecycle:
    1. Check subscriptions before stream
    2. Start stream, check subscriptions appear
    3. End stream, check subscriptions cleaned up
    """
    print("=" * 70)
    print("NATS + SSE Integration Test - Phase 1B")
    print("=" * 70)

    # Step 1: Check baseline subscriptions
    print("\n📍 Step 1: Baseline NATS state")
    subs_before = await check_nats_subscriptions()

    # Step 2: Start SSE stream in background
    print("\n📍 Step 2: Starting SSE stream...")

    # Create stream task
    stream_task = asyncio.create_task(
        stream_chat_request("Hello, what do you see around here?", duration=5)
    )

    # Give stream time to establish and subscribe
    await asyncio.sleep(2)

    # Step 3: Check subscriptions during active stream
    print("\n📍 Step 3: Checking subscriptions during active stream...")
    subs_during = await check_nats_subscriptions()

    # Look for our user's subscription
    expected_subject = f"world.updates.user.{TEST_USER_ID}"
    found_subscription = any(expected_subject in str(sub) for sub in subs_during)

    if found_subscription:
        print(f"✅ SUCCESS: Found subscription to {expected_subject}")
    else:
        print(f"❌ FAILURE: No subscription to {expected_subject}")
        print(f"   Expected: {expected_subject}")
        print(f"   Found: {subs_during}")

    # Step 4: Wait for stream to complete
    print("\n📍 Step 4: Waiting for stream to complete...")
    stream_result = await stream_task

    # Give cleanup time to run
    await asyncio.sleep(1)

    # Step 5: Check subscriptions after cleanup
    print("\n📍 Step 5: Checking subscriptions after cleanup...")
    subs_after = await check_nats_subscriptions()

    # Verify cleanup
    still_subscribed = any(expected_subject in str(sub) for sub in subs_after)

    if not still_subscribed:
        print(f"✅ SUCCESS: Subscription cleaned up properly")
    else:
        print(f"❌ WARNING: Subscription still exists (may indicate leak)")

    # Final summary
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    print(f"Subscriptions before: {len(subs_before)}")
    print(f"Subscriptions during: {len(subs_during)}")
    print(f"Subscriptions after:  {len(subs_after)}")
    print(f"Stream duration: {stream_result['duration']:.2f}s")
    print(f"Chunks received: {stream_result['chunks']}")
    print(f"NATS events: {stream_result['nats_events']}")
    print()

    if found_subscription and not still_subscribed:
        print("✅ Phase 1B NATS Integration: WORKING")
    else:
        print("❌ Phase 1B NATS Integration: ISSUES DETECTED")

    return {
        'subscription_created': found_subscription,
        'subscription_cleaned': not still_subscribed,
        'stream_result': stream_result
    }


async def main():
    """Run the integration test."""
    try:
        results = await test_nats_subscription_lifecycle()

        # Exit code based on results
        if results['subscription_created'] and results['subscription_cleaned']:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure

    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
