#!/usr/bin/env python3
"""
Test the ultrafast-redis endpoint with Jason Luna conversation
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8666"
API_KEY = "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"

# Test messages for Jason Luna conversation
messages = [
    "Hello, I'm Jason Luna. I'm interested in learning about consciousness technology.",
    "What are the key principles behind consciousness-aware AI systems?",
    "How might we integrate mindfulness practices into AI development?",
    "Can you explain the concept of emergent consciousness in complex systems?",
    "What role does embodiment play in consciousness?",
]

def test_ultrafast_redis():
    """Test the ultrafast-redis endpoint with multiple messages"""
    
    print("=== Testing Ultrafast Redis Endpoint ===\n")
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    total_times = []
    
    for i, message in enumerate(messages, 1):
        print(f"Message {i}: {message[:50]}...")
        
        # Prepare request
        data = {
            "message": message,
            "max_tokens": 1000
        }
        
        # Make request
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/ultrafast-redis",
            headers=headers,
            json=data
        )
        end_time = time.time()
        
        # Calculate times
        request_time = (end_time - start_time) * 1000
        
        if response.status_code == 200:
            result = response.json()
            api_time = result.get("api_time_ms", 0)
            response_time = result.get("response_time_ms", 0)
            history_length = result.get("history_length", 0)
            
            print(f"✓ Success!")
            print(f"  Response: {result['response'][:100]}...")
            print(f"  Total time: {request_time:.0f}ms")
            print(f"  API time: {api_time}ms")
            print(f"  Server time: {response_time}ms")
            print(f"  History length: {history_length} messages")
            
            total_times.append(response_time)
        else:
            print(f"✗ Failed with status {response.status_code}")
            print(f"  Error: {response.text}")
        
        print()
        
        # Small delay between messages
        if i < len(messages):
            time.sleep(0.5)
    
    # Summary statistics
    if total_times:
        print("\n=== Performance Summary ===")
        print(f"Messages sent: {len(messages)}")
        print(f"Successful: {len(total_times)}")
        print(f"Average response time: {sum(total_times)/len(total_times):.0f}ms")
        print(f"Min response time: {min(total_times)}ms")
        print(f"Max response time: {max(total_times)}ms")
        
        # Check if we met the <1s goal
        under_1s = sum(1 for t in total_times if t < 1000)
        print(f"Responses under 1s: {under_1s}/{len(total_times)} ({under_1s/len(total_times)*100:.0f}%)")
        
        under_500ms = sum(1 for t in total_times if t < 500)
        print(f"Responses under 500ms: {under_500ms}/{len(total_times)} ({under_500ms/len(total_times)*100:.0f}%)")

def test_conversation_persistence():
    """Test that conversation history persists across requests"""
    
    print("\n\n=== Testing Conversation Persistence ===\n")
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    # First message
    response1 = requests.post(
        f"{BASE_URL}/api/v1/chat/ultrafast-redis",
        headers=headers,
        json={"message": "My name is Jason Luna. Remember this."}
    )
    
    if response1.status_code == 200:
        print("✓ First message sent successfully")
        print(f"  Response: {response1.json()['response']}")
    
    # Wait a moment
    time.sleep(1)
    
    # Second message testing memory
    response2 = requests.post(
        f"{BASE_URL}/api/v1/chat/ultrafast-redis",
        headers=headers,
        json={"message": "What's my name?"}
    )
    
    if response2.status_code == 200:
        result = response2.json()
        print("\n✓ Second message sent successfully")
        print(f"  Response: {result['response']}")
        
        # Check if the AI remembers the name
        if "Jason Luna" in result['response'] or "Jason" in result['response']:
            print("  ✓ AI successfully remembered the name!")
        else:
            print("  ✗ AI did not remember the name")
        
        print(f"  History length: {result.get('history_length', 0)} messages")

if __name__ == "__main__":
    # Run tests
    test_ultrafast_redis()
    test_conversation_persistence()
    
    print("\n=== Test Complete ===")