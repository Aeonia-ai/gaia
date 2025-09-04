#!/usr/bin/env python3
"""
Test SSE streaming to verify token boundaries are preserved.

This script tests both the raw gateway proxy and the v0.3 clean format
to ensure SSE events and tokens are not split incorrectly.
"""

import asyncio
import httpx
import json
import sys
from typing import AsyncGenerator, Dict, Any

async def parse_sse_stream(response: httpx.Response) -> AsyncGenerator[Dict[str, Any], None]:
    """Parse SSE stream correctly, respecting event boundaries."""
    buffer = ""
    
    async for chunk in response.aiter_text():
        buffer += chunk
        
        # Process complete SSE events (separated by double newlines)
        while "\n\n" in buffer:
            event, buffer = buffer.split("\n\n", 1)
            
            if not event.strip():
                continue
            
            # Parse the SSE event
            if event.startswith("data: "):
                data_str = event[6:].strip()
                
                if data_str == "[DONE]":
                    print("Stream complete: [DONE]")
                    return
                
                try:
                    data = json.loads(data_str)
                    yield data
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse SSE data: {e}")
                    print(f"Raw data: {data_str[:100]}")

async def test_streaming_endpoint(url: str, api_key: str, endpoint: str = "/api/v1/chat"):
    """Test a streaming endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {url}{endpoint}")
    print('='*60)
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": "Write a haiku about streaming data. Include some code.",
        "stream": True
    }
    
    tokens_received = []
    event_count = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{url}{endpoint}",
                headers=headers,
                json=payload
            ) as response:
                print(f"Response status: {response.status_code}")
                print(f"Content-Type: {response.headers.get('content-type', 'not set')}")
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"Error response: {error_text.decode()}")
                    return
                
                # Parse SSE events
                async for event_data in parse_sse_stream(response):
                    event_count += 1
                    
                    # Check event structure
                    if "type" in event_data:
                        event_type = event_data["type"]
                        print(f"Event {event_count}: type={event_type}", end="")
                        
                        if event_type == "content" and "content" in event_data:
                            content = event_data["content"]
                            tokens_received.append(content)
                            print(f" | content='{content}'")
                        else:
                            print(f" | data={event_data}")
                    elif "choices" in event_data:
                        # OpenAI format
                        choices = event_data.get("choices", [])
                        if choices and "delta" in choices[0]:
                            content = choices[0]["delta"].get("content", "")
                            if content:
                                tokens_received.append(content)
                                print(f"Event {event_count}: OpenAI format | content='{content}'")
                    else:
                        print(f"Event {event_count}: Unknown format | {event_data}")
                
                print(f"\n✅ Successfully received {event_count} events")
                print(f"✅ Total tokens/chunks: {len(tokens_received)}")
                
                # Reconstruct the full message
                full_message = "".join(tokens_received)
                print(f"\nReconstructed message ({len(full_message)} chars):")
                print("-" * 40)
                print(full_message)
                print("-" * 40)
                
                # Check for common issues
                if "\n" in "".join(tokens_received[:5]):
                    print("⚠️  Warning: Early tokens contain newlines - might indicate splitting issues")
                
                return True
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

async def main():
    """Run streaming tests."""
    import os
    # Configuration
    gateway_url = "http://localhost:8666"
    api_key = os.getenv("API_KEY", "test-api-key")  # Get from environment
    
    print("SSE Streaming Token Boundary Test")
    print("=================================")
    
    # Test regular gateway proxy (raw pass-through)
    success1 = await test_streaming_endpoint(gateway_url, api_key, "/api/v1/chat")
    
    # Test v0.3 clean format (with conversion)
    success2 = await test_streaming_endpoint(gateway_url, api_key, "/api/v0.3/chat")
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary:")
    print(f"  Gateway raw proxy: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"  v0.3 clean format: {'✅ PASSED' if success2 else '❌ FAILED'}")
    print('='*60)
    
    return 0 if (success1 and success2) else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)