#!/bin/bash
# Simple API test script for Gaia Platform

BASE_URL="http://localhost:8666"

# Load API key from .env file
if [ -f ".env" ]; then
    export $(grep -E '^API_KEY=' .env | head -1 | xargs)
fi

# Fallback API key if not in .env
API_KEY="${API_KEY:-FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

function test_endpoint() {
    local method=$1
    local path=$2
    local data=$3
    local description=$4
    
    print_header "$description"
    
    if [ "$method" = "GET" ]; then
        curl -X GET "${BASE_URL}${path}" \
            -H "x-api-key: ${API_KEY}" \
            -H "Content-Type: application/json" \
            2>/dev/null | jq . 2>/dev/null || echo "Failed to parse JSON"
    elif [ "$method" = "POST" ]; then
        curl -X POST "${BASE_URL}${path}" \
            -H "x-api-key: ${API_KEY}" \
            -H "Content-Type: application/json" \
            -d "$data" \
            2>/dev/null | jq . 2>/dev/null || echo "Failed to parse JSON"
    elif [ "$method" = "DELETE" ]; then
        curl -X DELETE "${BASE_URL}${path}" \
            -H "x-api-key: ${API_KEY}" \
            -H "Content-Type: application/json" \
            2>/dev/null | jq . 2>/dev/null || echo "Failed to parse JSON"
    fi
    echo ""
}

function test_streaming() {
    local message=$1
    print_header "Testing Streaming Chat: $message"
    
    curl -X POST "${BASE_URL}/api/v0.2/chat/stream" \
        -H "x-api-key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$message\", \"activity\": \"generic\"}" \
        --no-buffer \
        2>/dev/null | while IFS= read -r line; do
            if [[ $line == data:* ]]; then
                # Extract JSON from SSE data line
                json="${line#data: }"
                if [[ $json == "[DONE]" ]]; then
                    echo -e "\n${GREEN}✓ Stream completed${NC}"
                elif [[ -n $json ]]; then
                    # Try to extract content field for cleaner display
                    content=$(echo "$json" | grep -o '"content":"[^"]*"' | cut -d'"' -f4)
                    if [[ -n $content ]]; then
                        echo -n "$content"
                    else
                        # For non-content events, show them on new lines
                        event_type=$(echo "$json" | grep -o '"type":"[^"]*"' | cut -d'"' -f4)
                        if [[ $event_type != "content" ]]; then
                            echo -e "\n${BLUE}[$event_type]${NC} $json"
                        fi
                    fi
                fi
            fi
        done
    echo -e "\n"
}

# Main menu
case "$1" in
    "health")
        test_endpoint "GET" "/health" "" "Health Check"
        ;;
    "chat")
        message="${2:-Hello, what is 2+2?}"
        test_endpoint "POST" "/api/v0.2/chat" "{\"message\": \"$message\", \"stream\": false}" "Chat (Non-streaming)"
        ;;
    "stream")
        message="${2:-Hello}"
        test_streaming "$message"
        ;;
    "status")
        test_endpoint "GET" "/api/v0.2/chat/stream/status" "" "Stream Status"
        ;;
    "models")
        test_endpoint "GET" "/api/v0.2/models" "" "Available Models"
        ;;
    "providers")
        test_endpoint "GET" "/api/v0.2/providers" "" "List Providers"
        ;;
    "provider-models")
        provider="${2:-claude}"
        test_endpoint "GET" "/api/v0.2/providers/$provider/models" "" "Provider Models ($provider)"
        ;;
    "provider-health")
        test_endpoint "GET" "/api/v0.2/providers/health" "" "Provider Health"
        ;;
    "provider-stats")
        test_endpoint "GET" "/api/v0.2/providers/stats" "" "Provider Statistics"
        ;;
    "model-info")
        model="${2:-claude-3-haiku-20240307}"
        test_endpoint "GET" "/api/v0.2/models/$model" "" "Model Info ($model)"
        ;;
    "pricing-current")
        provider="${2:-dalle}"
        test_endpoint "GET" "/api/v0.2/assets/pricing/current?provider=$provider" "" "Current Pricing ($provider)"
        ;;
    "pricing-analytics")
        test_endpoint "GET" "/api/v0.2/assets/pricing/analytics" "" "Pricing Analytics"
        ;;
    "pricing-providers")
        test_endpoint "GET" "/api/v0.2/assets/pricing/providers" "" "Pricing Providers"
        ;;
    "cost-estimate")
        test_endpoint "POST" "/api/v0.2/assets/pricing/cost-estimator/estimate" "{\"provider\": \"dalle\", \"operation\": \"image_generation\", \"quantity\": 5, \"quality\": \"standard\"}" "Cost Estimation"
        ;;
    "dalle-tiers")
        test_endpoint "GET" "/api/v0.2/assets/pricing/cost-estimator/dalle-tiers" "" "DALL-E Tiers"
        ;;
    "meshy-packages")
        test_endpoint "GET" "/api/v0.2/assets/pricing/cost-estimator/meshy-packages" "" "Meshy Packages"
        ;;
    "provider-comparison")
        test_endpoint "GET" "/api/v0.2/assets/pricing/cost-estimator/provider-comparison?operation=image_generation&quantity=10" "" "Provider Cost Comparison"
        ;;
    "usage-current")
        test_endpoint "GET" "/api/v0.2/usage/current" "" "Current Usage"
        ;;
    "usage-history")
        test_endpoint "GET" "/api/v0.2/usage/history?days=7" "" "Usage History (7 days)"
        ;;
    "usage-limits")
        test_endpoint "GET" "/api/v0.2/usage/limits" "" "Usage Limits"
        ;;
    "billing-current")
        test_endpoint "GET" "/api/v0.2/usage/billing/current" "" "Current Billing"
        ;;
    "monthly-report")
        test_endpoint "GET" "/api/v0.2/usage/reports/monthly" "" "Monthly Report"
        ;;
    "personas-list")
        test_endpoint "GET" "/api/v0.2/personas" "" "List Personas"
        ;;
    "personas-current")
        test_endpoint "GET" "/api/v0.2/personas/current" "" "Current User Persona"
        ;;
    "personas-create")
        test_endpoint "POST" "/api/v0.2/personas" "{\"name\": \"TestBot\", \"description\": \"A test persona\", \"system_prompt\": \"You are a helpful test assistant.\", \"personality_traits\": {\"helpful\": true}, \"capabilities\": {\"testing\": true}}" "Create Test Persona"
        ;;
    "personas-initialize")
        test_endpoint "POST" "/api/v0.2/personas/initialize-default" "" "Initialize Default Persona"
        ;;
    "personas-get")
        persona_id="${2:-f2c9199c-6612-4ff3-8625-9db643728854}"
        test_endpoint "GET" "/api/v0.2/personas/$persona_id" "" "Get Persona ($persona_id)"
        ;;
    "personas-set")
        persona_id="${2:-f2c9199c-6612-4ff3-8625-9db643728854}"
        test_endpoint "POST" "/api/v0.2/personas/set" "{\"persona_id\": \"$persona_id\"}" "Set Active Persona"
        ;;
    "performance-summary")
        test_endpoint "GET" "/api/v0.2/performance/summary" "" "Performance Summary"
        ;;
    "performance-providers")
        test_endpoint "GET" "/api/v0.2/performance/providers" "" "Provider Performance Metrics"
        ;;
    "performance-stages")
        test_endpoint "GET" "/api/v0.2/performance/stages" "" "Stage Timing Analysis"
        ;;
    "performance-live")
        test_endpoint "GET" "/api/v0.2/performance/live" "" "Live Performance Metrics"
        ;;
    "performance-health")
        test_endpoint "GET" "/api/v0.2/performance/health" "" "Performance Health Status"
        ;;
    "performance-reset")
        test_endpoint "DELETE" "/api/v0.2/performance/reset" "" "Reset Performance Metrics"
        ;;
    "auth-register")
        email="${2:-testuser@gmail.com}"
        password="${3:-SecurePass123!}"
        test_endpoint "POST" "/api/v1/auth/register" "{\"email\": \"$email\", \"password\": \"$password\"}" "User Registration"
        ;;
    "auth-login")
        email="${2:-testuser@gmail.com}"
        password="${3:-SecurePass123!}"
        test_endpoint "POST" "/api/v1/auth/login" "{\"email\": \"$email\", \"password\": \"$password\"}" "User Login"
        ;;
    "vr")
        test_endpoint "GET" "/api/v0.2/chat/stream/models/vr-recommendation" "" "VR Model Recommendation"
        ;;
    "cache")
        test_endpoint "GET" "/api/v0.2/chat/stream/cache/status" "" "Cache Status"
        ;;
    "clear")
        test_endpoint "DELETE" "/api/v0.2/chat/stream/history" "" "Clear History"
        ;;
    "all")
        echo -e "${GREEN}Running all tests...${NC}\n"
        $0 health
        $0 status
        $0 providers
        $0 provider-health
        $0 models
        $0 cache
        ;;
    "providers-all")
        echo -e "${GREEN}Testing all provider endpoints...${NC}\n"
        $0 providers
        $0 provider-models claude
        $0 provider-models openai
        $0 provider-health
        $0 provider-stats
        $0 models
        $0 model-info claude-3-haiku-20240307
        ;;
    "pricing-all")
        echo -e "${GREEN}Testing all asset pricing endpoints...${NC}\n"
        $0 pricing-current dalle
        $0 pricing-analytics
        $0 pricing-providers
        $0 cost-estimate
        $0 dalle-tiers
        $0 meshy-packages
        $0 provider-comparison
        ;;
    "usage-all")
        echo -e "${GREEN}Testing all usage tracking endpoints...${NC}\n"
        $0 usage-current
        $0 usage-history
        $0 usage-limits
        $0 billing-current
        $0 monthly-report
        ;;
    "personas-all")
        echo -e "${GREEN}Testing all persona endpoints...${NC}\n"
        $0 personas-list
        $0 personas-current
        $0 personas-initialize
        $0 personas-get
        $0 personas-set
        ;;
    "performance-all")
        echo -e "${GREEN}Testing all performance monitoring endpoints...${NC}\n"
        $0 performance-summary
        $0 performance-providers
        $0 performance-stages
        $0 performance-live
        $0 performance-health
        ;;
    "auth-all")
        echo -e "${GREEN}Testing all authentication endpoints...${NC}\n"
        $0 auth-register
        $0 auth-login
        ;;
    *)
        echo "Usage: $0 {health|chat|stream|providers|models|pricing|usage|all} [args]"
        echo ""
        echo "Core Tests:"
        echo "  $0 health                    # Check service health"
        echo "  $0 chat \"What is 2+2?\"       # Non-streaming chat"
        echo "  $0 stream \"Tell me a joke\"   # Streaming chat"
        echo ""
        echo "Provider Tests:"
        echo "  $0 providers                 # List all providers"
        echo "  $0 provider-models claude    # List Claude models"
        echo "  $0 provider-health           # Check provider health"
        echo "  $0 provider-stats            # Provider usage stats"
        echo ""
        echo "Model Tests:"
        echo "  $0 models                    # List all models"
        echo "  $0 model-info claude-3-haiku # Get model details"
        echo ""
        echo "Asset Pricing Tests:"
        echo "  $0 pricing-current dalle     # Get current pricing"
        echo "  $0 pricing-analytics         # Cost analytics"
        echo "  $0 cost-estimate             # Estimate generation cost"
        echo "  $0 dalle-tiers               # DALL-E tier info"
        echo "  $0 provider-comparison       # Compare provider costs"
        echo ""
        echo "Usage Tracking Tests:"
        echo "  $0 usage-current             # Current usage stats"
        echo "  $0 usage-history             # Historical usage"
        echo "  $0 usage-limits              # Usage limits & quotas"
        echo "  $0 billing-current           # Current billing info"
        echo "  $0 monthly-report            # Monthly usage report"
        echo ""
        echo "Persona Management Tests:"
        echo "  $0 personas-list             # List all personas"
        echo "  $0 personas-current          # Get current user persona"
        echo "  $0 personas-get [id]         # Get specific persona"
        echo "  $0 personas-set [id]         # Set active persona"
        echo "  $0 personas-initialize       # Initialize default Mu"
        echo ""
        echo "Performance Monitoring Tests:"
        echo "  $0 performance-summary       # Overall performance summary"
        echo "  $0 performance-providers     # Provider performance metrics"
        echo "  $0 performance-stages        # Request stage timing analysis"
        echo "  $0 performance-live          # Live/real-time metrics"
        echo "  $0 performance-health        # Performance health status"
        echo "  $0 performance-reset         # Reset metrics data"
        echo ""
        echo "Authentication Tests:"
        echo "  $0 auth-register [email] [pw] # Register new user"
        echo "  $0 auth-login [email] [pw]    # Login existing user"
        echo ""
        echo "Batch Tests:"
        echo "  $0 all                       # Run core tests"
        echo "  $0 providers-all             # Test all provider endpoints"
        echo "  $0 pricing-all               # Test all pricing endpoints"
        echo "  $0 usage-all                 # Test all usage endpoints"
        echo "  $0 personas-all              # Test all persona endpoints"
        echo "  $0 performance-all           # Test all performance endpoints"
        echo "  $0 auth-all                  # Test all authentication endpoints"
        exit 1
        ;;
esac