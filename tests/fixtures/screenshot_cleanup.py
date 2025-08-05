"""
Screenshot cleanup fixtures for pytest.

These fixtures ensure that test-generated screenshots are properly cleaned up
after test runs while preserving baseline/reference screenshots.
"""
import os
import shutil
from pathlib import Path
import pytest
from typing import List, Optional


class ScreenshotManager:
    """Manages screenshot lifecycle during tests"""
    
    def __init__(self, base_dir: str = "tests/web/screenshots"):
        self.base_dir = Path(base_dir)
        self.preserved_dirs = {"baseline", "reference"}  # Don't clean these
        self.screenshots_taken = []
        
    def take_screenshot(self, page, name: str, subdir: Optional[str] = None) -> Path:
        """Take a screenshot and track it for cleanup"""
        if subdir:
            screenshot_dir = self.base_dir / subdir
        else:
            screenshot_dir = self.base_dir
            
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / name
        
        # Take the screenshot
        page.screenshot(path=str(screenshot_path))
        
        # Track it for cleanup
        self.screenshots_taken.append(screenshot_path)
        
        return screenshot_path
    
    def cleanup_test_screenshots(self):
        """Clean up screenshots taken during this test run"""
        for screenshot_path in self.screenshots_taken:
            try:
                if screenshot_path.exists():
                    screenshot_path.unlink()
            except Exception as e:
                print(f"Warning: Failed to delete {screenshot_path}: {e}")
                
        self.screenshots_taken.clear()
    
    def cleanup_all_test_screenshots(self):
        """Clean up all test screenshots (except preserved directories)"""
        if not self.base_dir.exists():
            return
            
        # Clean up files in root directory
        for file in self.base_dir.glob("*.png"):
            try:
                file.unlink()
            except Exception as e:
                print(f"Warning: Failed to delete {file}: {e}")
        
        # Clean up subdirectories (except preserved ones)
        for subdir in self.base_dir.iterdir():
            if subdir.is_dir() and subdir.name not in self.preserved_dirs:
                try:
                    shutil.rmtree(subdir)
                except Exception as e:
                    print(f"Warning: Failed to delete directory {subdir}: {e}")
    
    def cleanup_specific_patterns(self, patterns: List[str]):
        """Clean up screenshots matching specific patterns"""
        for pattern in patterns:
            for file in self.base_dir.rglob(pattern):
                if file.is_file() and not any(
                    preserved in file.parts for preserved in self.preserved_dirs
                ):
                    try:
                        file.unlink()
                    except Exception as e:
                        print(f"Warning: Failed to delete {file}: {e}")


@pytest.fixture
def screenshot_manager():
    """Fixture that provides screenshot management for tests"""
    manager = ScreenshotManager()
    yield manager
    # Cleanup screenshots taken during this test
    manager.cleanup_test_screenshots()


@pytest.fixture(scope="session")
def screenshot_cleanup():
    """Session-scoped fixture for cleaning up all test screenshots"""
    manager = ScreenshotManager()
    yield manager
    # Clean up all test screenshots at the end of the session
    if os.getenv("KEEP_TEST_SCREENSHOTS", "false").lower() != "true":
        manager.cleanup_all_test_screenshots()


@pytest.fixture
async def screenshot_on_failure(request, page):
    """Automatically take screenshot on test failure"""
    yield
    if request.node.rep_call and request.node.rep_call.failed:
        test_name = request.node.name.replace("/", "_").replace("::", "_")
        screenshot_path = Path("tests/web/screenshots/failures")
        screenshot_path.mkdir(parents=True, exist_ok=True)
        
        try:
            await page.screenshot(
                path=str(screenshot_path / f"{test_name}_failure.png"),
                full_page=True
            )
        except Exception:
            pass  # Don't fail the test if screenshot fails


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Make test results available to fixtures"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


# Utility functions for tests
async def take_debug_screenshot(page, name: str, test_name: str = None):
    """
    Utility function for taking debug screenshots.
    
    Usage in tests:
        await take_debug_screenshot(page, "before-login", test_name=request.node.name)
    """
    screenshot_dir = Path("tests/web/screenshots/debug")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    if test_name:
        name = f"{test_name}_{name}"
    
    screenshot_path = screenshot_dir / f"{name}.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    
    return screenshot_path


async def compare_screenshots(page, reference_name: str, threshold: float = 0.95):
    """
    Compare current page to a reference screenshot.
    
    Returns:
        bool: True if screenshots match within threshold
    """
    from PIL import Image
    import numpy as np
    
    # Take current screenshot
    current_path = Path("tests/web/screenshots/current") / f"{reference_name}.png"
    current_path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(current_path))
    
    # Load reference
    reference_path = Path("tests/web/screenshots/baseline") / f"{reference_name}.png"
    if not reference_path.exists():
        print(f"Warning: No baseline screenshot found at {reference_path}")
        return False
    
    # Compare images
    try:
        current_img = np.array(Image.open(current_path))
        reference_img = np.array(Image.open(reference_path))
        
        # Simple pixel comparison (you might want more sophisticated comparison)
        if current_img.shape != reference_img.shape:
            return False
            
        # Calculate similarity
        diff = np.abs(current_img.astype(float) - reference_img.astype(float))
        similarity = 1 - (diff.sum() / (255.0 * current_img.size))
        
        return similarity >= threshold
        
    except Exception as e:
        print(f"Error comparing screenshots: {e}")
        return False


# Environment-based configuration
def should_keep_screenshots():
    """Check if screenshots should be preserved"""
    return os.getenv("KEEP_TEST_SCREENSHOTS", "false").lower() == "true"


def get_screenshot_dir():
    """Get the screenshot directory from environment or default"""
    return os.getenv("SCREENSHOT_DIR", "tests/web/screenshots")