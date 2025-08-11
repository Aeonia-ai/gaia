#!/usr/bin/env python3
"""Final comprehensive fix for all test syntax issues."""
import os
import re

def fix_test_file(filepath):
    """Fix all syntax issues in a test file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix 1: Remove any leading spaces from decorator lines
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # If line contains the skip decorator, ensure it has no leading spaces
        if '@pytest.mark.skip(reason="Integration test should not use mocks - violates testing principles")' in line:
            fixed_lines.append('@pytest.mark.skip(reason="Integration test should not use mocks - violates testing principles")')
        elif line.strip().startswith('async def') and i > 0:
            # If this is an async def following a decorator, ensure proper indentation
            if '@pytest.mark.skip' in lines[i-1]:
                fixed_lines.append('async def' + line.strip()[9:])  # Remove 'async def' and re-add without indent
            else:
                fixed_lines.append(line)
        elif line.strip().startswith('"""') and i > 0 and lines[i-1].strip().startswith('async def'):
            # Docstring after function def needs proper indentation
            fixed_lines.append('    ' + line.strip())
        else:
            fixed_lines.append(line)
    
    # Write back
    fixed_content = '\n'.join(fixed_lines)
    
    with open(filepath, 'w') as f:
        f.write(fixed_content)
    
    print(f"Fixed: {filepath}")

# Fix the problematic files identified in the error
problem_files = [
    'tests/integration/web/test_auth_diagnosis.py',
    'tests/integration/web/test_auth_htmx_fix.py', 
    'tests/integration/web/test_browser_pattern_examples.py',
    'tests/integration/web/test_chat_browser_auth_fixed.py',
    'tests/integration/web/test_debug_login.py'
]

for filepath in problem_files:
    if os.path.exists(filepath):
        try:
            fix_test_file(filepath)
        except Exception as e:
            print(f"Error fixing {filepath}: {e}")

print("\nFinal fixes complete!")