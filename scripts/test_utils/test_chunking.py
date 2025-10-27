#!/usr/bin/env python3
"""Test StreamBuffer v3 sentence chunking"""

import json
import requests
import time

def test_chunking():
    url = "http://localhost:8666/api/v0.3/chat"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
    }
    data = {
        "message": "Tell me three facts about robots. Each fact should be a complete sentence.",
        "stream": True
    }

    print("Testing StreamBuffer v3 sentence chunking...")
    print("-" * 50)

    response = requests.post(url, headers=headers, json=data, stream=True)

    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        print(response.text)
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
                        if event_data.get("type") == "content":
                            content = event_data.get("content", "")
                            chunks.append(content)
                            print(f"Chunk {len(chunks)}: {repr(content)}")
                except json.JSONDecodeError:
                    pass

    print("-" * 50)
    print("Analysis of chunks:")
    for i, chunk in enumerate(chunks):
        # Check if chunk contains sentence boundaries
        has_period = '.' in chunk
        has_exclamation = '!' in chunk
        has_question = '?' in chunk
        has_json_directive = '{' in chunk and '}' in chunk

        boundary_type = []
        if has_period: boundary_type.append("period")
        if has_exclamation: boundary_type.append("exclamation")
        if has_question: boundary_type.append("question")
        if has_json_directive: boundary_type.append("JSON directive")

        print(f"  Chunk {i+1}: {len(chunk)} chars, boundaries: {boundary_type or ['none']}")

    print("-" * 50)
    full_text = ''.join(chunks)
    print(f"Full response ({len(full_text)} chars):")
    print(full_text)

if __name__ == "__main__":
    test_chunking()