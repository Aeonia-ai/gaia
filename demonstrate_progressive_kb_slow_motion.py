#!/usr/bin/env python3
"""
Slow Motion Progressive KB Streaming Demonstration

Shows the progressive KB streaming phases with:
- Very slow browser automation (5-10 second delays)
- Detailed narration of each phase
- Multiple screenshots at key moments
- Extended observation periods

This will clearly show:
1. "🤖 Coordinating..." appearing first
2. "📊 Analyzing..." appearing next
3. KB results streaming in progressively
4. Final complete response with recommendations
"""

import asyncio
from playwright.async_api import async_playwright

async def demonstrate_progressive_kb_slow_motion():
    """Slow motion demonstration of progressive KB streaming"""

    print("🎬 SLOW MOTION PROGRESSIVE KB STREAMING DEMONSTRATION")
    print("=" * 60)
    print("This demo will show each phase of progressive streaming clearly")
    print("Watch the browser carefully - each phase will be highlighted!")

    playwright = await async_playwright().start()
    # Very slow motion for clear demonstration
    browser = await playwright.chromium.launch(headless=False, slow_mo=5000)  # 5 second delays

    try:
        page = await browser.new_page()

        # Step 1: Login with narration
        print("\n🎬 PHASE 1: LOGIN SEQUENCE")
        print("=" * 30)
        await page.goto("http://localhost:8080/login")

        print("⏳ Filling in credentials...")
        await page.fill('input[placeholder="Email address"]', "admin@aeonia.ai")
        await page.fill('input[placeholder="Password"]', "auVwGUGt7GHAnv6nFxR8")

        print("🔐 Clicking sign in...")
        await page.click('button:has-text("Sign In")')
        await page.wait_for_url("**/chat")

        await page.screenshot(path="demo_1_logged_in.png", full_page=True)
        print("✅ Login complete - screenshot saved: demo_1_logged_in.png")

        # Step 2: New conversation setup
        print("\n🎬 PHASE 2: NEW CONVERSATION SETUP")
        print("=" * 35)
        print("🆕 Starting new conversation...")
        await page.click('button:has-text("New Chat")')
        await page.wait_for_timeout(3000)

        await page.screenshot(path="demo_2_new_chat.png", full_page=True)
        print("📝 New conversation ready - screenshot saved: demo_2_new_chat.png")

        # Step 3: Prepare the KB query
        print("\n🎬 PHASE 3: PREPARING KB QUERY")
        print("=" * 32)

        # Query that will definitely trigger KB analysis
        kb_query = "Analyze the GAIA platform's authentication architecture and microservices design patterns from the knowledge base"

        print(f"📝 Query: {kb_query}")
        print("⏳ This query should trigger:")
        print("   1. 🤖 Coordinating technical, knowledge_management agents...")
        print("   2. 📊 Analyzing knowledge base content...")
        print("   3. Progressive KB results streaming")
        print("   4. Complete response with architecture details")

        await page.fill('input[id="chat-message-input"]', kb_query)
        await page.wait_for_timeout(2000)

        await page.screenshot(path="demo_3_query_ready.png", full_page=True)
        print("🎯 Query prepared - screenshot saved: demo_3_query_ready.png")

        # Step 4: Send query and monitor phases
        print("\n🎬 PHASE 4: PROGRESSIVE STREAMING OBSERVATION")
        print("=" * 45)
        print("🚀 Sending query and monitoring each phase...")

        await page.click('button:has-text("Send")')
        print("📤 Query sent - watching for progressive phases...")

        # Monitor phases with detailed observation
        phases_observed = []

        # Phase 1: Immediate response
        print("\n👀 WATCHING FOR PHASE 1: Immediate Coordination...")
        await page.wait_for_timeout(3000)

        ai_messages = await page.query_selector_all('[class*="assistant"], .message-ai, .bg-slate-700')
        if ai_messages:
            content = await ai_messages[-1].text_content()
            if "🤖" in content or "Coordinating" in content:
                print("✅ PHASE 1 DETECTED: Immediate coordination message!")
                phases_observed.append("immediate")
                await page.screenshot(path="demo_4_phase1_immediate.png", full_page=True)
                print("📸 Phase 1 screenshot saved: demo_4_phase1_immediate.png")

        # Phase 2: Analysis status
        print("\n👀 WATCHING FOR PHASE 2: Analysis Status...")
        await page.wait_for_timeout(5000)

        ai_messages = await page.query_selector_all('[class*="assistant"], .message-ai, .bg-slate-700')
        if ai_messages:
            content = await ai_messages[-1].text_content()
            if "📊" in content or "Analyzing" in content:
                print("✅ PHASE 2 DETECTED: Analysis status message!")
                phases_observed.append("analysis")
                await page.screenshot(path="demo_5_phase2_analysis.png", full_page=True)
                print("📸 Phase 2 screenshot saved: demo_5_phase2_analysis.png")

        # Phase 3: Detailed KB content
        print("\n👀 WATCHING FOR PHASE 3: KB Content Streaming...")
        await page.wait_for_timeout(8000)

        ai_messages = await page.query_selector_all('[class*="assistant"], .message-ai, .bg-slate-700')
        if ai_messages:
            content = await ai_messages[-1].text_content()
            if "KB Agent Analysis" in content or "architecture" in content.lower():
                print("✅ PHASE 3 DETECTED: KB content streaming!")
                phases_observed.append("kb_content")
                await page.screenshot(path="demo_6_phase3_kb_content.png", full_page=True)
                print("📸 Phase 3 screenshot saved: demo_6_phase3_kb_content.png")

        # Phase 4: Complete response
        print("\n👀 WATCHING FOR PHASE 4: Complete Response...")
        await page.wait_for_timeout(10000)

        ai_messages = await page.query_selector_all('[class*="assistant"], .message-ai, .bg-slate-700')
        if ai_messages:
            content = await ai_messages[-1].text_content()
            if len(content) > 1000:  # Substantial response indicates completion
                print("✅ PHASE 4 DETECTED: Complete response delivered!")
                phases_observed.append("complete")
                await page.screenshot(path="demo_7_phase4_complete.png", full_page=True)
                print("📸 Phase 4 screenshot saved: demo_7_phase4_complete.png")

        # Step 5: Final analysis and extended viewing
        print("\n🎬 PHASE 5: FINAL ANALYSIS")
        print("=" * 28)

        final_content = await ai_messages[-1].text_content() if ai_messages else ""

        print(f"📊 PROGRESSIVE STREAMING RESULTS:")
        print(f"   Phases observed: {len(phases_observed)}/4")
        print(f"   Phases detected: {', '.join(phases_observed)}")
        print(f"   Final response length: {len(final_content)} characters")
        print(f"   Contains architecture info: {'authentication' in final_content.lower()}")
        print(f"   Contains KB analysis: {'KB Agent' in final_content}")

        # Take a final comprehensive screenshot
        await page.screenshot(path="demo_8_final_comprehensive.png", full_page=True)
        print("📸 Final comprehensive screenshot: demo_8_final_comprehensive.png")

        # Extended viewing period with countdown
        print(f"\n🔍 EXTENDED VIEWING PERIOD")
        print("=" * 26)
        print("Browser will stay open for 30 seconds for detailed inspection...")
        print("You can:")
        print("- Scroll through the response")
        print("- See the complete progressive streaming result")
        print("- Compare with the screenshots taken during each phase")

        for i in range(30, 0, -5):
            print(f"   ⏰ {i} seconds remaining...")
            await page.wait_for_timeout(5000)

    except Exception as e:
        print(f"\n💥 Error during demonstration: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser.close()
        await playwright.stop()

    print(f"\n🎬 SLOW MOTION DEMONSTRATION COMPLETE")
    print("=" * 40)
    print("Screenshots captured during demonstration:")
    print("1. demo_1_logged_in.png - Login complete")
    print("2. demo_2_new_chat.png - New conversation ready")
    print("3. demo_3_query_ready.png - KB query prepared")
    print("4. demo_4_phase1_immediate.png - Immediate coordination")
    print("5. demo_5_phase2_analysis.png - Analysis status")
    print("6. demo_6_phase3_kb_content.png - KB content streaming")
    print("7. demo_7_phase4_complete.png - Complete response")
    print("8. demo_8_final_comprehensive.png - Final state")
    print("\nUse 'open demo_*.png' to view all screenshots!")

if __name__ == "__main__":
    asyncio.run(demonstrate_progressive_kb_slow_motion())