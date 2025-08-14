#!/usr/bin/env python3
"""
Analyze tests that accept both 401 and 403 status codes.
Categorize them to determine which should be updated.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict

# Patterns to identify authentication vs authorization scenarios
AUTHENTICATION_PATTERNS = [
    r"invalid.*api.*key",
    r"missing.*auth",
    r"no.*auth",
    r"without.*auth",
    r"unauthenticated",
    r"invalid.*jwt",
    r"invalid.*token",
    r"expired.*token",
    r"malformed.*token",
    r"invalid.*credentials",
    r"not.*authenticated",
]

AUTHORIZATION_PATTERNS = [
    r"permission.*denied",
    r"insufficient.*scope",
    r"rbac",
    r"not.*authorized",
    r"forbidden",
    r"access.*denied",
    r"requires.*permission",
    r"role.*required",
]

def find_auth_test_files(base_path: str = "tests/") -> List[Path]:
    """Find all test files that might contain auth tests."""
    test_files = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py") and file.startswith("test_"):
                test_files.append(Path(root) / file)
    return test_files

def extract_test_context(lines: List[str], line_num: int, context_lines: int = 10) -> str:
    """Extract context around a line for analysis."""
    start = max(0, line_num - context_lines)
    end = min(len(lines), line_num + context_lines + 1)
    return "\n".join(lines[start:end])

def categorize_test(test_name: str, context: str) -> str:
    """Categorize a test based on its name and context."""
    combined = (test_name + " " + context).lower()
    
    # Check for authentication patterns
    for pattern in AUTHENTICATION_PATTERNS:
        if re.search(pattern, combined):
            return "authentication"
    
    # Check for authorization patterns
    for pattern in AUTHORIZATION_PATTERNS:
        if re.search(pattern, combined):
            return "authorization"
    
    # Default to authentication (most common case)
    return "authentication"

def find_401_403_assertions(file_path: Path) -> List[Dict]:
    """Find all assertions that accept both 401 and 403."""
    results = []
    
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return results
    
    # Pattern to find assertions accepting [401, 403]
    patterns = [
        r"assert.*status_code.*in.*\[401,\s*403\]",
        r"assert.*status_code.*in.*\[403,\s*401\]",
        r"status_code\s+in\s+\[401,\s*403\]",
        r"status_code\s+in\s+\[403,\s*401\]",
    ]
    
    for line_num, line in enumerate(lines):
        for pattern in patterns:
            if re.search(pattern, line):
                # Find the test function name
                test_name = "unknown"
                for i in range(line_num, -1, -1):
                    test_match = re.search(r"def\s+(test_\w+)", lines[i])
                    if test_match:
                        test_name = test_match.group(1)
                        break
                
                # Extract context
                context = extract_test_context(lines, line_num)
                
                # Categorize
                category = categorize_test(test_name, context)
                
                results.append({
                    "file": str(file_path),
                    "line": line_num + 1,
                    "test_name": test_name,
                    "line_content": line.strip(),
                    "category": category,
                    "context": context
                })
                break
    
    return results

def main():
    """Main function to analyze all tests."""
    print("🔍 Analyzing tests that accept both 401 and 403...\n")
    
    # Find all test files
    test_files = find_auth_test_files()
    print(f"Found {len(test_files)} test files to analyze\n")
    
    # Analyze each file
    all_results = []
    for file_path in test_files:
        results = find_401_403_assertions(file_path)
        all_results.extend(results)
    
    # Group by category
    auth_tests = [r for r in all_results if r["category"] == "authentication"]
    authz_tests = [r for r in all_results if r["category"] == "authorization"]
    
    print(f"📊 Analysis Results:")
    print(f"Total tests accepting [401, 403]: {len(all_results)}")
    print(f"Authentication failures (should be 401): {len(auth_tests)}")
    print(f"Authorization failures (should be 403): {len(authz_tests)}")
    print()
    
    # Show authentication tests that need updating
    if auth_tests:
        print("🔧 Authentication tests that should expect only 401:")
        print("-" * 80)
        for test in auth_tests[:10]:  # Show first 10
            print(f"File: {test['file']}")
            print(f"Line {test['line']}: {test['test_name']}")
            print(f"Code: {test['line_content']}")
            print()
        
        if len(auth_tests) > 10:
            print(f"... and {len(auth_tests) - 10} more")
        print()
    
    # Show authorization tests that might be correct
    if authz_tests:
        print("🔐 Authorization tests that might correctly expect 403:")
        print("-" * 80)
        for test in authz_tests:
            print(f"File: {test['file']}")
            print(f"Line {test['line']}: {test['test_name']}")
            print(f"Code: {test['line_content']}")
            print()
    
    # Generate update script
    if auth_tests:
        print("\n📝 Generating update commands...")
        print("-" * 80)
        print("# Commands to update authentication tests to expect only 401:")
        print()
        
        # Group by file for efficient editing
        files_to_update = {}
        for test in auth_tests:
            if test['file'] not in files_to_update:
                files_to_update[test['file']] = []
            files_to_update[test['file']].append(test)
        
        for file_path, tests in files_to_update.items():
            print(f"# {file_path}")
            for test in tests:
                # Generate sed command for each line
                old_pattern = test['line_content'].strip()
                new_pattern = old_pattern.replace("[401, 403]", "401").replace("[403, 401]", "401")
                print(f"sed -i '' 's/{re.escape(old_pattern)}/{re.escape(new_pattern)}/g' {file_path}")
            print()

if __name__ == "__main__":
    main()