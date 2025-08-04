#!/bin/bash
# Schedule auto-suspend check for 35 minutes from now

WAIT_TIME=2100  # 35 minutes in seconds
LOG_FILE="auto-suspend-check-$(date +%Y%m%d-%H%M%S).log"
PID_FILE=".auto-suspend-check.pid"

# Check if already scheduled
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "❌ Auto-suspend check already scheduled (PID: $OLD_PID)"
        exit 1
    else
        rm "$PID_FILE"
    fi
fi

echo "🕐 Scheduling auto-suspend check for 35 minutes from now..."
echo "Start time: $(date)"
echo "Check time: $(date -d '+35 minutes' 2>/dev/null || date -v +35M)"

# Run in background
(
    sleep $WAIT_TIME
    echo "=== Auto-Suspend Check Results ===" > "$LOG_FILE"
    echo "Check time: $(date)" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    /Users/jasonasbahr/Development/Aeonia/Server/gaia/scripts/check-auto-suspend.sh >> "$LOG_FILE" 2>&1
    
    # Send notification if possible
    if command -v osascript &> /dev/null; then
        osascript -e 'display notification "Auto-suspend check complete" with title "GAIA Services"'
    fi
    
    # Clean up PID file
    rm -f "$PID_FILE"
) &

# Save PID
echo $! > "$PID_FILE"

echo "✅ Check scheduled successfully!"
echo "📄 Results will be saved to: $LOG_FILE"
echo "🔍 To check progress: ps -p $(cat $PID_FILE)"
echo "📖 To view results when ready: cat $LOG_FILE"