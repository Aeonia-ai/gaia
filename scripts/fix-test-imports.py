#!/usr/bin/env python3
"""
Fix import issues after test reorganization.
"""

import os
from pathlib import Path
import re

def fix_imports_in_file(file_path: Path):
    """Fix imports in a single test file."""
    content = file_path.read_text()
    original_content = content
    
    # Fix imports from web directory fixtures
    if "from browser_auth_fixtures import" in content:
        content = content.replace(
            "from browser_auth_fixtures import",
            "from tests.web.browser_auth_fixtures import"
        )
    
    if "from browser_test_config import" in content:
        content = content.replace(
            "from browser_test_config import",
            "from tests.web.browser_test_config import"
        )
    
    if "from playwright_conftest import" in content:
        content = content.replace(
            "from playwright_conftest import",
            "from tests.web.playwright_conftest import"
        )
    
    # Fix relative imports from web conftest
    if "from .conftest import" in content:
        content = content.replace(
            "from .conftest import",
            "from tests.web.conftest import"
        )
    
    # Fix relative imports from fixtures
    if "from ..fixtures" in content:
        content = content.replace(
            "from ..fixtures",
            "from tests.fixtures"
        )
    
    # Only write if changed
    if content != original_content:
        file_path.write_text(content)
        print(f"Fixed imports in: {file_path}")
        return True
    return False

def main():
    """Fix all import issues in reorganized tests."""
    test_root = Path("tests")
    directories = ["unit", "integration", "e2e"]
    
    fixed_count = 0
    
    for directory in directories:
        dir_path = test_root / directory
        if not dir_path.exists():
            continue
            
        print(f"\nChecking {directory} tests...")
        
        for test_file in dir_path.glob("test_*.py"):
            if fix_imports_in_file(test_file):
                fixed_count += 1
    
    print(f"\n✅ Fixed imports in {fixed_count} files")

if __name__ == "__main__":
    main()