#!/usr/bin/env python3
"""
Show raw SSE streaming output from the gateway without any parsing.
This helps debug exactly what bytes are being sent over the wire.
"""

import asyncio
import httpx
import sys
import os

async def show_raw_stream(url: str, api_key: str, endpoint: str = "/api/v1/chat"):
    """Show raw bytes from streaming endpoint."""
    print(f"\n{'='*60}")
    print(f"RAW STREAM from: {url}{endpoint}")
    print('='*60)
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": "Count from 1 to 5 slowly",
        "stream": True
    }
    
    byte_count = 0
    chunk_count = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{url}{endpoint}",
                headers=headers,
                json=payload
            ) as response:
                print(f"Status: {response.status_code}")
                print(f"Headers:")
                for k, v in response.headers.items():
                    print(f"  {k}: {v}")
                print("-" * 40)
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"Error: {error_text.decode()}")
                    return
                
                print("RAW BYTES (showing as UTF-8 with escape sequences):")
                print("-" * 40)
                
                # Show raw bytes as they arrive
                async for chunk in response.aiter_bytes():
                    chunk_count += 1
                    byte_count += len(chunk)
                    
                    # Decode to show human-readable form with escapes
                    try:
                        text = chunk.decode('utf-8')
                        # Show with visible newlines and special chars
                        display = repr(text)[1:-1]  # Remove quotes from repr
                        print(f"[Chunk {chunk_count:3d}] {len(chunk):4d} bytes: {display}")
                    except:
                        # If not UTF-8, show hex
                        print(f"[Chunk {chunk_count:3d}] {len(chunk):4d} bytes: {chunk.hex()}")
                
                print("-" * 40)
                print(f"Total: {chunk_count} chunks, {byte_count} bytes")
                
        except Exception as e:
            print(f"Error: {e}")

async def show_with_line_boundaries(url: str, api_key: str, endpoint: str = "/api/v1/chat"):
    """Show stream with line boundaries visible."""
    print(f"\n{'='*60}")
    print(f"LINE-BASED VIEW from: {url}{endpoint}")
    print('='*60)
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": "Count from 1 to 5 slowly",
        "stream": True
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{url}{endpoint}",
                headers=headers,
                json=payload
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"Error: {error_text.decode()}")
                    return
                
                print("LINES (with \\n markers):")
                print("-" * 40)
                
                line_count = 0
                buffer = ""
                
                # Accumulate and show lines
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    # Show each complete line
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line_count += 1
                        if line:
                            print(f"[Line {line_count:3d}] {line}")
                        else:
                            print(f"[Line {line_count:3d}] <empty>")
                
                # Show any remaining buffer
                if buffer:
                    line_count += 1
                    print(f"[Line {line_count:3d}] {buffer} (no newline)")
                
                print("-" * 40)
                print(f"Total: {line_count} lines")
                
        except Exception as e:
            print(f"Error: {e}")

async def show_event_boundaries(url: str, api_key: str, endpoint: str = "/api/v1/chat"):
    """Show SSE event boundaries (double newlines)."""
    print(f"\n{'='*60}")
    print(f"SSE EVENT BOUNDARIES from: {url}{endpoint}")
    print('='*60)
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": "Count from 1 to 5 slowly",
        "stream": True
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{url}{endpoint}",
                headers=headers,
                json=payload
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"Error: {error_text.decode()}")
                    return
                
                print("SSE EVENTS (split on \\n\\n):")
                print("-" * 40)
                
                event_count = 0
                buffer = ""
                
                # Accumulate and show events
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    # Show each complete SSE event
                    while '\n\n' in buffer:
                        event, buffer = buffer.split('\n\n', 1)
                        event_count += 1
                        print(f"[Event {event_count:3d}]")
                        for line in event.split('\n'):
                            if line:
                                print(f"  {line}")
                            else:
                                print(f"  <empty line>")
                        print()
                
                # Show any remaining buffer
                if buffer.strip():
                    event_count += 1
                    print(f"[Event {event_count:3d}] INCOMPLETE:")
                    for line in buffer.split('\n'):
                        if line:
                            print(f"  {line}")
                
                print("-" * 40)
                print(f"Total: {event_count} SSE events")
                
        except Exception as e:
            print(f"Error: {e}")

async def main():
    """Run raw streaming tests."""
    # Configuration
    gateway_url = "http://localhost:8666"
    api_key = os.getenv("API_KEY", "test-api-key")
    
    print("="*60)
    print("RAW SSE STREAMING ANALYSIS")
    print("="*60)
    print(f"Gateway: {gateway_url}")
    print(f"API Key: {api_key[:10]}..." if len(api_key) > 10 else api_key)
    
    # Test both endpoints
    endpoints = [
        "/api/v1/chat",      # Raw proxy
        "/api/v0.3/chat"     # Clean format
    ]
    
    for endpoint in endpoints:
        # Show raw bytes
        await show_raw_stream(gateway_url, api_key, endpoint)
        
        # Show line boundaries
        await show_with_line_boundaries(gateway_url, api_key, endpoint)
        
        # Show SSE event boundaries
        await show_event_boundaries(gateway_url, api_key, endpoint)
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())