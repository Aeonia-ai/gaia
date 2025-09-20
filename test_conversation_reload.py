#!/usr/bin/env python3
"""
Conversation Reload Test

Tests what happens when you reload the page while a conversation is open.
This is a critical UX test that could reveal state persistence issues.
"""

import asyncio
from playwright.async_api import async_playwright

async def test_conversation_reload():
    """Test reloading page during active conversation"""

    print("🔄 CONVERSATION RELOAD TEST")
    print("=" * 50)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,
        slow_mo=2000  # Slow so you can see what's happening
    )

    try:
        page = await browser.new_page()

        # Step 1: Login
        print("\n1. 🔐 Logging in...")
        await page.goto("http://localhost:8080/login")
        await page.fill('input[placeholder="Email address"]', "admin@aeonia.ai")
        await page.fill('input[placeholder="Password"]', "auVwGUGt7GHAnv6nFxR8")
        await page.click('button:has-text("Sign In")')
        await page.wait_for_url("**/chat")
        print("   ✅ Login successful")

        # Step 2: Create a new conversation with some messages
        print("\n2. 💬 Creating conversation with messages...")
        await page.click('button:has-text("New Chat")')

        # Send first message
        await page.fill('input[id="chat-message-input"]', "Hello, this is my first message in this conversation")
        await page.click('button:has-text("Send")')
        await page.wait_for_timeout(3000)  # Wait for response

        # Send second message
        await page.fill('input[id="chat-message-input"]', "And this is my second message")
        await page.click('button:has-text("Send")')
        await page.wait_for_timeout(3000)  # Wait for response

        print("   ✅ Conversation created with messages")

        # Step 3: Capture current state
        print("\n3. 📊 Capturing current state...")
        current_url = page.url
        print(f"   Current URL: {current_url}")

        # Count messages before reload
        user_messages = await page.query_selector_all('[class*="user"], .message-user')
        ai_messages = await page.query_selector_all('[class*="assistant"], .message-ai, .bg-slate-700')

        before_user_count = len(user_messages)
        before_ai_count = len(ai_messages)

        print(f"   Messages before reload - User: {before_user_count}, AI: {before_ai_count}")

        # Take screenshot before reload
        await page.screenshot(path="conversation_before_reload.png", full_page=True)
        print("   📸 Screenshot before reload: conversation_before_reload.png")

        # Step 4: Reload the page
        print("\n4. 🔄 Reloading page...")
        await page.reload()
        await page.wait_for_timeout(3000)  # Wait for page to fully load

        # Step 5: Check state after reload
        print("\n5. 🔍 Checking state after reload...")

        new_url = page.url
        print(f"   URL after reload: {new_url}")
        print(f"   URL preserved: {current_url == new_url}")

        # Count messages after reload
        user_messages_after = await page.query_selector_all('[class*="user"], .message-user')
        ai_messages_after = await page.query_selector_all('[class*="assistant"], .message-ai, .bg-slate-700')

        after_user_count = len(user_messages_after)
        after_ai_count = len(ai_messages_after)

        print(f"   Messages after reload - User: {after_user_count}, AI: {after_ai_count}")

        # Check if messages are preserved
        messages_preserved = (before_user_count == after_user_count and before_ai_count == after_ai_count)
        print(f"   Messages preserved: {messages_preserved}")

        # Take screenshot after reload
        await page.screenshot(path="conversation_after_reload.png", full_page=True)
        print("   📸 Screenshot after reload: conversation_after_reload.png")

        # Step 6: Test if we can continue the conversation
        print("\n6. 💬 Testing if conversation can continue...")
        try:
            await page.fill('input[id="chat-message-input"]', "This is a message after page reload")
            await page.click('button:has-text("Send")')
            await page.wait_for_timeout(2000)

            # Check if message was sent
            final_user_messages = await page.query_selector_all('[class*="user"], .message-user')
            if len(final_user_messages) > after_user_count:
                print("   ✅ Can continue conversation after reload")
            else:
                print("   ❌ Cannot continue conversation after reload")

        except Exception as e:
            print(f"   ❌ Error continuing conversation: {e}")

        # Step 7: Check conversation list state
        print("\n7. 📋 Checking conversation list...")
        conversation_items = await page.query_selector_all('#conversation-list > div')
        print(f"   Conversation list items: {len(conversation_items)}")

        # Check if current conversation is highlighted/selected
        try:
            active_conversation = await page.query_selector('[class*="active"], [class*="selected"]')
            if active_conversation:
                print("   ✅ Active conversation is highlighted in list")
            else:
                print("   ⚠️ No conversation appears to be marked as active")
        except Exception:
            print("   ⚠️ Could not determine active conversation state")

        # Step 8: Manual inspection
        print("\n8. 👀 Manual inspection time...")
        print("   Compare before/after screenshots")
        print("   Check if conversation state looks correct")
        print("   Try using the interface manually")
        print("   Waiting 20 seconds for exploration...")
        await page.wait_for_timeout(20000)

        # Step 9: Summary
        print("\n🎯 RELOAD TEST SUMMARY:")
        print(f"   URL Preservation: {'✅' if current_url == new_url else '❌'}")
        print(f"   Message Preservation: {'✅' if messages_preserved else '❌'}")
        print(f"   Conversation Continuity: {'✅' if len(final_user_messages) > after_user_count else '❌'}")

    except Exception as e:
        print(f"\n💥 Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser.close()
        await playwright.stop()

        # Clean up test conversations created during testing
        print("\n🧹 Cleaning up test conversations...")
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from tests.fixtures.conversation_cleanup import cleanup_test_conversations
            cleaned_count = cleanup_test_conversations()
            if cleaned_count > 0:
                print(f"   ✅ Cleaned up {cleaned_count} test conversations")
            else:
                print("   ℹ️ No test conversations to clean up")
        except Exception as e:
            print(f"   ⚠️ Error during cleanup: {e}")

    print("\n🔄 CONVERSATION RELOAD TEST COMPLETE")

if __name__ == "__main__":
    asyncio.run(test_conversation_reload())