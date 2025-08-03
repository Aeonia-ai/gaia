#!/usr/bin/env python3
"""
Debug conversation persistence.
"""

import httpx
import os
import asyncio
import json

async def test_conversation():
    gateway_url = "http://localhost:8666"  # External gateway port
    api_key = os.getenv("API_KEY")
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=== Testing Conversation Persistence ===\n")
        
        # First message
        print("1. Sending first message...")
        response1 = await client.post(
            f"{gateway_url}/api/v1/chat",
            headers=headers,
            json={"message": "My favorite number is 42. Remember this."}
        )
        
        print(f"   Status: {response1.status_code}")
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"   Response keys: {list(data1.keys())}")
            if "_metadata" in data1:
                print(f"   Metadata: {data1['_metadata']}")
                conversation_id = data1['_metadata'].get('conversation_id')
                print(f"   Conversation ID: {conversation_id}")
            
            # Second message with conversation_id
            if conversation_id:
                print(f"\n2. Sending second message with conversation_id: {conversation_id}")
                response2 = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={
                        "message": "What is my favorite number?",
                        "conversation_id": conversation_id
                    }
                )
                
                print(f"   Status: {response2.status_code}")
                if response2.status_code == 200:
                    data2 = response2.json()
                    content = data2["choices"][0]["message"]["content"]
                    print(f"   AI Response: {content}")
                    
                    if "42" in content:
                        print("\n✅ SUCCESS: Conversation context maintained!")
                    else:
                        print("\n❌ FAILED: Conversation context lost")
                else:
                    print(f"   Error: {response2.text}")
        else:
            print(f"   Error: {response1.text}")

if __name__ == "__main__":
    asyncio.run(test_conversation())