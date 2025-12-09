# Mobile Testing Guide for Gaia Web UI



## Overview
This guide documents best practices and methods for testing the mobile-responsive features of the Gaia FastHTML web interface.

## Mobile Features Implemented

### 1. Responsive Layout
- **Breakpoint**: 768px (Tailwind's `md:` prefix)
- **Mobile**: < 768px width
- **Desktop**: ≥ 768px width

### 2. Mobile-Specific UI Elements
- **Hamburger Menu**: Three-line menu icon that toggles sidebar visibility
- **Sidebar Overlay**: Dark overlay that appears behind sidebar on mobile
- **Touch Gestures**: Tap overlay to close sidebar
- **User Dropdown**: Avatar button with dropdown menu for profile/logout
- **Responsive Forms**: Full-width inputs and buttons on mobile

### 3. CSS Classes for Mobile
```css
/* Mobile-only elements */
.md:hidden  /* Visible on mobile, hidden on desktop */
.hidden.md:block  /* Hidden on mobile, visible on desktop */

/* Responsive spacing */
.p-4.md:p-6  /* Smaller padding on mobile */
.text-sm.md:text-base  /* Smaller text on mobile */
```

## Testing Methods

### 1. Browser Developer Tools
**Chrome/Edge DevTools**:
1. Open DevTools (F12)
2. Click "Toggle device toolbar" (Ctrl+Shift+M)
3. Select device preset or set custom dimensions
4. Test interactions and responsiveness

**Recommended Presets**:
- iPhone SE (375×667)
- iPhone X/XS (375×812)
- iPhone 14 Pro Max (430×932)
- Pixel 5 (393×851)
- Samsung Galaxy S20 (360×800)

### 2. Simple HTML Test File
Create `mobile-test.html`:
```html
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mobile UI Test</title>
    <style>
        body { 
            margin: 0; 
            padding: 20px;
            font-family: system-ui, -apple-system, sans-serif;
        }
        .test-frame {
            width: 375px;
            height: 812px;
            border: 16px solid #333;
            border-radius: 36px;
            overflow: hidden;
            margin: 0 auto;
            box-shadow: 0 0 20px rgba(0,0,0,0.3);
        }
        iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
        .controls {
            text-align: center;
            margin: 20px 0;
        }
        button {
            padding: 10px 20px;
            margin: 0 5px;
            font-size: 16px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="controls">
        <button onclick="setDevice('iphone-se')">iPhone SE</button>
        <button onclick="setDevice('iphone-x')">iPhone X</button>
        <button onclick="setDevice('ipad')">iPad</button>
        <button onclick="setDevice('android')">Android</button>
    </div>
    
    <div class="test-frame" id="frame">
        <iframe src="http://localhost:8080" id="mobile-view"></iframe>
    </div>
    
    <script>
        function setDevice(device) {
            const frame = document.getElementById('frame');
            const devices = {
                'iphone-se': { width: 375, height: 667 },
                'iphone-x': { width: 375, height: 812 },
                'ipad': { width: 768, height: 1024 },
                'android': { width: 360, height: 800 }
            };
            
            const { width, height } = devices[device];
            frame.style.width = width + 'px';
            frame.style.height = height + 'px';
        }
    </script>
</body>
</html>
```

### 3. Automated Testing Script
```bash
#!/bin/bash
# test-mobile-view.sh

echo "Testing mobile responsiveness..."

# Test with different viewport sizes
VIEWPORTS=(
    "375,667,iPhone SE"
    "375,812,iPhone X"
    "390,844,iPhone 14"
    "360,800,Android"
    "768,1024,iPad"
)

for viewport in "${VIEWPORTS[@]}"; do
    IFS=',' read -r width height device <<< "$viewport"
    echo "Testing $device ($width×$height)..."
    
    # Use puppeteer or playwright for automated screenshots
    # Example with curl for basic testing
    curl -H "User-Agent: Mobile" \
         -H "X-Viewport-Width: $width" \
         "http://localhost:8080" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✓ $device loads successfully"
    else
        echo "✗ $device failed to load"
    fi
done
```

### 4. Manual Testing Checklist

#### Login Page
- [ ] Form is centered and responsive
- [ ] Input fields are full-width
- [ ] Text is readable without zooming
- [ ] Buttons are large enough for touch

#### Chat Page
- [ ] Hamburger menu is visible (mobile only)
- [ ] Sidebar is hidden by default (mobile)
- [ ] User avatar button is accessible
- [ ] Chat input is responsive
- [ ] Messages display correctly

#### Interactions
- [ ] Hamburger menu opens sidebar
- [ ] Clicking overlay closes sidebar
- [ ] User dropdown menu works
- [ ] Profile link navigates correctly
- [ ] Logout works properly

#### Profile Page
- [ ] Content stacks vertically on mobile
- [ ] Forms are responsive
- [ ] Navigation back to chat works

### 5. Using iOS Simulator
```bash
# Install Xcode (macOS only)
xcode-select --install

# Open iOS Simulator
open -a Simulator

# In Simulator, open Safari and navigate to:
# http://localhost:8080

# Test different devices via:
# Device > iOS > iPhone model
```

### 6. Using Android Emulator
```bash
# Install Android Studio
# Create AVD (Android Virtual Device)
# Start emulator
emulator -avd Pixel_5_API_30

# In emulator Chrome, navigate to:
# http://10.0.2.2:8080  # Special IP for localhost
```

## Common Issues and Solutions

### 1. Hamburger Menu Not Working
**Issue**: Clicking hamburger doesn't open sidebar
**Solution**: Check JavaScript function and CSS classes
```javascript
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    sidebar.classList.toggle('-translate-x-full');
    overlay.style.display = overlay.style.display === 'none' ? 'block' : 'none';
}
```

### 2. Layout Overflow on Mobile
**Issue**: Content extends beyond viewport
**Solution**: Use responsive width classes
```html
<!-- Bad -->
<div class="w-[800px]">

<!-- Good -->
<div class="w-full max-w-4xl">
```

### 3. Touch Targets Too Small
**Issue**: Buttons/links hard to tap
**Solution**: Minimum 44×44px touch targets
```css
.touch-target {
    min-width: 44px;
    min-height: 44px;
    padding: 12px;
}
```

### 4. Text Too Small
**Issue**: Text unreadable on mobile
**Solution**: Use responsive text sizing
```html
<p class="text-sm md:text-base">Responsive text</p>
```

## Session Persistence Testing

When testing mobile views, ensure sessions persist:

1. **Login first**: Always login before testing protected pages
2. **Check cookies**: Mobile browsers handle cookies differently
3. **Test navigation**: Ensure session persists across page changes

```bash
# Test session persistence
curl -c cookies.txt -X POST -d "email=dev@gaia.local&password=testtest" \
  http://localhost:8080/auth/login

curl -b cookies.txt http://localhost:8080/profile
```

## Performance Considerations

### Mobile Network Simulation
Test with throttled network to simulate mobile connections:

**Chrome DevTools**:
1. Network tab > Throttling
2. Select "Slow 3G" or "Fast 3G"
3. Test page load times

### Lighthouse Audit
```bash
# Run Lighthouse CLI for mobile
lighthouse http://localhost:8080 \
  --emulated-form-factor=mobile \
  --throttling.cpuSlowdownMultiplier=4
```

## Key Takeaways

1. **Always test with actual devices when possible**
2. **Use multiple testing methods** for comprehensive coverage
3. **Test both portrait and landscape orientations**
4. **Verify touch interactions** work smoothly
5. **Ensure text is readable** without zooming
6. **Check performance** on slower connections
7. **Test session persistence** across navigation
8. **Validate forms** work with mobile keyboards

## Quick Test Command

For rapid mobile testing during development:
```bash
# Quick mobile test
python3 -m http.server 8888 --directory . &
open "http://localhost:8888/mobile-test.html"
```

This opens a simple mobile viewport simulator for quick visual checks during development.