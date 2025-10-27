#!/usr/bin/env python3
"""Compare sentence mode vs phrase mode for Unity streaming"""

import asyncio
from app.services.streaming_buffer import StreamBuffer

async def test_modes():
    # Test content with multiple phrase boundaries
    test_text = "Hello there, Unity client! Here's what I can do: spawn entities; manage state; and provide responses. Isn't that great?"

    print("TEST TEXT:")
    print(test_text)
    print("\n" + "="*60 + "\n")

    # Test SENTENCE MODE (current)
    print("SENTENCE MODE (current):")
    print("-" * 40)
    sentence_buffer = StreamBuffer(preserve_json=True, sentence_mode=True)
    sentence_chunks = []

    async for chunk in sentence_buffer.process(test_text):
        sentence_chunks.append(chunk)
        print(f"Chunk {len(sentence_chunks)}: {repr(chunk)}")

    async for chunk in sentence_buffer.flush():
        if chunk:
            sentence_chunks.append(chunk)
            print(f"Chunk {len(sentence_chunks)} (flush): {repr(chunk)}")

    print(f"\nTotal chunks: {len(sentence_chunks)}")
    print(f"Average size: {sum(len(c) for c in sentence_chunks) / len(sentence_chunks):.1f} chars")

    print("\n" + "="*60 + "\n")

    # Test PHRASE MODE
    print("PHRASE MODE (alternative):")
    print("-" * 40)
    phrase_buffer = StreamBuffer(preserve_json=True, sentence_mode=False)
    phrase_chunks = []

    async for chunk in phrase_buffer.process(test_text):
        phrase_chunks.append(chunk)
        print(f"Chunk {len(phrase_chunks)}: {repr(chunk)}")

    async for chunk in phrase_buffer.flush():
        if chunk:
            phrase_chunks.append(chunk)
            print(f"Chunk {len(phrase_chunks)} (flush): {repr(chunk)}")

    print(f"\nTotal chunks: {len(phrase_chunks)}")
    print(f"Average size: {sum(len(c) for c in phrase_chunks) / len(phrase_chunks):.1f} chars")

    print("\n" + "="*60 + "\n")
    print("COMPARISON:")
    print(f"Sentence mode: {len(sentence_chunks)} chunks, smoother but less responsive")
    print(f"Phrase mode:   {len(phrase_chunks)} chunks, more granular updates")
    print("\nFor Unity: Phrase mode might give better perceived responsiveness")
    print("while still avoiding word splits!")

if __name__ == "__main__":
    asyncio.run(test_modes())