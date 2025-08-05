#!/bin/bash
# Docker Build Status Checker

PID_FILE=".docker-build.pid"
LOG_DIR="logs/docker"

if [ ! -f "$PID_FILE" ]; then
    echo "✅ No build in progress"
    
    # Show latest build log
    LATEST_LOG=$(ls -t "$LOG_DIR"/docker-build-*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo ""
        echo "Latest build log: $LATEST_LOG"
        
        # Check if build was successful
        if grep -q "Successfully built" "$LATEST_LOG"; then
            echo "🎉 Last build: SUCCESS"
        elif grep -q "ERROR" "$LATEST_LOG"; then
            echo "❌ Last build: FAILED"
            echo ""
            echo "Error details:"
            grep -A 5 "ERROR" "$LATEST_LOG" | tail -20
        fi
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")
if ps -p "$PID" > /dev/null 2>&1; then
    echo "🔄 Build still running (PID: $PID)"
    
    # Find the latest log file
    LOG_FILE=$(ls -t "$LOG_DIR"/docker-build-*.log 2>/dev/null | head -1)
    if [ -n "$LOG_FILE" ]; then
        echo "📊 Progress:"
        tail -5 "$LOG_FILE"
    fi
else
    echo "✅ Build completed!"
    rm "$PID_FILE"
    
    # Check if build was successful
    LOG_FILE=$(ls -t "$LOG_DIR"/docker-build-*.log 2>/dev/null | head -1)
    if [ -n "$LOG_FILE" ] && grep -q "Successfully built" "$LOG_FILE"; then
        echo "🎉 All services built successfully!"
        echo "Run: docker compose up -d"
    else
        echo "❌ Build may have failed. Check the log:"
        echo "tail -100 $LOG_FILE"
    fi
fi