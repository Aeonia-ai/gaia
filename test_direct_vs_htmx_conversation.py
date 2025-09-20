#!/usr/bin/env python3
"""
Test Direct vs HTMX Conversation Loading

Compare what happens when accessing conversation route directly vs via HTMX
"""

import asyncio
from playwright.async_api import async_playwright

async def test_direct_vs_htmx():
    """Test direct URL vs HTMX conversation access"""

    print("🔍 DIRECT vs HTMX CONVERSATION ACCESS TEST")
    print("=" * 60)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False, slow_mo=1000)

    try:
        page = await browser.new_page()

        # Enable request/response logging
        requests_log = []

        def log_request(request):
            if '/chat/' in request.url:
                requests_log.append({
                    'type': 'request',
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers)
                })
                print(f"🔄 REQUEST: {request.method} {request.url}")
                if 'hx-request' in request.headers:
                    print(f"   📡 HTMX Request: {request.headers['hx-request']}")

        def log_response(response):
            if '/chat/' in response.url:
                print(f"📨 RESPONSE: {response.status} {response.url}")

        page.on("request", log_request)
        page.on("response", log_response)

        # Step 1: Login first
        print("\n1. 🔐 Logging in...")
        await page.goto("http://localhost:8080/login")
        await page.fill('input[placeholder="Email address"]', "admin@aeonia.ai")
        await page.fill('input[placeholder="Password"]', "auVwGUGt7GHAnv6nFxR8")
        await page.click('button:has-text("Sign In")')
        await page.wait_for_url("**/chat")
        print("   ✅ Login successful")

        # Step 2: Get a conversation ID from the list
        conversation_links = await page.query_selector_all('#conversation-list a[href*="/chat/"]')
        if not conversation_links:
            print("   ❌ No conversations found")
            return

        first_link = conversation_links[0]
        href = await first_link.get_attribute('href')
        conversation_id = href.split('/chat/')[-1]
        full_url = f"http://localhost:8080{href}"

        print(f"\n2. 🎯 Testing conversation: {conversation_id}")
        print(f"   URL: {full_url}")

        # Step 3: Test HTMX click (how it normally works)
        print("\n3. 📡 Testing HTMX click (normal navigation)...")
        requests_log.clear()

        await first_link.click()
        await page.wait_for_timeout(2000)

        htmx_user_messages = await page.query_selector_all('[class*="user"], .message-user')
        htmx_ai_messages = await page.query_selector_all('[class*="assistant"], .message-ai, .bg-slate-700')

        print(f"   Messages via HTMX - User: {len(htmx_user_messages)}, AI: {len(htmx_ai_messages)}")
        print(f"   Requests made: {len([r for r in requests_log if r['type'] == 'request'])}")

        # Step 4: Test direct URL navigation
        print("\n4. 🌐 Testing direct URL navigation...")
        requests_log.clear()

        await page.goto(full_url)
        await page.wait_for_timeout(3000)

        direct_user_messages = await page.query_selector_all('[class*="user"], .message-user')
        direct_ai_messages = await page.query_selector_all('[class*="assistant"], .message-ai, .bg-slate-700')

        print(f"   Messages via direct URL - User: {len(direct_user_messages)}, AI: {len(direct_ai_messages)}")
        print(f"   Requests made: {len([r for r in requests_log if r['type'] == 'request'])}")

        # Step 5: Compare the HTML content
        print("\n5. 📄 Comparing page content...")

        # Get page title and check if we're on the right page
        title = await page.title()
        url = page.url
        print(f"   Page title: {title}")
        print(f"   Current URL: {url}")

        # Check for main content area
        main_content = await page.query_selector('#main-content')
        if main_content:
            content_html = await main_content.inner_html()
            has_messages_container = 'id="messages"' in content_html
            print(f"   Has messages container: {has_messages_container}")
            print(f"   Content length: {len(content_html)} characters")
        else:
            print("   ❌ No #main-content found")

        # Step 6: Check conversation list state
        print("\n6. 📋 Checking conversation list...")
        conv_list = await page.query_selector('#conversation-list')
        if conv_list:
            list_html = await conv_list.inner_html()
            has_conversations = '/chat/' in list_html
            print(f"   Conversation list has items: {has_conversations}")
        else:
            print("   ❌ No conversation list found")

        # Step 7: Take screenshots for comparison
        await page.screenshot(path="direct_vs_htmx_comparison.png", full_page=True)
        print("\n7. 📸 Screenshot saved: direct_vs_htmx_comparison.png")

        # Summary
        print(f"\n🎯 COMPARISON SUMMARY:")
        print(f"   HTMX Messages: User={len(htmx_user_messages)}, AI={len(htmx_ai_messages)}")
        print(f"   Direct Messages: User={len(direct_user_messages)}, AI={len(direct_ai_messages)}")

        messages_match = (len(htmx_user_messages) == len(direct_user_messages) and
                         len(htmx_ai_messages) == len(direct_ai_messages))
        print(f"   Messages match: {'✅' if messages_match else '❌'}")

        await page.wait_for_timeout(10000)  # Manual inspection time

    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_direct_vs_htmx())