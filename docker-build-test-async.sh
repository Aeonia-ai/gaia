#\!/bin/bash
# Async Docker build script for test image

LOG_FILE="docker-build-test-$(date +%Y%m%d-%H%M%S).log"
PID_FILE=".docker-build-test.pid"

# Check if a build is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "❌ Build already in progress (PID: $OLD_PID)"
        exit 1
    else
        rm "$PID_FILE"
    fi
fi

echo "🚀 Starting Docker test build in background..."
docker compose build test > "$LOG_FILE" 2>&1 &
BUILD_PID=$\!
echo $BUILD_PID > "$PID_FILE"

echo "✅ Build started (PID: $BUILD_PID)"
echo "📄 Log: $LOG_FILE"
echo "Check status: tail -f $LOG_FILE"
