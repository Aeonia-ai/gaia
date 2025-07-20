"""
Layout Integrity Tests

These tests ensure that layout isolation rules are enforced and prevent
the recurring "mobile width on desktop" and layout mixing bugs.

This includes both unit tests for isolation utilities and integration
tests with real browser rendering.
"""
import pytest
from playwright.async_api import async_playwright, expect
import asyncio
from pathlib import Path
import json
from fasthtml.components import Div, A, Button
from starlette.responses import HTMLResponse

# Import our layout isolation utilities
try:
    from app.services.web.utils.layout_isolation import (
        auth_page_replacement,
        chat_content_replacement, 
        safe_htmx_response,
        validate_layout_isolation
    )
    LAYOUT_UTILS_AVAILABLE = True
except ImportError:
    LAYOUT_UTILS_AVAILABLE = False


@pytest.mark.skipif(not LAYOUT_UTILS_AVAILABLE, reason="Layout isolation utilities not available")
class TestAuthLayoutIsolation:
    """Test auth page layout isolation rules (Unit Tests)"""
    
    def test_auth_page_replacement_basic(self):
        """Test basic auth page replacement works"""
        response = auth_page_replacement(
            title="Test Auth Page",
            content="Test content"
        )
        
        assert isinstance(response, HTMLResponse)
        content_str = response.body.decode()
        
        # Must contain auth container
        assert 'id="auth-container"' in content_str
        
        # Must not contain sidebar or chat elements
        assert 'id="sidebar"' not in content_str
        assert 'id="chat-form"' not in content_str
        assert 'id="messages"' not in content_str
    
    def test_auth_page_replacement_forbids_sidebar(self):
        """Test that auth pages cannot have sidebar"""
        with pytest.raises(ValueError, match="Auth pages must never show sidebar"):
            auth_page_replacement(
                title="Test",
                content="Test",
                show_sidebar=True  # This should raise an error
            )
    
    def test_auth_page_with_actions(self):
        """Test auth page with action buttons"""
        response = auth_page_replacement(
            title="📧 Check Your Email",
            content=["We sent a link", "Check your email"],
            actions=[
                ("Resend", "/resend", {"email": "test@example.com"}),
                ("Back to login", "/login", None)
            ]
        )
        
        content_str = response.body.decode()
        
        # Should contain action buttons
        assert "Resend" in content_str
        assert "Back to login" in content_str
    
    def test_email_verification_isolation(self):
        """Test the exact email verification scenario that keeps breaking"""
        response = auth_page_replacement(
            title="📧 Check Your Email",
            content=[
                "We've sent a verification link to: test@example.com",
                "Please check your email and click the verification link to activate your account."
            ],
            actions=[("Resend verification", "/auth/resend-verification", {"email": "test@example.com"})]
        )
        
        content_str = response.body.decode()
        
        # CRITICAL: Must not contain any form input elements
        assert '<input' not in content_str
        assert 'type="email"' not in content_str
        assert 'type="password"' not in content_str
        
        # Must contain verification message
        assert "Check Your Email" in content_str
        assert "test@example.com" in content_str
        
        # Must be properly isolated
        assert 'id="auth-container"' in content_str
        assert 'id="sidebar"' not in content_str


@pytest.mark.skipif(not LAYOUT_UTILS_AVAILABLE, reason="Layout isolation utilities not available")  
class TestHTMXSafety:
    """Test HTMX response safety rules"""
    
    def test_safe_htmx_response_blocks_dangerous_targets(self):
        """Test that dangerous HTMX targets are blocked"""
        dangerous_targets = ["#app", "body", ".flex.h-screen"]
        
        for target in dangerous_targets:
            with pytest.raises(ValueError, match="layout-breaking and forbidden"):
                safe_htmx_response("content", target)
    
    def test_auth_container_requires_outer_html(self):
        """Test that auth container replacement requires outerHTML"""
        with pytest.raises(ValueError, match="Auth container replacement must use outerHTML"):
            safe_htmx_response("content", "#auth-container", swap="innerHTML")


class TestLayoutIntegrity:
    """Critical browser-based tests to prevent layout breakages"""
    
    @pytest.mark.asyncio
    async def test_chat_layout_full_width(self):
        """Ensure chat interface uses full viewport width"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            # Login first
            await page.goto('http://localhost:8080/login')
            await page.fill('input[name="email"]', 'dev@gaia.local')
            await page.fill('input[name="password"]', 'testtest')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            
            # Check main layout container
            main_container = await page.query_selector('.flex.h-screen')
            assert main_container, "Main container must have flex and h-screen classes"
            
            # Get container dimensions
            box = await main_container.bounding_box()
            assert box['width'] >= 1900, f"Chat container must be full width. Got {box['width']}px"
            
            # Check sidebar width
            sidebar = await page.query_selector('#sidebar')
            if sidebar:
                sidebar_box = await sidebar.bounding_box()
                assert 200 <= sidebar_box['width'] <= 300, f"Sidebar must be 200-300px. Got {sidebar_box['width']}px"
            
            # Check main content area fills remaining space
            main_content = await page.query_selector('#main-content')
            main_box = await main_content.bounding_box()
            assert main_box['width'] >= 1500, f"Main content must use remaining width. Got {main_box['width']}px"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_login_page_no_chat_elements(self):
        """Ensure login page doesn't render chat interface elements"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            await page.goto('http://localhost:8080/login')
            
            # These elements should NOT exist on login page
            forbidden_elements = [
                '#sidebar',
                '#chat-form',
                '#messages',
                '#conversation-list',
                '.mobile-header',
                '#sidebar-toggle'
            ]
            
            for selector in forbidden_elements:
                element = await page.query_selector(selector)
                assert element is None, f"Login page must not contain {selector}"
            
            # Login form should exist
            login_form = await page.query_selector('form[hx-post="/auth/login"]')
            assert login_form, "Login form must exist"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_responsive_breakpoints(self):
        """Test layout at critical responsive breakpoints"""
        breakpoints = [
            {'width': 375, 'height': 667, 'name': 'iPhone SE'},
            {'width': 768, 'height': 1024, 'name': 'iPad'},
            {'width': 1024, 'height': 768, 'name': 'Desktop Small'},
            {'width': 1920, 'height': 1080, 'name': 'Desktop Full'}
        ]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            
            for breakpoint in breakpoints:
                context = await browser.new_context(viewport={
                    'width': breakpoint['width'],
                    'height': breakpoint['height']
                })
                page = await context.new_page()
                
                # Test login page
                await page.goto('http://localhost:8080/login')
                await page.wait_for_load_state('networkidle')
                
                # Login to test chat
                await page.fill('input[name="email"]', 'dev@gaia.local')
                await page.fill('input[name="password"]', 'testtest')
                await page.click('button[type="submit"]')
                await page.wait_for_url('**/chat')
                
                # Verify layout integrity
                main_container = await page.query_selector('.flex.h-screen')
                box = await main_container.bounding_box()
                
                # Container should use full viewport width
                assert box['width'] >= breakpoint['width'] - 20, \
                    f"{breakpoint['name']}: Container width {box['width']} < viewport {breakpoint['width']}"
                
                # On mobile, sidebar should be hidden by default
                if breakpoint['width'] < 768:
                    sidebar = await page.query_selector('#sidebar')
                    if sidebar:
                        is_visible = await sidebar.is_visible()
                        transform = await sidebar.evaluate('el => window.getComputedStyle(el).transform')
                        assert not is_visible or 'translateX(-' in transform, \
                            f"{breakpoint['name']}: Sidebar must be hidden on mobile"
                
                await context.close()
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_htmx_navigation_preserves_layout(self):
        """Ensure HTMX navigation doesn't break layout"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Login
            await page.goto('http://localhost:8080/login')
            await page.fill('input[name="email"]', 'dev@gaia.local')
            await page.fill('input[name="password"]', 'testtest')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            
            # Get initial layout dimensions
            initial_container = await page.query_selector('.flex.h-screen')
            initial_box = await initial_container.bounding_box()
            
            # Trigger HTMX navigation (create new chat)
            await page.click('button:has-text("New Chat")')
            await page.wait_for_timeout(500)  # Wait for HTMX
            
            # Verify layout hasn't changed
            after_container = await page.query_selector('.flex.h-screen')
            after_box = await after_container.bounding_box()
            
            assert initial_box['width'] == after_box['width'], \
                "Layout width changed after HTMX navigation"
            assert initial_box['height'] == after_box['height'], \
                "Layout height changed after HTMX navigation"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_email_verification_no_form_elements(self):
        """Test that email verification page doesn't show form elements (the recurring bug)"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Go to registration page and submit
            await page.goto('http://localhost:8080/register') 
            await page.fill('input[name="email"]', 'test@example.com')
            await page.fill('input[name="password"]', 'testtest123')
            await page.click('button[type="submit"]')
            
            # Wait for verification response
            await page.wait_for_timeout(1000)
            
            # CRITICAL: After registration, must NOT show form elements alongside verification
            email_inputs = await page.query_selector_all('input[type="email"]')
            password_inputs = await page.query_selector_all('input[type="password"]')
            
            # If verification message is shown, form elements must be gone
            verification_msg = await page.query_selector('text="Check Your Email"')
            if verification_msg:
                assert len(email_inputs) == 0, "Email verification page must not show email input"
                assert len(password_inputs) == 0, "Email verification page must not show password input"
                
                # Should show verification message
                assert await page.query_selector('text="We\'ve sent a verification link"'), \
                    "Must show verification message"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_no_nested_layouts(self):
        """Prevent nested layout containers that could cause sizing issues"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Check login page
            await page.goto('http://localhost:8080/login')
            
            # Count flex containers with h-screen
            containers = await page.query_selector_all('.flex.h-screen')
            assert len(containers) == 1, f"Login page must have exactly 1 main container, found {len(containers)}"
            
            # Login and check chat page
            await page.fill('input[name="email"]', 'dev@gaia.local')
            await page.fill('input[name="password"]', 'testtest')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            
            # Count flex containers again
            containers = await page.query_selector_all('.flex.h-screen')
            assert len(containers) == 1, f"Chat page must have exactly 1 main container, found {len(containers)}"
            
            await browser.close()


class TestVisualRegression:
    """Visual regression tests using screenshots"""
    
    SCREENSHOTS_DIR = Path("tests/web/screenshots")
    BASELINE_DIR = SCREENSHOTS_DIR / "baseline"
    CURRENT_DIR = SCREENSHOTS_DIR / "current"
    
    @classmethod
    def setup_class(cls):
        """Create screenshot directories"""
        cls.BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        cls.CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    
    @pytest.mark.asyncio
    async def test_capture_baseline_screenshots(self):
        """Capture baseline screenshots for comparison"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            
            # Desktop viewport
            desktop = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await desktop.new_page()
            
            # Login page
            await page.goto('http://localhost:8080/login')
            await page.screenshot(path=self.CURRENT_DIR / "login_desktop.png", full_page=True)
            
            # Chat page
            await page.fill('input[name="email"]', 'dev@gaia.local')
            await page.fill('input[name="password"]', 'testtest')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            await page.screenshot(path=self.CURRENT_DIR / "chat_desktop.png", full_page=True)
            
            await desktop.close()
            
            # Mobile viewport
            mobile = await browser.new_context(
                viewport={'width': 375, 'height': 667},
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)'
            )
            page = await mobile.new_page()
            
            # Login page mobile
            await page.goto('http://localhost:8080/login')
            await page.screenshot(path=self.CURRENT_DIR / "login_mobile.png", full_page=True)
            
            # Chat page mobile
            await page.fill('input[name="email"]', 'dev@gaia.local')
            await page.fill('input[name="password"]', 'testtest')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            await page.screenshot(path=self.CURRENT_DIR / "chat_mobile.png", full_page=True)
            
            await mobile.close()
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_layout_dimensions_tracking(self):
        """Track critical layout dimensions in JSON for automated checking"""
        dimensions = {}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Login and navigate to chat
            await page.goto('http://localhost:8080/login')
            await page.fill('input[name="email"]', 'dev@gaia.local')
            await page.fill('input[name="password"]', 'testtest')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            
            # Collect dimensions
            dimensions['viewport'] = await page.viewport_size()
            
            # Main container
            main = await page.query_selector('.flex.h-screen')
            if main:
                dimensions['main_container'] = await main.bounding_box()
            
            # Sidebar
            sidebar = await page.query_selector('#sidebar')
            if sidebar:
                dimensions['sidebar'] = await sidebar.bounding_box()
            
            # Main content
            content = await page.query_selector('#main-content')
            if content:
                dimensions['main_content'] = await content.bounding_box()
            
            # Chat input
            chat_input = await page.query_selector('#chat-form')
            if chat_input:
                dimensions['chat_input'] = await chat_input.bounding_box()
            
            # Save dimensions
            dimensions_file = self.CURRENT_DIR / "layout_dimensions.json"
            with open(dimensions_file, 'w') as f:
                json.dump(dimensions, f, indent=2)
            
            # Validate critical constraints
            assert dimensions['main_container']['width'] >= dimensions['viewport']['width'] - 20, \
                "Main container must use full viewport width"
            
            if 'sidebar' in dimensions and dimensions['sidebar']:
                assert 200 <= dimensions['sidebar']['width'] <= 300, \
                    f"Sidebar width out of range: {dimensions['sidebar']['width']}px"
            
            await browser.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])