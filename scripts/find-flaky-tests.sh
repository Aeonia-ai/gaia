#!/bin/bash
# Find Flaky Tests - Run same tests multiple times to identify inconsistent results

set -e

RUNS=${1:-3}
TEST_PATTERN=${2:-"tests/integration"}
RESULTS_DIR="logs/flaky-analysis"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "🔍 Finding flaky tests by running $RUNS times: $TEST_PATTERN"
echo "📁 Results will be saved to: $RESULTS_DIR/$TIMESTAMP"

mkdir -p "$RESULTS_DIR/$TIMESTAMP"

# Run tests multiple times
for i in $(seq 1 $RUNS); do
    echo "🔄 Run $i of $RUNS..."
    
    # Run tests and capture results
    ./scripts/pytest-for-claude.sh "$TEST_PATTERN" --tb=no -v > "$RESULTS_DIR/$TIMESTAMP/run-$i.log" 2>&1 || true
    
    # Extract just the test results (PASSED/FAILED lines)
    grep -E "(PASSED|FAILED|SKIPPED)" "$RESULTS_DIR/$TIMESTAMP/run-$i.log" | \
        sed 's/.*::\([^:]*\) \(PASSED\|FAILED\|SKIPPED\).*/\1 \2/' > "$RESULTS_DIR/$TIMESTAMP/results-$i.txt" || true
    
    echo "✅ Run $i completed"
    sleep 5  # Brief pause between runs
done

echo "📊 Analyzing results for flaky tests..."

# Create analysis script
cat > "$RESULTS_DIR/$TIMESTAMP/analyze.py" << 'EOF'
import sys
import os
from collections import defaultdict

# Read all result files
runs = []
for i in range(1, int(sys.argv[1]) + 1):
    file_path = f"results-{i}.txt"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            run_results = {}
            for line in f:
                line = line.strip()
                if ' ' in line:
                    test_name, result = line.rsplit(' ', 1)
                    run_results[test_name] = result
            runs.append(run_results)

# Find all unique test names
all_tests = set()
for run in runs:
    all_tests.update(run.keys())

# Analyze each test for consistency
flaky_tests = []
consistent_failures = []
consistent_passes = []

for test in sorted(all_tests):
    results = []
    for run in runs:
        if test in run:
            results.append(run[test])
        else:
            results.append("MISSING")
    
    unique_results = set(results)
    
    if len(unique_results) > 1:
        # Test has different results across runs
        flaky_tests.append((test, results))
    elif "FAILED" in unique_results:
        consistent_failures.append((test, results))
    elif "PASSED" in unique_results:
        consistent_passes.append((test, results))

# Output results
print(f"\n🎯 FLAKY TESTS ({len(flaky_tests)}):")
print("=" * 80)
for test, results in flaky_tests:
    print(f"{test}")
    print(f"  Results: {' -> '.join(results)}")
    print()

print(f"\n❌ CONSISTENT FAILURES ({len(consistent_failures)}):")
print("=" * 80)
for test, results in consistent_failures:
    print(f"{test} (always fails)")

print(f"\n✅ CONSISTENT PASSES ({len(consistent_passes)}):")
print("=" * 80)
print(f"Total consistent passing tests: {len(consistent_passes)}")

print(f"\n📈 SUMMARY:")
print(f"Total tests analyzed: {len(all_tests)}")
print(f"Flaky tests: {len(flaky_tests)}")
print(f"Consistent failures: {len(consistent_failures)}")  
print(f"Consistent passes: {len(consistent_passes)}")
print(f"Flaky rate: {len(flaky_tests)/len(all_tests)*100:.1f}%")
EOF

# Run analysis
cd "$RESULTS_DIR/$TIMESTAMP"
python3 analyze.py "$RUNS"

echo ""
echo "🔍 Full analysis saved to: $RESULTS_DIR/$TIMESTAMP/"
echo ""
echo "Next steps:"
echo "1. Mark flaky tests with @pytest.mark.flaky"
echo "2. Fix consistent failures"
echo "3. Re-run analysis to verify improvements"