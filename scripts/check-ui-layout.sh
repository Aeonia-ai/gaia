#!/bin/bash
# Script to check if UI layout changes might break the interface
# Focuses on common patterns that have caused issues

echo "🎨 Checking UI layout modifications..."

# Check if any UI-related files are being committed
UI_FILES=$(git diff --cached --name-only | grep -E "(gaia_ui|components|templates|static/.*\.css)\.py$")

if [ -n "$UI_FILES" ]; then
    echo "⚠️  UI-related files detected in commit:"
    echo "$UI_FILES"
    echo ""
    echo "Please ensure:"
    echo "✓ No flex-col md:flex-row patterns (breaks layout)"
    echo "✓ Loading indicators are outside HTMX swap targets"
    echo "✓ Consistent color palette (slate, purple, violet)"
    echo "✓ Standard spacing scale (p-2, p-4, p-6, etc.)"
    echo "✓ Mobile-first responsive design"
    echo ""
    
    # Check for problematic flex patterns
    if git diff --cached | grep -E "flex-col.*md:flex-row|flex-col.*lg:flex-row" > /dev/null; then
        echo "❌ ERROR: Found flex-col with responsive flex-row pattern!"
        echo "This pattern breaks the layout by displaying content in columns."
        echo "Use a consistent flex direction or adjust only spacing/sizing."
        exit 1
    fi
    
    # Check for loading indicators inside potential swap targets
    if git diff --cached | grep -A5 -B5 "htmx-indicator" | grep -E "hx-target.*#.*htmx-indicator" > /dev/null; then
        echo "⚠️  WARNING: Possible loading indicator inside swap target detected!"
        echo "Loading indicators must be outside the element being swapped."
    fi
    
    # Check for non-standard colors
    if git diff --cached | grep -E "bg-(red|orange|pink|teal|cyan)-[0-9]+" > /dev/null; then
        echo "⚠️  WARNING: Non-standard colors detected!"
        echo "Please use our defined color palette: slate, purple, violet, indigo"
        echo "Status colors: red, green, yellow, blue (sparingly)"
    fi
    
    # Check for inline styles
    if git diff --cached | grep -E "style=" > /dev/null; then
        echo "⚠️  WARNING: Inline styles detected!"
        echo "Use Tailwind CSS classes instead of inline styles."
    fi
    
    # Check for custom CSS that might conflict
    if git diff --cached | grep -E "\.css\"|'\.css'" > /dev/null; then
        echo "📋 Custom CSS file references detected."
        echo "Ensure custom CSS doesn't override Tailwind utilities."
    fi
    
    echo ""
    echo "✅ No critical layout issues detected, but please:"
    echo "1. Run UI tests: pytest tests/web/test_ui_layout.py"
    echo "2. Test on mobile, tablet, and desktop sizes"
    echo "3. Check loading indicators work correctly"
    echo "4. Review the CSS Style Guide: docs/css-style-guide.md"
fi

exit 0