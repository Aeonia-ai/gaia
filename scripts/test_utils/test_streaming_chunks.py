#!/usr/bin/env python3
"""Test that streaming chunks are properly using sentence boundaries"""

import json
import requests
import sys

def test_streaming_chunks():
    url = "http://localhost:8666/api/v0.3/chat"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
    }

    # Test with a message that should produce multiple sentences
    data = {
        "message": "Write 3 sentences about cats. Each sentence should be complete and separated.",
        "stream": True
    }

    print("Testing sentence boundary chunking...")
    print("-" * 60)

    response = requests.post(url, headers=headers, json=data, stream=True)

    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        return False

    chunks = []
    all_good = True

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                try:
                    data_str = line_str[6:]
                    if data_str.strip() and data_str != "[DONE]":
                        event_data = json.loads(data_str)

                        if event_data.get("type") == "content":
                            content = event_data.get("content", "")
                            if content:
                                chunks.append(content)

                                # Check chunk characteristics
                                print(f"Chunk {len(chunks)}: {repr(content)}")

                                # Check for bad splits (mid-word)
                                if len(content) > 0:
                                    # Check if starts with lowercase (might be mid-word)
                                    if content[0].islower() and len(chunks) > 1:
                                        prev = chunks[-2] if len(chunks) > 1 else ""
                                        if prev and not prev.rstrip().endswith(('.', '!', '?', '\n')):
                                            print(f"  ⚠️ WARNING: Possible mid-word split")
                                            all_good = False

                                    # Check if chunk is too short (less than a word)
                                    if len(content.strip()) < 4 and content.strip() not in ['.', '!', '?', ',', ';', ':']:
                                        print(f"  ⚠️ WARNING: Very short chunk, might be fragment")
                                        all_good = False

                except json.JSONDecodeError:
                    pass

    print("-" * 60)
    full_text = ''.join(chunks)
    print(f"Full response:\n{full_text}")
    print("-" * 60)

    # Analysis
    print("Chunk Analysis:")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Average chunk size: {sum(len(c) for c in chunks) / len(chunks):.1f} chars")

    # Count sentences
    sentences = [s.strip() for s in full_text.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    print(f"  Sentences detected: {len(sentences)}")

    if all_good:
        print("✅ SUCCESS: Chunks appear to respect word/sentence boundaries!")
        return True
    else:
        print("❌ FAILURE: Some chunks may have boundary issues")
        return False

if __name__ == "__main__":
    success = test_streaming_chunks()
    sys.exit(0 if success else 1)