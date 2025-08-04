"""
End-to-End (E2E) Test Suite for GAIA Platform

IMPORTANT E2E TESTING PRINCIPLES:
=================================

1. NO MOCKS ALLOWED
   - E2E tests MUST use real services (Supabase, chat service, etc.)
   - If you need to mock, you're writing an integration test, not E2E
   - Use real authentication, real databases, real AI responses

2. Real User Flows
   - E2E tests should simulate actual user behavior
   - Start from login, perform actions, verify results
   - Test the full stack from browser to database

3. Clean Up After Tests
   - Always clean up test users and data
   - Use TestUserFactory.cleanup_test_user() in finally blocks
   - Don't pollute production databases

4. Handle Async Operations
   - Real services have latency - use appropriate waits
   - Don't use arbitrary sleep() - wait for specific conditions
   - Example: wait_for_selector() instead of wait_for_timeout()

5. Test Real Scenarios
   - New user experience (empty state)
   - Existing user with data
   - Error conditions and recovery
   - Cross-browser compatibility

BAD Example (uses mocks):
```python
# L WRONG - This is NOT an E2E test
async def test_chat(self):
    await page.route("**/api/chat", lambda route: route.fulfill(
        json={"response": "Mocked response"}
    ))
```

GOOD Example (uses real services):
```python
#  CORRECT - Real E2E test
async def test_chat(self):
    # Create real user
    user = factory.create_verified_test_user()
    
    # Real login
    await page.fill('input[name="email"]', user["email"])
    await page.fill('input[name="password"]', user["password"])
    await page.click('button[type="submit"]')
    
    # Real chat message
    await page.fill('input[name="message"]', "Hello")
    await page.keyboard.press("Enter")
    
    # Wait for real AI response
    await page.wait_for_selector('.assistant-message')
```

Remember: E2E tests are slow but valuable. They catch real issues that
unit and integration tests miss. Keep them focused on critical user journeys.
"""