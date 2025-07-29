"""
Browser test configuration and utilities.

Provides configuration for different browser test scenarios.
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class BrowserTestMode(Enum):
    """Different modes for running browser tests"""
    UNIT = "unit"  # Fast, mocked responses
    INTEGRATION = "integration"  # Real backend calls
    E2E = "e2e"  # Full end-to-end with real services
    VISUAL = "visual"  # Visual regression testing
    PERFORMANCE = "performance"  # Performance testing


@dataclass
class BrowserTestConfig:
    """Configuration for browser tests"""
    mode: BrowserTestMode
    headless: bool = True
    slow_mo: int = 0  # Milliseconds to slow down operations
    timeout: int = 30000  # Default timeout in ms
    viewport: Dict[str, int] = None
    record_video: bool = False
    record_har: bool = False
    trace: bool = False
    
    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1280, "height": 720}
    
    @property
    def launch_options(self) -> Dict[str, Any]:
        """Get Playwright launch options"""
        options = {
            "headless": self.headless,
            "args": ['--no-sandbox', '--disable-setuid-sandbox']
        }
        
        if self.slow_mo > 0:
            options["slow_mo"] = self.slow_mo
        
        return options
    
    @property
    def context_options(self) -> Dict[str, Any]:
        """Get Playwright context options"""
        options = {
            "viewport": self.viewport,
            "ignore_https_errors": True
        }
        
        if self.record_video:
            options["record_video_dir"] = "tests/web/videos/"
            options["record_video_size"] = self.viewport
        
        if self.record_har:
            options["record_har_path"] = "tests/web/har/test.har"
        
        return options
    
    @classmethod
    def from_env(cls) -> "BrowserTestConfig":
        """Create config from environment variables"""
        mode_str = os.getenv("BROWSER_TEST_MODE", "unit").lower()
        mode = BrowserTestMode(mode_str)
        
        return cls(
            mode=mode,
            headless=os.getenv("BROWSER_HEADLESS", "true").lower() == "true",
            slow_mo=int(os.getenv("BROWSER_SLOW_MO", "0")),
            timeout=int(os.getenv("BROWSER_TIMEOUT", "30000")),
            record_video=os.getenv("BROWSER_RECORD_VIDEO", "false").lower() == "true",
            trace=os.getenv("BROWSER_TRACE", "false").lower() == "true"
        )


# Preset configurations
BROWSER_TEST_CONFIGS = {
    "fast": BrowserTestConfig(
        mode=BrowserTestMode.UNIT,
        headless=True,
        timeout=10000
    ),
    "debug": BrowserTestConfig(
        mode=BrowserTestMode.UNIT,
        headless=False,
        slow_mo=500,
        timeout=60000
    ),
    "integration": BrowserTestConfig(
        mode=BrowserTestMode.INTEGRATION,
        headless=True,
        timeout=30000
    ),
    "visual": BrowserTestConfig(
        mode=BrowserTestMode.VISUAL,
        headless=True,
        viewport={"width": 1920, "height": 1080}
    ),
    "mobile": BrowserTestConfig(
        mode=BrowserTestMode.UNIT,
        headless=True,
        viewport={"width": 375, "height": 667}
    ),
    "tablet": BrowserTestConfig(
        mode=BrowserTestMode.UNIT,
        headless=True,
        viewport={"width": 768, "height": 1024}
    ),
    "performance": BrowserTestConfig(
        mode=BrowserTestMode.PERFORMANCE,
        headless=True,
        record_har=True,
        trace=True
    )
}


def get_browser_config(name: Optional[str] = None) -> BrowserTestConfig:
    """Get browser test configuration by name or from environment"""
    if name and name in BROWSER_TEST_CONFIGS:
        return BROWSER_TEST_CONFIGS[name]
    return BrowserTestConfig.from_env()


# Mock response helpers
class MockResponses:
    """Common mock responses for browser tests"""
    
    @staticmethod
    def auth_success(email: str = "test@test.local"):
        return {
            "status": 200,
            "json": {
                "access_token": "mock-jwt-token",
                "user": {
                    "id": "test-123",
                    "email": email
                }
            }
        }
    
    @staticmethod
    def auth_failure(error: str = "Invalid credentials"):
        return {
            "status": 400,
            "json": {"error": error}
        }
    
    @staticmethod
    def chat_response(content: str = "Hello! How can I help you?"):
        return {
            "status": 200,
            "json": {
                "id": "chatcmpl-123",
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }]
            }
        }
    
    @staticmethod
    def conversations_list(conversations: list = None):
        if conversations is None:
            conversations = []
        return {
            "status": 200,
            "json": {
                "conversations": conversations,
                "has_more": False
            }
        }
    
    @staticmethod
    def html_error(message: str = "An error occurred"):
        return {
            "status": 400,
            "headers": {"Content-Type": "text/html"},
            "body": f'<div role="alert" class="error">{message}</div>'
        }


# Browser automation helpers
class BrowserHelpers:
    """Helper methods for common browser test operations"""
    
    @staticmethod
    async def mock_successful_login(page):
        """Set up mocks for successful login flow"""
        await page.route("**/auth/login", lambda route: route.fulfill(
            status=303,
            headers={"Location": "/chat"},
            body=""
        ))
        await page.route("**/api/conversations", lambda route: route.fulfill(
            **MockResponses.conversations_list()
        ))
    
    @staticmethod
    async def mock_failed_login(page, error="Invalid credentials"):
        """Set up mocks for failed login"""
        await page.route("**/auth/login", lambda route: route.fulfill(
            **MockResponses.auth_failure(error)
        ))
    
    @staticmethod
    async def login_user(page, email="test@test.local", password="test123"):
        """Perform login action"""
        await page.goto("/login")
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
    
    @staticmethod
    async def wait_for_chat_page(page):
        """Wait for chat page to load completely"""
        await page.wait_for_url("**/chat")
        await page.wait_for_selector("#chat-form")
        await page.wait_for_selector("#messages")
    
    @staticmethod
    async def send_chat_message(page, message: str):
        """Send a message in chat"""
        await page.fill('textarea[name="message"]', message)
        await page.keyboard.press("Enter")
    
    @staticmethod
    async def check_console_errors(page) -> list:
        """Check for console errors"""
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg))
        return [msg for msg in console_messages if msg.type == "error"]
    
    @staticmethod
    async def take_screenshot_on_failure(page, test_name: str):
        """Take screenshot for debugging failed tests"""
        try:
            await page.screenshot(
                path=f"tests/web/screenshots/failures/{test_name}.png",
                full_page=True
            )
        except Exception:
            pass  # Don't fail the test if screenshot fails


# Performance testing utilities
class PerformanceMetrics:
    """Utilities for performance testing"""
    
    @staticmethod
    async def measure_page_load_time(page, url: str) -> float:
        """Measure time to load a page"""
        start_time = asyncio.get_event_loop().time()
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        end_time = asyncio.get_event_loop().time()
        return (end_time - start_time) * 1000  # Convert to ms
    
    @staticmethod
    async def get_performance_metrics(page) -> dict:
        """Get browser performance metrics"""
        return await page.evaluate('''
            () => {
                const perfData = performance.getEntriesByType("navigation")[0];
                return {
                    domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
                    loadComplete: perfData.loadEventEnd - perfData.loadEventStart,
                    firstPaint: performance.getEntriesByName("first-paint")[0]?.startTime || 0,
                    firstContentfulPaint: performance.getEntriesByName("first-contentful-paint")[0]?.startTime || 0
                };
            }
        ''')
    
    @staticmethod
    async def measure_interaction_responsiveness(page, action_callback) -> float:
        """Measure time for an interaction to complete"""
        start_time = asyncio.get_event_loop().time()
        await action_callback()
        end_time = asyncio.get_event_loop().time()
        return (end_time - start_time) * 1000


# Test data generators
class TestDataGenerator:
    """Generate test data for browser tests"""
    
    @staticmethod
    def generate_test_email():
        """Generate unique test email"""
        import uuid
        return f"test-{uuid.uuid4().hex[:8]}@test.local"
    
    @staticmethod
    def generate_test_conversation():
        """Generate test conversation data"""
        import uuid
        from datetime import datetime
        return {
            "id": f"conv-{uuid.uuid4().hex[:8]}",
            "title": "Test Conversation",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "message_count": 0
        }
    
    @staticmethod
    def generate_long_text(words: int = 100):
        """Generate long text for testing text areas"""
        import random
        word_list = ["test", "message", "content", "data", "value", "text", "word", "sample"]
        return " ".join(random.choice(word_list) for _ in range(words))