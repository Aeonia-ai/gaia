#!/usr/bin/env python3
"""
Phase 3: Test Reorganization Script
Reorganizes tests into unit/integration/e2e directories based on markers.
"""

import os
import ast
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple

class TestReorganizer:
    def __init__(self):
        self.test_root = Path("tests")
        self.unit_dir = self.test_root / "unit"
        self.integration_dir = self.test_root / "integration"
        self.e2e_dir = self.test_root / "e2e"
        
        # Files to preserve in root
        self.root_files = {
            "conftest.py",
            "__init__.py",
            "fixtures"  # Directory
        }
        
        # Track moves for rollback
        self.moves: List[Tuple[Path, Path]] = []
        
    def analyze_test_file(self, file_path: Path) -> str:
        """Determine test type from markers."""
        content = file_path.read_text()
        
        # Parse AST to find markers
        tree = ast.parse(content)
        markers = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        if (isinstance(decorator.value, ast.Attribute) and
                            decorator.value.attr == "mark"):
                            markers.add(decorator.attr)
        
        # Determine category
        if "e2e" in markers or "browser" in markers:
            return "e2e"
        elif "integration" in markers:
            return "integration"
        elif "unit" in markers:
            return "unit"
        else:
            # Default based on imports/content
            if "browser" in content or "playwright" in content:
                return "e2e"
            elif any(x in content for x in ["httpx.AsyncClient", "TestAuthManager", "gateway:8000"]):
                return "integration"
            else:
                return "unit"
    
    def get_new_path(self, old_path: Path, category: str) -> Path:
        """Calculate new path for file."""
        if category == "unit":
            new_dir = self.unit_dir
        elif category == "integration":
            new_dir = self.integration_dir
        else:  # e2e
            new_dir = self.e2e_dir
            
        # Preserve subdirectory structure
        relative_path = old_path.relative_to(self.test_root)
        if "/" in str(relative_path):
            # Has subdirectory
            parts = relative_path.parts[1:]  # Skip first part
            return new_dir / Path(*parts)
        else:
            return new_dir / old_path.name
    
    def create_init_files(self):
        """Create __init__.py files in all directories."""
        for dir_path in [self.unit_dir, self.integration_dir, self.e2e_dir]:
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                init_file.write_text("")
                print(f"Created {init_file}")
    
    def plan_reorganization(self) -> Dict[str, List[Tuple[Path, Path, str]]]:
        """Plan the reorganization without executing."""
        plan = {
            "unit": [],
            "integration": [],
            "e2e": []
        }
        
        # Find all test files
        test_files = []
        seen_files = set()
        
        for pattern in ["test_*.py", "*_test.py"]:
            # Add files from root
            for f in self.test_root.glob(pattern):
                if f not in seen_files:
                    test_files.append(f)
                    seen_files.add(f)
            
            # Add files from subdirectories
            for f in self.test_root.glob(f"**/{pattern}"):
                if f not in seen_files:
                    test_files.append(f)
                    seen_files.add(f)
        
        for test_file in test_files:
            # Skip files in new structure
            if any(str(test_file).startswith(str(d)) for d in [self.unit_dir, self.integration_dir, self.e2e_dir]):
                continue
                
            # Skip root files
            if test_file.name in self.root_files:
                continue
                
            category = self.analyze_test_file(test_file)
            new_path = self.get_new_path(test_file, category)
            
            plan[category].append((test_file, new_path, category))
        
        return plan
    
    def execute_move(self, old_path: Path, new_path: Path):
        """Execute a single file move."""
        # Create parent directory if needed
        new_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file
        shutil.move(str(old_path), str(new_path))
        self.moves.append((old_path, new_path))
        
        print(f"Moved {old_path} → {new_path}")
    
    def update_imports(self, file_path: Path):
        """Update imports in moved file."""
        content = file_path.read_text()
        
        # Update relative imports from fixtures
        if "../fixtures" in content:
            content = content.replace("from ..fixtures", "from tests.fixtures")
            content = content.replace("from ../fixtures", "from tests.fixtures")
        
        # Update other test imports
        content = content.replace("from tests.", "from tests.")
        
        file_path.write_text(content)
    
    def reorganize(self, dry_run: bool = True):
        """Execute the reorganization."""
        print("Phase 3: Test Reorganization")
        print("=" * 50)
        
        # Create directories
        if not dry_run:
            self.unit_dir.mkdir(exist_ok=True)
            self.integration_dir.mkdir(exist_ok=True)
            self.e2e_dir.mkdir(exist_ok=True)
            self.create_init_files()
        
        # Plan moves
        plan = self.plan_reorganization()
        
        # Show summary
        total_moves = sum(len(moves) for moves in plan.values())
        print(f"\nTotal files to move: {total_moves}")
        print(f"- Unit tests: {len(plan['unit'])}")
        print(f"- Integration tests: {len(plan['integration'])}")
        print(f"- E2E tests: {len(plan['e2e'])}")
        
        if dry_run:
            print("\nDRY RUN - No files will be moved")
            print("\nPlanned moves:")
            for category, moves in plan.items():
                if moves:
                    print(f"\n{category.upper()} Tests:")
                    for old_path, new_path, _ in moves[:5]:  # Show first 5
                        print(f"  {old_path.name} → {new_path.relative_to(self.test_root)}")
                    if len(moves) > 5:
                        print(f"  ... and {len(moves) - 5} more")
        else:
            print("\nExecuting reorganization...")
            
            # Execute moves
            for category, moves in plan.items():
                for old_path, new_path, _ in moves:
                    try:
                        self.execute_move(old_path, new_path)
                        self.update_imports(new_path)
                    except Exception as e:
                        print(f"ERROR moving {old_path}: {e}")
                        self.rollback()
                        return
            
            # Update conftest.py if needed
            self.update_conftest()
            
            print("\n✅ Reorganization complete!")
            print(f"Moved {len(self.moves)} files")
    
    def update_conftest(self):
        """Update conftest.py for new structure."""
        conftest_path = self.test_root / "conftest.py"
        if conftest_path.exists():
            content = conftest_path.read_text()
            
            # Add marker explanations
            marker_docs = '''
"""
Test organization:
- tests/unit/: Fast, isolated unit tests
- tests/integration/: Service interaction tests
- tests/e2e/: End-to-end browser and API tests
"""
'''
            if marker_docs.strip() not in content:
                content = marker_docs + "\n" + content
                conftest_path.write_text(content)
    
    def rollback(self):
        """Rollback all moves in case of error."""
        print("\nRolling back changes...")
        for old_path, new_path in reversed(self.moves):
            try:
                shutil.move(str(new_path), str(old_path))
                print(f"Restored {old_path}")
            except Exception as e:
                print(f"ERROR restoring {old_path}: {e}")
    
    def verify_structure(self):
        """Verify the new structure is correct."""
        print("\nVerifying new structure...")
        
        issues = []
        
        # Check all categories have files
        for category, dir_path in [("unit", self.unit_dir), 
                                   ("integration", self.integration_dir),
                                   ("e2e", self.e2e_dir)]:
            if dir_path.exists():
                test_files = list(dir_path.glob("test_*.py"))
                print(f"{category}: {len(test_files)} test files")
                
                if len(test_files) == 0:
                    issues.append(f"No tests in {category} directory")
        
        # Check no test files left in root (except allowed)
        root_tests = []
        for pattern in ["test_*.py", "*_test.py"]:
            for f in self.test_root.glob(pattern):
                if f.name not in self.root_files and f.parent == self.test_root:
                    root_tests.append(f)
        
        if root_tests:
            issues.append(f"{len(root_tests)} test files still in root")
            for f in root_tests[:5]:
                print(f"  - {f.name}")
        
        if issues:
            print("\n⚠️  Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✅ Structure verified successfully!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Reorganize tests into unit/integration/e2e structure")
    parser.add_argument("--execute", action="store_true", help="Execute the reorganization (default is dry run)")
    parser.add_argument("--verify", action="store_true", help="Verify current structure")
    
    args = parser.parse_args()
    
    reorganizer = TestReorganizer()
    
    if args.verify:
        reorganizer.verify_structure()
    else:
        reorganizer.reorganize(dry_run=not args.execute)


if __name__ == "__main__":
    main()