# Manual SPA Testing Guide

## Prerequisites
- Web service running on http://localhost:8080
- Browser with developer tools

## Test Steps

### 1. Authentication Flow
1. Open http://localhost:8080 in browser
2. ✓ Should redirect to /login
3. ✓ Login form should have email and password fields
4. ✓ Form should have HTMX attributes (hx-post="/auth/login")

### 2. Navigation Without Login
1. Try to access http://localhost:8080/chat directly
2. ✓ Should redirect to /login
3. Check browser network tab - should see 303 redirect

### 3. HTMX Form Submission (if you have test credentials)
1. Enter email and password
2. Submit form
3. Check network tab - should see HTMX request
4. Should redirect to /chat without full page reload

### 4. SPA Navigation Features (after login)
1. Click on different conversations in sidebar
2. Should update main content without page reload
3. URL should update in browser
4. Active conversation should be highlighted
5. Check for smooth transitions

### 5. Browser Navigation
1. After switching conversations, try browser back button
2. Should navigate to previous conversation
3. Forward button should work too

### 6. Create New Conversation
1. Click "New Chat" button
2. Should create new conversation without page reload
3. Conversation list should update automatically

## Expected Behaviors
- ✓ No full page reloads during navigation
- ✓ Smooth fade transitions between views
- ✓ URL updates match current view
- ✓ Loading indicators appear during requests
- ✓ Active states update in sidebar

## Console Checks
Open browser console and look for:
- HTMX configuration messages
- Any JavaScript errors
- Transition animations logging

## Network Tab Checks
- HTMX requests should have "HX-Request: true" header
- Responses should be partial HTML, not full pages
- Check response times are fast