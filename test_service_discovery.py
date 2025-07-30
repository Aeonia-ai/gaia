#!/usr/bin/env python3
"""Test service discovery to debug route extraction"""

import asyncio
import httpx

async def test_route_discovery():
    async with httpx.AsyncClient() as client:
        # Test health endpoint without routes
        resp = await client.get("https://gaia-chat-dev.fly.dev/health")
        print("Basic health:", resp.json())
        
        # Test with include_routes
        resp = await client.get("https://gaia-chat-dev.fly.dev/health?include_routes=true")
        data = resp.json()
        print(f"\nHealth with routes: {data.get('service')}, {data.get('version')}")
        print(f"Number of routes: {len(data.get('routes', []))}")
        
        if data.get('routes'):
            print("\nDiscovered routes:")
            for route in data['routes']:
                print(f"  {route['methods']} {route['path']}")
        else:
            print("\nNo routes discovered!")
            
        # Try to access the docs to see if routes are there
        resp = await client.get("https://gaia-chat-dev.fly.dev/docs")
        print(f"\nDocs endpoint status: {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(test_route_discovery())