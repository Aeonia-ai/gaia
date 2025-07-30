#!/bin/bash
# Run tests that require Docker access from the host machine

echo "🏃 Running host-only tests from host machine..."
echo "These tests require Docker access and cannot run inside containers"
echo ""

# Make sure we have pytest installed on host
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found on host. Installing..."
    pip install pytest pytest-xdist
fi

# Run only host-only marked tests
python -m pytest tests/ -m "host_only" -v

echo ""
echo "✅ Host-only tests complete"