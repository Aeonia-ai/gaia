# 🎭 Manual Web UI Testing Checklist

Use this checklist for quick manual verification of web UI functionality.

## 🔐 Authentication Flow Tests

### Login Tests
- [ ] **Valid Login**: Use `admin@aeonia.ai` / `auVwGUGt7GHAnv6nFxR8`
  - Should redirect to `/chat`
  - Should show "Welcome back, admin!"
  - Should show user email in header

- [ ] **Invalid Login**: Use wrong credentials
  - Should stay on login page
  - Should show error message
  - Should not redirect

- [ ] **Empty Fields**: Click Sign In without filling fields
  - Should show validation errors
  - Should not submit form

- [ ] **Session Persistence**: Login, refresh page
  - Should remain logged in
  - Should not redirect to login

### Logout Tests
- [ ] **Logout Flow**: Click "Logout" link
  - Should redirect to login page
  - Should clear session
  - Refreshing should not auto-login

## 🧭 Navigation Tests

- [ ] **New Chat Button**: Click "New Chat"
  - Should show welcome message
  - Should clear conversation view
  - Should show empty message input

- [ ] **Conversation List Navigation**: Click existing conversations
  - Should load conversation messages
  - Should update URL with conversation ID
  - Should highlight active conversation

- [ ] **Profile Page**: Click "Profile" link
  - Should navigate to profile page
  - Back button should return to chat

- [ ] **Browser Navigation**: Use back/forward buttons
  - Should work correctly
  - Should maintain state

## 💬 Conversation Management

### Creating Conversations
- [ ] **New Conversation**: Start fresh conversation
  - Click "New Chat"
  - Type message and send
  - Should create new conversation in list
  - Should show conversation with proper title

- [ ] **Conversation Titles**: Check title generation
  - Should use first 50 characters of message
  - Should truncate long messages with "..."
  - Should handle Unicode characters

### Managing Conversations
- [ ] **Delete Conversations**: Click "×" button
  - Should remove conversation from list
  - Should update list immediately
  - Should not affect other conversations

- [ ] **Search Conversations**: Use search box
  - Should filter conversation list
  - Should work with partial matches
  - Should clear when search is cleared

## 📝 Message Tests

### Basic Messaging
- [ ] **Simple Text**: Send "Hello, how are you?"
  - Should show "Message sent successfully!"
  - Should display user message with timestamp
  - Should show "Gaia is thinking..." indicator
  - Should receive AI response

- [ ] **Empty Message**: Try to send empty message
  - Should show "Please enter a message" error
  - Should not send message

### Message Content Variations
- [ ] **Long Message**: Send 500+ character message
  - Should send successfully
  - Should display properly without breaking layout

- [ ] **Special Characters**: Send `!@#$%^&*()_+-=[]{}|;':\",./<>?`
  - Should display exactly as typed
  - Should not break HTML rendering

- [ ] **Unicode/Emoji**: Send `🚀 Hello 世界 مرحبا העולם`
  - Should display all characters correctly
  - Should maintain proper encoding

- [ ] **Code Blocks**: Send ```python\nprint("hello")```
  - Should format as code if supported
  - Should preserve formatting

### Message Flow
- [ ] **Rapid Sending**: Send 3 messages quickly
  - Should handle all messages
  - Should maintain order
  - Should not cause conflicts

- [ ] **Streaming Responses**: Send complex question
  - Should show thinking indicator
  - Should stream response content
  - Should show complete response when done

## 🎨 UI Responsiveness

### Different Screen Sizes
- [ ] **Mobile (375px)**: Resize to phone size
  - Layout should adapt
  - All functionality should work
  - Text should be readable

- [ ] **Tablet (768px)**: Resize to tablet size
  - Should use appropriate layout
  - Sidebar behavior should be optimal

- [ ] **Desktop (1920px)**: Full desktop size
  - Should use full screen effectively
  - Should not have excessive white space

### UI State
- [ ] **Scrolling**: In conversation with many messages
  - Should scroll smoothly
  - Should auto-scroll to bottom when new message arrives
  - Should maintain scroll position when appropriate

- [ ] **Loading States**: During various operations
  - Should show appropriate loading indicators
  - Should disable actions during loading
  - Should handle loading failures gracefully

## ⚠️ Error Handling

### Network Issues
- [ ] **Disconnect Network**: Disable internet, try to send message
  - Should show connection error
  - Should allow retry when connection restored

- [ ] **Server Errors**: Simulate 500 errors (if possible)
  - Should show appropriate error messages
  - Should not crash the application

### Session Issues
- [ ] **Session Expiry**: Clear cookies, try to use app
  - Should detect expired session
  - Should redirect to login
  - Should show session expired message

## ⚡ Performance Checks

### Loading Times
- [ ] **Initial Page Load**: Fresh visit to `/login`
  - Should load within 3 seconds
  - Should be responsive immediately

- [ ] **Conversation Loading**: Open conversation with many messages
  - Should load within 5 seconds
  - Should not freeze browser

- [ ] **Message Response Time**: Send message
  - Should acknowledge within 1 second
  - Should start streaming within 5 seconds

### Resource Usage
- [ ] **Memory Usage**: Use for extended period
  - Should not continuously increase memory
  - Should handle long sessions (30+ minutes)

- [ ] **Network Efficiency**: Monitor network tab
  - Should not make unnecessary requests
  - Should use appropriate caching

## ♿ Accessibility

### Keyboard Navigation
- [ ] **Tab Navigation**: Use only keyboard
  - Should be able to navigate all interactive elements
  - Tab order should be logical
  - Focus should be visible

- [ ] **Keyboard Shortcuts**: Test common shortcuts
  - Enter should send messages
  - Escape should close modals/dialogs

### Screen Reader Support
- [ ] **ARIA Labels**: Check with screen reader or inspect
  - Buttons should have descriptive labels
  - Form fields should have proper labels
  - Dynamic content should announce changes

## 🔬 Edge Cases

### Boundary Conditions
- [ ] **Very Long Conversation Title**: Send 1000+ character message
  - Should truncate title appropriately
  - Should not break layout

- [ ] **Many Conversations**: Create 50+ conversations
  - List should handle large numbers
  - Performance should remain acceptable
  - Search should work correctly

### Concurrent Usage
- [ ] **Multiple Tabs**: Open app in multiple tabs
  - Should maintain consistent state
  - Actions in one tab should not break others

### Browser Compatibility
- [ ] **Different Browsers**: Test in Chrome, Firefox, Safari
  - Should work consistently
  - Should handle browser-specific features

## 🛡️ Security

### Input Validation
- [ ] **XSS Prevention**: Try `<script>alert('xss')</script>`
  - Should not execute JavaScript
  - Should display as plain text

- [ ] **HTML Injection**: Try `<img src=x onerror=alert(1)>`
  - Should not render as HTML
  - Should escape properly

### Authentication Security
- [ ] **Direct URL Access**: Try accessing `/chat` without login
  - Should redirect to login
  - Should not show any private content

---

## 📊 Test Results Summary

**Date**: ________________

**Tester**: ________________

### Results Overview
- **Total Tests**: _____ / _____
- **Passed**: _____
- **Failed**: _____
- **Skipped**: _____

### Critical Issues Found
1. ________________________________________________
2. ________________________________________________
3. ________________________________________________

### Performance Issues
1. ________________________________________________
2. ________________________________________________
3. ________________________________________________

### Recommendations
1. ________________________________________________
2. ________________________________________________
3. ________________________________________________

---

## 🚀 Quick Test Commands

For automated testing with Playwright:

```bash
# Install Playwright
pip install playwright
playwright install

# Run all tests
pytest tests/e2e/test_webui_comprehensive.py -v

# Run specific category
pytest tests/e2e/test_webui_comprehensive.py -k "test_login" -v

# Run with HTML report
pytest tests/e2e/test_webui_comprehensive.py --html=report.html

# Run in parallel
pytest tests/e2e/test_webui_comprehensive.py -n auto
```