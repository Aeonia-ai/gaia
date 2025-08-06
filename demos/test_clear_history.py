#!/usr/bin/env python3
"""
Test that clearing history properly clears Redis
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8666"
API_KEY = "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("=== Testing Clear History with Redis ===\n")

# Step 1: Send a message with unique data
unique_number = 12345
print(f"1. Sending message with unique number: {unique_number}")
response = requests.post(
    f"{BASE_URL}/api/v1/chat/ultrafast-redis-v3",
    headers=headers,
    json={"message": f"Remember this number: {unique_number}"}
)
if response.status_code == 200:
    print(f"   ✓ Response: {response.json()['response'][:50]}...")
    print(f"   Time: {response.json()['response_time_ms']}ms\n")

time.sleep(1)

# Step 2: Verify memory works
print("2. Testing memory before clear")
response = requests.post(
    f"{BASE_URL}/api/v1/chat/ultrafast-redis-v3",
    headers=headers,
    json={"message": "What number did I ask you to remember?"}
)
if response.status_code == 200:
    result = response.json()
    print(f"   Response: {result['response']}")
    if str(unique_number) in result['response']:
        print(f"   ✓ AI remembers {unique_number}\n")
    else:
        print(f"   ✗ AI does not remember {unique_number}\n")

# Step 3: Clear history
print("3. Clearing history via API")
response = requests.delete(
    f"{BASE_URL}/api/v1/chat/history",
    headers={"X-API-Key": API_KEY}
)
if response.status_code == 200:
    result = response.json()
    print(f"   ✓ History cleared: {result}")
    print(f"   Cleared: {result.get('cleared', [])}\n")

time.sleep(1)

# Step 4: Test memory after clear
print("4. Testing memory after clear")
response = requests.post(
    f"{BASE_URL}/api/v1/chat/ultrafast-redis-v3",
    headers=headers,
    json={"message": "What number did I ask you to remember?"}
)
if response.status_code == 200:
    result = response.json()
    print(f"   Response: {result['response']}")
    if str(unique_number) not in result['response'] and ("don't" in result['response'].lower() or "no" in result['response'].lower() or "haven't" in result['response'].lower()):
        print(f"   ✓ AI correctly forgot the number (Redis was cleared)")
    else:
        print(f"   ✗ AI still remembers {unique_number} (Redis not cleared?)")

# Step 5: Send new data to verify fresh start
print("\n5. Sending new data after clear")
new_number = 67890
response = requests.post(
    f"{BASE_URL}/api/v1/chat/ultrafast-redis-v3",
    headers=headers,
    json={"message": f"My new favorite number is {new_number}"}
)
if response.status_code == 200:
    print(f"   ✓ Response: {response.json()['response'][:50]}...")

time.sleep(0.5)

# Step 6: Verify new memory works
print("\n6. Verifying new memory")
response = requests.post(
    f"{BASE_URL}/api/v1/chat/ultrafast-redis-v3",
    headers=headers,
    json={"message": "What's my favorite number?"}
)
if response.status_code == 200:
    result = response.json()
    print(f"   Response: {result['response']}")
    if str(new_number) in result['response'] and str(unique_number) not in result['response']:
        print(f"   ✓ Perfect! AI remembers new number {new_number} but not old {unique_number}")
    else:
        print(f"   ? Unexpected memory state")

print("\n=== Test Complete ===")