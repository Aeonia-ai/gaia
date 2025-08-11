#!/bin/bash
# Fix syntax errors in mock-skipped tests

echo "Fixing syntax errors in mock-skipped tests..."

# Find all Python test files with the bad syntax pattern
find tests/integration/web -name "*.py" -type f | while read -r file; do
    # Check if file has the syntax error pattern
    if grep -q '@pytest.mark.skip(reason="Integration test should not use mocks - violates testing principles")[[:space:]]*async def' "$file"; then
        echo "Fixing: $file"
        
        # macOS compatible sed to fix the pattern
        # Replace the pattern where decorator and async def are on same line
        sed -i '' 's/@pytest.mark.skip(reason="Integration test should not use mocks - violates testing principles")[[:space:]]*async def/@pytest.mark.skip(reason="Integration test should not use mocks - violates testing principles")\
    async def/g' "$file"
    fi
done

echo "Syntax fixes complete!"