#!/usr/bin/env python3
"""Browser test for SSE functionality"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os

async def test_sse_in_browser():
    print("=== Browser SSE Test ===\n")
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        # Collect console logs
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        # Collect network activity (show all responses)
        page.on("response", lambda response: 
            print(f"[Network] {response.status} {response.url}")
        )
        
        try:
            # Test 1: Try to login first
            print("1. Testing login...")
            base_url = os.environ.get('BASE_URL', 'http://localhost:8080')
            login_url = f"{base_url}/login"
            print(f"   Login URL: {login_url}")
            
            response = await page.goto(login_url)
            print(f"   Response status: {response.status if response else 'None'}")
            
            # Try to login with test credentials
            email_input = await page.query_selector('input[name="email"], input[type="email"]')
            password_input = await page.query_selector('input[name="password"], input[type="password"]')
            
            if email_input and password_input:
                print("   Found login form, attempting login...")
                await email_input.fill("admin@aeonia.ai")
                await password_input.fill("TestPassword123!")
                
                # Find and click submit button
                submit_button = await page.query_selector('button[type="submit"], input[type="submit"]')
                if submit_button:
                    await submit_button.click()
                    await page.wait_for_load_state("networkidle")
                    
                    current_url = page.url
                    print(f"   After login attempt, URL: {current_url}")
                    
                    if "/chat" in current_url or "/dashboard" in current_url:
                        print("   ✅ Login successful!")
                        # Now test chat SSE
                        chat_url = f"{base_url}/chat"
                        await page.goto(chat_url)
                        await page.wait_for_load_state("networkidle")
                        print(f"   Chat page loaded: {page.url}")
                        
                        # Test chat input and SSE
                        chat_input = await page.query_selector('textarea, input[type="text"]')
                        if chat_input:
                            print("   Found chat input, testing message...")
                            await chat_input.fill("Test SSE message")
                            # Find send button  
                            send_button = await page.query_selector('button:has-text("Send"), button[type="submit"]')
                            if send_button:
                                await send_button.click()
                                await asyncio.sleep(3)  # Wait for SSE response
                                print("   Message sent, waiting for response...")
                    else:
                        print("   ❌ Login failed, redirected to:", current_url)
                else:
                    print("   ❌ Submit button not found")
            else:
                print("   ❌ Login form not found")
            
            # Test 2: Load debug page regardless
            print("\n2. Loading debug page...")
            debug_url = f"{base_url}/test/sse-debug"
            print(f"   URL: {debug_url}")
            
            response = await page.goto(debug_url)
            print(f"   Response status: {response.status if response else 'None'}")
            print(f"   Response URL: {response.url if response else 'None'}")
            
            await page.wait_for_load_state("networkidle")
            
            # Check if page loaded properly
            page_title = await page.title()
            print(f"   Page title: {page_title}")
            
            # Check if expected elements exist
            simple_status_exists = await page.query_selector("#simple-status") is not None
            simple_content_exists = await page.query_selector("#simple-content") is not None
            log_exists = await page.query_selector("#log") is not None
            
            print(f"   Elements found - simple-status: {simple_status_exists}, simple-content: {simple_content_exists}, log: {log_exists}")
            
            if not simple_status_exists:
                # Let's see what elements do exist
                all_divs = await page.query_selector_all("div")
                print(f"   Found {len(all_divs)} div elements")
                
                # Get some IDs that do exist
                ids = await page.evaluate("Array.from(document.querySelectorAll('[id]')).map(e => e.id)")
                print(f"   Found element IDs: {ids}")
            
            # Wait for SSE connections
            print("\n2. Waiting for SSE connections...")
            await asyncio.sleep(5)  # Give more time for SSE to connect
            
            # Check simple SSE test
            simple_status = await page.text_content("#simple-status", timeout=10000)
            simple_content = await page.text_content("#simple-content", timeout=10000)
            print(f"\nSimple SSE Test:")
            print(f"  Status: {simple_status}")
            print(f"  Content: {simple_content}")
            
            # Get debug log
            debug_log = await page.text_content("#log", timeout=5000)
            print(f"\nDebug Log:")
            for line in debug_log.split('\n')[-15:]:  # Last 15 lines
                if line.strip():
                    print(f"  {line}")
            
            # Check for HTMX SSE state
            htmx_state = await page.evaluate("""() => {
                return {
                    htmxVersion: typeof htmx !== 'undefined' ? htmx.version : null,
                    sseExtLoaded: typeof htmx !== 'undefined' && htmx.ext && htmx.ext.sse,
                    activeSSE: document.querySelectorAll('[sse-connect]').length,
                    errors: Array.from(document.querySelectorAll('#log')).map(e => e.textContent).join('').includes('Error')
                };
            }""")
            
            print(f"\nHTMX State:")
            print(f"  Version: {htmx_state['htmxVersion']}")
            print(f"  SSE Extension: {htmx_state['sseExtLoaded']}")
            print(f"  Active SSE Elements: {htmx_state['activeSSE']}")
            print(f"  Has Errors: {htmx_state['errors']}")
            
            # Print console logs
            if console_logs:
                print(f"\nBrowser Console:")
                for log in console_logs[-20:]:
                    print(f"  {log}")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            
            # Get page content and URL for debugging
            current_url = page.url
            page_title = await page.title() if page else "Unknown"
            print(f"Current URL: {current_url}")
            print(f"Page title: {page_title}")
            
            # Get page HTML for debugging
            try:
                page_content = await page.content()
                print(f"Page content length: {len(page_content)} chars")
                # Print first 500 chars of body
                body_start = page_content.find('<body')
                if body_start != -1:
                    body_content = page_content[body_start:body_start+500]
                    print(f"Body preview: {body_content}")
            except:
                print("Could not get page content")
            
            # Take screenshot with full path
            screenshot_path = "/screenshots/sse-test-error.png"
            try:
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"Screenshot saved as {screenshot_path}")
            except Exception as screenshot_error:
                print(f"Failed to save screenshot: {screenshot_error}")
                # Try alternative path
                try:
                    await page.screenshot(path="./sse-test-error.png", full_page=True)
                    print("Screenshot saved as ./sse-test-error.png")
                except:
                    print("Could not save screenshot anywhere")
        
        finally:
            await browser.close()
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_sse_in_browser())