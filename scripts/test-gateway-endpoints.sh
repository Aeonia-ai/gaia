#!/bin/bash

cat << 'EOF'
⚠️  DEPRECATED: This test script has been migrated to pytest
════════════════════════════════════════════════════════════

This functionality is now available in the automated test suite:
  tests/integration/gateway/test_gateway_auth_endpoints.py

To run gateway endpoint tests:
  ./scripts/pytest-for-claude.sh tests/integration/gateway/ -v

To run specific auth tests:
  ./scripts/pytest-for-claude.sh tests/integration/gateway/test_gateway_auth_endpoints.py -v

For all available tests:
  ./scripts/run-tests.sh

This script will be removed in the next release.
EOF

exit 1