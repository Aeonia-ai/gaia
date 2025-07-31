#!/usr/bin/env python3
"""
Script to migrate broken e2e browser tests to working async_playwright pattern.
"""
import os
import re
import glob

# List of files that still use broken fixtures (that need migration)
BROKEN_FILES = [
    "tests/e2e/test_browser_edge_cases.py",
    "tests/e2e/test_chat_browser.py", 
    "tests/e2e/test_authenticated_browser.py",
    "tests/e2e/test_chat_browser_auth.py",
    "tests/e2e/test_layout_integrity.py",
    "tests/e2e/test_real_e2e_with_supabase.py",
    "tests/e2e/test_browser_config.py",
    "tests/e2e/test_full_web_browser.py",
    "tests/e2e/test_chat_simple.py",
    "tests/e2e/test_real_auth_browser.py",
    "tests/e2e/test_simple_auth_fixed.py",
    "tests/e2e/test_manual_auth_browser.py",
    "tests/e2e/test_e2e_real_auth.py"
]

def migrate_file(filepath):
    """Migrate a single file to use working pattern"""
    print(f"Migrating {filepath}...")
    
    if not os.path.exists(filepath):
        print(f"  ❌ File not found: {filepath}")
        return False
        
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Skip if already uses async_playwright (working pattern)
    if 'async_playwright' in content:
        print(f"  ✅ Already uses working pattern")
        return True
    
    # Skip if it doesn't use page fixture (not broken)
    if 'def test_' not in content or ', page)' not in content:
        print(f"  ✅ No page fixture usage found")
        return True
    
    # Basic transformations
    original_content = content
    
    # Add async_playwright import
    if 'from playwright.async_api import async_playwright' not in content:
        # Find existing playwright imports
        if 'from playwright.async_api import' in content:
            content = re.sub(
                r'from playwright\.async_api import ([^\n]+)',
                r'from playwright.async_api import async_playwright, \1',
                content
            )
        else:
            # Add new import after existing imports
            import_match = re.search(r'(import [^\n]+\n)+', content)
            if import_match:
                insert_pos = import_match.end()
                content = content[:insert_pos] + 'from playwright.async_api import async_playwright\n' + content[insert_pos:]
    
    # Add WEB_SERVICE_URL if not present
    if 'WEB_SERVICE_URL' not in content:
        # Add after imports
        import_section_end = content.find('\n\n')
        if import_section_end != -1:
            content = content[:import_section_end] + '\n\nWEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")' + content[import_section_end:]
    
    # Transform test functions with page parameter
    def transform_test_function(match):
        indent = match.group(1)
        async_marker = match.group(2)
        func_name = match.group(3)
        page_param = match.group(4)
        func_body = match.group(5)
        
        # Remove page parameter
        new_signature = f'{indent}{async_marker}def {func_name}():'
        
        # Add browser setup
        browser_setup = f"""
{indent}    async with async_playwright() as p:
{indent}        browser = await p.chromium.launch(
{indent}            headless=True,
{indent}            args=['--no-sandbox', '--disable-setuid-sandbox']
{indent}        )
{indent}        page = await browser.new_page()
{indent}        
{indent}        try:"""
        
        # Indent the existing function body
        indented_body = '\n'.join([f'{indent}            {line}' if line.strip() else line 
                                  for line in func_body.split('\n')])
        
        # Add cleanup
        cleanup = f"""
{indent}        finally:
{indent}            await browser.close()"""
        
        return new_signature + browser_setup + indented_body + cleanup
    
    # Pattern to match test functions with page parameter
    pattern = r'(\s*)(async def )(test_[^(]+)\([^,]*,\s*page\):([^}]+?)(?=\n\s*(?:async def|def|class|\Z))'
    
    content = re.sub(pattern, transform_test_function, content, flags=re.MULTILINE | re.DOTALL)
    
    # Write back if changed
    if content != original_content:
        # Create backup
        backup_path = filepath + '.backup'
        with open(backup_path, 'w') as f:
            f.write(original_content)
        print(f"  📄 Created backup: {backup_path}")
        
        # Write migrated content
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✅ Migrated successfully")
        return True
    else:
        print(f"  ℹ️  No changes needed")
        return True

def main():
    """Main migration script"""
    print("🔧 Migrating broken e2e browser tests to working async_playwright pattern...\n")
    
    successful = 0
    failed = 0
    
    for filepath in BROKEN_FILES:
        try:
            if migrate_file(filepath):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ Error migrating {filepath}: {e}")
            failed += 1
        print()
    
    print(f"📊 Migration Summary:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📁 Total: {len(BROKEN_FILES)}")
    
    if failed == 0:
        print("\n🎉 All migrations completed successfully!")
    else:
        print(f"\n⚠️  {failed} files had issues. Check logs above.")

if __name__ == "__main__":
    main()