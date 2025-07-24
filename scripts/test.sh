#!/bin/bash
# Smart API test script for Gaia Platform - Local and Remote testing

# Default to local development
BASE_URL="http://localhost:8666"
ENVIRONMENT="local"

# Parse command line arguments for environment
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            BASE_URL="http://localhost:8666"
            ENVIRONMENT="local"
            shift
            ;;
        --staging)
            BASE_URL="https://gaia-gateway-staging.fly.dev"
            ENVIRONMENT="staging"
            shift
            ;;
        --prod)
            BASE_URL="https://gaia-gateway-prod.fly.dev"
            ENVIRONMENT="production"
            shift
            ;;
        --url)
            BASE_URL="$2"
            ENVIRONMENT="custom"
            shift 2
            ;;
        *)
            # If it's not a flag, treat it as the test command
            break
            ;;
    esac
done

# Load environment variables from .env file
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Use Jason's API key if available, otherwise fallback
API_KEY="${JASON_API_KEY:-${API_KEY:-FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE}}"

# Environment-specific API keys
case $ENVIRONMENT in
    "staging")
        API_KEY="${STAGING_API_KEY:-$API_KEY}"
        ;;
    "production")
        API_KEY="${PROD_API_KEY:-$API_KEY}"
        ;;
esac

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

function print_environment() {
    echo -e "${GREEN}🌍 Testing Environment: ${ENVIRONMENT}${NC}"
    echo -e "${GREEN}🔗 Base URL: ${BASE_URL}${NC}"
    echo -e "${GREEN}🔑 API Key: ${API_KEY:0:8}...${NC}"
    
    # Environment-specific expectations
    case $ENVIRONMENT in
        "local")
            echo -e "${BLUE}💡 Expected: Full microservices, NATS enabled${NC}"
            ;;
        "staging")
            echo -e "${BLUE}💡 Expected: Gateway only, some service failures normal${NC}"
            echo -e "${BLUE}⚠️  Note: Asset/persona endpoints may fail (services not deployed)${NC}"
            ;;
        "production")
            echo -e "${BLUE}💡 Expected: All services operational${NC}"
            ;;
        "custom")
            echo -e "${BLUE}💡 Expected: Unknown - check manually${NC}"
            ;;
    esac
    echo ""
}

function test_endpoint() {
    local method=$1
    local path=$2
    local data=$3
    local description=$4
    
    print_header "$description"
    
    local response
    local status_code
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}${path}" \
            -H "x-api-key: ${API_KEY}" \
            -H "Content-Type: application/json")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}${path}" \
            -H "x-api-key: ${API_KEY}" \
            -H "Content-Type: application/json" \
            -d "$data")
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE "${BASE_URL}${path}" \
            -H "x-api-key: ${API_KEY}" \
            -H "Content-Type: application/json")
    fi
    
    # Extract status code (last line) and body (everything else)
    status_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    # Environment-specific status handling
    if [[ $status_code -ge 200 && $status_code -lt 300 ]]; then
        echo -e "${GREEN}✅ Status: $status_code${NC}"
        echo "$body" | jq . 2>/dev/null || echo "$body"
    elif [[ $ENVIRONMENT == "staging" && ($path == *"/assets/"* || $path == *"/personas/"* || $path == *"/performance/"*) ]]; then
        echo -e "${BLUE}⚠️  Status: $status_code (Expected in staging - service not deployed)${NC}"
        echo "$body" | jq . 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ Status: $status_code${NC}"
        echo "$body" | jq . 2>/dev/null || echo "$body"
        
        # Add more debugging info for errors
        if [[ $status_code -eq 500 || $status_code -eq 502 || $status_code -eq 503 ]]; then
            echo -e "${RED}Debug info:${NC}"
            echo "  - Endpoint: ${method} ${BASE_URL}${path}"
            echo "  - Environment: ${ENVIRONMENT}"
            if [ "$method" = "POST" ]; then
                echo "  - Request body: $(echo "$data" | jq -c . 2>/dev/null || echo "$data")"
            fi
            
            # Suggest checking logs for server errors
            if [[ $ENVIRONMENT != "local" ]]; then
                echo -e "${BLUE}💡 To check logs:${NC}"
                case $ENVIRONMENT in
                    "staging")
                        echo "  fly logs -a gaia-gateway-staging"
                        echo "  fly logs -a gaia-asset-staging"
                        ;;
                    "production")
                        echo "  fly logs -a gaia-gateway-production"
                        echo "  fly logs -a gaia-asset-production"
                        ;;
                    *)
                        # Extract app name from URL if it's a fly.dev domain
                        if [[ $BASE_URL == *"fly.dev"* ]]; then
                            local app_name=$(echo $BASE_URL | sed -E 's|https?://([^.]+)\.fly\.dev.*|\1|')
                            echo "  fly logs -a $app_name"
                            # Also suggest checking the asset service if gateway
                            if [[ $app_name == *"gateway"* ]]; then
                                local asset_app=$(echo $app_name | sed 's/gateway/asset/')
                                echo "  fly logs -a $asset_app"
                            fi
                        else
                            echo "  Check your deployment logs"
                        fi
                        ;;
                esac
            fi
        fi
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
    "ultrafast")
        message="${2:-What is 2+2?}"
        test_endpoint "POST" "/api/v1/chat/ultrafast" "{\"message\": \"$message\"}" "Ultrafast Chat (No History)"
        ;;
    "ultrafast-redis")
        message="${2:-What is 2+2?}"
        test_endpoint "POST" "/api/v1/chat/ultrafast-redis" "{\"message\": \"$message\"}" "Ultrafast Redis Chat"
        ;;
    "ultrafast-redis-v2")
        message="${2:-What is 2+2?}"
        test_endpoint "POST" "/api/v1/chat/ultrafast-redis-v2" "{\"message\": \"$message\"}" "Ultrafast Redis V2 (Optimized)"
        ;;
    "ultrafast-redis-v3")
        message="${2:-What is 2+2?}"
        test_endpoint "POST" "/api/v1/chat/ultrafast-redis-v3" "{\"message\": \"$message\"}" "Ultrafast Redis V3 (Parallel)"
        ;;
    "direct")
        message="${2:-What is 2+2?}"
        test_endpoint "POST" "/api/v1/chat/direct" "{\"message\": \"$message\"}" "Direct Chat (Simple)"
        ;;
    "direct-db")
        message="${2:-What is 2+2?}"
        test_endpoint "POST" "/api/v1/chat/direct-db" "{\"message\": \"$message\"}" "Direct Chat with DB"
        ;;
    "mcp-agent")
        message="${2:-What is 2+2?}"
        test_endpoint "POST" "/api/v1/chat/mcp-agent" "{\"message\": \"$message\"}" "MCP-Agent Chat"
        ;;
    "orchestrated")
        message="${2:-What is 2+2?}"
        test_endpoint "POST" "/api/v1/chat/orchestrated" "{\"message\": \"$message\"}" "Orchestrated Multi-Agent Chat"
        ;;
    "gamemaster")
        message="${2:-A hooded figure enters the tavern and asks about missing merchants}"
        test_endpoint "POST" "/api/v1/chat/gamemaster" "{\"message\": \"$message\"}" "Game Master + NPCs Orchestration"
        ;;
    "worldbuilding")
        message="${2:-Create a new fantasy region called The Crimson Reaches}"
        test_endpoint "POST" "/api/v1/chat/worldbuilding" "{\"message\": \"$message\"}" "Collaborative World Building"
        ;;
    "storytelling")
        message="${2:-Tell the story of a powerful artifact discovery from multiple perspectives}"
        test_endpoint "POST" "/api/v1/chat/storytelling" "{\"message\": \"$message\"}" "Multi-Perspective Storytelling"
        ;;
    "problemsolving")
        message="${2:-Design a complex multiplayer puzzle for 6-8 players called The Resonance Chamber}"
        test_endpoint "POST" "/api/v1/chat/problemsolving" "{\"message\": \"$message\"}" "Expert Team Problem Solving"
        ;;
    "kb-enhanced")
        message="${2:-Search the KB for information about consciousness and synthesize insights across domains}"
        test_endpoint "POST" "/api/v1/chat/kb-enhanced" "{\"message\": \"$message\"}" "KB-Enhanced Multiagent Chat"
        ;;
    "kb-research")
        message="${2:-Research the implementation of consciousness frameworks in MMOIRL}"
        test_endpoint "POST" "/api/v1/chat/kb-research" "{\"message\": \"$message\"}" "KB Research with Knowledge Agents"
        ;;
    "kb-gamemaster")
        message="${2:-Create a tavern scene using established world lore and character backgrounds}"
        test_endpoint "POST" "/api/v1/chat/kb-gamemaster" "{\"message\": \"$message\"}" "KB-Enhanced Game Master"
        ;;
    "kb-development")
        message="${2:-How should I implement KB caching in the multiagent orchestrator?}"
        test_endpoint "POST" "/api/v1/chat/kb-development" "{\"message\": \"$message\"}" "KB Development Advisor"
        ;;
    "kb-health")
        echo -e "${BLUE}=== KB Health Check ===${NC}"
        # For KB service, use the direct URL not gateway
        if [[ "$ENVIRONMENT" == "local" ]]; then
            kb_url="http://localhost:8005"  # KB service port
        else
            kb_url="https://gaia-kb-$ENVIRONMENT.fly.dev"
        fi
        
        response=$(curl -s -w "\n\nHTTP Status: %{http_code}" "$kb_url/health" -H "X-API-Key: $API_KEY")
        http_code=$(echo "$response" | tail -n1 | cut -d' ' -f3)
        body=$(echo "$response" | sed '$d' | sed '$d')
        
        if [[ "$http_code" -eq 200 ]]; then
            echo -e "${GREEN}✅ Status: $http_code${NC}"
            echo "$body" | jq '.'
            
            # Show repository status specifically
            repo_status=$(echo "$body" | jq -r '.repository.status // "Not available"' 2>/dev/null)
            file_count=$(echo "$body" | jq -r '.repository.file_count // 0' 2>/dev/null)
            has_git=$(echo "$body" | jq -r '.repository.has_git // false' 2>/dev/null)
            
            echo -e "\n${BLUE}Repository Details:${NC}"
            echo "  Status: $repo_status"
            echo "  Has Git: $has_git"
            if [[ "$file_count" -gt 0 ]]; then
                echo -e "  Files: ${GREEN}$file_count${NC}"
            fi
        else
            echo -e "${RED}❌ Status: $http_code${NC}"
            echo "$body"
        fi
        ;;
    "kb-search")
        query="${2:-consciousness}"
        test_endpoint "POST" "/api/v0.2/kb/search" "{\"message\": \"$query\"}" "Direct KB Search"
        ;;
    "kb-context")
        context="${2:-gaia}"
        test_endpoint "POST" "/api/v0.2/kb/context" "{\"message\": \"$context\"}" "KOS Context Loading"
        ;;
    "kb-multitask")
        message="${2:-Search for 'multiagent' and load the 'gaia' context}"
        test_endpoint "POST" "/api/v0.2/kb/multitask" "{\"message\": \"$message\"}" "KB Multi-Task Execution"
        ;;
    "multi-provider")
        message="${2:-What is 2+2?}"
        test_endpoint "POST" "/api/v0.2/chat" "{\"message\": \"$message\", \"stream\": false}" "Multi-Provider Chat (v0.2)"
        ;;
    "mcp-agent-hot")
        message="${2:-What is 2+2?}"
        test_endpoint "POST" "/api/v1/chat/mcp-agent-hot" "{\"message\": \"$message\"}" "MCP-Agent Hot (Pre-initialized)"
        ;;
    "chat-status")
        test_endpoint "GET" "/api/v1/chat/status" "" "Chat Service Status"
        ;;
    "reload-prompt")
        test_endpoint "POST" "/api/v1/chat/reload-prompt" "{}" "Reload Prompt Templates"
        ;;
    "conversations")
        test_endpoint "GET" "/api/v1/chat/personas" "" "List Personas (Conversations endpoint not exposed)"
        ;;
    "conversations-search")
        query="${2:-test}"
        echo -e "${BLUE}=== Search Conversations ===${NC}"
        echo "Note: This endpoint is not exposed through the gateway yet"
        ;;
    "orchestrated-metrics")
        echo -e "${BLUE}=== Orchestration Metrics ===${NC}"
        echo "Note: This endpoint is not exposed through the gateway yet"
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
    
    # Asset Generation Tests
    "assets-test")
        test_endpoint "GET" "/api/v1/assets/test" "" "Asset Service Test (No Auth)"
        ;;
    "assets-list")
        test_endpoint "GET" "/api/v1/assets" "" "List Assets"
        ;;
    "assets-generate-image")
        # First check if asset service is healthy (for non-local environments)
        if [[ $ENVIRONMENT != "local" && $BASE_URL == *"fly.dev"* ]]; then
            asset_url=$(echo $BASE_URL | sed 's/gateway/asset/')
            echo -e "${BLUE}Checking asset service health first...${NC}"
            health_response=$(curl -s "$asset_url/health")
            echo "$health_response" | jq . 2>/dev/null || echo "$health_response"
            echo ""
        fi
        
        image_request='{"category": "image", "style": "realistic", "description": "A beautiful sunset over mountains"}'
        test_endpoint "POST" "/api/v1/assets/generate" "$image_request" "Generate Image Asset"
        ;;
    "assets-generate-audio")
        audio_request='{
            "category": "audio",
            "style": "ambient-calm",
            "description": "Peaceful background music for meditation",
            "requirements": {
                "platform": "mobile_vr",
                "quality": "medium"
            },
            "preferences": {
                "allow_generation": true,
                "max_cost": 0.15,
                "max_wait_time_ms": 45000
            }
        }'
        test_endpoint "POST" "/api/v1/assets/generate" "$audio_request" "Generate Audio Asset"
        ;;
    "assets-generate-3d")
        model_request='{
            "category": "prop",
            "style": "sci_fi",
            "description": "A futuristic energy crystal with glowing effects",
            "requirements": {
                "platform": "desktop_vr",
                "quality": "high",
                "polygon_count_max": 5000
            },
            "preferences": {
                "allow_generation": true,
                "max_cost": 0.50,
                "max_wait_time_ms": 120000
            }
        }'
        test_endpoint "POST" "/api/v1/assets/generate" "$model_request" "Generate 3D Model Asset"
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
    
    # Web UI Tests
    "web-health")
        echo -e "${COLOR_INFO}=== Web Service Health ===${COLOR_RESET}"
        response=$(curl -s -w "\n%{http_code}" -X GET "http://localhost:8080/health")
        status_code="${response##*$'\n'}"
        body="${response%$'\n'*}"
        
        if [ "$status_code" = "200" ]; then
            echo -e "${COLOR_SUCCESS}✅ Status: $status_code${COLOR_RESET}"
            echo "$body" | jq . 2>/dev/null || echo "$body"
        else
            echo -e "${COLOR_ERROR}❌ Status: $status_code${COLOR_RESET}"
            echo "$body"
        fi
        ;;
    
    "web-login")
        echo -e "${COLOR_INFO}=== Web UI Login Test ===${COLOR_RESET}"
        echo "Testing login form submission with dev user..."
        
        # Test login endpoint
        response=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8080/auth/login" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -H "Accept: text/html" \
            -d "email=dev@gaia.local&password=test" \
            -c /tmp/gaia-cookies.txt)
        
        # Check if we got a success message
        if echo "$response" | grep -q "Development login successful"; then
            echo -e "${COLOR_SUCCESS}✅ Login successful${COLOR_RESET}"
            echo "Session cookie created:"
            grep -E "session" /tmp/gaia-cookies.txt | tail -1 || echo "No session cookie found"
        else
            echo -e "${COLOR_ERROR}❌ Login failed${COLOR_RESET}"
            echo "Response: $response"
        fi
        ;;
    
    "web-chat-test")
        echo -e "${COLOR_INFO}=== Web Chat Interface Test ===${COLOR_RESET}"
        
        # First login
        echo "1. Logging in..."
        $0 web-login > /dev/null 2>&1
        
        # Test chat page access
        echo "2. Accessing chat page..."
        response=$(curl -s -w "\n%{http_code}" -X GET "http://localhost:8080/chat" \
            -b /tmp/gaia-cookies.txt \
            -L)
        
        status_code="${response##*$'\n'}"
        
        if [ "$status_code" = "200" ]; then
            echo -e "${COLOR_SUCCESS}✅ Chat page accessible${COLOR_RESET}"
            if echo "$response" | grep -q "Welcome back"; then
                echo "   User session active"
            fi
        else
            echo -e "${COLOR_ERROR}❌ Chat page not accessible (Status: $status_code)${COLOR_RESET}"
            exit 1
        fi
        
        # Test sending a message
        echo "3. Sending test message..."
        chat_response=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8080/api/chat/send" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -H "Accept: text/html" \
            -d "message=Hello from test script" \
            -b /tmp/gaia-cookies.txt)
        
        status_code="${chat_response##*$'\n'}"
        
        if [ "$status_code" = "200" ]; then
            echo -e "${COLOR_SUCCESS}✅ Message sent successfully${COLOR_RESET}"
            
            # Look for HTMX attributes (new approach) or script tag (old approach)  
            if echo "$chat_response" | grep -q "hx-get\|htmx.ajax"; then
                # Extract the message ID from the response
                message_id=$(echo "$chat_response" | grep -o "id=\w\+" | cut -d'=' -f2 | head -1)
                
                if [ ! -z "$message_id" ]; then
                    echo "4. Getting AI response for message ID: $message_id"
                    # Get the AI response directly
                    ai_response=$(curl -s -w "\n%{http_code}" -X GET "http://localhost:8080/api/chat/stream?message=Hello%20from%20test%20script&id=$message_id" \
                        -b /tmp/gaia-cookies.txt)
                
                status_code="${ai_response##*$'\n'}"
                
                if [ "$status_code" = "200" ]; then
                    echo -e "${COLOR_SUCCESS}✅ AI response received${COLOR_RESET}"
                    # Check if response contains actual content
                    if echo "$ai_response" | grep -q "assistant-message-placeholder\|Failed to get response"; then
                        echo -e "${COLOR_ERROR}❌ But response contains error${COLOR_RESET}"
                        echo "Response preview:"
                        echo "$ai_response" | head -n 10
                    else
                        echo "Response preview:"
                        echo "$ai_response" | grep -o '<div[^>]*>[^<]*</div>' | head -n 3
                    fi
                else
                    echo -e "${COLOR_ERROR}❌ Failed to get AI response (Status: $status_code)${COLOR_RESET}"
                fi
                else
                    echo -e "${COLOR_ERROR}❌ No message ID found${COLOR_RESET}"
                fi
            else
                echo -e "${COLOR_ERROR}❌ No HTMX triggers found in response${COLOR_RESET}"
            fi
        else
            echo -e "${COLOR_ERROR}❌ Failed to send message (Status: $status_code)${COLOR_RESET}"
        fi
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
        print_environment
        echo -e "${GREEN}Running all tests...${NC}\n"
        $0 --$ENVIRONMENT health
        $0 --$ENVIRONMENT status
        $0 --$ENVIRONMENT providers
        $0 --$ENVIRONMENT provider-health
        $0 --$ENVIRONMENT models
        $0 --$ENVIRONMENT cache
        ;;
    "chat-all")
        echo -e "${GREEN}Testing all chat endpoints with: 'What is 2+2?'${NC}\n"
        $0 --$ENVIRONMENT chat "What is 2+2?"
        $0 --$ENVIRONMENT direct "What is 2+2?"
        $0 --$ENVIRONMENT direct-db "What is 2+2?"
        $0 --$ENVIRONMENT ultrafast "What is 2+2?"
        $0 --$ENVIRONMENT ultrafast-redis "What is 2+2?"
        $0 --$ENVIRONMENT ultrafast-redis-v2 "What is 2+2?"
        $0 --$ENVIRONMENT ultrafast-redis-v3 "What is 2+2?"
        $0 --$ENVIRONMENT mcp-agent "What is 2+2?"
        $0 --$ENVIRONMENT mcp-agent-hot "What is 2+2?"
        $0 --$ENVIRONMENT orchestrated "What is 2+2?"
        $0 --$ENVIRONMENT multi-provider "What is 2+2?"
        echo -e "\n${BLUE}Testing sophisticated multiagent capabilities...${NC}"
        $0 --$ENVIRONMENT gamemaster
        $0 --$ENVIRONMENT worldbuilding
        $0 --$ENVIRONMENT storytelling
        $0 --$ENVIRONMENT problemsolving
        echo -e "\n${BLUE}Testing KB-enhanced multiagent capabilities...${NC}"
        $0 --$ENVIRONMENT kb-enhanced
        $0 --$ENVIRONMENT kb-research
        $0 --$ENVIRONMENT kb-gamemaster
        $0 --$ENVIRONMENT kb-development
        $0 --$ENVIRONMENT kb-search "consciousness"
        $0 --$ENVIRONMENT kb-context "gaia"
        $0 --$ENVIRONMENT kb-multitask
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
    "assets-all")
        echo -e "${GREEN}Testing all asset generation endpoints...${NC}\n"
        $0 assets-test
        $0 assets-list
        $0 assets-generate-image
        $0 assets-generate-audio
        $0 assets-generate-3d
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
    "web-all")
        echo -e "${GREEN}Testing all web UI endpoints...${NC}\n"
        $0 web-health
        $0 web-login
        $0 web-chat-test
        ;;
    *)
        echo "Usage: $0 [--local|--staging|--prod|--url URL] {health|chat|stream|providers|models|pricing|usage|all} [args]"
        echo ""
        echo "Environment Options:"
        echo "  --local                      # Test local development (default)"
        echo "  --staging                    # Test staging deployment"
        echo "  --prod                       # Test production deployment"
        echo "  --url URL                    # Test custom URL"
        echo ""
        echo "Core Tests:"
        echo "  $0 health                    # Check service health"
        echo "  $0 chat \"What is 2+2?\"       # Non-streaming chat"
        echo "  $0 stream \"Tell me a joke\"   # Streaming chat"
        echo ""
        echo "MMOIRL Chat Endpoints:"
        echo "  $0 ultrafast \"Question\"      # Ultrafast chat (no history, <500ms)"
        echo "  $0 ultrafast-redis \"Q\"       # Ultrafast with Redis history"
        echo "  $0 ultrafast-redis-v2 \"Q\"    # Optimized Redis chat"
        echo "  $0 ultrafast-redis-v3 \"Q\"    # Parallel Redis chat (fastest!)"
        echo "  $0 direct \"Question\"         # Direct Anthropic API"
        echo "  $0 direct-db \"Question\"      # Direct with PostgreSQL storage"
        echo "  $0 mcp-agent \"Question\"      # Full MCP-agent framework"
        echo "  $0 mcp-agent-hot \"Q\"        # Pre-initialized MCP agent (faster)"
        echo "  $0 orchestrated \"Question\"   # Multi-agent orchestration"
        echo "  $0 multi-provider \"Q\"        # Auto-select best provider"
        echo ""
        echo "KB-Enhanced Chat Endpoints (KOS Integration):"
        echo "  $0 kb-enhanced \"Query\"        # Adaptive KB-enhanced multiagent"
        echo "  $0 kb-research \"Topic\"        # Research with knowledge agents"
        echo "  $0 kb-gamemaster \"Scene\"      # Game master with world knowledge"
        echo "  $0 kb-development \"Question\"  # Development guidance from KB"
        echo "  $0 kb-health                  # KB health with repository status"
        echo "  $0 kb-search \"Keywords\"       # Direct KB search interface"
        echo "  $0 kb-context \"ContextName\"   # Load KOS context (gaia, mmoirl, etc)"
        echo "  $0 kb-multitask \"Tasks\"       # Parallel KB task execution"
        echo ""
        echo "Chat Utility Endpoints:"
        echo "  $0 chat-status               # Chat service detailed status"
        echo "  $0 reload-prompt             # Reload prompt templates"
        echo "  $0 conversations             # List all conversations"
        echo "  $0 conversations-search      # Search conversations"
        echo "  $0 orchestrated-metrics      # Orchestration performance metrics"
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
        echo "Asset Generation Tests:"
        echo "  $0 assets-test               # Asset service health check"
        echo "  $0 assets-list               # List available assets"
        echo "  $0 assets-generate-image     # Generate image asset"
        echo "  $0 assets-generate-audio     # Generate audio asset"
        echo "  $0 assets-generate-3d        # Generate 3D model asset"
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
        echo "Web UI Tests:"
        echo "  $0 web-health                # Web service health check"
        echo "  $0 web-login                 # Test web UI login"
        echo "  $0 web-chat-test             # Test chat interface access"
        echo ""
        echo "Batch Tests:"
        echo "  $0 all                       # Run core tests"
        echo "  $0 chat-all                  # Test all chat endpoints"
        echo "  $0 providers-all             # Test all provider endpoints"
        echo "  $0 pricing-all               # Test all pricing endpoints"
        echo "  $0 assets-all                # Test all asset generation endpoints"
        echo "  $0 usage-all                 # Test all usage endpoints"
        echo "  $0 personas-all              # Test all persona endpoints"
        echo "  $0 performance-all           # Test all performance endpoints"
        echo "  $0 auth-all                  # Test all authentication endpoints"
        echo "  $0 web-all                   # Test all web UI endpoints"
        exit 1
        ;;
esac