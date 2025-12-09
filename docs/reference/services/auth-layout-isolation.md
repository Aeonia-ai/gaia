# Auth Layout Isolation Rules



## 🚨 CRITICAL: Auth Page Layout Isolation

**NEVER MIX AUTH CONTENT WITH LAYOUT ELEMENTS**

### The Core Problem
When showing email verification, password reset, or other auth messages, developers often add content to existing forms instead of replacing them entirely. This creates the dreaded "mobile width on desktop" bug and form duplication.

### WRONG ❌
```python
# This ADDS verification message to existing form
return Div(
    Div("📧 Check Your Email"),
    Div(f"We've sent a verification link to: {email}")
)
# Result: Email field + password field + verification message = BROKEN
```

### RIGHT ✅
```python
# This REPLACES the entire auth area with clean verification page
from app.services.web.utils.layout_isolation import auth_page_replacement

return auth_page_replacement(
    title="Check Your Email",
    content=f"We've sent a verification link to: {email}",
    show_sidebar=False  # Critical: auth pages never show sidebar
)
```

## Standard Auth Layout Patterns

### 1. Email Verification Page
```python
def email_verification_response(email: str):
    """Returns complete auth page replacement for email verification"""
    return auth_page_replacement(
        title="📧 Check Your Email",
        content=[
            f"We've sent a verification link to: {email}",
            "Please check your email and click the verification link to activate your account."
        ],
        actions=[
            ("Resend verification", "/auth/resend-verification", {"email": email}),
            ("Back to login", "/login", None)
        ]
    )
```

### 2. Password Reset Page
```python
def password_reset_response(email: str):
    """Returns complete auth page replacement for password reset"""
    return auth_page_replacement(
        title="🔑 Reset Password",
        content=f"We've sent a password reset link to: {email}",
        actions=[("Back to login", "/login", None)]
    )
```

### 3. Error State Page
```python
def auth_error_response(message: str):
    """Returns complete auth page replacement for errors"""
    return auth_page_replacement(
        title="⚠️ Authentication Error",
        content=message,
        actions=[("Try again", "/login", None)]
    )
```

## HTMX Target Rules

### Auth Form Replacement (Complete)
```python
# Target the entire auth container for complete replacement
hx_target="#auth-container"
hx_swap="outerHTML"
```

### Message Area Only (Partial)
```python
# Only for non-critical messages that don't change the form
hx_target="#auth-message"
hx_swap="innerHTML"
# ⚠️ WARNING: Never use this for verification/success states
```

## Layout Validation Checklist

Before ANY auth change, verify:

- [ ] `show_sidebar=False` for ALL auth routes
- [ ] No sidebar, chat, or main app elements on auth pages
- [ ] Verification states replace forms, don't add to them
- [ ] HTMX targets use `outerHTML` for major state changes
- [ ] Auth pages redirect with `HX-Redirect` for navigation

## Code Review Requirements

**Auth Route Changes MUST:**

1. Use `auth_page_replacement()` for state changes
2. Include layout isolation test
3. Pass `pytest tests/web/test_layout_integrity.py::test_auth_isolation`
4. Have manual verification at mobile + desktop sizes

**Automatic Rejection Criteria:**

- Any auth route returning `Div()` without `auth_page_replacement()`
- Missing `show_sidebar=False` parameter
- HTMX swap using `innerHTML` for verification states
- Auth pages containing `#sidebar`, `#chat-form`, or layout elements

## Testing Requirements

```bash
# Required before ANY auth change
pytest tests/web/test_layout_integrity.py::test_auth_isolation -v

# Visual verification
./scripts/test-auth-layout.sh --mobile --desktop
```

## Emergency Fix Pattern

If auth layout breaks in production:

```python
# Step 1: Immediate isolation
return auth_page_replacement(
    title="Temporary Fix",
    content="Please contact support",
    show_sidebar=False  # Critical
)

# Step 2: Proper fix with tests
# (Follow this document)
```

## Why This Matters

**Layout bugs cost us:**
- Development time (recurring fixes)
- User trust (broken UX)
- Support burden (confused users)
- Technical debt (inconsistent patterns)

**Prevention is 10x cheaper than fixes.**