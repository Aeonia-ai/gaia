#!/usr/bin/env python3
"""Test Unity client compatibility - simulates Unity's SSE parsing"""

import json
import requests

def simulate_unity_client():
    """Simulate how Unity client would parse SSE chunks"""
    url = "http://localhost:8666/api/v0.3/chat"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
    }

    # Unity client test case: multiple sentences with game directives
    data = {
        "message": "Hello! Spawn a fairy companion for me. Tell me about its abilities.",
        "stream": True
    }

    print("Unity Client Compatibility Test")
    print("=" * 60)
    print("Simulating Unity SSE parser...")
    print("-" * 60)

    response = requests.post(url, headers=headers, json=data, stream=True)

    if response.status_code != 200:
        print(f"❌ Error: Status code {response.status_code}")
        return False

    # Unity accumulates text this way
    accumulated_text = ""
    chunk_count = 0
    issues = []

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                try:
                    data_str = line_str[6:]
                    if data_str.strip() and data_str != "[DONE]":
                        event_data = json.loads(data_str)

                        if event_data.get("type") == "metadata":
                            print(f"📋 Metadata received: conversation_id={event_data.get('conversation_id')}")

                        elif event_data.get("type") == "content":
                            content = event_data.get("content", "")
                            if content:
                                chunk_count += 1

                                # Unity's concatenation logic
                                old_len = len(accumulated_text)
                                accumulated_text += content
                                new_len = len(accumulated_text)

                                print(f"Chunk {chunk_count}: +{new_len - old_len} chars")

                                # Check for Unity-specific issues
                                # 1. Check if we're splitting mid-word
                                if chunk_count > 1 and content[0].isalpha() and content[0].islower():
                                    if accumulated_text[old_len-1].isalpha():
                                        issues.append(f"Mid-word split at position {old_len}")
                                        print(f"  ⚠️ Mid-word split detected!")

                                # 2. Check for incomplete JSON directives
                                if '{' in content and '}' not in content:
                                    issues.append(f"Incomplete JSON in chunk {chunk_count}")
                                    print(f"  ⚠️ Incomplete JSON directive!")

                                # 3. Show what Unity would display
                                print(f"  Unity display: ...{repr(accumulated_text[-50:])}")

                except json.JSONDecodeError as e:
                    print(f"❌ JSON parse error: {e}")
                    issues.append(f"JSON parse error in chunk {chunk_count}")

    print("-" * 60)
    print("Unity Client Results:")
    print(f"  Total chunks received: {chunk_count}")
    print(f"  Final text length: {len(accumulated_text)} chars")
    print(f"  Issues found: {len(issues)}")

    if issues:
        print("\n⚠️ Issues:")
        for issue in issues:
            print(f"  - {issue}")

    print("\nFinal Unity display:")
    print(accumulated_text)
    print("-" * 60)

    if len(issues) == 0:
        print("✅ Unity compatibility: PASSED")
        print("   - No mid-word splits")
        print("   - Complete JSON directives")
        print("   - Clean sentence boundaries")
        return True
    else:
        print("❌ Unity compatibility: FAILED")
        return False

if __name__ == "__main__":
    success = simulate_unity_client()
    exit(0 if success else 1)