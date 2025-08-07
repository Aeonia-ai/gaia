#!/bin/bash
# Run E2E tests sequentially to avoid hanging

set -e

echo "🧪 Running E2E tests sequentially..."
echo "================================"

# Run E2E tests with sequential execution (-n 1)
docker compose run --rm test bash -c "PYTHONPATH=/app pytest tests/e2e -v -n 1 --tb=short"

echo "================================"
echo "✅ E2E tests completed"