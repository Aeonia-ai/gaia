#!/usr/bin/env python3
"""Analyze test failures from test run log."""

import re
from collections import defaultdict

def analyze_test_log(log_file):
    """Analyze test failures from pytest log."""
    failures = defaultdict(list)
    errors = defaultdict(list)
    
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        # Match FAILED lines
        if "FAILED" in line:
            match = re.search(r'FAILED (tests/\S+)::', line)
            if match:
                test_path = match.group(1)
                category = test_path.split('/')[1]  # e2e, integration, unit
                failures[category].append(test_path)
        
        # Match ERROR lines
        elif "ERROR" in line:
            match = re.search(r'ERROR (tests/\S+)::', line)
            if match:
                test_path = match.group(1)
                category = test_path.split('/')[1]
                errors[category].append(test_path)
    
    # Print analysis
    print("=== TEST FAILURE ANALYSIS ===\n")
    
    total_failures = sum(len(v) for v in failures.values())
    total_errors = sum(len(v) for v in errors.values())
    
    print(f"Total Failures: {total_failures}")
    print(f"Total Errors: {total_errors}")
    print(f"Total Issues: {total_failures + total_errors}\n")
    
    print("Failures by Category:")
    for category, tests in sorted(failures.items()):
        print(f"\n{category.upper()} ({len(tests)} failures):")
        # Group by test file
        file_counts = defaultdict(int)
        for test in tests:
            file_name = test.split('::')[0].split('/')[-1]
            file_counts[file_name] += 1
        
        for file_name, count in sorted(file_counts.items(), key=lambda x: -x[1]):
            print(f"  - {file_name}: {count} failure(s)")
    
    if errors:
        print("\nErrors by Category:")
        for category, tests in sorted(errors.items()):
            print(f"\n{category.upper()} ({len(tests)} errors):")
            file_counts = defaultdict(int)
            for test in tests:
                file_name = test.split('::')[0].split('/')[-1]
                file_counts[file_name] += 1
            
            for file_name, count in sorted(file_counts.items(), key=lambda x: -x[1]):
                print(f"  - {file_name}: {count} error(s)")
    
    # Identify problem areas
    print("\n=== PROBLEM AREAS ===")
    
    # E2E browser tests are clearly problematic
    e2e_issues = len(failures.get('e2e', [])) + len(errors.get('e2e', []))
    if e2e_issues > 10:
        print(f"\n⚠️  E2E Browser Tests: {e2e_issues} issues")
        print("   These tests likely have environment or configuration issues")
        print("   Common causes: playwright setup, authentication mocking, HTMX handling")
    
    # Check for specific problem files
    all_issues = []
    for tests in failures.values():
        all_issues.extend(tests)
    for tests in errors.values():
        all_issues.extend(tests)
    
    problem_files = defaultdict(int)
    for test in all_issues:
        file_path = test.split('::')[0]
        problem_files[file_path] += 1
    
    print("\nMost Problematic Files:")
    for file_path, count in sorted(problem_files.items(), key=lambda x: -x[1])[:5]:
        print(f"  - {file_path}: {count} issues")

if __name__ == "__main__":
    analyze_test_log("/Users/jasbahr/Development/Aeonia/server/gaia/test-run-20250731-074915.log")