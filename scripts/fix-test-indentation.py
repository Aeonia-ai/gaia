#!/usr/bin/env python3
"""Fix indentation issues in test files after decorator insertion."""
import os
import re

def fix_test_file(filepath):
    """Fix indentation issues in a single test file."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line has the skip decorator
        if '@pytest.mark.skip(reason="Integration test should not use mocks - violates testing principles")' in line:
            # Add the decorator line
            fixed_lines.append(line)
            
            # Check if there's a function definition on the next line that needs indentation
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # If the next line starts with 'async def' at column 0, it needs indentation
                if next_line.strip().startswith('async def') and not next_line.startswith('    '):
                    # Add proper indentation (4 spaces)
                    fixed_lines.append('    ' + next_line.strip() + '\n')
                    i += 1  # Skip the next line since we've already processed it
                else:
                    i += 1
            else:
                i += 1
        else:
            fixed_lines.append(line)
            i += 1
    
    # Write the fixed content back
    with open(filepath, 'w') as f:
        f.writelines(fixed_lines)
    print(f"Fixed: {filepath}")

# Find all Python test files in the web integration tests
test_dir = 'tests/integration/web'
for filename in os.listdir(test_dir):
    if filename.endswith('.py') and filename.startswith('test_'):
        filepath = os.path.join(test_dir, filename)
        fix_test_file(filepath)

print("Indentation fixes complete!")