#!/usr/bin/env python3
"""
Script to run resource-intensive tests sequentially instead of in parallel.
This prevents resource exhaustion from concurrent Supabase API calls.
"""

import subprocess
import sys
import os

def run_sequential_tests():
    """Run resource-intensive integration tests one at a time."""
    
    # Sequential tests that create/manage external resources
    sequential_tests = [
        "tests/integration/test_supabase_auth_integration.py",
        "tests/integration/test_provider_model_endpoints.py", 
        "tests/integration/test_conversation_persistence.py",
    ]
    
    print("🔄 Running resource-intensive tests sequentially...")
    
    for test_file in sequential_tests:
        print(f"\n▶️  Running: {test_file}")
        
        # Run with n=1 to force sequential execution
        cmd = [
            "./scripts/pytest-for-claude.sh", 
            test_file,
            "-n", "1",  # Force single worker
            "-v", 
            "--tb=short"
        ]
        
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode != 0:
            print(f"❌ Failed: {test_file}")
            return False
        else:
            print(f"✅ Passed: {test_file}")
    
    print("\n🎉 All sequential tests completed!")
    return True

def run_parallel_tests():
    """Run the remaining tests in parallel."""
    
    print("\n🚀 Running remaining tests in parallel...")
    
    # Exclude the sequential tests we already ran
    cmd = [
        "./scripts/pytest-for-claude.sh",
        "tests/integration/",
        "--ignore=tests/integration/web",
        "--ignore=tests/integration/test_kb_service.py",
        "--ignore=tests/integration/test_supabase_auth_integration.py",
        "--ignore=tests/integration/test_provider_model_endpoints.py", 
        "--ignore=tests/integration/test_conversation_persistence.py",
        "-v"
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0

if __name__ == "__main__":
    print("🧪 Running integration tests with proper resource management...")
    
    # Run sequential tests first
    sequential_success = run_sequential_tests()
    
    if not sequential_success:
        print("❌ Sequential tests failed, skipping parallel tests")
        sys.exit(1)
    
    # Run remaining tests in parallel  
    parallel_success = run_parallel_tests()
    
    if not parallel_success:
        print("❌ Some parallel tests failed")
        sys.exit(1)
    
    print("🎉 All integration tests completed successfully!")