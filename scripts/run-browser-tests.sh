#!/bin/bash
# Browser test runner script
# Provides easy ways to run different types of browser tests

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
BROWSER_MODE="unit"
HEADLESS="true"
RECORD_VIDEO="false"
VERBOSE=""
SPECIFIC_TEST=""

# Help function
show_help() {
    echo "Browser Test Runner"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE        Test type: all, auth, chat, edge, htmx, full (default: all)"
    echo "  -m, --mode MODE        Browser mode: unit, integration, e2e, visual (default: unit)"
    echo "  -h, --headed           Run with browser visible (default: headless)"
    echo "  -v, --verbose          Verbose output"
    echo "  -r, --record           Record videos of test runs"
    echo "  -s, --specific TEST    Run specific test by name"
    echo "  -d, --debug            Debug mode (slow, visible browser)"
    echo "  --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                     # Run all browser tests in unit mode"
    echo "  $0 -t auth             # Run auth browser tests"
    echo "  $0 -m integration      # Run integration browser tests"
    echo "  $0 -d -s test_login    # Debug specific test with visible browser"
    echo "  $0 -t edge -r          # Run edge case tests with video recording"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -m|--mode)
            BROWSER_MODE="$2"
            shift 2
            ;;
        -h|--headed)
            HEADLESS="false"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -r|--record)
            RECORD_VIDEO="true"
            shift
            ;;
        -s|--specific)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        -d|--debug)
            HEADLESS="false"
            BROWSER_MODE="debug"
            VERBOSE="-v"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Set environment variables
export BROWSER_TEST_MODE="$BROWSER_MODE"
export BROWSER_HEADLESS="$HEADLESS"
export BROWSER_RECORD_VIDEO="$RECORD_VIDEO"
export RUN_BROWSER_TESTS="true"

# Create directories for outputs
mkdir -p tests/web/screenshots/failures
mkdir -p tests/web/videos
mkdir -p tests/web/har

# Determine which tests to run
case $TEST_TYPE in
    all)
        TEST_FILES="tests/web/test_authenticated_browser.py tests/web/test_full_web_browser.py tests/web/test_browser_edge_cases.py tests/web/test_chat_browser_auth.py"
        ;;
    auth)
        TEST_FILES="tests/web/test_authenticated_browser.py tests/web/test_chat_browser_auth.py"
        ;;
    chat)
        TEST_FILES="tests/web/test_chat_browser_auth.py"
        ;;
    edge)
        TEST_FILES="tests/web/test_browser_edge_cases.py"
        ;;
    htmx)
        TEST_FILES="tests/web/test_full_web_browser.py::TestHTMXBehavior"
        ;;
    full)
        TEST_FILES="tests/web/test_full_web_browser.py"
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        show_help
        exit 1
        ;;
esac

# Add specific test if requested
if [[ -n "$SPECIFIC_TEST" ]]; then
    TEST_FILES="tests/web/ -k $SPECIFIC_TEST"
fi

# Show configuration
echo -e "${GREEN}Running Browser Tests${NC}"
echo "------------------------"
echo "Test Type: $TEST_TYPE"
echo "Browser Mode: $BROWSER_MODE"
echo "Headless: $HEADLESS"
echo "Record Video: $RECORD_VIDEO"
echo "Test Files: $TEST_FILES"
echo "------------------------"
echo ""

# Check if running in Docker
if [[ -f /.dockerenv ]]; then
    echo -e "${YELLOW}Running inside Docker container${NC}"
    # Run tests directly
    pytest $TEST_FILES $VERBOSE --tb=short
else
    echo -e "${YELLOW}Running via Docker Compose${NC}"
    # Run tests in Docker
    docker compose run --rm test pytest $TEST_FILES $VERBOSE --tb=short
fi

# Check exit code
EXIT_CODE=$?

# Show results
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "\n${GREEN}✓ Browser tests passed!${NC}"
    
    # Clean up videos if tests passed and not in debug mode
    if [[ "$BROWSER_MODE" != "debug" && "$RECORD_VIDEO" != "true" ]]; then
        rm -rf tests/web/videos/*.webm 2>/dev/null || true
    fi
else
    echo -e "\n${RED}✗ Browser tests failed!${NC}"
    
    # Show where to find artifacts
    if [[ "$RECORD_VIDEO" == "true" ]]; then
        echo -e "${YELLOW}Videos saved in: tests/web/videos/${NC}"
    fi
    
    if [[ -d tests/web/screenshots/failures ]] && [[ -n "$(ls -A tests/web/screenshots/failures 2>/dev/null)" ]]; then
        echo -e "${YELLOW}Screenshots saved in: tests/web/screenshots/failures/${NC}"
    fi
fi

exit $EXIT_CODE