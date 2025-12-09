#!/bin/bash
# Monitor ALL KB server activity in real-time

echo "🔍 Monitoring ALL KB Server Events..."
echo "Press Ctrl+C to stop"
echo ""

docker logs -f --tail 0 gaia-kb-service-1 2>&1 | grep --line-buffered -E \
  "(timing_analysis|action_received|response_sent|Appended item|Processing \$append|Cannot remove|WebSocket.*accepted|Published|NATS|collect|give|drop|send_json|initial_state|connected)" \
  | while read line; do
    # Color code by event type
    if [[ $line == *"timing_analysis"* ]]; then
      # Highlight action timing in bright yellow
      echo -e "\033[1;33m$line\033[0m"  # Bright yellow - client exchanges
    elif [[ $line == *"Appended"* ]] || [[ $line == *"Processing"* ]]; then
      echo -e "\033[32m$line\033[0m"  # Green - state changes
    elif [[ $line == *"ERROR"* ]] || [[ $line == *"Cannot remove"* ]]; then
      echo -e "\033[31m$line\033[0m"  # Red - errors
    elif [[ $line == *"WebSocket"* ]] || [[ $line == *"NATS"* ]] || [[ $line == *"Published"* ]]; then
      echo -e "\033[36m$line\033[0m"  # Cyan - networking
    else
      echo -e "\033[33m$line\033[0m"  # Yellow - other activity
    fi
  done
