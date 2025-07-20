#!/usr/bin/env python3
"""
Run the mTLS connection test script directly.
"""
import subprocess
import sys

# Run the test script
result = subprocess.run([sys.executable, "./scripts/test-mtls-connections.py"], capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

sys.exit(result.returncode)