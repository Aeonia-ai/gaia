#!/usr/bin/env python3
"""Test sentence boundary chunking for Unity client"""

import json
import requests

def test_sentence_chunking():
    url = "http://localhost:8666/api/v0.3/chat"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
    }
    data = {
        "message": "Tell me three facts. Make them short sentences.",
        "stream": True
    }

    print("Testing sentence boundary chunking...")
    print("-" * 60)

    response = requests.post(url, headers=headers, json=data, stream=True)

    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        return

    chunks = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                try:
                    data_str = line_str[6:]
                    if data_str.strip():
                        event_data = json.loads(data_str)

                        if event_data.get("type") == "metadata":
                            print(f"✅ Metadata: conversation_id={event_data.get('conversation_id')}")

                        elif event_data.get("type") == "content":
                            content = event_data.get("content", "")
                            chunks.append(content)

                            # Check if chunk ends with sentence boundary
                            ends_with_sentence = any(content.rstrip().endswith(p) for p in ['.', '!', '?'])
                            status = "✅" if ends_with_sentence else "⚠️"

                            print(f"{status} Chunk {len(chunks)}: {repr(content[:80])}")
                            if not ends_with_sentence and content.strip():
                                print(f"    ^ Does not end with sentence boundary")

                except json.JSONDecodeError:
                    pass

    print("-" * 60)
    print("Chunk Analysis:")

    sentence_chunks = 0
    partial_chunks = 0

    for i, chunk in enumerate(chunks):
        if any(chunk.rstrip().endswith(p) for p in ['.', '!', '?']):
            sentence_chunks += 1
        elif chunk.strip():
            partial_chunks += 1

    print(f"  Complete sentences: {sentence_chunks}")
    print(f"  Partial chunks: {partial_chunks}")
    print(f"  Total chunks: {len(chunks)}")

    print("-" * 60)
    full_text = ''.join(chunks)
    print(f"Full response ({len(full_text)} chars):")
    print(full_text[:500] + "..." if len(full_text) > 500 else full_text)

    print("-" * 60)
    if partial_chunks == 0:
        print("✅ SUCCESS: All chunks are complete sentences!")
    else:
        print(f"⚠️  WARNING: {partial_chunks} chunks are not complete sentences")

if __name__ == "__main__":
    test_sentence_chunking()