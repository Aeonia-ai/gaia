#!/usr/bin/env python3
"""
Robust memory test for ultrafast-redis-v2 endpoint
Tests that the AI truly remembers context, not just returning cached responses
"""
import requests
import json
import time
import random
import string

# Configuration
BASE_URL = "http://localhost:8666"
API_KEY = "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"
ENDPOINT = "ultrafast-redis-v3"  # Can be v2 or v3

def generate_random_data():
    """Generate random test data that can't be cached"""
    random_number = random.randint(1000, 9999)
    random_word = ''.join(random.choices(string.ascii_lowercase, k=6))
    random_color = random.choice(['red', 'blue', 'green', 'yellow', 'purple', 'orange'])
    return random_number, random_word, random_color

def test_robust_memory():
    """Test memory with random data that can't be cached"""
    
    print("=== Robust Memory Test ===\n")
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Generate random test data
    number, word, color = generate_random_data()
    
    print(f"Test data: number={number}, word={word}, color={color}\n")
    
    # Test 1: Introduce multiple pieces of information
    response1 = requests.post(
        f"{BASE_URL}/api/v1/chat/{ENDPOINT}",
        headers=headers,
        json={"message": f"Remember these three things: my favorite number is {number}, my secret word is '{word}', and my favorite color is {color}."}
    )
    
    if response1.status_code == 200:
        result1 = response1.json()
        print("✓ Message 1 sent")
        print(f"  Response: {result1['response'][:100]}...")
        print(f"  Time: {result1['response_time_ms']}ms\n")
    
    time.sleep(1)
    
    # Test 2: Ask about the number
    response2 = requests.post(
        f"{BASE_URL}/api/v1/chat/{ENDPOINT}",
        headers=headers,
        json={"message": "What's my favorite number?"}
    )
    
    if response2.status_code == 200:
        result2 = response2.json()
        print("✓ Message 2 sent (favorite number)")
        print(f"  Response: {result2['response']}")
        print(f"  Time: {result2['response_time_ms']}ms")
        
        if str(number) in result2['response']:
            print(f"  ✓ AI correctly remembered: {number}")
        else:
            print(f"  ✗ AI did not remember the number {number}")
    
    time.sleep(1)
    
    # Test 3: Ask about the word
    response3 = requests.post(
        f"{BASE_URL}/api/v1/chat/{ENDPOINT}",
        headers=headers,
        json={"message": "What was my secret word?"}
    )
    
    if response3.status_code == 200:
        result3 = response3.json()
        print("\n✓ Message 3 sent (secret word)")
        print(f"  Response: {result3['response']}")
        print(f"  Time: {result3['response_time_ms']}ms")
        
        if word in result3['response']:
            print(f"  ✓ AI correctly remembered: {word}")
        else:
            print(f"  ✗ AI did not remember the word {word}")
    
    time.sleep(1)
    
    # Test 4: Ask about the color
    response4 = requests.post(
        f"{BASE_URL}/api/v1/chat/{ENDPOINT}",
        headers=headers,
        json={"message": "What color did I say I liked?"}
    )
    
    if response4.status_code == 200:
        result4 = response4.json()
        print("\n✓ Message 4 sent (favorite color)")
        print(f"  Response: {result4['response']}")
        print(f"  Time: {result4['response_time_ms']}ms")
        
        if color in result4['response']:
            print(f"  ✓ AI correctly remembered: {color}")
        else:
            print(f"  ✗ AI did not remember the color {color}")
    
    # Test 5: Complex recall - ask for all three
    response5 = requests.post(
        f"{BASE_URL}/api/v1/chat/{ENDPOINT}",
        headers=headers,
        json={"message": "Can you list all three things I asked you to remember?"}
    )
    
    if response5.status_code == 200:
        result5 = response5.json()
        print("\n✓ Message 5 sent (all three items)")
        print(f"  Response: {result5['response']}")
        print(f"  Time: {result5['response_time_ms']}ms")
        
        correct_count = 0
        if str(number) in result5['response']:
            correct_count += 1
            print(f"  ✓ Remembered number: {number}")
        if word in result5['response']:
            correct_count += 1
            print(f"  ✓ Remembered word: {word}")
        if color in result5['response']:
            correct_count += 1
            print(f"  ✓ Remembered color: {color}")
        
        print(f"  Total recall: {correct_count}/3 items")

def test_conversation_coherence():
    """Test that the AI maintains conversation coherence"""
    
    print("\n\n=== Conversation Coherence Test ===\n")
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Generate a random topic
    topics = ["quantum computing", "underwater cities", "time travel", "telepathy", "nanotechnology"]
    topic = random.choice(topics)
    
    print(f"Random topic: {topic}\n")
    
    # Start a conversation about the topic
    response1 = requests.post(
        f"{BASE_URL}/api/v1/chat/{ENDPOINT}",
        headers=headers,
        json={"message": f"Let's talk about {topic}. What's the most interesting aspect of it?"}
    )
    
    if response1.status_code == 200:
        result1 = response1.json()
        print("✓ Started conversation")
        print(f"  Response: {result1['response'][:150]}...")
        print(f"  Time: {result1['response_time_ms']}ms\n")
    
    time.sleep(1)
    
    # Follow up with a question that requires context
    response2 = requests.post(
        f"{BASE_URL}/api/v1/chat/{ENDPOINT}",
        headers=headers,
        json={"message": "Can you elaborate on that last point?"}
    )
    
    if response2.status_code == 200:
        result2 = response2.json()
        print("✓ Follow-up question")
        print(f"  Response: {result2['response'][:150]}...")
        print(f"  Time: {result2['response_time_ms']}ms")
        
        # Check if response is relevant to the topic
        if topic.replace(" ", "").lower() in result2['response'].lower() or "that" in result2['response'].lower() or "point" in result2['response'].lower():
            print(f"  ✓ Response maintains context about {topic}")
        else:
            print(f"  ? Response coherence unclear")

def test_memory_limits():
    """Test the 3-message context window"""
    
    print("\n\n=== Context Window Test (3 messages) ===\n")
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Send 4 messages with different facts
    facts = [
        ("My cat's name is Whiskers", "cat", "Whiskers"),
        ("My dog's name is Rover", "dog", "Rover"),
        ("My bird's name is Tweety", "bird", "Tweety"),
        ("My fish's name is Nemo", "fish", "Nemo")
    ]
    
    for i, (message, _, _) in enumerate(facts):
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/{ENDPOINT}",
            headers=headers,
            json={"message": message}
        )
        if response.status_code == 200:
            print(f"✓ Message {i+1}: {message}")
            print(f"  Time: {response.json()['response_time_ms']}ms")
        time.sleep(0.5)
    
    print("\nTesting recall (should only remember last 3):")
    
    # Test recall of each pet
    for _, animal, name in facts:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/{ENDPOINT}",
            headers=headers,
            json={"message": f"What's my {animal}'s name?"}
        )
        if response.status_code == 200:
            result = response.json()
            print(f"\n  Asked about {animal}:")
            print(f"  Response: {result['response']}")
            
            if name in result['response']:
                print(f"  ✓ Remembered {name}")
            else:
                print(f"  ✗ Forgot {name} (expected if >3 messages ago)")

if __name__ == "__main__":
    # Clear history first
    print("Clearing chat history...")
    requests.delete(f"{BASE_URL}/api/v1/chat/history", headers={"X-API-Key": API_KEY})
    time.sleep(1)
    
    # Run tests
    test_robust_memory()
    test_conversation_coherence()
    test_memory_limits()
    
    print("\n=== All Tests Complete ===")