#!/bin/bash
# Quick Flaky Test Check - Run a specific test multiple times

TEST_FILE=${1:-"tests/integration/web/test_full_web_browser.py"}
RUNS=${2:-3}

echo "🔍 Checking for flaky behavior in: $TEST_FILE"
echo "🔄 Running $RUNS times..."

for i in $(seq 1 $RUNS); do
    echo ""
    echo "=== RUN $i ==="
    
    # Run the test directly and capture just the summary
    ./scripts/pytest-for-claude.sh "$TEST_FILE" -v --tb=no | grep -E "=+ .* =" | tail -1
done

echo ""
echo "✅ Done! Look for different results across runs to identify flaky tests."
echo ""
echo "If results are identical each time = CONSISTENT (good)"  
echo "If results differ = FLAKY (bad)"