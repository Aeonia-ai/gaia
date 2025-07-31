#!/usr/bin/env python3
"""
Apply pytest markers to all test files based on test patterns and content.
Part of Phase 2 of the test improvement plan.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestMarkerAnalyzer:
    """Analyze and apply appropriate pytest markers to test files."""
    
    # Patterns to identify test types
    UNIT_PATTERNS = [
        r'mock\.',
        r'Mock\(',
        r'patch\(',
        r'@patch',
        r'monkeypatch',
        r'test.*without.*service',
        r'test.*in.*isolation',
        r'test.*parsing',
        r'test.*validation',
        r'test.*model',
        r'test.*schema',
    ]
    
    INTEGRATION_PATTERNS = [
        r'httpx\.',
        r'AsyncClient',
        r'test.*endpoint',
        r'test.*api',
        r'test.*service.*interaction',
        r'gateway_url',
        r'auth_service',
        r'chat_service',
        r'kb_service',
    ]
    
    E2E_PATTERNS = [
        r'test.*end.*to.*end',
        r'test.*e2e',
        r'test.*journey',
        r'test.*flow',
        r'test.*conversation.*flow',
        r'playwright',
        r'page\.',
        r'browser',
        r'test.*full.*system',
    ]
    
    def __init__(self):
        self.stats = {
            'total_files': 0,
            'total_tests': 0,
            'marked_tests': 0,
            'unit_marked': 0,
            'integration_marked': 0,
            'e2e_marked': 0,
            'already_marked': 0,
            'files_modified': 0
        }
    
    def analyze_test_content(self, content: str) -> str:
        """Determine test type based on content patterns."""
        content_lower = content.lower()
        
        # Count pattern matches
        unit_score = sum(1 for pattern in self.UNIT_PATTERNS 
                        if re.search(pattern, content_lower))
        integration_score = sum(1 for pattern in self.INTEGRATION_PATTERNS 
                               if re.search(pattern, content_lower))
        e2e_score = sum(1 for pattern in self.E2E_PATTERNS 
                       if re.search(pattern, content_lower))
        
        # Determine primary type
        if e2e_score > integration_score and e2e_score > unit_score:
            return 'e2e'
        elif integration_score > unit_score:
            return 'integration'
        elif unit_score > 0:
            return 'unit'
        else:
            # Default based on imports and structure
            if 'httpx' in content or 'AsyncClient' in content:
                return 'integration'
            return 'unit'  # Conservative default
    
    def find_test_functions(self, content: str) -> List[Tuple[int, str, str]]:
        """Find all test functions and their current markers."""
        lines = content.split('\n')
        test_functions = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for test function definitions
            if re.match(r'^(async\s+)?def\s+test_\w+', line.strip()):
                func_name = re.search(r'def\s+(test_\w+)', line).group(1)
                
                # Check for existing markers in previous lines
                existing_markers = []
                j = i - 1
                while j >= 0 and lines[j].strip().startswith('@'):
                    marker_line = lines[j].strip()
                    if 'pytest.mark' in marker_line:
                        existing_markers.append(marker_line)
                    j -= 1
                
                # Extract the function content to analyze
                func_content = []
                indent_level = len(line) - len(line.lstrip())
                k = i + 1
                while k < len(lines):
                    next_line = lines[k]
                    if next_line.strip() and not next_line.startswith(' '):
                        break
                    if next_line.strip():
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent <= indent_level:
                            break
                    func_content.append(next_line)
                    k += 1
                
                func_text = '\n'.join([line] + func_content)
                test_functions.append((i, func_name, func_text))
            
            i += 1
        
        return test_functions
    
    def has_test_marker(self, content: str, line_num: int) -> bool:
        """Check if a test already has a layer marker."""
        lines = content.split('\n')
        
        # Look backwards from the test function for markers
        i = line_num - 1
        while i >= 0 and lines[i].strip():
            line = lines[i].strip()
            if any(marker in line for marker in ['@pytest.mark.unit', 
                                                  '@pytest.mark.integration', 
                                                  '@pytest.mark.e2e']):
                return True
            if not line.startswith('@'):
                break
            i -= 1
        
        return False
    
    def apply_marker(self, content: str, line_num: int, marker_type: str) -> str:
        """Apply a marker to a test function."""
        lines = content.split('\n')
        marker = f'@pytest.mark.{marker_type}'
        
        # Find the right place to insert the marker
        insert_line = line_num
        
        # If there are other decorators, add after them
        i = line_num - 1
        while i >= 0 and lines[i].strip().startswith('@'):
            insert_line = i
            i -= 1
        
        # Insert the marker
        lines.insert(insert_line, f'    {marker}')
        
        # Track statistics
        self.stats[f'{marker_type}_marked'] += 1
        self.stats['marked_tests'] += 1
        
        return '\n'.join(lines)
    
    def process_file(self, file_path: Path) -> bool:
        """Process a single test file and apply markers."""
        print(f"Processing: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        modified = False
        
        # Ensure pytest is imported
        if 'import pytest' not in content:
            # Add import after other imports
            import_lines = []
            other_lines = []
            in_imports = True
            
            for line in content.split('\n'):
                if in_imports and (line.startswith('import ') or 
                                 line.startswith('from ') or 
                                 not line.strip()):
                    import_lines.append(line)
                else:
                    in_imports = False
                    other_lines.append(line)
            
            # Add pytest import
            import_lines.append('import pytest')
            import_lines.append('')
            
            content = '\n'.join(import_lines + other_lines)
            modified = True
        
        # Find and process test functions
        test_functions = self.find_test_functions(content)
        self.stats['total_tests'] += len(test_functions)
        
        # Process from bottom to top to maintain line numbers
        for line_num, func_name, func_content in reversed(test_functions):
            if self.has_test_marker(content, line_num):
                self.stats['already_marked'] += 1
                continue
            
            # Determine test type
            test_type = self.analyze_test_content(func_content)
            
            # Apply marker
            content = self.apply_marker(content, line_num, test_type)
            modified = True
            
            print(f"  - {func_name}: {test_type}")
        
        # Write back if modified
        if modified and content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            self.stats['files_modified'] += 1
            return True
        
        return False
    
    def process_directory(self, directory: Path):
        """Process all test files in a directory."""
        test_files = list(directory.rglob('test_*.py'))
        self.stats['total_files'] = len(test_files)
        
        print(f"Found {len(test_files)} test files to process\n")
        
        for test_file in sorted(test_files):
            self.process_file(test_file)
        
        self.print_summary()
    
    def print_summary(self):
        """Print processing summary."""
        print("\n" + "="*60)
        print("MARKER APPLICATION SUMMARY")
        print("="*60)
        print(f"Total files processed: {self.stats['total_files']}")
        print(f"Total test functions: {self.stats['total_tests']}")
        print(f"Tests already marked: {self.stats['already_marked']}")
        print(f"Tests newly marked: {self.stats['marked_tests']}")
        print(f"  - Unit tests: {self.stats['unit_marked']}")
        print(f"  - Integration tests: {self.stats['integration_marked']}")
        print(f"  - E2E tests: {self.stats['e2e_marked']}")
        print(f"Files modified: {self.stats['files_modified']}")
        print(f"Unmarked tests remaining: {self.stats['total_tests'] - self.stats['already_marked'] - self.stats['marked_tests']}")


def main():
    """Main entry point."""
    analyzer = TestMarkerAnalyzer()
    
    # Process tests directory
    tests_dir = project_root / 'tests'
    if not tests_dir.exists():
        print(f"Error: {tests_dir} does not exist!")
        sys.exit(1)
    
    print("Starting pytest marker application...")
    print(f"Processing directory: {tests_dir}\n")
    
    analyzer.process_directory(tests_dir)
    
    print("\n✅ Marker application complete!")
    print("\nNext steps:")
    print("1. Review the changes with: git diff")
    print("2. Run tests to ensure markers are correct")
    print("3. Commit the changes")


if __name__ == "__main__":
    main()