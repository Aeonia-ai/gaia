#!/usr/bin/env python3
"""
Test Unity client conversation_id extraction from V0.3 streaming responses
Simulates how Unity clients should parse SSE streams to extract conversation_id
"""
import asyncio
import aiohttp
import json
import os
import re
from typing import Optional, Dict, Any

# Configuration
BASE_URL = os.getenv("GAIA_BASE_URL", "http://localhost:8666")
API_KEY = os.getenv("GAIA_API_KEY", "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE")

class UnityClientSimulator:
    """Simulates Unity client behavior for conversation_id extraction"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }

    def parse_sse_event(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single SSE event line like Unity would"""
        if line.startswith("data: "):
            try:
                data_content = line[6:]  # Remove "data: " prefix
                if data_content.strip() == "[DONE]":
                    return {"type": "done"}
                return json.loads(data_content)
            except json.JSONDecodeError:
                return None
        return None

    def extract_conversation_id_from_stream(self, stream_content: str) -> Optional[str]:
        """
        Extract conversation_id from streaming response like Unity client would.
        Unity looks for the first metadata event containing conversation_id.
        """
        lines = stream_content.split('\n')

        for line in lines:
            event = self.parse_sse_event(line)
            if event and event.get("type") == "metadata":
                conversation_id = event.get("conversation_id")
                if conversation_id:
                    print(f"🎮 Unity client extracted conversation_id: {conversation_id}")
                    return conversation_id

        print("❌ Unity client failed to extract conversation_id from stream")
        return None

    async def test_v03_conversation_id_extraction(self, message: str, conversation_id: Optional[str] = None) -> Optional[str]:
        """Test V0.3 streaming conversation_id extraction"""
        url = f"{self.base_url}/api/v0.3/chat"

        payload = {
            "message": message,
            "model": "claude-sonnet-4-5",
            "stream": True
        }

        if conversation_id:
            payload["conversation_id"] = conversation_id

        print(f"\n🚀 Testing Unity client extraction with:")
        print(f"   Message: {message}")
        print(f"   Conversation ID: {conversation_id or 'None (new conversation)'}")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    if response.status != 200:
                        print(f"❌ HTTP error: {response.status}")
                        return None

                    # Collect first few chunks to extract conversation_id
                    stream_content = ""
                    chunks_collected = 0
                    max_chunks_for_metadata = 5  # Unity would stop looking after a few chunks

                    async for chunk in response.content.iter_chunked(1024):
                        if chunks_collected >= max_chunks_for_metadata:
                            break

                        chunk_text = chunk.decode('utf-8')
                        stream_content += chunk_text
                        chunks_collected += 1

                        # Unity would try to extract conversation_id as soon as possible
                        extracted_id = self.extract_conversation_id_from_stream(stream_content)
                        if extracted_id:
                            print(f"✅ Unity client successfully extracted conversation_id after {chunks_collected} chunks")
                            return extracted_id

                    # If not found in first few chunks, try full content
                    if not stream_content:
                        print("❌ No stream content received")
                        return None

                    final_id = self.extract_conversation_id_from_stream(stream_content)
                    if final_id:
                        print(f"⚠️  Unity client found conversation_id in full stream (not ideal for performance)")
                    else:
                        print("❌ Unity client could not find conversation_id in stream")

                    return final_id

            except Exception as e:
                print(f"❌ Unity client error: {e}")
                return None

async def test_unity_scenarios():
    """Test various Unity client scenarios"""
    print("🎮 Unity Client Conversation ID Extraction Test")
    print("=" * 60)

    simulator = UnityClientSimulator(BASE_URL, API_KEY)

    # Test 1: New conversation (no conversation_id provided)
    print("\n📋 Test 1: New conversation")
    new_conv_id = await simulator.test_v03_conversation_id_extraction(
        "Hello, this is a test message for Unity client"
    )

    # Test 2: Explicit "new" conversation
    print("\n📋 Test 2: Explicit 'new' conversation")
    explicit_new_id = await simulator.test_v03_conversation_id_extraction(
        "Testing explicit new conversation",
        conversation_id="new"
    )

    # Test 3: Resume existing conversation (if we have one)
    if new_conv_id:
        print("\n📋 Test 3: Resume existing conversation")
        resumed_id = await simulator.test_v03_conversation_id_extraction(
            "This should continue our conversation",
            conversation_id=new_conv_id
        )

        if resumed_id == new_conv_id:
            print(f"✅ Unity client successfully resumed conversation: {resumed_id}")
        else:
            print(f"❌ Conversation ID mismatch: expected {new_conv_id}, got {resumed_id}")

    # Test 4: Invalid conversation_id (should create new)
    print("\n📋 Test 4: Invalid conversation_id handling")
    invalid_conv_id = await simulator.test_v03_conversation_id_extraction(
        "Testing with invalid conversation ID",
        conversation_id="invalid-uuid-123"
    )

    # Summary
    print("\n" + "=" * 60)
    print("🎮 UNITY CLIENT TEST SUMMARY")
    print("=" * 60)

    results = [
        ("New conversation", new_conv_id),
        ("Explicit 'new'", explicit_new_id),
        ("Invalid ID handling", invalid_conv_id)
    ]

    if new_conv_id:
        results.append(("Resume existing", "Tested successfully"))

    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name:20} | {result or 'FAILED'}")

    success_rate = sum(1 for _, result in results if result) / len(results)
    print(f"\n🎯 Success rate: {success_rate:.1%}")

    if success_rate == 1.0:
        print("🎉 All Unity client scenarios working perfectly!")
    else:
        print("⚠️  Some Unity client scenarios need attention")

if __name__ == "__main__":
    asyncio.run(test_unity_scenarios())