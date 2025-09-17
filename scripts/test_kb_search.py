#!/usr/bin/env python3
"""
Test KB search functionality with actual combat content.
"""

import httpx
import json
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_kb_search():
    """Test KB search through the chat API."""

    # Test queries related to our combat.md content
    test_queries = [
        "Search the knowledge base for fire damage",
        "Find information about combat mechanics in the KB",
        "What does the knowledge base say about health points",
        "Search KB for elemental damage types"
    ]

    gateway_url = "http://localhost:8666"
    api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")

    if not api_key:
        print("❌ No API key found. Set API_KEY in .env file")
        sys.exit(1)

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        print("🔍 Testing KB Search Functionality\n")
        print("=" * 60)

        for query in test_queries:
            print(f"\n📝 Query: {query}")
            print("-" * 40)

            try:
                response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={
                        "message": query,
                        "stream": False,
                        "use_kb_tools": True  # Ensure KB tools are used
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]

                    # Check if KB was actually searched
                    kb_indicators = ["knowledge base", "kb", "search", "found", "results", "documents"]
                    kb_used = any(indicator in content.lower() for indicator in kb_indicators)

                    # Check if combat content was found
                    combat_terms = ["fire", "damage", "health", "hp", "elemental", "combat"]
                    content_found = any(term in content.lower() for term in combat_terms)

                    print(f"✅ Response received (length: {len(content)} chars)")
                    print(f"📊 KB search indicators found: {kb_used}")
                    print(f"🎯 Combat content found: {content_found}")

                    # Show first 300 chars of response
                    preview = content[:300] + "..." if len(content) > 300 else content
                    print(f"\n📄 Preview:\n{preview}")

                    if not kb_used:
                        print("⚠️  Warning: Response may not have used KB search")
                    if not content_found:
                        print("⚠️  Warning: Response doesn't contain expected combat terms")

                else:
                    print(f"❌ Error: Status {response.status_code}")
                    print(f"Response: {response.text}")

            except Exception as e:
                print(f"❌ Exception: {e}")

        print("\n" + "=" * 60)
        print("🎯 KB Search Test Complete\n")

if __name__ == "__main__":
    asyncio.run(test_kb_search())