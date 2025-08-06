#!/usr/bin/env python3
"""
Run integration tests with intelligent parallelization strategy.

Categorizes tests and runs them with appropriate worker counts to avoid
resource exhaustion while maintaining reasonable execution time.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple
import os

# Test categories with appropriate worker counts
TEST_CATEGORIES = {
    "resource_intensive": {
        "paths": [
            "tests/integration/test_supabase_auth_integration.py",
            "tests/integration/test_conversation_delete.py",
            "tests/integration/test_conversation_persistence.py",
        ],
        "workers": 1,  # Sequential execution
        "description": "Tests that create/delete external resources"
    },
    
    "web_browser": {
        "paths": [
            "tests/integration/web/",
        ],
        "workers": 2,  # Limited parallelism for browser tests
        "description": "Playwright browser tests (resource heavy)"
    },
    
    "api_heavy": {
        "paths": [
            "tests/integration/test_v02_chat_api.py",
            "tests/integration/test_v03_api.py",
            "tests/integration/test_unified_chat_endpoint.py",
            "tests/integration/test_provider_model_endpoints.py",
        ],
        "workers": 4,  # Moderate parallelism
        "description": "API tests with multiple service calls"
    },
    
    "standard": {
        "paths": [
            "tests/integration/test_api_endpoints_comprehensive.py",
            "tests/integration/test_format_negotiation.py",
            "tests/integration/test_gateway_client.py",
            "tests/integration/test_working_endpoints.py",
        ],
        "workers": 8,  # Full parallelism for simple tests
        "description": "Standard integration tests"
    }
}

def run_test_category(category_name: str, config: dict) -> Tuple[bool, int, int]:
    """
    Run tests in a category with specified worker count.
    Returns (success, passed_count, failed_count)
    """
    print(f"\n{'='*60}")
    print(f"Running {category_name} tests")
    print(f"Description: {config['description']}")
    print(f"Workers: {config['workers']}")
    print(f"Paths: {', '.join(config['paths'])}")
    print(f"{'='*60}\n")
    
    # Build pytest command
    cmd = ["./scripts/pytest-for-claude.sh"]
    cmd.extend(config["paths"])
    cmd.extend(["-v", "-n", str(config["workers"])])
    
    # Add markers if needed
    if category_name == "resource_intensive":
        cmd.extend(["-m", "not skip"])
    
    # Show the command being run
    print(f"Running command: {' '.join(cmd)}")
    
    # Run tests
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time
    
    # Parse results from pytest output
    output = result.stdout + result.stderr
    
    # Look for pytest summary line (e.g., "====== 5 passed, 2 failed ======")
    import re
    summary_pattern = r'(\d+)\s+passed'
    failed_pattern = r'(\d+)\s+failed'
    
    passed_match = re.search(summary_pattern, output)
    failed_match = re.search(failed_pattern, output)
    
    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0
    
    # Also check for errors in running the command itself
    if result.returncode != 0 and passed == 0 and failed == 0:
        print("\n⚠️  Tests may not have run properly. Check output above.")
        print(f"Return code: {result.returncode}")
        if result.stderr:
            print(f"Error output: {result.stderr[:500]}")
    
    print(f"\nCategory '{category_name}' completed in {duration:.1f}s")
    print(f"Results: {passed} passed, {failed} failed")
    
    return result.returncode == 0, passed, failed

def main():
    """Run all integration tests with intelligent parallelization."""
    print("Integration Test Runner - Intelligent Parallelization")
    print("=" * 60)
    print("This script runs integration tests with appropriate worker counts")
    print("to avoid resource exhaustion while maintaining good performance.")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    failed_categories = []
    
    # Run each category
    for category_name, config in TEST_CATEGORIES.items():
        success, passed, failed = run_test_category(category_name, config)
        total_passed += passed
        total_failed += failed
        
        if not success:
            failed_categories.append(category_name)
    
    # Summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Total tests passed: {total_passed}")
    print(f"Total tests failed: {total_failed}")
    
    if total_passed + total_failed > 0:
        success_rate = total_passed / (total_passed + total_failed) * 100
        print(f"Success rate: {success_rate:.1f}%")
    else:
        print("No tests were run!")
        return 1
    
    if failed_categories:
        print(f"\nFailed categories: {', '.join(failed_categories)}")
        return 1
    else:
        print("\n✅ All test categories passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())