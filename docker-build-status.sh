#!/bin/bash
# Docker Build Status Checker

PID_FILE=".docker-build.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "✅ No build in progress"
    exit 0
fi

PID=$(cat "$PID_FILE")
if ps -p "$PID" > /dev/null 2>&1; then
    echo "🔄 Build still running (PID: $PID)"
    
    # Find the latest log file
    LOG_FILE=$(ls -t docker-build-*.log 2>/dev/null | head -1)
    if [ -n "$LOG_FILE" ]; then
        echo "📊 Progress:"
        tail -5 "$LOG_FILE"
    fi
else
    echo "✅ Build completed!"
    rm "$PID_FILE"
    
    # Check if build was successful
    LOG_FILE=$(ls -t docker-build-*.log 2>/dev/null | head -1)
    if [ -n "$LOG_FILE" ] && grep -q "Successfully built" "$LOG_FILE"; then
        echo "🎉 All services built successfully!"
        echo "Run: docker compose up -d"
    else
        echo "❌ Build may have failed. Check the log:"
        echo "tail -100 $LOG_FILE"
    fi
fi