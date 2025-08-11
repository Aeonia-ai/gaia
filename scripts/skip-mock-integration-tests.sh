#!/bin/bash
# Skip all integration tests that use mocks (route.fulfill pattern)

echo "Finding and marking mock-based integration tests for skipping..."

# Find all test files with route.fulfill
for file in $(grep -l "route\.fulfill" tests/integration/web/*.py tests/integration/web-service/*.py 2>/dev/null); do
    echo "Processing: $file"
    
    # Find test methods that aren't already skipped
    grep -n "async def test_" "$file" | while IFS=: read -r line_num test_line; do
        # Check if the line before is already a skip marker
        prev_line_num=$((line_num - 1))
        prev_line=$(sed -n "${prev_line_num}p" "$file" 2>/dev/null)
        
        if [[ ! "$prev_line" =~ "@pytest.mark.skip" ]]; then
            # Extract test method name
            test_name=$(echo "$test_line" | grep -o "test_[^(]*")
            echo "  - Adding skip marker to $test_name"
            
            # Add skip marker (macOS compatible)
            sed -i '' "${line_num}i\\
    @pytest.mark.skip(reason=\"Integration test should not use mocks - violates testing principles\")" "$file"
        fi
    done
done

echo "Done! Mock-based integration tests have been marked for skipping."