#!/usr/bin/env python3
"""
Analyze current marker usage in test files without making changes.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def analyze_markers():
    """Analyze current test marker usage."""
    tests_dir = Path(__file__).parent.parent / 'tests'
    
    stats = defaultdict(int)
    unmarked_tests = []
    marked_tests = defaultdict(list)
    
    for test_file in tests_dir.rglob('test_*.py'):
        rel_path = test_file.relative_to(tests_dir)
        
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Find all test functions
        test_pattern = re.compile(r'^(async\s+)?def\s+(test_\w+)', re.MULTILINE)
        
        for match in test_pattern.finditer(content):
            test_name = match.group(2)
            func_start = match.start()
            
            # Look for markers before the function
            before_func = content[:func_start]
            lines_before = before_func.split('\n')
            
            found_marker = None
            for i in range(len(lines_before) - 1, max(0, len(lines_before) - 10), -1):
                line = lines_before[i].strip()
                if '@pytest.mark.unit' in line:
                    found_marker = 'unit'
                    break
                elif '@pytest.mark.integration' in line:
                    found_marker = 'integration'
                    break
                elif '@pytest.mark.e2e' in line:
                    found_marker = 'e2e'
                    break
                elif '@pytest.mark.browser' in line:
                    found_marker = 'browser'
                elif '@pytest.mark.host_only' in line and not found_marker:
                    found_marker = 'host_only'
            
            if found_marker:
                stats[f'marked_{found_marker}'] += 1
                marked_tests[found_marker].append(f"{rel_path}::{test_name}")
            else:
                stats['unmarked'] += 1
                unmarked_tests.append(f"{rel_path}::{test_name}")
            
            stats['total'] += 1
    
    # Print summary
    print("TEST MARKER ANALYSIS")
    print("=" * 60)
    print(f"Total test functions: {stats['total']}")
    print(f"Marked tests: {stats['total'] - stats['unmarked']}")
    print(f"  - Unit: {stats['marked_unit']}")
    print(f"  - Integration: {stats['marked_integration']}")  
    print(f"  - E2E: {stats['marked_e2e']}")
    print(f"  - Browser: {stats['marked_browser']}")
    print(f"  - Host-only: {stats['marked_host_only']}")
    print(f"Unmarked tests: {stats['unmarked']} ({stats['unmarked']/stats['total']*100:.1f}%)")
    
    if unmarked_tests:
        print("\nUNMARKED TESTS (showing first 20):")
        for test in unmarked_tests[:20]:
            print(f"  - {test}")
        if len(unmarked_tests) > 20:
            print(f"  ... and {len(unmarked_tests) - 20} more")

if __name__ == "__main__":
    analyze_markers()