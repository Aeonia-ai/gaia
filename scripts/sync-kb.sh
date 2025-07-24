#!/bin/bash
# KB Synchronization Script for Remote Deployments

KB_DIR="${KB_PATH:-/kb}"
KB_GIT_URL="${KB_GIT_URL}"
KB_GIT_TOKEN="${KB_GIT_TOKEN}"
LOCK_FILE="/tmp/kb-sync.lock"

# Add color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting KB sync...${NC}"

# Prevent concurrent syncs
if [ -f "$LOCK_FILE" ]; then
    echo -e "${YELLOW}KB sync already in progress${NC}"
    exit 0
fi

touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

# Construct authenticated URL if token provided
if [ -n "$KB_GIT_TOKEN" ] && [ -n "$KB_GIT_URL" ]; then
    # Extract the URL parts and insert token
    AUTH_URL=$(echo "$KB_GIT_URL" | sed "s|https://|https://${KB_GIT_TOKEN}@|")
else
    AUTH_URL="$KB_GIT_URL"
fi

# Clone or update KB
if [ -d "$KB_DIR/.git" ]; then
    echo -e "${GREEN}Updating existing KB...${NC}"
    cd "$KB_DIR"
    git pull origin main --quiet
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}KB updated successfully${NC}"
    else
        echo -e "${RED}KB update failed${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Cloning KB repository...${NC}"
    git clone --depth 1 "$AUTH_URL" "$KB_DIR"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}KB cloned successfully${NC}"
    else
        echo -e "${RED}KB clone failed${NC}"
        exit 1
    fi
fi

# Update sync timestamp
date +%s > "$KB_DIR/.last-sync"
echo -e "${GREEN}KB sync completed at $(date)${NC}"