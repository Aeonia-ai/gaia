#!/usr/bin/env python3
"""Test chunking for Unity client compatibility"""

import json
import requests

def test_unity_streaming():
    url = "http://localhost:8666/api/v0.3/chat"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
    }
    data = {
        "message": "Tell me a short story. The robot woke up. It blinked twice. Then it smiled.",
        "stream": True
    }

    print("Testing Unity-friendly sentence chunking...")
    print("-" * 50)

    response = requests.post(url, headers=headers, json=data, stream=True)

    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        print(response.text)
        return

    chunks = []
    conversation_id = None

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                try:
                    data_str = line_str[6:]
                    if data_str.strip():
                        event_data = json.loads(data_str)

                        if event_data.get("type") == "metadata":
                            conversation_id = event_data.get("conversation_id")
                            print(f"✅ Metadata: conversation_id={conversation_id}")

                        elif event_data.get("type") == "content":
                            content = event_data.get("content", "")
                            chunks.append(content)

                            # Check for word breaks
                            clean_content = content.strip()
                            starts_mid_word = clean_content and not content.startswith((' ', '\n')) and len(chunks) > 1
                            ends_mid_word = clean_content and not content.endswith((' ', '.', '!', '?', '\n'))

                            status = "✅" if not (starts_mid_word or ends_mid_word) else "⚠️"
                            print(f"{status} Chunk {len(chunks)}: {repr(content)}")

                            if starts_mid_word:
                                print(f"   ^ WARNING: Starts mid-word!")
                            if ends_mid_word and '.' not in content and '!' not in content and '?' not in content:
                                print(f"   ^ WARNING: May end mid-word!")

                except json.JSONDecodeError:
                    pass

    print("-" * 50)
    print("Chunk Analysis:")

    # Check for word splitting issues
    word_splits = 0
    for i in range(1, len(chunks)):
        prev = chunks[i-1].rstrip()
        curr = chunks[i].lstrip()

        # Check if previous chunk ended mid-word and current starts with continuation
        if prev and curr and not prev[-1] in '.!? \n' and not curr[0].isupper():
            word_splits += 1
            print(f"⚠️  Possible word split between chunks {i} and {i+1}")

    print("-" * 50)
    full_text = ''.join(chunks)
    print(f"Full response ({len(full_text)} chars):")
    print(full_text)

    print("-" * 50)
    if word_splits == 0:
        print("✅ SUCCESS: No word splits detected - Unity client compatible!")
    else:
        print(f"⚠️  WARNING: {word_splits} possible word splits detected")

    if conversation_id:
        print(f"✅ Conversation ID properly delivered: {conversation_id}")

if __name__ == "__main__":
    test_unity_streaming()