#!/bin/bash
# Manual Consistency Check - Start runs manually due to Claude Code 2-minute timeout

echo "🔍 Manual consistency check for integration tests"
echo "Due to Claude Code 2-minute timeout, starting runs manually"
echo ""

RESULTS_DIR="logs/consistency-check/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Function to start a test run
start_run() {
    local run_num=$1
    echo "🔄 Starting run $run_num..."
    ./scripts/pytest-for-claude.sh tests/integration -v
    
    # Get the latest log file
    local latest_log=$(ls -t logs/tests/pytest/test-run-*.log | head -1)
    echo "📝 Run $run_num log: $latest_log"
    
    # Copy it to our results directory
    cp "$latest_log" "$RESULTS_DIR/run-$run_num-full.log"
    echo "✅ Run $run_num started, monitoring: $latest_log"
    echo ""
}

echo "Starting Run 1..."
start_run 1

echo "📊 Check progress with: ./scripts/check-test-progress.sh"
echo "📁 Results being saved to: $RESULTS_DIR"
echo ""
echo "Next steps:"
echo "1. Wait for Run 1 to complete (check with: ./scripts/check-test-progress.sh)"
echo "2. Run this script again for Run 2: $0 2"
echo "3. Run this script again for Run 3: $0 3"
echo "4. Analyze results with: ls -la $RESULTS_DIR"