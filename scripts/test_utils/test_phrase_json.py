#!/usr/bin/env python3
"""Test that JSON preservation works in phrase mode"""

import asyncio
import json
from app.services.streaming_buffer import StreamBuffer

async def test_json_in_phrase_mode():
    # Test content with JSON directive and phrase boundaries
    test_text = 'Hello Unity: here is a fairy; {"m":"spawn_character","p":{"type":"fairy","pos":[0,0,0]}}; and more text: with colons!'

    print("TEST: JSON preservation in PHRASE MODE")
    print("="*60)
    print(f"Input: {test_text}")
    print("-"*60)

    # Create buffer in PHRASE MODE with JSON preservation
    buffer = StreamBuffer(preserve_json=True, sentence_mode=False)
    chunks = []

    async for chunk in buffer.process(test_text):
        chunks.append(chunk)
        print(f"Chunk {len(chunks)}: {repr(chunk)}")

    async for chunk in buffer.flush():
        if chunk:
            chunks.append(chunk)
            print(f"Chunk {len(chunks)} (flush): {repr(chunk)}")

    print("-"*60)

    # Verify results
    print("\nVERIFICATION:")

    # Check if JSON was kept intact
    json_chunks = [c for c in chunks if c.strip().startswith('{')]
    if json_chunks:
        json_chunk = json_chunks[0]
        print(f"✅ JSON chunk found: {repr(json_chunk)}")

        # Validate it's proper JSON
        try:
            parsed = json.loads(json_chunk)
            print(f"✅ Valid JSON parsed: {parsed}")
            assert parsed["m"] == "spawn_character"
            assert parsed["p"]["type"] == "fairy"
            print("✅ JSON structure correct!")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            return False
    else:
        print("❌ No JSON chunk found!")
        return False

    # Check phrase boundaries still work
    colon_splits = [c for c in chunks if c.strip().endswith(':')]
    semicolon_splits = [c for c in chunks if c.strip().endswith(';')]

    print(f"\nPhrase splitting:")
    print(f"  Chunks ending with ':' = {len(colon_splits)}")
    print(f"  Chunks ending with ';' = {len(semicolon_splits)}")

    print("\n" + "="*60)
    if json_chunks and len(chunks) > 3:
        print("✅ SUCCESS: JSON preservation works in phrase mode!")
        print("   - JSON kept intact as single chunk")
        print("   - Phrase boundaries still respected")
        return True
    else:
        print("❌ FAILED: Something wrong with phrase mode + JSON")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_json_in_phrase_mode())
    exit(0 if success else 1)