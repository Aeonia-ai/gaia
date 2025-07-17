#!/bin/bash
# Automated test script for mobile-responsive sidebar functionality

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
BASE_URL="http://localhost:8080"
TEST_RESULTS=()

function print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    TEST_RESULTS+=("PASS: $1")
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
    TEST_RESULTS+=("FAIL: $1")
}

function print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    TEST_RESULTS+=("WARN: $1")
}

function test_service_health() {
    print_header "Testing Service Health"
    
    response=$(curl -s -w "%{http_code}" "$BASE_URL/health")
    status_code="${response: -3}"
    body="${response%???}"
    
    if [ "$status_code" = "200" ]; then
        print_success "Web service is healthy (HTTP $status_code)"
        if echo "$body" | grep -q '"status".*"healthy"'; then
            print_success "Health endpoint returns healthy status"
        else
            print_error "Health endpoint returns unhealthy status: $body"
        fi
    else
        print_error "Web service not accessible (HTTP $status_code)"
        return 1
    fi
}

function test_mobile_elements_present() {
    print_header "Testing Mobile Sidebar Elements"
    
    chat_page=$(curl -s "$BASE_URL/chat")
    
    # Test 1: Hamburger menu button
    if echo "$chat_page" | grep -q 'id="sidebar-toggle"'; then
        print_success "Hamburger menu button present (sidebar-toggle)"
    else
        print_error "Hamburger menu button missing"
    fi
    
    # Test 2: Sidebar overlay
    if echo "$chat_page" | grep -q 'id="sidebar-overlay"'; then
        print_success "Mobile sidebar overlay present"
    else
        print_error "Mobile sidebar overlay missing"
    fi
    
    # Test 3: Responsive classes
    if echo "$chat_page" | grep -q 'md:hidden'; then
        print_success "Responsive classes present (md:hidden for mobile-only elements)"
    else
        print_error "Responsive classes missing"
    fi
    
    # Test 4: Hamburger lines
    if echo "$chat_page" | grep -q 'hamburger-lines'; then
        print_success "Hamburger icon structure present"
    else
        print_error "Hamburger icon structure missing"
    fi
    
    # Test 5: Mobile header
    mobile_header_count=$(echo "$chat_page" | grep -c 'md:hidden.*class.*flex.*items-center')
    if [ "$mobile_header_count" -gt 0 ]; then
        print_success "Mobile header elements present ($mobile_header_count found)"
    else
        print_warning "Mobile header elements may be missing"
    fi
}

function test_javascript_functions() {
    print_header "Testing JavaScript Functionality"
    
    chat_page=$(curl -s "$BASE_URL/chat")
    
    # Test 1: Toggle function
    if echo "$chat_page" | grep -q 'function toggleSidebar'; then
        print_success "toggleSidebar function present"
    else
        print_error "toggleSidebar function missing"
    fi
    
    # Test 2: Event listeners
    if echo "$chat_page" | grep -q 'addEventListener.*click'; then
        print_success "Click event listeners present"
    else
        print_error "Click event listeners missing"
    fi
    
    # Test 3: Touch events
    if echo "$chat_page" | grep -q 'touchstart\|touchend\|touchmove'; then
        print_success "Touch event support present for swipe gestures"
    else
        print_error "Touch event support missing"
    fi
    
    # Test 4: Resize handler
    if echo "$chat_page" | grep -q 'addEventListener.*resize'; then
        print_success "Window resize handler present"
    else
        print_error "Window resize handler missing"
    fi
}

function test_mobile_css() {
    print_header "Testing Mobile CSS and Responsive Design"
    
    chat_page=$(curl -s "$BASE_URL/chat")
    
    # Test 1: Mobile media queries
    if echo "$chat_page" | grep -q '@media.*max-width.*768'; then
        print_success "Mobile media queries present (max-width: 768px)"
    else
        print_error "Mobile media queries missing"
    fi
    
    # Test 2: Safe area support
    if echo "$chat_page" | grep -q 'safe-area-inset'; then
        print_success "iOS safe area support present"
    else
        print_warning "iOS safe area support missing (may affect modern devices)"
    fi
    
    # Test 3: Touch-friendly sizing
    if echo "$chat_page" | grep -q 'min-height:.*44\|min-width:.*44'; then
        print_success "Touch-friendly minimum sizes present"
    else
        print_warning "Touch-friendly minimum sizes may be missing"
    fi
    
    # Test 4: Animations
    if echo "$chat_page" | grep -q 'slideInRight\|slideInLeft\|fadeIn'; then
        print_success "Sidebar animations present"
    else
        print_error "Sidebar animations missing"
    fi
    
    # Test 5: Transform classes
    if echo "$chat_page" | grep -q 'translate-x\|transform'; then
        print_success "CSS transform classes for sidebar positioning present"
    else
        print_error "CSS transform classes missing"
    fi
}

function test_responsive_chat_input() {
    print_header "Testing Responsive Chat Input"
    
    chat_page=$(curl -s "$BASE_URL/chat")
    
    # Test 1: Mobile send button
    if echo "$chat_page" | grep -q 'sm:hidden.*→'; then
        print_success "Mobile send button with arrow icon present"
    else
        print_warning "Mobile send button arrow may be missing"
    fi
    
    # Test 2: Responsive text hiding
    if echo "$chat_page" | grep -q 'hidden sm:inline.*Send'; then
        print_success "Responsive text hiding for send button present"
    else
        print_warning "Send button text responsiveness may be missing"
    fi
    
    # Test 3: Input sizing
    if echo "$chat_page" | grep -q 'min-w-0.*flex-1'; then
        print_success "Responsive input sizing classes present"
    else
        print_warning "Input responsive sizing may be missing"
    fi
}

function test_auth_pages_mobile_support() {
    print_header "Testing Auth Pages Mobile Support"
    
    # Test login page
    login_page=$(curl -s "$BASE_URL/login")
    if echo "$login_page" | grep -q '@media.*max-width.*768'; then
        print_success "Login page has mobile CSS support"
    else
        print_error "Login page missing mobile CSS"
    fi
    
    # Test register page
    register_page=$(curl -s "$BASE_URL/register")
    if echo "$register_page" | grep -q '@media.*max-width.*768'; then
        print_success "Register page has mobile CSS support"
    else
        print_error "Register page missing mobile CSS"
    fi
}

function run_all_tests() {
    print_header "Mobile-Responsive Sidebar Test Suite"
    echo "Testing URL: $BASE_URL"
    echo "Started at: $(date)"
    echo ""
    
    test_service_health || exit 1
    test_mobile_elements_present
    test_javascript_functions
    test_mobile_css
    test_responsive_chat_input
    test_auth_pages_mobile_support
    
    print_header "Test Results Summary"
    
    total_tests=${#TEST_RESULTS[@]}
    passed_tests=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c "^PASS:")
    failed_tests=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c "^FAIL:")
    warned_tests=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c "^WARN:")
    
    echo "Total Tests: $total_tests"
    echo -e "${GREEN}Passed: $passed_tests${NC}"
    echo -e "${RED}Failed: $failed_tests${NC}"
    echo -e "${YELLOW}Warnings: $warned_tests${NC}"
    echo ""
    
    if [ "$failed_tests" -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed! Mobile sidebar is ready.${NC}"
        if [ "$warned_tests" -gt 0 ]; then
            echo -e "${YELLOW}Note: $warned_tests warnings detected - review for optimal experience.${NC}"
        fi
        return 0
    else
        echo -e "${RED}❌ $failed_tests tests failed. Please review the issues above.${NC}"
        return 1
    fi
}

# Show detailed results if requested
if [ "$1" = "--verbose" ] || [ "$1" = "-v" ]; then
    run_all_tests
    echo ""
    print_header "Detailed Test Results"
    for result in "${TEST_RESULTS[@]}"; do
        if [[ $result == PASS:* ]]; then
            echo -e "${GREEN}$result${NC}"
        elif [[ $result == FAIL:* ]]; then
            echo -e "${RED}$result${NC}"
        else
            echo -e "${YELLOW}$result${NC}"
        fi
    done
else
    run_all_tests
fi