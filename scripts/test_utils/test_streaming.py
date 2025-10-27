#!/usr/bin/env python3
"""Test streaming response with conversation ID in metadata"""

import json
import requests

def test_streaming():
    url = "http://localhost:8666/api/v0.3/chat"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
    }
    data = {
        "message": "Say hello in 5 words",
        "stream": True
    }

    print("Testing streaming response...")
    print("-" * 50)

    response = requests.post(url, headers=headers, json=data, stream=True)

    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        print(response.text)
        return

    conversation_id = None
    event_count = 0

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            print(f"Event {event_count}: {line_str}")

            # Check for metadata event with conversation_id
            if line_str.startswith("data: "):
                try:
                    data_str = line_str[6:]  # Remove "data: " prefix
                    if data_str.strip():
                        event_data = json.loads(data_str)
                        if event_data.get("type") == "metadata":
                            conversation_id = event_data.get("conversation_id")
                            print(f"✅ Found conversation_id in metadata: {conversation_id}")
                except json.JSONDecodeError:
                    pass

            event_count += 1
            if event_count >= 10:  # Show first 10 events
                break

    print("-" * 50)
    if conversation_id:
        print(f"✅ SUCCESS: Conversation ID delivered in metadata event: {conversation_id}")
    else:
        print("❌ FAILED: No conversation ID found in metadata event")

if __name__ == "__main__":
    test_streaming()