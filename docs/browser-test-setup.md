# Browser Test Setup Guide

This guide explains how to properly configure and run the Playwright browser tests for the Gaia platform.

## Overview

The Gaia platform includes browser-based integration tests using Playwright to verify:
- Layout integrity at different viewport sizes
- HTMX navigation behavior
- Visual regression testing
- Responsive design breakpoints

These tests are currently skipped by default in the Docker test container due to environment configuration requirements.

## Running Browser Tests

### Option 1: Docker Compose (Recommended)

To run browser tests in the Docker environment:

1. **Set environment variable**:
   ```bash
   RUN_BROWSER_TESTS=true docker compose run --rm test pytest tests/web/test_layout_integrity.py -v
   ```

2. **Ensure services are running**:
   ```bash
   docker compose up -d web-service gateway auth-service
   ```

3. **Wait for services to be ready**:
   ```bash
   ./scripts/test.sh --local health
   ```

### Option 2: Local Development

For local development with browser tests:

1. **Install Playwright**:
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **Set web service URL**:
   ```bash
   export WEB_SERVICE_URL=http://localhost:8080
   ```

3. **Run tests**:
   ```bash
   pytest tests/web/test_layout_integrity.py -v -k browser
   ```

## Test Categories

### Unit Tests (Always Run)
- `TestAuthLayoutIsolation` - Component isolation rules
- `TestHTMXSafety` - HTMX response safety checks

### Browser Tests (Require Setup)
- `test_chat_layout_full_width` - Full viewport usage
- `test_responsive_breakpoints` - Mobile/tablet/desktop layouts
- `test_htmx_navigation_preserves_layout` - Navigation stability
- `test_no_nested_layouts` - Prevent layout nesting bugs
- `test_capture_baseline_screenshots` - Visual regression baselines
- `test_layout_dimensions_tracking` - Layout metrics tracking

## Configuration

### Environment Variables

- `RUN_BROWSER_TESTS`: Set to `true` to run browser tests
- `WEB_SERVICE_URL`: Override the web service URL for tests
- `SKIP_BROWSER_TESTS`: Set to `true` to explicitly skip browser tests

### Docker Configuration

The test container includes:
- Playwright with Chromium
- Required system dependencies
- Headless browser support

### Network Configuration

In Docker Compose, services communicate via:
- `web-service:8000` - Web frontend
- `gateway:8000` - API gateway
- `auth-service:8000` - Authentication

## Troubleshooting

### Tests Timing Out

If browser tests timeout:

1. **Check service health**:
   ```bash
   curl http://localhost:8080/health
   ```

2. **Verify network connectivity**:
   ```bash
   docker compose exec test curl http://web-service:8000/health
   ```

3. **Check browser launch**:
   ```bash
   docker compose run --rm test python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(headless=True); print('Browser OK')"
   ```

### Visual Regression Tests

Visual tests require:
1. Baseline screenshots in `tests/web/screenshots/baseline/`
2. Consistent viewport sizes
3. Stable rendering (wait for animations)

## Future Improvements

1. **GitHub Actions Integration**: Run browser tests in CI/CD
2. **Multiple Browser Support**: Test on Firefox and WebKit
3. **Performance Metrics**: Capture rendering performance
4. **Accessibility Testing**: Add automated a11y checks
5. **Cross-browser Screenshots**: Visual testing across browsers

## Running Specific Browser Tests

To run individual browser tests when properly configured:

```bash
# Chat layout test
pytest tests/web/test_layout_integrity.py::TestLayoutIntegrity::test_chat_layout_full_width -v

# Responsive design test
pytest tests/web/test_layout_integrity.py::TestLayoutIntegrity::test_responsive_breakpoints -v

# Visual regression
pytest tests/web/test_layout_integrity.py::TestVisualRegression::test_capture_baseline_screenshots -v
```

## Best Practices

1. **Always run services first**: Browser tests need live services
2. **Use headless mode**: More stable in containers
3. **Add waits for dynamic content**: HTMX and animations need time
4. **Capture screenshots on failure**: Helps debug issues
5. **Test multiple viewports**: Mobile, tablet, desktop

## Related Documentation

- [Testing and Quality Assurance Guide](testing-and-quality-assurance.md)
- [HTMX + FastHTML Debugging Guide](htmx-fasthtml-debugging-guide.md)
- [Layout Constraints Guide](layout-constraints.md)