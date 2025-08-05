# Screenshot Cleanup Migration Guide

This guide explains how to update existing tests to use the new screenshot cleanup fixtures.

## Overview

The new screenshot cleanup system ensures that test-generated screenshots are automatically cleaned up after test runs, while preserving baseline/reference screenshots for visual regression testing.

## Key Features

1. **Automatic Cleanup**: Screenshots are deleted after tests complete
2. **Preservation Options**: Keep screenshots for debugging with environment variables
3. **Organized Structure**: Screenshots are organized into appropriate directories
4. **Failure Capture**: Automatic screenshots on test failures
5. **Visual Regression Support**: Baseline screenshots are never deleted

## Migration Steps

### 1. Update Test Imports

Add the screenshot fixtures to your test imports:

```python
# Old pattern
import pytest
from playwright.async_api import async_playwright

# New pattern
import pytest
from playwright.async_api import async_playwright
from tests.fixtures.screenshot_cleanup import (
    screenshot_manager,
    take_debug_screenshot,
    compare_screenshots
)
```

### 2. Replace Direct Screenshot Calls

#### For Debug Screenshots

**Old Pattern:**
```python
await page.screenshot(path="tests/web/screenshots/login-test.png")
```

**New Pattern:**
```python
# Option 1: Using screenshot manager (auto-cleanup)
def test_login(screenshot_manager):
    screenshot_manager.take_screenshot(page, "login-test.png")

# Option 2: Using debug utility (respects KEEP_TEST_SCREENSHOTS)
async def test_login(page, request):
    await take_debug_screenshot(page, "login-test", test_name=request.node.name)
```

#### For Failure Screenshots

**Old Pattern:**
```python
try:
    # test code
except Exception:
    await page.screenshot(path="tests/web/screenshots/failure.png")
    raise
```

**New Pattern:**
```python
@pytest.mark.screenshot
async def test_something(page, screenshot_on_failure):
    # test code - screenshot automatically taken on failure
    assert something_that_might_fail()
```

### 3. Organize Screenshot Directories

The new structure organizes screenshots into subdirectories:

```
tests/web/screenshots/
├── baseline/       # Reference screenshots (never deleted)
├── current/        # Current test run screenshots
├── debug/          # Debug screenshots
├── failures/       # Automatic failure screenshots
└── *.png          # Legacy screenshots (will be cleaned)
```

### 4. Add Test Markers

Mark tests that take screenshots:

```python
@pytest.mark.screenshot
async def test_visual_check(page):
    # Test that takes screenshots
    pass

@pytest.mark.screenshot
@pytest.mark.keep_screenshots
async def test_important_visual(page):
    # Screenshots from this test are preserved
    pass
```

### 5. Update CI/CD Configuration

Update your CI/CD scripts to handle screenshot artifacts:

```yaml
# GitHub Actions example
- name: Run tests
  run: |
    # Keep screenshots in CI for debugging
    KEEP_TEST_SCREENSHOTS=true pytest tests/e2e/
    
- name: Upload screenshots
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: test-screenshots
    path: tests/web/screenshots/
```

## Environment Variables

- `KEEP_TEST_SCREENSHOTS=true` - Preserve all test screenshots
- `SCREENSHOT_DIR=/custom/path` - Use custom screenshot directory

## Examples

### Example 1: Simple Test Update

**Before:**
```python
async def test_login_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto("http://localhost:8000/login")
        await page.screenshot(path="tests/web/screenshots/before-login.png")
        
        # ... test logic ...
        
        await page.screenshot(path="tests/web/screenshots/after-login.png")
        await browser.close()
```

**After:**
```python
@pytest.mark.screenshot
async def test_login_flow(screenshot_manager):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto("http://localhost:8000/login")
        screenshot_manager.take_screenshot(page, "before-login.png", subdir="login")
        
        # ... test logic ...
        
        screenshot_manager.take_screenshot(page, "after-login.png", subdir="login")
        await browser.close()
```

### Example 2: Visual Regression Test

```python
@pytest.mark.screenshot
async def test_login_page_layout(page):
    await page.goto("http://localhost:8000/login")
    
    # Compare against baseline
    matches = await compare_screenshots(page, "login-layout", threshold=0.95)
    assert matches, "Login page layout has changed"
```

### Example 3: Debugging with Preserved Screenshots

```python
@pytest.mark.screenshot
@pytest.mark.keep_screenshots
async def test_complex_interaction(page, request):
    """Complex test where we want to keep screenshots for analysis"""
    
    await page.goto("http://localhost:8000")
    
    # Take multiple debug screenshots
    for i in range(5):
        await page.click(f"#button-{i}")
        await take_debug_screenshot(
            page, 
            f"step-{i}", 
            test_name=request.node.name
        )
```

## Running Tests

```bash
# Run tests with automatic cleanup (default)
pytest tests/e2e/

# Run tests and keep screenshots for debugging
KEEP_TEST_SCREENSHOTS=true pytest tests/e2e/

# Run only tests that take screenshots
pytest -m screenshot

# Run visual regression tests
pytest -m "screenshot and not keep_screenshots"
```

## Best Practices

1. **Use subdirectories** to organize screenshots by feature or test type
2. **Include test names** in screenshot filenames for easier debugging
3. **Mark visual regression tests** to distinguish them from debug screenshots
4. **Clean up old patterns** to prevent accumulation of untracked screenshots
5. **Document screenshot purposes** in test comments

## Troubleshooting

### Screenshots Not Being Cleaned Up

Check that:
1. Tests are using the screenshot fixtures
2. `KEEP_TEST_SCREENSHOTS` is not set to `true`
3. Screenshots are not in preserved directories (baseline, reference)

### Screenshots Not Being Created

Verify:
1. The screenshot directory exists and is writable
2. The page object is valid when taking the screenshot
3. The fixture is properly imported and used

### Baseline Screenshots Missing

Ensure:
1. Baseline screenshots are committed to the repository
2. They are in the `tests/web/screenshots/baseline/` directory
3. The filename matches exactly in `compare_screenshots()`