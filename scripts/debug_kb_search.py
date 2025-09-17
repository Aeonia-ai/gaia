#!/usr/bin/env python3
"""Debug KB search to understand why no results are returned."""

import asyncio
import sys
import json

# Add app to path
sys.path.insert(0, '/app')

from app.services.kb.kb_mcp_server import KBMCPServer

async def test_search():
    """Test KB search directly."""
    print("=" * 60)
    print("Testing KB MCP Server Search")
    print("=" * 60)

    # Initialize KB server
    kb = KBMCPServer('/kb')
    print(f"✓ KB server initialized with path: {kb.kb_path}")

    # Test search for "fire"
    print("\n🔍 Searching for: 'fire'")
    result = await kb.search_kb(
        query='fire',
        limit=5
    )

    # Display result structure
    print(f"\n📊 Result structure:")
    print(f"  - Type: {type(result)}")
    print(f"  - Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    print(f"  - Success: {result.get('success', 'N/A')}")
    print(f"  - Total results: {result.get('total_results', 'N/A')}")
    print(f"  - Results list length: {len(result.get('results', []))}")

    # Display results
    print(f"\n📄 Search results:")
    results = result.get('results', [])
    if results:
        for i, r in enumerate(results[:5], 1):
            print(f"\n  {i}. File: {r.get('relative_path', 'Unknown')}")
            print(f"     Line: {r.get('line_number', 'N/A')}")
            print(f"     Excerpt: {r.get('content_excerpt', '')[:100]}")
            print(f"     Keywords: {r.get('keywords', [])[:5]}")
    else:
        print("  ❌ No results in the results list")

    # Show raw result (truncated)
    print(f"\n🔧 Raw result (first 1000 chars):")
    result_json = json.dumps(result, indent=2, default=str)
    print(result_json[:1000])

    return result

if __name__ == "__main__":
    asyncio.run(test_search())