#!/usr/bin/env python3
"""
Test script to verify database persistence is working
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.web.utils.database_conversation_store import database_conversation_store

def test_persistence():
    print("🧪 Testing Database Persistence...")
    
    # Test user creation and conversation creation
    print("\n1. Creating test conversation...")
    user_id = "dev-user-id"
    conv = database_conversation_store.create_conversation(user_id, "Test Persistence Chat")
    print(f"✅ Created conversation: {conv['id']}")
    
    # Add some messages
    print("\n2. Adding test messages...")
    msg1 = database_conversation_store.add_message(conv['id'], "user", "Hello, can you remember this message?")
    print(f"✅ Added user message: {msg1['id']}")
    
    msg2 = database_conversation_store.add_message(conv['id'], "assistant", "Yes, I can remember this message in the database!")
    print(f"✅ Added assistant message: {msg2['id']}")
    
    # Update conversation
    print("\n3. Updating conversation...")
    database_conversation_store.update_conversation(user_id, conv['id'], 
                                                  title="Persistence Test Complete",
                                                  preview="Testing database persistence")
    print("✅ Updated conversation title and preview")
    
    # Retrieve conversations
    print("\n4. Retrieving conversations...")
    conversations = database_conversation_store.get_conversations(user_id)
    print(f"✅ Found {len(conversations)} conversations")
    for c in conversations:
        print(f"   - {c['title']} (ID: {c['id']})")
    
    # Retrieve messages
    print("\n5. Retrieving messages...")
    messages = database_conversation_store.get_messages(conv['id'])
    print(f"✅ Found {len(messages)} messages")
    for m in messages:
        print(f"   - {m['role']}: {m['content'][:50]}...")
    
    # Test conversation stats
    print("\n6. Getting conversation stats...")
    stats = database_conversation_store.get_conversation_stats(user_id)
    print(f"✅ Stats: {stats['total_conversations']} conversations, {stats['total_messages']} messages")
    
    print("\n🎉 Database persistence test completed successfully!")
    return conv['id']

if __name__ == "__main__":
    conversation_id = test_persistence()
    print(f"\n📋 Test conversation ID: {conversation_id}")
    print("💡 You can now restart the web service and verify this conversation persists!")