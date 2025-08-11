#!/usr/bin/env python3
"""Fix all syntax issues in test files after decorator insertion."""
import os
import re

def fix_test_file(filepath):
    """Fix all syntax issues in a single test file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern 1: Fix decorator on same line as function
    # @pytest.mark.skip(reason="...")async def -> @pytest.mark.skip(reason="...")\n    async def
    content = re.sub(
        r'(@pytest\.mark\.skip\(reason="[^"]+"\))\s*async def',
        r'\1\n    async def',
        content
    )
    
    # Pattern 2: Fix standalone decorator followed by unindented function
    # Fix cases where decorator is on its own line but function isn't indented
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        if '@pytest.mark.skip(reason="Integration test should not use mocks - violates testing principles")' in line:
            fixed_lines.append(line)
            
            # Look ahead for async def
            j = i + 1
            while j < len(lines) and j < i + 5:  # Look up to 5 lines ahead
                next_line = lines[j]
                if next_line.strip().startswith('async def'):
                    # Check if it's already properly indented
                    if not next_line.startswith('    '):
                        # Add proper indentation
                        fixed_lines.append('    ' + next_line.strip())
                    else:
                        fixed_lines.append(next_line)
                    
                    # Handle the docstring if it exists
                    if j + 1 < len(lines) and lines[j + 1].strip().startswith('"""'):
                        docstring_line = lines[j + 1]
                        if not docstring_line.startswith('        '):
                            fixed_lines.append('        ' + docstring_line.strip())
                        else:
                            fixed_lines.append(docstring_line)
                        j += 1
                    
                    i = j
                    break
                elif next_line.strip():  # Non-empty line that's not async def
                    fixed_lines.append(next_line)
                else:
                    fixed_lines.append(next_line)
                j += 1
            else:
                # Didn't find async def, just continue
                pass
        else:
            fixed_lines.append(line)
        
        i += 1
    
    # Join and write back
    fixed_content = '\n'.join(fixed_lines)
    
    # Fix any remaining indentation issues with docstrings after async def
    fixed_content = re.sub(
        r'(    async def [^:]+:)\n    """',
        r'\1\n        """',
        fixed_content
    )
    
    with open(filepath, 'w') as f:
        f.write(fixed_content)
    
    print(f"Fixed: {filepath}")

# Find all Python test files in the web integration tests
test_dir = 'tests/integration/web'
for filename in os.listdir(test_dir):
    if filename.endswith('.py') and filename.startswith('test_'):
        filepath = os.path.join(test_dir, filename)
        try:
            fix_test_file(filepath)
        except Exception as e:
            print(f"Error fixing {filepath}: {e}")

print("\nAll syntax fixes complete!")