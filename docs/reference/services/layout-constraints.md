# Layout Constraints and Critical CSS Rules



This document defines the **MANDATORY** layout constraints that must NEVER be violated to prevent UI breakages.

## 🚨 CRITICAL: Layout Rules That Must Never Be Broken

### 1. Main Container Rules
```css
/* The main layout container MUST always have these classes */
.flex.h-screen {
  /* REQUIRED: Full viewport height and flexbox layout */
}

/* FORBIDDEN: Never nest multiple .flex.h-screen containers */
/* BAD: <div class="flex h-screen"><div class="flex h-screen">...</div></div> */
```

### 2. Full Width Constraints
- **Chat Interface**: Must ALWAYS use full viewport width
- **Login/Auth Pages**: Centered content is OK, but parent must be full width
- **Main Container**: Width must be >= viewport width - 20px (for scrollbars)

### 3. Sidebar Constraints
```css
#sidebar {
  width: 16rem; /* 256px - MUST be between 200-300px */
  /* Mobile: Transform translateX(-100%) when hidden */
}
```

### 4. Page-Specific Rules

#### Login Page (`/login`, `/register`)
**MUST NOT CONTAIN:**
- `#sidebar`
- `#chat-form`
- `#messages`
- `#conversation-list`
- `.mobile-header`
- `#sidebar-toggle`

#### Chat Page (`/chat`)
**MUST CONTAIN:**
- Exactly ONE `.flex.h-screen` container
- `#sidebar` (can be hidden on mobile)
- `#main-content` filling remaining space
- `#chat-form` at bottom

### 5. HTMX Navigation Rules
- Layout dimensions MUST remain constant during HTMX swaps
- Use `innerHTML` swap for content areas, not layout containers
- Auth redirects MUST use `HX-Redirect` header, not content swaps

### 6. Responsive Breakpoints
```css
/* Mobile: < 768px */
@media (max-width: 767px) {
  #sidebar { transform: translateX(-100%); } /* Hidden by default */
  .mobile-header { display: block; }
}

/* Tablet: 768px - 1023px */
@media (min-width: 768px) and (max-width: 1023px) {
  #sidebar { width: 14rem; } /* Slightly narrower */
}

/* Desktop: >= 1024px */
@media (min-width: 1024px) {
  #sidebar { width: 16rem; }
  .mobile-header { display: none; }
}
```

## 🛡️ Layout Protection Checklist

Before ANY deployment or code change:

1. **Run Layout Integrity Tests**
   ```bash
   pytest tests/web/test_layout_integrity.py -v
   ```

2. **Check Visual Regression**
   ```bash
   pytest tests/web/test_layout_integrity.py::TestVisualRegression -v
   ```

3. **Verify No Nested Containers**
   - Search for duplicate `.flex.h-screen` classes
   - Ensure single root layout container

4. **Test HTMX Navigation**
   - Click "New Chat" - layout must not change
   - Switch conversations - layout must not change
   - Session timeout - must redirect, not embed login

## 🔍 Common Layout Bugs and Fixes

### Bug: Mobile Width on Desktop (The Classic Bug)
**Symptoms:**
- Chat shows at ~375px width on 1920px screen
- Sidebar and main content squeezed into narrow column

**Causes:**
1. Nested layout containers
2. Missing/incorrect container classes
3. HTMX swapping entire layout instead of content

**Fix:**
1. Ensure single `.flex.h-screen` root container
2. Check auth middleware returns `HX-Redirect` for HTMX requests
3. Verify no page mixing (login elements in chat page)

### Bug: Login Page Shows Chat Elements
**Symptoms:**
- Sidebar visible on login page
- Chat input on auth pages

**Causes:**
1. Incorrect `show_sidebar` parameter
2. Layout function not respecting parameters
3. Cached/stale content

**Fix:**
1. Verify `show_sidebar=False` in auth routes
2. Check layout function's else branch
3. Clear session and browser cache

## 📋 Pre-Deployment Validation Script

Add to your deployment pipeline:

```bash
#!/bin/bash
# layout-check.sh

echo "🔍 Running Layout Integrity Checks..."

# 1. Run layout tests
pytest tests/web/test_layout_integrity.py -v || exit 1

# 2. Check for forbidden patterns
echo "Checking for nested containers..."
if grep -r "flex h-screen.*flex h-screen" app/services/web/; then
  echo "❌ ERROR: Nested layout containers found!"
  exit 1
fi

# 3. Validate auth pages don't have chat elements
echo "Validating auth page isolation..."
if grep -E "(#sidebar|#chat-form)" app/services/web/routes/auth.py; then
  echo "⚠️ WARNING: Auth routes may contain chat elements"
fi

echo "✅ Layout integrity checks passed!"
```

## 🚀 Preventing Future Breakages

1. **Code Review Checklist**
   - [ ] No nested `.flex.h-screen` containers
   - [ ] Auth pages use `show_sidebar=False`
   - [ ] HTMX swaps target content, not layout
   - [ ] Full viewport width maintained

2. **Testing Requirements**
   - [ ] Layout integrity tests pass
   - [ ] Visual regression tests pass
   - [ ] Manual test at 375px, 768px, 1920px widths
   - [ ] HTMX navigation preserves layout

3. **Monitoring**
   - Track layout dimensions in production
   - Alert on container width < viewport - 20px
   - Screenshot key pages after deployment

## 🎯 Golden Rule

**If the chat interface ever appears narrower than the viewport, STOP and check:**
1. Is there only ONE `.flex.h-screen` container?
2. Are auth and chat pages properly separated?
3. Is HTMX swapping content or layout?

Remember: The layout that works is sacred. Don't touch it without running ALL tests!