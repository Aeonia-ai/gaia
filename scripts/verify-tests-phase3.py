#!/usr/bin/env python3
"""
Phase 3 Test Verification Script
Ensures tests still pass after reorganization.
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, description, use_docker=True):
    """Run a command and report results."""
    print(f"\n🔄 {description}...")
    start_time = time.time()
    
    # Wrap command in docker compose if needed
    if use_docker and not cmd.startswith("docker"):
        cmd = f"docker compose run --rm test {cmd}"
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED ({elapsed:.1f}s)")
            return True
        else:
            print(f"❌ {description} - FAILED ({elapsed:.1f}s)")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️  {description} - TIMEOUT after 5 minutes")
        return False
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False

def verify_phase3():
    """Verify tests work after Phase 3 reorganization."""
    print("=" * 60)
    print("PHASE 3 VERIFICATION: Test Reorganization")
    print("=" * 60)
    
    tests_to_run = [
        # Quick sanity checks first
        ("Test Discovery", "python -m pytest --collect-only -q | grep -E '^<' | wc -l"),
        
        # Run by marker (should work regardless of location)
        ("Unit Tests by Marker", "python -m pytest -m unit --maxfail=5 -x"),
        ("Integration Tests by Marker", "python -m pytest -m integration --maxfail=5 -x"),
        
        # Run by directory (if reorganized)
        ("Unit Tests by Directory", "python -m pytest tests/unit --maxfail=5 -x"),
        ("Integration Tests by Directory", "python -m pytest tests/integration --maxfail=5 -x"),
        
        # Critical tests
        ("Conversation Delete Test", "python -m pytest tests/integration/test_conversation_delete.py -v"),
        ("Comprehensive Suite", "python -m pytest tests/integration/test_comprehensive_suite.py::TestComprehensiveSuite::test_core_system_health -v"),
        
        # Import verification
        ("Import Check", "python -c 'from tests.fixtures.test_auth import TestAuthManager; print(\"Imports OK\")'"),
    ]
    
    results = {}
    
    for test_name, command in tests_to_run:
        # Skip directory tests if not reorganized yet
        if "by Directory" in test_name:
            if test_name.startswith("Unit") and not Path("tests/unit").exists():
                print(f"\n⏭️  Skipping {test_name} - directory doesn't exist yet")
                continue
            if test_name.startswith("Integration") and not Path("tests/integration").exists():
                print(f"\n⏭️  Skipping {test_name} - directory doesn't exist yet")
                continue
        
        results[test_name] = run_command(command, test_name, use_docker=True)
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ All verification checks passed! Safe to proceed.")
        return True
    else:
        print("\n❌ Some checks failed. Review before proceeding.")
        print("\nFailed checks:")
        for test_name, result in results.items():
            if not result:
                print(f"  - {test_name}")
        return False

def check_current_structure():
    """Check current test structure."""
    print("\n📁 Current Test Structure:")
    
    # Check if already reorganized
    new_dirs = ["tests/unit", "tests/integration", "tests/e2e"]
    reorganized = any(Path(d).exists() for d in new_dirs)
    
    if reorganized:
        print("  ✅ Tests appear to be reorganized")
        for d in new_dirs:
            if Path(d).exists():
                count = len(list(Path(d).glob("test_*.py")))
                print(f"     {d}: {count} test files")
    else:
        print("  📋 Tests still in original structure")
        test_count = len(list(Path("tests").glob("test_*.py")))
        print(f"     tests/: {test_count} test files")
    
    return reorganized

def main():
    print("Phase 3 Test Verification")
    print("This ensures tests still work after reorganization")
    
    # Check structure
    reorganized = check_current_structure()
    
    # Run verification
    success = verify_phase3()
    
    if not success:
        print("\n⚠️  WARNING: Tests are not passing!")
        print("Fix issues before proceeding with reorganization.")
        sys.exit(1)
    else:
        if not reorganized:
            print("\n✅ Tests are passing. Safe to reorganize!")
            print("\nNext step: Run reorganization with:")
            print("  python scripts/reorganize-tests.py --execute")
        else:
            print("\n✅ Reorganized tests are working correctly!")

if __name__ == "__main__":
    main()