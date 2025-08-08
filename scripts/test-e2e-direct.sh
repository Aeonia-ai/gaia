#!/bin/bash
# Direct E2E test runner - simple wrapper for pytest-for-claude

set -e

echo "🧪 Running E2E tests directly..."
echo "================================"

# Run E2E tests with sequential execution to prevent hanging
./scripts/pytest-for-claude.sh tests/e2e -v -n 1

echo "================================"
echo "✅ E2E tests completed"