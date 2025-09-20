#!/usr/bin/env python3
"""
Cleanup Test Conversations

Removes test conversations and empty conversations created during development/testing.
This helps keep the development database clean.
"""

import asyncio
import aiohttp
import os
from datetime import datetime

async def cleanup_test_conversations():
    """Clean up test conversations via the web API"""

    print("🧹 CLEANING UP TEST CONVERSATIONS")
    print("=" * 50)

    # Login to get session
    login_url = "http://localhost:8080/login"
    chat_url = "http://localhost:8080/chat"

    async with aiohttp.ClientSession() as session:
        # Step 1: Login
        print("1. 🔐 Logging in...")
        login_data = {
            "email": "admin@aeonia.ai",
            "password": "auVwGUGt7GHAnv6nFxR8"
        }

        async with session.post(login_url, data=login_data) as resp:
            if resp.status != 200:
                print(f"❌ Login failed: {resp.status}")
                return

        # Follow redirect to chat page to establish session
        async with session.get(chat_url) as resp:
            if resp.status != 200:
                print(f"❌ Failed to access chat: {resp.status}")
                return

        print("✅ Login successful")

        # Step 2: Get conversation list
        print("\n2. 📋 Getting conversation list...")
        conversations_url = "http://localhost:8080/api/conversations"

        async with session.get(conversations_url) as resp:
            if resp.status != 200:
                print(f"❌ Failed to get conversations: {resp.status}")
                return

            # Parse HTML response to extract conversation IDs
            html_content = await resp.text()

            # Extract conversation links from HTML
            import re
            conversation_pattern = r'href="/chat/([a-f0-9-]+)"'
            conversation_ids = re.findall(conversation_pattern, html_content)

            print(f"Found {len(conversation_ids)} conversations")

        if not conversation_ids:
            print("✅ No conversations to clean up")
            return

        # Step 3: Identify test conversations to delete
        print("\n3. 🔍 Identifying test conversations...")

        test_patterns = [
            "test message",
            "investigating creation",
            "duplicate investigation",
            "hello, this is my first message",
            "this is a message after page reload",
            "and this is my second message",
            "conversation reload test",
            "test conversation for deletion"
        ]

        conversations_to_delete = []
        empty_conversations = []

        # For each conversation, check if it should be deleted
        for conv_id in conversation_ids:
            conv_url = f"http://localhost:8080/chat/{conv_id}"

            try:
                async with session.get(conv_url) as resp:
                    if resp.status == 200:
                        html = await resp.text()

                        # Check if conversation appears to be a test conversation
                        html_lower = html.lower()
                        is_test = any(pattern in html_lower for pattern in test_patterns)

                        # Check if conversation has any meaningful content
                        # Look for message content in the HTML
                        has_messages = 'id="messages"' in html and len(html.split('class="message-')) > 1

                        if is_test:
                            conversations_to_delete.append((conv_id, "test conversation"))
                        elif not has_messages:
                            empty_conversations.append((conv_id, "empty conversation"))

            except Exception as e:
                print(f"   ⚠️ Error checking conversation {conv_id}: {e}")

        total_to_delete = len(conversations_to_delete) + len(empty_conversations)
        print(f"   Test conversations to delete: {len(conversations_to_delete)}")
        print(f"   Empty conversations to delete: {len(empty_conversations)}")
        print(f"   Total to delete: {total_to_delete}")

        if total_to_delete == 0:
            print("✅ No conversations need cleanup")
            return

        # Step 4: Delete conversations
        print(f"\n4. 🗑️ Deleting {total_to_delete} conversations...")

        deleted_count = 0
        failed_count = 0

        all_to_delete = conversations_to_delete + empty_conversations

        for conv_id, reason in all_to_delete:
            delete_url = f"http://localhost:8080/api/conversations/{conv_id}"

            try:
                async with session.delete(delete_url) as resp:
                    if resp.status in [200, 204]:
                        deleted_count += 1
                        print(f"   ✅ Deleted {conv_id[:8]}... ({reason})")
                    else:
                        failed_count += 1
                        print(f"   ❌ Failed to delete {conv_id[:8]}... ({resp.status})")

            except Exception as e:
                failed_count += 1
                print(f"   ❌ Error deleting {conv_id[:8]}...: {e}")

        # Step 5: Verify cleanup
        print(f"\n5. ✅ Cleanup complete!")
        print(f"   Successfully deleted: {deleted_count}")
        print(f"   Failed to delete: {failed_count}")

        # Get final conversation count
        async with session.get(conversations_url) as resp:
            if resp.status == 200:
                html_content = await resp.text()
                remaining_conversations = re.findall(conversation_pattern, html_content)
                print(f"   Remaining conversations: {len(remaining_conversations)}")
            else:
                print("   Could not verify final count")

if __name__ == "__main__":
    asyncio.run(cleanup_test_conversations())