# Shared Test User Implementation

## Overview
Implemented a single shared test user (`pytest@aeonia.ai`) for the entire test suite to dramatically reduce email sending and improve test efficiency.

## Changes Made

### 1. Updated TestUserFactory
- Added `send_email: False` parameter to prevent ALL emails when creating test users
- Location: `tests/fixtures/test_auth.py`

### 2. Modified conftest.py
- Changed shared test user email from `shared-test-user@test.local` to `pytest@aeonia.ai`
- Password: `PyTest-Aeonia-2025!`
- Session-scoped fixture creates user once per test run
- Location: `tests/conftest.py`

### 3. Updated E2E Tests
- `test_e2e_real_auth.py`: Now uses `shared_test_user` fixture instead of creating new users
- `test_browser_registration.py`: Changed from registration test to login test with shared user
- Registration tests now verify that the shared user "already exists" error

## Benefits

### Before:
- ~70+ test users created per test run
- ~70+ confirmation emails sent to Supabase
- Risk of email bounce/restriction issues
- Slower test execution

### After:
- 1 test user created per test run
- 0-1 emails sent (only on first run if user doesn't exist)
- No email bounce issues
- Faster test execution
- Consistent test data

## Usage

### In Tests:
```python
@pytest.mark.asyncio
async def test_something(shared_test_user):
    """Test using the shared user"""
    email = shared_test_user["email"]      # pytest@aeonia.ai
    password = shared_test_user["password"]  # PyTest-Aeonia-2025!
    user_id = shared_test_user["user_id"]
```

### Manual Testing:
- Email: `pytest@aeonia.ai`
- Password: `PyTest-Aeonia-2025!`
- This user is pre-verified and ready to use

## Implementation Notes

1. The shared user is created once at the start of the test session
2. If the user already exists (from a previous run), we reuse it
3. We intentionally DON'T delete the user after tests to avoid recreation
4. The `send_email: False` flag prevents any confirmation emails
5. All E2E tests now share this single user instead of creating their own

## Remaining Work

Some tests may still attempt UI registration that sends emails:
- `test_real_e2e_with_supabase.py`
- `test_real_auth_browser.py`
- Other browser tests that fill registration forms

These should be updated to use the shared test user as well.