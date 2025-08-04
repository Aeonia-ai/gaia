#!/bin/bash
# Check auto-suspend status for GAIA services
# Run this script after idle timeout to verify auto-suspension is working

echo "🔍 Checking GAIA services auto-suspend status..."
echo "================================================"
echo "Expected: Services should be suspended after 30 minutes of inactivity"
echo ""

# Array of services to check
services=(
    "gaia-auth-dev"
    "gaia-chat-dev"
    "gaia-asset-dev"
    "gaia-web-dev"
    "gaia-kb-dev"
    "gaia-gateway-dev"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
all_suspended=true
gateway_running=false

# Check each service
for service in "${services[@]}"; do
    echo -n "Checking $service... "
    
    # Get machine states
    machines=$(fly machines list --app "$service" --json 2>/dev/null | jq -r '.[] | .state' 2>/dev/null)
    
    if [ -z "$machines" ]; then
        echo -e "${RED}ERROR: Unable to check status${NC}"
        continue
    fi
    
    # Check if any machines are running
    running_count=$(echo "$machines" | grep -c "started")
    stopped_count=$(echo "$machines" | grep -c "stopped")
    total_count=$(echo "$machines" | wc -l)
    
    if [ "$running_count" -eq 0 ]; then
        echo -e "${GREEN}✓ SUSPENDED${NC} (all $total_count machines stopped)"
    else
        echo -e "${YELLOW}⚡ RUNNING${NC} ($running_count of $total_count machines active)"
        all_suspended=false
        if [ "$service" = "gaia-gateway-dev" ]; then
            gateway_running=true
        fi
    fi
done

echo ""
echo "================================================"
echo "Summary:"

if $all_suspended; then
    echo -e "${GREEN}✅ All services successfully suspended!${NC}"
    echo "💰 Maximum cost savings achieved"
elif $gateway_running; then
    echo -e "${YELLOW}⚠️  Some services still running${NC}"
    echo "This is expected if there was recent activity"
else
    echo -e "${GREEN}✅ Most services suspended successfully${NC}"
    echo "Only essential services remain active"
fi

echo ""
echo "💡 Tips:"
echo "- Services auto-suspend after 30 minutes of inactivity"
echo "- They wake up automatically on first request (~15-20s)"
echo "- To force immediate suspension: fly scale count 0 --app SERVICE_NAME"
echo "- To check specific service: fly status --app SERVICE_NAME"