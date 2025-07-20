#!/bin/bash
# Layout Integrity Check Script
# Prevents layout breakages before they reach production

set -e

echo "🔍 Running Layout Integrity Checks..."
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
if ! curl -s http://localhost:8080/health > /dev/null; then
    echo -e "${YELLOW}⚠️  Web service not running. Starting services...${NC}"
    docker compose up -d web-service
    sleep 5
fi

# 1. Check for nested layout containers
echo -n "Checking for nested layout containers... "
if grep -r "flex h-screen.*flex h-screen" app/services/web/ 2>/dev/null | grep -v "test_" | grep -v ".md"; then
    echo -e "${RED}❌ FAILED${NC}"
    echo -e "${RED}ERROR: Nested layout containers found!${NC}"
    echo "These files contain nested .flex.h-screen containers:"
    grep -r "flex h-screen.*flex h-screen" app/services/web/ | grep -v "test_" | grep -v ".md"
    exit 1
else
    echo -e "${GREEN}✅ PASSED${NC}"
fi

# 2. Check auth pages don't reference chat elements
echo -n "Checking auth page isolation... "
FORBIDDEN_IN_AUTH=(
    "#sidebar"
    "#chat-form"
    "#messages"
    "#conversation-list"
    "mobile-header"
    "sidebar-toggle"
)

auth_issues=0
for element in "${FORBIDDEN_IN_AUTH[@]}"; do
    if grep -q "$element" app/services/web/routes/auth.py 2>/dev/null; then
        if [ $auth_issues -eq 0 ]; then
            echo -e "${RED}❌ FAILED${NC}"
            echo -e "${RED}ERROR: Auth routes contain chat elements:${NC}"
        fi
        echo "  - Found '$element' in auth.py"
        ((auth_issues++))
    fi
done

# Check for dangerous Div() patterns in auth routes
if grep -q "return Div(" app/services/web/routes/auth.py 2>/dev/null; then
    if [ $auth_issues -eq 0 ]; then
        echo -e "${RED}❌ FAILED${NC}"
        echo -e "${RED}ERROR: Auth layout violations found:${NC}"
    fi
    echo "  - Found raw 'return Div()' in auth.py (causes form+verification mixing)"
    echo "  - Fix: Use auth_page_replacement() instead"
    ((auth_issues++))
fi

# Check for dangerous HTMX form patterns (the actual bug we just fixed)
if grep -rE "hx_target=\"#[^\"]*message\".*hx_swap=\"innerHTML\"" app/services/web/ 2>/dev/null | grep -v "test_" | grep -v ".md"; then
    if [ $auth_issues -eq 0 ]; then
        echo -e "${RED}❌ FAILED${NC}"
        echo -e "${RED}ERROR: Dangerous HTMX patterns found:${NC}"
    fi
    echo "  - Found form targeting message element with innerHTML (causes form+message mixing)"
    echo "  - Fix: Use container targeting with outerHTML instead"
    echo "  - Wrong: hx_target=\"#auth-message\" hx_swap=\"innerHTML\""
    echo "  - Right: hx_target=\"#auth-form-container\" hx_swap=\"outerHTML\""
    ((auth_issues++))
fi

# Check for missing auth_page_replacement import
if ! grep -q "auth_page_replacement" app/services/web/routes/auth.py 2>/dev/null; then
    if [ $auth_issues -eq 0 ]; then
        echo -e "${YELLOW}⚠️  WARNING${NC}"
        echo -e "${YELLOW}WARNING: Auth isolation patterns missing:${NC}"
    fi
    echo "  - auth_page_replacement not imported (needed for proper isolation)"
    echo "  - Add: from app.services.web.utils.layout_isolation import auth_page_replacement"
fi

if [ $auth_issues -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
else
    echo ""
    echo "Critical auth layout violations found!"
    echo "See: docs/auth-layout-isolation.md"
    exit 1
fi

# 3. Verify gaia_layout usage in main.py
echo -n "Checking layout configuration... "
if ! grep -q "show_sidebar=False" app/services/web/main.py; then
    echo -e "${YELLOW}⚠️  WARNING${NC}"
    echo "Auth pages might not have show_sidebar=False set"
else
    echo -e "${GREEN}✅ PASSED${NC}"
fi

# 4. Check for common CSS anti-patterns
echo -n "Checking for CSS anti-patterns... "
css_issues=0

# Check for max-width on main containers
if grep -r "flex.*h-screen.*max-w-" app/services/web/ 2>/dev/null | grep -v "test_" | grep -v ".md"; then
    if [ $css_issues -eq 0 ]; then
        echo -e "${YELLOW}⚠️  WARNING${NC}"
        echo "Found max-width constraints on main layout containers:"
    fi
    grep -r "flex.*h-screen.*max-w-" app/services/web/ | grep -v "test_" | grep -v ".md"
    ((css_issues++))
fi

if [ $css_issues -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
fi

# 5. Run Python layout tests if available
if [ -f "tests/web/test_layout_integrity.py" ]; then
    echo ""
    echo "Running Python layout integrity tests..."
    echo "----------------------------------------"
    
    # Run only the critical layout tests
    pytest tests/web/test_layout_integrity.py::TestLayoutIntegrity::test_chat_layout_full_width -v || {
        echo -e "${RED}❌ Layout width test FAILED${NC}"
        exit 1
    }
    
    pytest tests/web/test_layout_integrity.py::TestLayoutIntegrity::test_login_page_no_chat_elements -v || {
        echo -e "${RED}❌ Page isolation test FAILED${NC}"
        exit 1
    }
    
    pytest tests/web/test_layout_integrity.py::TestLayoutIntegrity::test_no_nested_layouts -v || {
        echo -e "${RED}❌ Nested layouts test FAILED${NC}"
        exit 1
    }
fi

# 6. Quick visual check with curl
echo ""
echo "Performing quick visual validation..."
echo "------------------------------------"

# Check login page structure
echo -n "Login page structure... "
login_html=$(curl -s http://localhost:8080/login)
if echo "$login_html" | grep -q "id=\"sidebar\""; then
    echo -e "${RED}❌ FAILED - Login page contains sidebar!${NC}"
    exit 1
else
    echo -e "${GREEN}✅ PASSED${NC}"
fi

# Check chat page requires auth
echo -n "Chat page auth check... "
chat_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/chat)
if [ "$chat_response" = "303" ] || [ "$chat_response" = "302" ]; then
    echo -e "${GREEN}✅ PASSED - Redirects when not authenticated${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING - Chat page returned $chat_response${NC}"
fi

# 7. Summary
echo ""
echo "===================================="
echo -e "${GREEN}✅ Layout Integrity Checks Complete!${NC}"
echo ""
echo "Remember the golden rules:"
echo "1. ONE .flex.h-screen container per page"
echo "2. Auth pages must use show_sidebar=False"
echo "3. Chat interface must use full viewport width"
echo "4. HTMX swaps content, not layout containers"
echo ""

# Create a timestamp file to track when checks were last run
echo "$(date): Layout checks passed" >> .layout-checks.log

exit 0