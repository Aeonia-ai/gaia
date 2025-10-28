#!/usr/bin/env python3
"""
Page Inspection Debug Script

Inspect a web page's structure, HTMX setup, and current state.

Usage:
    python scripts/webui/debug/inspect_page.py --url /chat
    python scripts/webui/debug/inspect_page.py --url /login --check-layout
    python scripts/webui/debug/inspect_page.py --url /chat --dump-htmx
    python scripts/webui/debug/inspect_page.py --url /chat --headful --wait
"""
import sys
import os
import asyncio
import argparse
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.browser import BrowserSession, get_common_args, handle_post_actions
from utils.auth import ensure_logged_in, get_test_credentials


async def inspect_htmx_setup(page):
    """Check if HTMX is properly loaded and configured"""
    print("\n🔍 HTMX Setup Check:")

    # Check if HTMX is loaded
    htmx_loaded = await page.evaluate("typeof htmx !== 'undefined'")
    print(f"  {'✅' if htmx_loaded else '❌'} HTMX loaded: {htmx_loaded}")

    if not htmx_loaded:
        return

    # Check HTMX version
    htmx_version = await page.evaluate("htmx.version || 'unknown'")
    print(f"  📦 HTMX version: {htmx_version}")

    # Count HTMX elements
    htmx_elements = await page.evaluate("""
        () => {
            const attrs = ['hx-get', 'hx-post', 'hx-put', 'hx-delete'];
            let count = 0;
            attrs.forEach(attr => {
                count += document.querySelectorAll(`[${attr}]`).length;
            });
            return count;
        }
    """)
    print(f"  📊 HTMX elements: {htmx_elements}")


async def inspect_layout(page):
    """Check for common layout issues"""
    print("\n🎨 Layout Inspection:")

    # Check for problematic flex patterns
    problematic_flex = await page.evaluate("""
        () => {
            const elements = document.querySelectorAll('[class*="flex"]');
            const problems = [];
            elements.forEach(el => {
                const classes = el.className;
                if (classes.includes('flex-col') &&
                    (classes.includes('md:flex-row') || classes.includes('lg:flex-row'))) {
                    problems.push({
                        tag: el.tagName,
                        id: el.id,
                        classes: classes
                    });
                }
            });
            return problems;
        }
    """)

    if len(problematic_flex) > 0:
        print(f"  ⚠️  Found {len(problematic_flex)} problematic flex patterns:")
        for item in problematic_flex[:5]:  # Show first 5
            print(f"     {item['tag']}#{item['id'] or 'no-id'}")
    else:
        print("  ✅ No problematic flex patterns found")

    # Check for loading indicators
    loading_indicators = await page.evaluate("""
        () => {
            return document.querySelectorAll('.htmx-indicator, [aria-busy]').length;
        }
    """)
    print(f"  📊 Loading indicators: {loading_indicators}")

    # Check for error messages
    error_messages = await page.evaluate("""
        () => {
            return document.querySelectorAll('[role="alert"], [data-testid="error-message"]').length;
        }
    """)
    print(f"  {'⚠️ ' if error_messages > 0 else '✅'} Error messages visible: {error_messages}")


async def inspect_forms(page):
    """Inspect forms on the page"""
    print("\n📋 Form Inspection:")

    forms = await page.evaluate("""
        () => {
            const forms = document.querySelectorAll('form');
            return Array.from(forms).map(form => ({
                action: form.action,
                method: form.method,
                hx_post: form.getAttribute('hx-post'),
                hx_target: form.getAttribute('hx-target'),
                inputs: Array.from(form.querySelectorAll('input, textarea')).length
            }));
        }
    """)

    if len(forms) == 0:
        print("  📭 No forms found")
    else:
        for i, form in enumerate(forms, 1):
            print(f"  Form {i}:")
            print(f"    Method: {form['method']}")
            if form['hx_post']:
                print(f"    HTMX Post: {form['hx_post']}")
                print(f"    HTMX Target: {form['hx_target']}")
            print(f"    Inputs: {form['inputs']}")


async def dump_page_structure(page):
    """Dump page structure to JSON"""
    structure = await page.evaluate("""
        () => {
            function extractElement(el) {
                return {
                    tag: el.tagName,
                    id: el.id || null,
                    classes: el.className || null,
                    testid: el.getAttribute('data-testid'),
                    children: Array.from(el.children).map(extractElement)
                };
            }
            return extractElement(document.body);
        }
    """)
    return structure


async def main():
    parser = argparse.ArgumentParser(description="Inspect web page")
    parser.add_argument(
        "--url",
        default="/chat",
        help="URL to inspect (default: /chat)"
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Login before inspecting"
    )
    parser.add_argument(
        "--email",
        help="User email for login"
    )
    parser.add_argument(
        "--password",
        help="User password for login"
    )
    parser.add_argument(
        "--check-layout",
        action="store_true",
        help="Check for layout issues"
    )
    parser.add_argument(
        "--dump-htmx",
        action="store_true",
        help="Dump HTMX element details"
    )
    parser.add_argument(
        "--dump-structure",
        type=str,
        help="Dump page structure to JSON file"
    )

    # Add common arguments
    parser = get_common_args(parser)
    args = parser.parse_args()

    print(f"🔍 Inspecting page: {args.url}")

    # Create browser session
    async with BrowserSession(
        headless=not args.headful,
        slow_mo=args.slow,
        base_url=args.base_url
    ) as session:
        page = session.get_page()

        # Login if requested
        if args.login:
            credentials = get_test_credentials()
            email = args.email or credentials["email"]
            password = args.password or credentials["password"]
            await ensure_logged_in(page, email, password, args.base_url)

        # Navigate to URL
        await session.goto(args.url)
        await session.wait_for_load()

        print(f"✅ Page loaded: {page.url}")

        # Always check HTMX setup
        await inspect_htmx_setup(page)

        # Always inspect forms
        await inspect_forms(page)

        # Check layout if requested
        if args.check_layout:
            await inspect_layout(page)

        # Dump structure if requested
        if args.dump_structure:
            structure = await dump_page_structure(page)
            with open(args.dump_structure, 'w') as f:
                json.dump(structure, f, indent=2)
            print(f"\n💾 Structure dumped to: {args.dump_structure}")

        # Handle post-actions
        await handle_post_actions(session, args)

    print("\n✅ Inspection complete")


if __name__ == "__main__":
    asyncio.run(main())
