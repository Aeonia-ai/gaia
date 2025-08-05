#!/bin/bash
# Docker Async Build Script with organized logging

LOG_DIR="logs/docker"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/docker-build-$(date +%Y%m%d-%H%M%S).log"
PID_FILE=".docker-build.pid"

# Check if a build is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "❌ Build already in progress (PID: $OLD_PID)"
        echo "Check status with: ./scripts/docker-build-status.sh"
        exit 1
    else
        rm "$PID_FILE"
    fi
fi

# Start the build
echo "🚀 Starting Docker build in background..."
docker compose build --no-cache > "$LOG_FILE" 2>&1 &
BUILD_PID=$!
echo $BUILD_PID > "$PID_FILE"

echo "✅ Build started successfully!"
echo "📄 Log file: $LOG_FILE"
echo "🔍 PID: $BUILD_PID"
echo ""
echo "Next steps:"
echo "1. Check status: ./scripts/docker-build-status.sh"
echo "2. Watch logs: tail -f $LOG_FILE"
echo "3. When complete: docker compose up -d"