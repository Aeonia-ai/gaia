#!/usr/bin/env python3
"""
Test script for the new streaming chat endpoint
Tests Time to First Token (TTFT) and overall streaming performance
"""

import asyncio
import aiohttp
import json
import time
import os
import sys
from typing import AsyncGenerator

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Environment configuration
API_BASE_URL = "http://localhost:8666"  # Docker mode  
API_KEY = os.getenv("API_KEY", "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE")

class StreamingTestClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_streaming_endpoint(
        self, 
        message: str,
        persona_id: str = "default",
        activity: str = "generic"
    ) -> dict:
        """Test the streaming endpoint and measure performance"""
        
        url = f"{self.base_url}/api/v0.2/chat/stream"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": message,
            "persona_id": persona_id,
            "activity": activity
        }
        
        print(f"\n🚀 Testing streaming endpoint: {message[:50]}...")
        print(f"📡 URL: {url}")
        
        start_time = time.time()
        first_token_time = None
        token_count = 0
        response_content = ""
        
        try:
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ HTTP Error {response.status}: {error_text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}"
                    }
                
                print(f"✅ Connection established, starting stream...")
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if not line_str:
                            continue
                        
                        try:
                            # Parse SSE data
                            if line_str.startswith('data: '):
                                data_str = line_str[6:]  # Remove 'data: ' prefix
                                data = json.loads(data_str)
                                
                                if data.get("type") == "start":
                                    print(f"📋 Stream started at: {data.get('timestamp')}")
                                
                                elif data.get("type") == "ready":
                                    persona_name = data.get("persona", "Unknown")
                                    print(f"🎭 Persona loaded: {persona_name}")
                                
                                elif data.get("type") == "content":
                                    if first_token_time is None:
                                        first_token_time = time.time()
                                        ttft = (first_token_time - start_time) * 1000
                                        print(f"⚡ First token in {ttft:.0f}ms")
                                    
                                    content = data.get("content", "")
                                    response_content += content
                                    token_count += 1
                                    print(content, end="", flush=True)
                                
                                elif data.get("type") == "tool_use":
                                    tool_name = data.get("tool", "unknown")
                                    print(f"\n🔧 Tool used: {tool_name}")
                                
                                elif data.get("type") == "complete":
                                    print(f"\n\n✅ Stream completed at: {data.get('timestamp')}")
                                    break
                                
                                elif data.get("type") == "error":
                                    error_msg = data.get("error", "Unknown error")
                                    print(f"\n❌ Stream error: {error_msg}")
                                    return {
                                        "success": False,
                                        "error": error_msg
                                    }
                            
                        except json.JSONDecodeError:
                            # Skip non-JSON lines
                            continue
                
                end_time = time.time()
                total_time = (end_time - start_time) * 1000
                ttft = (first_token_time - start_time) * 1000 if first_token_time else None
                
                return {
                    "success": True,
                    "ttft_ms": ttft,
                    "total_time_ms": total_time,
                    "token_count": token_count,
                    "response_length": len(response_content),
                    "response_content": response_content
                }
        
        except Exception as e:
            print(f"\n❌ Connection error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_traditional_endpoint(
        self, 
        message: str,
        persona_id: str = "default"
    ) -> dict:
        """Test the traditional blocking endpoint for comparison"""
        
        url = f"{self.base_url}/api/v1/chat"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": message
        }
        
        print(f"\n🐢 Testing traditional endpoint: {message[:50]}...")
        
        start_time = time.time()
        
        try:
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}"
                    }
                
                result = await response.json()
                end_time = time.time()
                total_time = (end_time - start_time) * 1000
                
                response_content = result.get("response", "")
                
                return {
                    "success": True,
                    "total_time_ms": total_time,
                    "response_length": len(response_content),
                    "response_content": response_content
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

async def run_performance_comparison():
    """Run performance tests comparing streaming vs traditional endpoints"""
    
    test_messages = [
        "Hello, how are you today?",
        "What's the weather like?",
        "Can you help me write a short poem about technology?"
    ]
    
    async with StreamingTestClient(API_BASE_URL, API_KEY) as client:
        print("=" * 80)
        print("🧪 STREAMING ENDPOINT PERFORMANCE TEST")
        print("=" * 80)
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n📝 Test {i}/{len(test_messages)}")
            print("-" * 50)
            
            # Test streaming endpoint
            streaming_result = await client.test_streaming_endpoint(message)
            
            # Test traditional endpoint  
            traditional_result = await client.test_traditional_endpoint(message)
            
            # Compare results
            print(f"\n📊 PERFORMANCE COMPARISON:")
            
            if streaming_result["success"] and traditional_result["success"]:
                streaming_time = streaming_result["total_time_ms"]
                traditional_time = traditional_result["total_time_ms"]
                ttft = streaming_result.get("ttft_ms")
                
                print(f"   Streaming Total:     {streaming_time:.0f}ms")
                print(f"   Traditional Total:   {traditional_time:.0f}ms")
                if ttft:
                    print(f"   Time to First Token: {ttft:.0f}ms")
                
                improvement = ((traditional_time - streaming_time) / traditional_time) * 100
                print(f"   Performance Impact:  {improvement:+.1f}%")
                
                if ttft:
                    perceived_improvement = ((traditional_time - ttft) / traditional_time) * 100
                    print(f"   Perceived Improvement: {perceived_improvement:+.1f}%")
            
            else:
                if not streaming_result["success"]:
                    print(f"   ❌ Streaming failed: {streaming_result['error']}")
                if not traditional_result["success"]:
                    print(f"   ❌ Traditional failed: {traditional_result['error']}")
            
            print("\n" + "=" * 50)

async def main():
    """Main test function"""
    print("🎯 Starting streaming endpoint tests...")
    
    # Check if server is running
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    print(f"✅ Server is running at {API_BASE_URL}")
                else:
                    print(f"❌ Server health check failed: {response.status}")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to server at {API_BASE_URL}: {e}")
            print("💡 Make sure the server is running with: ./scripts/deploy-local-venv.sh")
            return
    
    # Run performance tests
    await run_performance_comparison()
    
    print("\n🎉 Testing completed!")

if __name__ == "__main__":
    asyncio.run(main())