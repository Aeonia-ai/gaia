"""
Test the lightweight chat endpoint

Tests the new /chat/lightweight endpoint that uses mcp-agent without MCP overhead.
"""
import asyncio
import httpx
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8666"  # Gateway port
API_KEY = "test-api-key"  # Replace with your API key from .env


async def test_lightweight_chat():
    """Test the lightweight chat endpoint"""
    
    async with httpx.AsyncClient() as client:
        # Test 1: Simple chat message
        print("Test 1: Simple lightweight chat")
        response = await client.post(
            f"{BASE_URL}/chat/lightweight",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "message": "Hello! Tell me a short joke about Python programming.",
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.7
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response: {result['choices'][0]['message']['content'][:200]}...")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
        
        print("\n" + "-"*50 + "\n")
        
        # Test 2: Multi-turn conversation
        print("Test 2: Multi-turn conversation")
        
        # First message
        response1 = await client.post(
            f"{BASE_URL}/chat/lightweight",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "message": "My name is Alice and I love hiking.",
            }
        )
        
        if response1.status_code == 200:
            print("✅ First message sent")
        
        # Second message (should remember context)
        response2 = await client.post(
            f"{BASE_URL}/chat/lightweight",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "message": "What's my name and what do I enjoy?",
            }
        )
        
        if response2.status_code == 200:
            result = response2.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ Context preserved: {content[:200]}...")
            
            # Check if it remembers
            if "Alice" in content and "hiking" in content:
                print("✅ Successfully remembered context!")
            else:
                print("⚠️  Context might not be preserved")
        
        print("\n" + "-"*50 + "\n")
        
        # Test 3: Compare with regular endpoint
        print("Test 3: Performance comparison")
        
        # Time lightweight endpoint
        import time
        start = time.time()
        response = await client.post(
            f"{BASE_URL}/chat/lightweight",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "message": "What is 2+2?",
            }
        )
        lightweight_time = time.time() - start
        
        print(f"✅ Lightweight endpoint: {lightweight_time:.2f}s")
        
        # Could compare with regular endpoint here
        # start = time.time()
        # response = await client.post(f"{BASE_URL}/chat/multi-provider", ...)
        # regular_time = time.time() - start
        # print(f"Regular endpoint: {regular_time:.2f}s")


async def test_meditation_pattern():
    """Test consciousness pattern (meditation)"""
    
    print("\nTest 4: Meditation pattern")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chat/lightweight",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "message": "Guide me through a brief breathing exercise for relaxation",
                "temperature": 0.8
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ Meditation response: {content[:300]}...")
            
            # Check for meditation-related content
            meditation_words = ['breath', 'relax', 'calm', 'inhale', 'exhale']
            if any(word in content.lower() for word in meditation_words):
                print("✅ Successfully generated meditation guidance!")


if __name__ == "__main__":
    print("🧪 Testing Lightweight Chat Endpoint\n")
    
    # Get API key from environment if available
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    if os.getenv("API_KEY"):
        API_KEY = os.getenv("API_KEY")
    
    asyncio.run(test_lightweight_chat())
    asyncio.run(test_meditation_pattern())