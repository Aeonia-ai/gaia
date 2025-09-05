#!/usr/bin/env python3
"""Test streaming on dev environment to verify word boundary fix."""

import asyncio
import httpx
import json
import os

async def test_streaming(url: str, api_key: str):
    """Test streaming to verify word boundaries are preserved."""
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": "Tell me about quantum computing in exactly 3 sentences",
        "stream": True
    }
    
    print(f"Testing streaming at: {url}/api/v1/chat")
    print("-" * 60)
    
    words_split = []
    buffer = ""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream(
            "POST",
            f"{url}/api/v1/chat",
            headers=headers,
            json=payload
        ) as response:
            if response.status_code != 200:
                error = await response.aread()
                print(f"Error {response.status_code}: {error.decode()}")
                return
            
            # Collect raw chunks to check for word splitting
            async for chunk in response.aiter_text():
                # Check if this chunk starts mid-word (lowercase letter at start)
                if buffer and chunk and chunk[0].islower() and buffer[-1].isalpha():
                    words_split.append(f"{buffer[-10:]}|{chunk[:10]}")
                buffer += chunk
                print(chunk, end='', flush=True)
    
    print("\n" + "-" * 60)
    
    if words_split:
        print("❌ FAILED: Words were split mid-token:")
        for split in words_split[:5]:  # Show first 5 examples
            print(f"  - {split}")
    else:
        print("✅ SUCCESS: No words were split mid-token")
    
    # Check for JSON integrity
    if '{"m":' in buffer:
        print("✅ JSON blocks detected in stream")

async def main():
    # Use dev environment
    url = "https://gaia-gateway-dev.fly.dev"
    api_key = os.getenv("API_KEY", "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY")
    
    await test_streaming(url, api_key)

if __name__ == "__main__":
    asyncio.run(main())
