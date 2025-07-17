#!/bin/bash

# curl_wrapper.sh - A wrapper script for curl with common options and configurations

# Default configuration
DEFAULT_TIMEOUT=30
DEFAULT_USER_AGENT="curl-wrapper/1.0"
VERBOSE=false
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] URL

A wrapper around curl with sensible defaults and additional features.

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -d, --dry-run           Show the curl command without executing
    -t, --timeout SECONDS  Set timeout (default: $DEFAULT_TIMEOUT)
    -u, --user-agent AGENT Set user agent (default: $DEFAULT_USER_AGENT)
    -H, --header HEADER     Add custom header (can be used multiple times)
    -X, --method METHOD     HTTP method (GET, POST, PUT, DELETE, etc.)
    -D, --data DATA         Request body data
    -j, --json              Set Content-Type to application/json
    -f, --form              Use form data (application/x-www-form-urlencoded)
    -o, --output FILE       Save output to file
    -i, --include           Include response headers in output
    -s, --silent            Silent mode (no progress bar)
    -L, --follow            Follow redirects
    -k, --insecure          Allow insecure SSL connections

EXAMPLES:
    $0 https://api.example.com/users
    $0 -X POST -j -D '{"name":"John"}' https://api.example.com/users
    $0 -H "Authorization: Bearer token" https://api.example.com/protected
    $0 -v -L https://example.com
    $0 --dry-run -X POST https://api.example.com/test

EOF
}

# Function to log messages
log() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[INFO]${NC} $1" >&2
    fi
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

# Initialize variables
HEADERS=()
METHOD=""
DATA=""
OUTPUT=""
URL=""
CURL_ARGS=()

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -t|--timeout)
            if [[ -z "$2" || "$2" =~ ^- ]]; then
                error "Timeout value required"
                exit 1
            fi
            DEFAULT_TIMEOUT="$2"
            shift 2
            ;;
        -u|--user-agent)
            if [[ -z "$2" || "$2" =~ ^- ]]; then
                error "User agent value required"
                exit 1
            fi
            DEFAULT_USER_AGENT="$2"
            shift 2
            ;;
        -H|--header)
            if [[ -z "$2" || "$2" =~ ^- ]]; then
                error "Header value required"
                exit 1
            fi
            HEADERS+=("$2")
            shift 2
            ;;
        -X|--method)
            if [[ -z "$2" || "$2" =~ ^- ]]; then
                error "HTTP method required"
                exit 1
            fi
            METHOD="$2"
            shift 2
            ;;
        -D|--data)
            if [[ -z "$2" || "$2" =~ ^- ]]; then
                error "Data value required"
                exit 1
            fi
            DATA="$2"
            shift 2
            ;;
        -j|--json)
            HEADERS+=("Content-Type: application/json")
            shift
            ;;
        -f|--form)
            HEADERS+=("Content-Type: application/x-www-form-urlencoded")
            shift
            ;;
        -o|--output)
            if [[ -z "$2" || "$2" =~ ^- ]]; then
                error "Output file required"
                exit 1
            fi
            OUTPUT="$2"
            shift 2
            ;;
        -i|--include)
            CURL_ARGS+=("--include")
            shift
            ;;
        -s|--silent)
            CURL_ARGS+=("--silent")
            shift
            ;;
        -L|--follow)
            CURL_ARGS+=("--location")
            shift
            ;;
        -k|--insecure)
            CURL_ARGS+=("--insecure")
            warning "Using insecure SSL connections"
            shift
            ;;
        -*)
            error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$URL" ]]; then
                URL="$1"
            else
                error "Multiple URLs provided: $URL and $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [[ -z "$URL" ]]; then
    error "URL is required"
    show_usage
    exit 1
fi

# Validate URL format
if ! [[ "$URL" =~ ^https?:// ]]; then
    error "URL must start with http:// or https://"
    exit 1
fi

# Build curl command
CURL_CMD=("curl")

# Add timeout
CURL_CMD+=("--max-time" "$DEFAULT_TIMEOUT")

# Add user agent
CURL_CMD+=("--user-agent" "$DEFAULT_USER_AGENT")

# Add headers
for header in "${HEADERS[@]}"; do
    CURL_CMD+=("--header" "$header")
done

# Add method if specified
if [[ -n "$METHOD" ]]; then
    CURL_CMD+=("--request" "$METHOD")
fi

# Add data if specified
if [[ -n "$DATA" ]]; then
    CURL_CMD+=("--data" "$DATA")
fi

# Add output file if specified
if [[ -n "$OUTPUT" ]]; then
    CURL_CMD+=("--output" "$OUTPUT")
fi

# Add additional curl arguments
CURL_CMD+=("${CURL_ARGS[@]}")

# Add URL
CURL_CMD+=("$URL")

# Show command if verbose or dry run
if [[ "$VERBOSE" = true || "$DRY_RUN" = true ]]; then
    echo -e "${BLUE}[COMMAND]${NC} ${CURL_CMD[*]}" >&2
fi

# Execute or show dry run
if [[ "$DRY_RUN" = true ]]; then
    success "Dry run completed"
    exit 0
fi

# Execute curl command
log "Executing curl request to: $URL"
"${CURL_CMD[@]}"
CURL_EXIT_CODE=$?

# Check exit code
if [[ $CURL_EXIT_CODE -eq 0 ]]; then
    log "Request completed successfully"
else
    error "Request failed with exit code: $CURL_EXIT_CODE"
    exit $CURL_EXIT_CODE
fi