#!/bin/bash
# Test Consistency Check - Run same tests multiple times and compare

set -e

TEST_PATTERN=${1:-"tests/integration"}
RUNS=3
RESULTS_DIR="logs/consistency-check"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "🔍 Testing consistency by running $RUNS identical test runs"
echo "📂 Test pattern: $TEST_PATTERN"
echo "📁 Results will be saved to: $RESULTS_DIR/$TIMESTAMP"

mkdir -p "$RESULTS_DIR/$TIMESTAMP"

# Function to extract clean summary from log
extract_summary() {
    local log_file=$1
    local run_num=$2
    
    echo "Extracting summary from run $run_num..."
    
    # Wait for log file to be written and process to complete
    while true; do
        if [[ -f "$log_file" ]]; then
            # Look for completion marker
            if grep -q "Test run completed" "$log_file" 2>/dev/null; then
                break
            fi
        fi
        sleep 5
        echo "  Waiting for run $run_num to complete..."
    done
    
    # Extract the final summary line
    grep -E "=+ .* failed.* passed.* in .*s" "$log_file" | tail -1 > "$RESULTS_DIR/$TIMESTAMP/summary-$run_num.txt" || echo "No summary found" > "$RESULTS_DIR/$TIMESTAMP/summary-$run_num.txt"
    
    # Also extract failed test names
    grep "FAILED " "$log_file" | sed 's/^.*FAILED \([^ ]*\) .*/\1/' | sort > "$RESULTS_DIR/$TIMESTAMP/failures-$run_num.txt" || touch "$RESULTS_DIR/$TIMESTAMP/failures-$run_num.txt"
    
    echo "  Run $run_num summary extracted"
}

# Run tests multiple times
for i in $(seq 1 $RUNS); do
    echo ""
    echo "🔄 Starting run $i of $RUNS at $(date)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Start test run
    ./scripts/pytest-for-claude.sh "$TEST_PATTERN" -v
    
    # Find the most recent log file
    LATEST_LOG=$(ls -t logs/tests/pytest/test-run-*.log | head -1)
    cp "$LATEST_LOG" "$RESULTS_DIR/$TIMESTAMP/run-$i-full.log"
    
    # Extract summary
    extract_summary "$LATEST_LOG" "$i"
    
    echo "✅ Run $i completed at $(date)"
    echo ""
    
    # Brief pause between runs to ensure clean separation
    if [[ $i -lt $RUNS ]]; then
        echo "⏸️  Pausing 10 seconds before next run..."
        sleep 10
    fi
done

echo ""
echo "📊 CONSISTENCY ANALYSIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$RESULTS_DIR/$TIMESTAMP"

echo ""
echo "🔢 SUMMARY COMPARISON:"
echo "────────────────────────────────────────────────────────────────────────────"
for i in $(seq 1 $RUNS); do
    echo "Run $i: $(cat summary-$i.txt)"
done

echo ""
echo "🎯 CONSISTENCY CHECK:"
echo "────────────────────────────────────────────────────────────────────────────"

# Compare summaries
if diff -q summary-1.txt summary-2.txt >/dev/null && diff -q summary-2.txt summary-3.txt >/dev/null; then
    echo "✅ PERFECTLY CONSISTENT: All runs have identical summary results"
else
    echo "❌ INCONSISTENT: Runs have different summary results"
    echo ""
    echo "Differences:"
    for i in $(seq 2 $RUNS); do
        echo "  Run 1 vs Run $i:"
        diff summary-1.txt summary-$i.txt || true
    done
fi

echo ""
echo "🔥 FAILED TEST COMPARISON:"
echo "────────────────────────────────────────────────────────────────────────────"

# Compare failure lists
for i in $(seq 1 $RUNS); do
    failure_count=$(wc -l < failures-$i.txt)
    echo "Run $i: $failure_count failed tests"
done

# Show unique failures across runs
echo ""
echo "Unique failing tests across all runs:"
cat failures-*.txt | sort | uniq -c | sort -nr

echo ""
echo "Tests that failed in some runs but not others:"
cat failures-*.txt | sort | uniq -u

# Detailed comparison
echo ""
echo "🔍 DETAILED FAILURE ANALYSIS:"
echo "────────────────────────────────────────────────────────────────────────────"

if diff -q failures-1.txt failures-2.txt >/dev/null && diff -q failures-2.txt failures-3.txt >/dev/null; then
    echo "✅ PERFECTLY CONSISTENT: All runs failed on exactly the same tests"
else
    echo "❌ INCONSISTENT: Different tests failed across runs"
    echo ""
    echo "Failed in Run 1 only:"
    comm -23 failures-1.txt <(cat failures-2.txt failures-3.txt | sort | uniq) || echo "  None"
    echo ""
    echo "Failed in Run 2 only:"
    comm -23 failures-2.txt <(cat failures-1.txt failures-3.txt | sort | uniq) || echo "  None"
    echo ""
    echo "Failed in Run 3 only:"
    comm -23 failures-3.txt <(cat failures-1.txt failures-2.txt | sort | uniq) || echo "  None"
fi

echo ""
echo "📈 FINAL ASSESSMENT:"
echo "────────────────────────────────────────────────────────────────────────────"

# Extract numbers from summaries for comparison
run1_failures=$(grep -o '[0-9]\+ failed' summary-1.txt | grep -o '[0-9]\+' || echo "0")
run2_failures=$(grep -o '[0-9]\+ failed' summary-2.txt | grep -o '[0-9]\+' || echo "0")
run3_failures=$(grep -o '[0-9]\+ failed' summary-3.txt | grep -o '[0-9]\+' || echo "0")

if [[ "$run1_failures" == "$run2_failures" && "$run2_failures" == "$run3_failures" ]]; then
    echo "✅ STABLE: All runs had exactly $run1_failures failures"
    echo "   Test suite is RELIABLE and DETERMINISTIC"
else
    echo "❌ FLAKY: Failure counts were $run1_failures, $run2_failures, $run3_failures"
    echo "   Test suite is UNRELIABLE and needs flakiness fixes"
fi

echo ""
echo "📄 All logs and analysis saved to: $RESULTS_DIR/$TIMESTAMP/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"