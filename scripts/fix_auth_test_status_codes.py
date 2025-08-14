#!/usr/bin/env python3
"""
Fix authentication tests to expect only 401 instead of [401, 403].
"""

import re
from pathlib import Path
from typing import List, Tuple

# Files and their specific fixes
FIXES = [
    # Simple replacements - in [401, 403] -> == 401
    {
        "files": [
            "tests/integration/chat/test_api_v1_conversations_auth.py",
            "tests/integration/chat/test_api_v02_chat_endpoints.py",
            "tests/integration/chat/test_api_v03_conversations_auth.py",
            "tests/integration/auth/test_auth_supabase_integration.py",
            "tests/integration/system/test_system_regression.py",
            "tests/integration/gateway/test_gateway_auth_endpoints.py",
        ],
        "pattern": r"assert response\.status_code in \[401, 403\]",
        "replacement": "assert response.status_code == 401"
    },
    # With comments
    {
        "files": ["tests/integration/chat/test_api_v03_endpoints.py"],
        "pattern": r"assert response\.status_code in \[401, 403\]  # Both are valid \"unauthorized\" responses",
        "replacement": "assert response.status_code == 401  # Authentication failure returns 401"
    },
    # With f-strings
    {
        "files": ["tests/integration/general/test_api_endpoints_comprehensive.py"],
        "pattern": r"assert response\.status_code in \[401, 403\], f\"Endpoint \{endpoint\} should require auth\"",
        "replacement": "assert response.status_code == 401, f\"Endpoint {endpoint} should require auth (401 for missing auth)\""
    },
    {
        "files": ["tests/integration/general/test_api_endpoints_comprehensive.py"],
        "pattern": r"assert response\.status_code in \[401, 403\], \"Invalid JWT should fail\"",
        "replacement": "assert response.status_code == 401, \"Invalid JWT should return 401\""
    },
    {
        "files": ["tests/integration/chat/test_api_v02_completions_auth.py"],
        "pattern": r"assert response\.status_code in \[401, 403\], f\"Expected auth error for invalid key, got \{response\.status_code\}\"",
        "replacement": "assert response.status_code == 401, f\"Expected 401 for invalid key, got {response.status_code}\""
    },
    {
        "files": ["tests/integration/system/test_system_comprehensive.py"],
        "pattern": r"assert response\.status_code in \[401, 403\], \"Unauthenticated requests should be rejected\"",
        "replacement": "assert response.status_code == 401, \"Unauthenticated requests should return 401\""
    },
    {
        "files": ["tests/integration/system/test_system_comprehensive.py"],
        "pattern": r"assert response\.status_code in \[401, 403\], \"Invalid API keys should be rejected\"",
        "replacement": "assert response.status_code == 401, \"Invalid API keys should return 401\""
    },
    # Special case - not in [401, 403]
    {
        "files": ["tests/integration/general/test_api_endpoints_comprehensive.py"],
        "pattern": r"assert response\.status_code not in \[401, 403\], f\"Valid JWT should work: \{response\.status_code\}\"",
        "replacement": "assert response.status_code != 401, f\"Valid JWT should work: {response.status_code}\""
    },
    # Web service special case
    {
        "files": ["tests/integration/web-service/test_web_conversations_api.py"],
        "pattern": r"assert response\.status_code in \[401, 403\] or \"Please log in\" in response\.text",
        "replacement": "assert response.status_code == 401 or \"Please log in\" in response.text"
    },
]

def fix_file(file_path: Path, pattern: str, replacement: str) -> bool:
    """Fix a single file with the given pattern and replacement."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if pattern exists
        if not re.search(pattern, content):
            return False
        
        # Replace
        new_content = re.sub(pattern, replacement, content)
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix all tests."""
    print("🔧 Fixing authentication tests to expect only 401...\n")
    
    total_fixed = 0
    
    for fix in FIXES:
        pattern = fix["pattern"]
        replacement = fix["replacement"]
        
        for file_path in fix["files"]:
            path = Path(file_path)
            if path.exists():
                if fix_file(path, pattern, replacement):
                    print(f"✅ Fixed: {file_path}")
                    total_fixed += 1
                else:
                    print(f"⚠️  No match found in: {file_path}")
            else:
                print(f"❌ File not found: {file_path}")
    
    print(f"\n✨ Total fixes applied: {total_fixed}")
    
    # Additional checks for edge cases
    print("\n🔍 Checking for remaining [401, 403] patterns...")
    remaining = check_remaining_patterns()
    if remaining:
        print(f"⚠️  Found {len(remaining)} remaining patterns that may need manual review:")
        for file, line_num, line in remaining[:5]:
            print(f"  {file}:{line_num} - {line.strip()}")
    else:
        print("✅ No remaining [401, 403] patterns found!")

def check_remaining_patterns() -> List[Tuple[str, int, str]]:
    """Check for any remaining [401, 403] patterns."""
    remaining = []
    
    test_dir = Path("tests/")
    for file_path in test_dir.rglob("test_*.py"):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                if re.search(r"\[401,\s*403\]|\[403,\s*401\]", line):
                    remaining.append((str(file_path), line_num, line))
        except Exception:
            pass
    
    return remaining

if __name__ == "__main__":
    main()