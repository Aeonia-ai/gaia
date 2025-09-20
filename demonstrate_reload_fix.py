#!/usr/bin/env python3
"""
Demonstrate Conversation Reload Fix

Visual demonstration that conversation reload is working properly.
Shows before/after state and proves messages persist across reload.
"""

import asyncio
from playwright.async_api import async_playwright

async def demonstrate_reload_fix():
    """Demonstrate that conversation reload is working"""

    print("🎬 DEMONSTRATING CONVERSATION RELOAD FIX")
    print("=" * 50)

    playwright = await async_playwright().start()
    # Run with visible browser so you can see it working
    browser = await playwright.chromium.launch(headless=False, slow_mo=2000)

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

        # Step 2: Navigate to a conversation
        print("\n2. 📱 Navigating to a conversation...")
        conversation_links = await page.query_selector_all('#conversation-list a[href*="/chat/"]')

        if conversation_links:
            first_conversation = conversation_links[0]
            href = await first_conversation.get_attribute('href')
            conversation_id = href.split('/chat/')[-1]

            print(f"   Clicking conversation: {conversation_id[:8]}...")
            await first_conversation.click()
            await page.wait_for_timeout(3000)

            # Check current state
            current_url = page.url
            messages_before = await page.query_selector_all('[class*="user"], [class*="assistant"], .message-user, .message-ai, .bg-slate-700')

            print(f"   Current URL: {current_url}")
            print(f"   Messages loaded: {len(messages_before)}")

            # Take screenshot before reload
            await page.screenshot(path="before_reload.png", full_page=True)
            print("   📸 Screenshot taken: before_reload.png")

            print(f"\n   🔍 You can see the conversation is loaded with {len(messages_before)} messages")
            print(f"   🌐 URL is: {current_url}")

            # Step 3: Reload the page
            print(f"\n3. 🔄 Reloading the page...")
            print("   Watch the browser - it will reload but stay on the same conversation!")

            await page.reload()
            await page.wait_for_timeout(4000)  # Give time for everything to load

            # Check state after reload
            url_after_reload = page.url
            messages_after = await page.query_selector_all('[class*="user"], [class*="assistant"], .message-user, .message-ai, .bg-slate-700')

            print(f"   URL after reload: {url_after_reload}")
            print(f"   Messages after reload: {len(messages_after)}")

            # Take screenshot after reload
            await page.screenshot(path="after_reload.png", full_page=True)
            print("   📸 Screenshot taken: after_reload.png")

            # Step 4: Verify the fix
            print(f"\n4. ✅ VERIFICATION:")

            url_preserved = current_url == url_after_reload
            messages_preserved = len(messages_before) == len(messages_after)

            print(f"   URL preserved: {'✅ YES' if url_preserved else '❌ NO'}")
            print(f"   Messages preserved: {'✅ YES' if messages_preserved else '❌ NO'}")

            if url_preserved and messages_preserved:
                print(f"\n   🎉 CONVERSATION RELOAD IS WORKING PERFECTLY!")
                print(f"   The conversation persists across page reloads.")
                print(f"   This means users can:")
                print(f"   • Refresh the page without losing their place")
                print(f"   • Share conversation URLs that work properly")
                print(f"   • Bookmark conversations and return to them")
            else:
                print(f"\n   ❌ There's still an issue with reload")

            # Step 5: Test message sending after reload
            print(f"\n5. 💬 Testing message sending after reload...")

            # Try to send a message to prove conversation is fully functional
            message_input = await page.query_selector('input[id="chat-message-input"]')
            if message_input:
                test_message = "This message sent after page reload - testing functionality"
                await page.fill('input[id="chat-message-input"]', test_message)
                await page.click('button:has-text("Send")')
                await page.wait_for_timeout(3000)

                # Check if message was sent
                final_messages = await page.query_selector_all('[class*="user"], [class*="assistant"], .message-user, .message-ai, .bg-slate-700')

                if len(final_messages) > len(messages_after):
                    print(f"   ✅ Message sent successfully after reload!")
                    print(f"   Message count: {len(messages_after)} → {len(final_messages)}")
                else:
                    print(f"   ⚠️ Message sending might have issues")
            else:
                print(f"   ⚠️ Could not find message input")

            print(f"\n   👀 Browser will stay open for 15 seconds so you can see the working conversation")
            await page.wait_for_timeout(15000)

        else:
            print("   ❌ No conversations found to test with")

    except Exception as e:
        print(f"\n💥 Error during demonstration: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser.close()
        await playwright.stop()

    print(f"\n🎬 DEMONSTRATION COMPLETE")
    print(f"Screenshots saved:")
    print(f"  • before_reload.png - Conversation before reload")
    print(f"  • after_reload.png - Same conversation after reload")

if __name__ == "__main__":
    asyncio.run(demonstrate_reload_fix())