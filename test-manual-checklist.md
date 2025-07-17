# Mobile Sidebar Manual Testing Checklist

## Browser Testing Instructions

### 1. Open Developer Tools
- Navigate to: `http://localhost:8080/chat`
- Press F12 (or Cmd+Option+I on Mac)
- Click device toolbar icon 📱

### 2. Mobile Testing (< 768px width)

**Set device to iPhone SE (375px) and test:**

#### Visual Elements
- [ ] Hamburger menu visible in top-left corner
- [ ] Mobile header bar with logo and user avatar
- [ ] Sidebar hidden by default
- [ ] Send button shows arrow (→) instead of "Send"
- [ ] No horizontal scrolling

#### Interaction Testing
- [ ] Click hamburger menu → sidebar slides in from left
- [ ] Click X button in sidebar → sidebar closes
- [ ] Click dark overlay → sidebar closes
- [ ] Sidebar animation is smooth (300ms transition)
- [ ] Background doesn't scroll when sidebar is open

#### Touch Simulation (if available)
- [ ] Swipe right from left edge → opens sidebar
- [ ] Swipe left on open sidebar → closes sidebar
- [ ] Tap conversation item → closes sidebar and navigates

### 3. Tablet Testing (768px - 1024px)

**Set device to iPad (768px) and test:**

- [ ] Sidebar becomes visible
- [ ] Hamburger menu disappears
- [ ] Layout transitions smoothly
- [ ] Send button shows "Send" text

### 4. Desktop Testing (> 1024px)

**Set device to responsive mode with 1200px width:**

- [ ] Full sidebar always visible
- [ ] No mobile header
- [ ] Traditional desktop layout
- [ ] All functionality works normally

### 5. Window Resize Testing

- [ ] Drag browser window from wide to narrow
- [ ] Layout adapts at 768px breakpoint
- [ ] No layout breaks or glitches
- [ ] Sidebar state resets appropriately

### 6. Auth Pages Testing

**Test mobile responsiveness on auth pages:**

- [ ] Visit `http://localhost:8080/login`
- [ ] Set mobile view (375px)
- [ ] Form should be touch-friendly
- [ ] Input fields prevent zoom on iOS
- [ ] Buttons are minimum 44px height

## Expected Behavior Summary

### Mobile (< 768px)
- Hidden sidebar with hamburger toggle
- Slide-in animation with backdrop
- Touch-friendly sizing throughout
- Auto-close on navigation

### Desktop (≥ 768px)  
- Always-visible sidebar
- Traditional chat layout
- No mobile-specific elements

## Common Issues to Watch For

- [ ] Sidebar doesn't get stuck open/closed
- [ ] No horizontal scrolling on mobile
- [ ] Animations are smooth, not jerky
- [ ] Touch targets are large enough (44px minimum)
- [ ] Text remains readable at all sizes
- [ ] No content overlapping or cutoff

## Performance Notes

- [ ] Initial page load feels fast
- [ ] Sidebar animations don't cause lag
- [ ] Touch responsiveness feels immediate
- [ ] No console errors in browser dev tools

---

✅ **If all items are checked, the mobile sidebar is working correctly!**