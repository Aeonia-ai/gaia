#!/bin/bash
# Run web service tests

set -e

echo "🧪 Running Web Service Tests"
echo "=========================="

# Set test environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export ENV="test"
export DEBUG="true"

# Run unit tests
echo ""
echo "📦 Running Unit Tests..."
docker compose run --rm test pytest -m "unit" tests/web/ -v

# Run integration tests if requested
if [ "$1" == "--integration" ] || [ "$1" == "--all" ]; then
    echo ""
    echo "🔗 Running Integration Tests..."
    export RUN_INTEGRATION_TESTS=true
    docker compose run --rm test pytest -m "integration" tests/web/ -v
fi

# Run all web tests if requested
if [ "$1" == "--all" ]; then
    echo ""
    echo "🎯 Running All Web Tests..."
    docker compose run --rm test pytest tests/web/ -v
fi

# Coverage report if requested
if [ "$2" == "--coverage" ]; then
    echo ""
    echo "📊 Generating Coverage Report..."
    docker compose run --rm test pytest tests/web/ \
        --cov=app/services/web \
        --cov-report=html \
        --cov-report=term
fi

echo ""
echo "✅ Web Service Tests Complete!"