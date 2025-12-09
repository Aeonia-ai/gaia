#!/usr/bin/env python3
"""
Code Specification Extractor

Extracts ground truth from Python source files using AST analysis.
This creates the "canon" that documentation is verified against.
"""

import ast
import json
import os
import sys
from pathlib import Path
from typing import Any


class CodeSpecExtractor(ast.NodeVisitor):
    """Extract specifications from Python AST."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.source_lines = source_code.split('\n')
        self.specs = {
            "classes": [],
            "functions": [],
            "constants": [],
            "imports": [],
        }

    def visit_ClassDef(self, node: ast.ClassDef):
        """Extract class specifications."""
        class_spec = {
            "name": node.name,
            "line": node.lineno,
            "end_line": node.end_lineno,
            "bases": [self._get_name(base) for base in node.bases],
            "methods": [],
            "docstring": ast.get_docstring(node),
        }

        # Extract methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                method_spec = self._extract_function(item)
                method_spec["is_async"] = isinstance(item, ast.AsyncFunctionDef)
                class_spec["methods"].append(method_spec)

        self.specs["classes"].append(class_spec)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract top-level function specifications."""
        # Skip if inside a class (handled by visit_ClassDef)
        if not self._is_top_level(node):
            return

        func_spec = self._extract_function(node)
        func_spec["is_async"] = False
        self.specs["functions"].append(func_spec)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Extract top-level async function specifications."""
        if not self._is_top_level(node):
            return

        func_spec = self._extract_function(node)
        func_spec["is_async"] = True
        self.specs["functions"].append(func_spec)

    def visit_Assign(self, node: ast.Assign):
        """Extract module-level constants/variables."""
        if not self._is_top_level(node):
            return

        for target in node.targets:
            if isinstance(target, ast.Name):
                # Check if it's a constant (UPPER_CASE)
                if target.id.isupper() or target.id[0].isupper():
                    const_spec = {
                        "name": target.id,
                        "line": node.lineno,
                        "value_type": self._infer_type(node.value),
                    }
                    # For lists/dicts, try to get length
                    if isinstance(node.value, ast.List):
                        const_spec["length"] = len(node.value.elts)
                    elif isinstance(node.value, ast.Dict):
                        const_spec["length"] = len(node.value.keys)

                    self.specs["constants"].append(const_spec)

    def visit_Import(self, node: ast.Import):
        """Extract imports."""
        for alias in node.names:
            self.specs["imports"].append({
                "module": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
            })

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Extract from imports."""
        for alias in node.names:
            self.specs["imports"].append({
                "module": f"{node.module}.{alias.name}" if node.module else alias.name,
                "alias": alias.asname,
                "line": node.lineno,
                "from_module": node.module,
            })

    def _extract_function(self, node) -> dict:
        """Extract function/method specification."""
        params = []
        for arg in node.args.args:
            param = {"name": arg.arg}
            if arg.annotation:
                param["type"] = self._get_annotation(arg.annotation)
            params.append(param)

        return_type = None
        if node.returns:
            return_type = self._get_annotation(node.returns)

        return {
            "name": node.name,
            "line": node.lineno,
            "end_line": node.end_lineno,
            "parameters": params,
            "param_count": len(params),
            "return_type": return_type,
            "docstring": ast.get_docstring(node),
            "decorators": [self._get_name(d) for d in node.decorator_list],
        }

    def _get_name(self, node) -> str:
        """Get name from various AST node types."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[...]"
        return str(node)

    def _get_annotation(self, node) -> str:
        """Get type annotation as string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Subscript):
            base = self._get_annotation(node.value)
            if isinstance(node.slice, ast.Tuple):
                args = ", ".join(self._get_annotation(e) for e in node.slice.elts)
            else:
                args = self._get_annotation(node.slice)
            return f"{base}[{args}]"
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Union type: X | Y
            left = self._get_annotation(node.left)
            right = self._get_annotation(node.right)
            return f"{left} | {right}"
        return "Any"

    def _infer_type(self, node) -> str:
        """Infer type from value node."""
        if isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return "unknown"

    def _is_top_level(self, node) -> bool:
        """Check if node is at module level (not nested)."""
        # This is a simplified check - node's col_offset == 0 for top-level
        return node.col_offset == 0


def extract_file_spec(filepath: str) -> dict:
    """Extract specifications from a Python file."""
    with open(filepath, 'r') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}", "file": filepath}

    extractor = CodeSpecExtractor(source)
    extractor.visit(tree)

    return {
        "file": filepath,
        "line_count": len(source.split('\n')),
        **extractor.specs
    }


def extract_directory_specs(directory: str, pattern: str = "**/*.py") -> dict:
    """Extract specifications from all Python files in directory."""
    specs = {}
    base_path = Path(directory)

    for filepath in base_path.glob(pattern):
        # Skip test files and __pycache__
        if '__pycache__' in str(filepath) or 'test_' in filepath.name:
            continue

        rel_path = str(filepath.relative_to(base_path))
        specs[rel_path] = extract_file_spec(str(filepath))

    return specs


def find_in_specs(specs: dict, target: str) -> list:
    """
    Find a function, class, or constant across all specs.

    Returns list of matches with file and line info.
    """
    matches = []

    for filepath, file_spec in specs.items():
        if "error" in file_spec:
            continue

        # Search classes
        for cls in file_spec.get("classes", []):
            if cls["name"] == target:
                matches.append({
                    "type": "class",
                    "file": filepath,
                    "line": cls["line"],
                    "spec": cls
                })
            # Search methods
            for method in cls.get("methods", []):
                if method["name"] == target:
                    matches.append({
                        "type": "method",
                        "file": filepath,
                        "class": cls["name"],
                        "line": method["line"],
                        "spec": method
                    })

        # Search functions
        for func in file_spec.get("functions", []):
            if func["name"] == target:
                matches.append({
                    "type": "function",
                    "file": filepath,
                    "line": func["line"],
                    "spec": func
                })

        # Search constants
        for const in file_spec.get("constants", []):
            if const["name"] == target:
                matches.append({
                    "type": "constant",
                    "file": filepath,
                    "line": const["line"],
                    "spec": const
                })

    return matches


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract code specifications")
    parser.add_argument("path", help="File or directory to analyze")
    parser.add_argument("--find", help="Find a specific function/class/constant")
    parser.add_argument("--output", "-o", help="Output file (JSON)")

    args = parser.parse_args()

    if os.path.isfile(args.path):
        specs = {args.path: extract_file_spec(args.path)}
    else:
        specs = extract_directory_specs(args.path)

    if args.find:
        matches = find_in_specs(specs, args.find)
        print(f"\nFound {len(matches)} match(es) for '{args.find}':\n")
        for match in matches:
            print(f"  {match['type']}: {match['file']}:{match['line']}")
            if match['type'] == 'method':
                print(f"    in class: {match['class']}")
    elif args.output:
        with open(args.output, 'w') as f:
            json.dump(specs, f, indent=2)
        print(f"Wrote specs to {args.output}")
    else:
        print(json.dumps(specs, indent=2))
