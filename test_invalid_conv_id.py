#!/usr/bin/env python3
"""
Debug invalid conversation ID handling.
"""

import httpx
import os
import asyncio
import json

async def test_invalid_conversation_id():
    gateway_url = "http://localhost:8666"  # External gateway port
    api_key = os.getenv("API_KEY")
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=== Testing Invalid Conversation ID Handling ===\n")
        
        # Send message with non-existent conversation_id
        print("1. Sending message with invalid conversation_id...")
        response = await client.post(
            f"{gateway_url}/api/v1/chat",
            headers=headers,
            json={
                "message": "Hello",
                "conversation_id": "non-existent-id-12345"
            }
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response keys: {list(data.keys())}")
            if "_metadata" in data:
                print(f"   Metadata: {data['_metadata']}")
                returned_id = data['_metadata'].get('conversation_id')
                print(f"   Returned conversation ID: {returned_id}")
                print(f"   Input ID: non-existent-id-12345")
                print(f"   IDs are different: {returned_id != 'non-existent-id-12345'}")
        else:
            print(f"   Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_invalid_conversation_id())