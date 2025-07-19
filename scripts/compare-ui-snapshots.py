#!/usr/bin/env python3
"""
Compare UI snapshots to detect visual regression.
Shows differences between current UI and saved snapshots.
"""
import os
import json
import asyncio
from capture_ui_snapshots import UISnapshotCapture
from deepdiff import DeepDiff
from colorama import Fore, Style, init

init(autoreset=True)


class UISnapshotComparer:
    def __init__(self):
        self.snapshot_dir = "tests/snapshots"
        self.capturer = UISnapshotCapture()
    
    async def compare_page(self, path: str, name: str):
        """Compare current page with saved snapshot"""
        # Load saved snapshot
        snapshot_file = f"{self.snapshot_dir}/{name}.json"
        if not os.path.exists(snapshot_file):
            print(f"⚠️  No saved snapshot for {name}. Run capture-ui-snapshots.py first.")
            return None
        
        with open(snapshot_file, 'r') as f:
            saved_snapshot = json.load(f)
        
        # Capture current state
        print(f"🔍 Comparing {name}...")
        current_snapshot = await self.capturer.capture_page(path, f"{name}_current")
        
        if not current_snapshot:
            return None
        
        # Compare snapshots
        differences = self._compare_snapshots(saved_snapshot, current_snapshot)
        
        if differences:
            print(f"\n{Fore.RED}❌ Changes detected in {name}:{Style.RESET_ALL}")
            self._print_differences(differences)
        else:
            print(f"{Fore.GREEN}✅ No changes in {name}{Style.RESET_ALL}")
        
        return differences
    
    def _compare_snapshots(self, saved, current):
        """Compare two snapshots and return differences"""
        # Ignore timestamp
        saved_copy = saved.copy()
        current_copy = current.copy()
        saved_copy.pop('timestamp', None)
        current_copy.pop('timestamp', None)
        
        # Deep comparison
        diff = DeepDiff(saved_copy, current_copy, ignore_order=True)
        
        return diff if diff else None
    
    def _print_differences(self, diff):
        """Print differences in a readable format"""
        if 'values_changed' in diff:
            print(f"\n{Fore.YELLOW}Changed values:{Style.RESET_ALL}")
            for path, change in diff['values_changed'].items():
                print(f"  {path}:")
                print(f"    Old: {change['old_value']}")
                print(f"    New: {change['new_value']}")
        
        if 'dictionary_item_added' in diff:
            print(f"\n{Fore.GREEN}Added elements:{Style.RESET_ALL}")
            for item in diff['dictionary_item_added']:
                print(f"  + {item}")
        
        if 'dictionary_item_removed' in diff:
            print(f"\n{Fore.RED}Removed elements:{Style.RESET_ALL}")
            for item in diff['dictionary_item_removed']:
                print(f"  - {item}")
        
        # Check for problematic patterns
        if 'values_changed' in diff or 'dictionary_item_added' in diff:
            self._check_problematic_changes(diff)
    
    def _check_problematic_changes(self, diff):
        """Check for known problematic patterns in changes"""
        warnings = []
        
        # Convert diff to string for pattern matching
        diff_str = str(diff)
        
        # Check for flex-col md:flex-row pattern
        if 'flex-col' in diff_str and 'md:flex-row' in diff_str:
            warnings.append("⚠️  Detected flex-col md:flex-row pattern - this breaks layout!")
        
        # Check for removal of key elements
        if 'dictionary_item_removed' in diff:
            for item in diff['dictionary_item_removed']:
                if any(key in str(item) for key in ['auth-container', 'messages', 'sidebar']):
                    warnings.append(f"⚠️  Critical element removed: {item}")
        
        # Check for inline styles
        if 'style=' in diff_str:
            warnings.append("⚠️  Inline styles detected - use Tailwind classes instead")
        
        if warnings:
            print(f"\n{Fore.RED}🚨 WARNINGS:{Style.RESET_ALL}")
            for warning in warnings:
                print(f"  {warning}")
    
    async def compare_all_snapshots(self):
        """Compare all saved snapshots with current state"""
        pages = [
            ("/", "homepage"),
            ("/login", "login"),
            ("/register", "register"),
        ]
        
        print("🔍 Comparing UI snapshots...\n")
        
        changes_detected = False
        for path, name in pages:
            snapshot_file = f"{self.snapshot_dir}/{name}.json"
            if os.path.exists(snapshot_file):
                differences = await self.compare_page(path, name)
                if differences:
                    changes_detected = True
                print()
        
        if changes_detected:
            print(f"\n{Fore.YELLOW}⚠️  UI changes detected!{Style.RESET_ALL}")
            print("Review the changes above and:")
            print("1. If changes are intentional, update snapshots: capture-ui-snapshots.py")
            print("2. If changes are unintended, fix the UI code")
            print("3. Run UI tests: pytest tests/web/test_ui_layout.py")
        else:
            print(f"\n{Fore.GREEN}✅ All UI snapshots match!{Style.RESET_ALL}")


async def main():
    # Check if web service is running
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/health")
            if response.status_code != 200:
                print("❌ Web service not responding on localhost:8080")
                print("Start it with: docker compose up web-service")
                return
    except:
        print("❌ Cannot connect to web service on localhost:8080")
        print("Start it with: docker compose up web-service")
        return
    
    comparer = UISnapshotComparer()
    await comparer.compare_all_snapshots()


if __name__ == "__main__":
    asyncio.run(main())