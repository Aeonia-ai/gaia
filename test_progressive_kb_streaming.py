#!/usr/bin/env python3
"""
Test Progressive KB Streaming

Tests the progressive KB response system where:
1. User sends a KB query
2. System immediately responds "🤖 Coordinating technical, knowledge_management agents..."
3. System updates with "📊 Analyzing knowledge base content..."
4. System streams the actual KB results progressively
5. System completes with metadata and timing info

This demonstrates the sophisticated streaming pattern for KB operations.
"""

import asyncio
from playwright.async_api import async_playwright

async def test_progressive_kb_streaming():
    """Test progressive KB streaming functionality"""

    print("🎬 TESTING PROGRESSIVE KB STREAMING")
    print("=" * 50)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False, slow_mo=1000)

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

        # Step 2: Start a new conversation to test KB streaming
        print("\n2. 🆕 Starting new conversation...")
        await page.click('button:has-text("New Chat")')
        await page.wait_for_timeout(1000)

        # Step 3: Send a KB query that should trigger progressive streaming
        print("\n3. 💬 Sending KB query to trigger progressive streaming...")

        # Query that should invoke KB interpretation
        kb_query = "What are the key architectural patterns used in the GAIA platform? Please analyze the knowledge base."

        await page.fill('input[id="chat-message-input"]', kb_query)

        print(f"   Query: {kb_query}")
        print("   Expected progressive response pattern:")
        print("   1. 🤖 Coordinating technical, knowledge_management agents...")
        print("   2. 📊 Analyzing knowledge base content...")
        print("   3. [KB results streaming progressively]")
        print("   4. [Metadata and completion]")

        # Monitor messages as they appear
        initial_message_count = len(await page.query_selector_all('[class*="user"], [class*="assistant"], .message-user, .message-ai, .bg-slate-700'))

        await page.click('button:has-text("Send")')
        await page.wait_for_timeout(1000)  # Wait for user message to appear

        # Step 4: Watch for progressive response phases
        print("\n4. 📡 Monitoring progressive response phases...")

        phase_detected = {
            "immediate": False,
            "analysis": False,
            "detailed": False,
            "kb_content": False
        }

        # Monitor for 30 seconds to capture the full progressive response
        for i in range(30):
            await page.wait_for_timeout(1000)

            # Get all AI messages
            ai_messages = await page.query_selector_all('[class*="assistant"], .message-ai, .bg-slate-700')

            if ai_messages:
                # Get the latest AI message content
                latest_message = ai_messages[-1]
                content = await latest_message.text_content()

                # Check for progressive phases
                if "🤖 Coordinating" in content and not phase_detected["immediate"]:
                    print(f"   ✅ Phase 1 (Immediate): Detected coordination message")
                    phase_detected["immediate"] = True

                if "📊 Analyzing" in content and not phase_detected["analysis"]:
                    print(f"   ✅ Phase 2 (Analysis): Detected analysis message")
                    phase_detected["analysis"] = True

                if "## 🧠 KB Agent Analysis" in content and not phase_detected["detailed"]:
                    print(f"   ✅ Phase 3 (Detailed): Detected KB agent response header")
                    phase_detected["detailed"] = True

                if ("GAIA" in content or "platform" in content or "architecture" in content) and phase_detected["detailed"] and not phase_detected["kb_content"]:
                    print(f"   ✅ Phase 4 (KB Content): Detected actual knowledge base content")
                    phase_detected["kb_content"] = True

                # Print progress update
                phases_complete = sum(phase_detected.values())
                print(f"   Progress: {phases_complete}/4 phases detected ({i+1}s elapsed)")

                # If we've seen all phases, we can finish early
                if all(phase_detected.values()):
                    print(f"   🎉 All progressive phases detected in {i+1} seconds!")
                    break

            # Print current content length for monitoring
            if i % 5 == 0 and ai_messages:
                latest_content = await ai_messages[-1].text_content()
                print(f"   Current response length: {len(latest_content)} characters")

        # Step 5: Take final screenshot and analyze results
        print("\n5. 📸 Capturing final state...")
        await page.screenshot(path="progressive_kb_streaming_result.png", full_page=True)
        print("   Screenshot saved: progressive_kb_streaming_result.png")

        # Get final message content
        final_ai_messages = await page.query_selector_all('[class*="assistant"], .message-ai, .bg-slate-700')
        if final_ai_messages:
            final_content = await final_ai_messages[-1].text_content()

            print(f"\n6. 📊 Final Analysis:")
            print(f"   Total response length: {len(final_content)} characters")
            print(f"   Contains KB analysis header: {'## 🧠 KB Agent Analysis' in final_content}")
            print(f"   Contains knowledge sources: {'Knowledge Sources' in final_content}")
            print(f"   Contains decision logic: {'Decision Logic' in final_content}")

            # Check for progressive streaming indicators
            has_immediate = any(phrase in final_content for phrase in ["🤖 Coordinating", "Coordinating technical"])
            has_analysis = any(phrase in final_content for phrase in ["📊 Analyzing", "Analyzing knowledge"])
            has_kb_content = any(phrase in final_content for phrase in ["KB Agent Analysis", "## 🧠"])

            print(f"\n   Progressive Pattern Analysis:")
            print(f"   ✅ Immediate phase: {has_immediate}")
            print(f"   ✅ Analysis phase: {has_analysis}")
            print(f"   ✅ KB content phase: {has_kb_content}")

            overall_success = has_immediate and has_analysis and has_kb_content
            print(f"\n   🎯 Progressive KB Streaming: {'✅ WORKING' if overall_success else '❌ NEEDS ATTENTION'}")

            if overall_success:
                print(f"   🎉 The progressive KB streaming system is working perfectly!")
                print(f"   Users see immediate feedback, progress updates, and detailed results.")
            else:
                print(f"   ⚠️ Progressive streaming may not be fully active.")
                print(f"   Check KB service status and progressive integration.")

        print(f"\n   👀 Browser staying open for 10 seconds for manual inspection...")
        await page.wait_for_timeout(10000)

    except Exception as e:
        print(f"\n💥 Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser.close()
        await playwright.stop()

        # Clean up test conversations
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

    print("\n🎬 PROGRESSIVE KB STREAMING TEST COMPLETE")

if __name__ == "__main__":
    asyncio.run(test_progressive_kb_streaming())