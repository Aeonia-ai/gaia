#!/usr/bin/env python3
"""
Documentation Claim Extractor

Extracts verifiable claims from markdown documentation files.
These claims are then compared against code specifications.
"""

import re
import json
from pathlib import Path
from typing import Any


class DocClaimExtractor:
    """Extract verifiable claims from markdown documentation."""

    def __init__(self, content: str, filepath: str = ""):
        self.content = content
        self.filepath = filepath
        self.lines = content.split('\n')
        self.claims = {
            "file_refs": [],        # References to code files
            "function_refs": [],    # References to functions/methods
            "class_refs": [],       # References to classes
            "line_refs": [],        # Specific line number claims
            "count_claims": [],     # Claims about counts (e.g., "6 tools")
            "code_samples": [],     # Code blocks that should match reality
            "constant_refs": [],    # References to constants/variables
            "behavior_claims": [],  # Semantic behavior descriptions
        }

    def extract_all(self) -> dict:
        """Extract all claim types from the document."""
        self._extract_file_refs()
        self._extract_function_refs()
        self._extract_class_refs()
        self._extract_line_refs()
        self._extract_count_claims()
        self._extract_code_samples()
        self._extract_constant_refs()
        self._extract_behavior_claims()

        return {
            "source_file": self.filepath,
            "total_lines": len(self.lines),
            "claims": self.claims,
            "claim_count": sum(len(v) for v in self.claims.values())
        }

    def _extract_file_refs(self):
        """Extract references to Python files."""
        # Pattern: `path/to/file.py` or (path/to/file.py)
        patterns = [
            r'`([a-zA-Z_][a-zA-Z0-9_/\-]*\.py)`',  # backtick wrapped
            r'\(([a-zA-Z_][a-zA-Z0-9_/\-]*\.py)\)',  # parenthesis wrapped
            r'`([a-zA-Z_][a-zA-Z0-9_/\-]*\.sql)`',  # SQL files
        ]

        for line_num, line in enumerate(self.lines, 1):
            for pattern in patterns:
                for match in re.finditer(pattern, line):
                    self.claims["file_refs"].append({
                        "file_path": match.group(1),
                        "doc_line": line_num,
                        "context": line.strip()[:100]
                    })

    def _extract_function_refs(self):
        """Extract references to functions and methods."""
        # Patterns for function references
        patterns = [
            # `function_name()` or `function_name(args)`
            (r'`([a-z_][a-z0-9_]*)\([^)]*\)`', "call"),
            # `ClassName.method_name()`
            (r'`([A-Z][a-zA-Z0-9]*\.[a-z_][a-z0-9_]*)\([^)]*\)`', "method_call"),
            # def function_name or async def function_name (in prose)
            (r'`(?:async\s+)?def\s+([a-z_][a-z0-9_]*)`', "definition"),
            # The `function_name` method/function
            (r'[Tt]he\s+`([a-z_][a-z0-9_]*)`\s+(?:method|function)', "reference"),
            # function_name() without backticks but clear context
            (r'(?:calls?|invoke|execute|run)\s+([a-z_][a-z0-9_]*)\(\)', "prose_call"),
        ]

        for line_num, line in enumerate(self.lines, 1):
            for pattern, ref_type in patterns:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    func_name = match.group(1)
                    # Filter out common false positives
                    if func_name not in ['the', 'a', 'an', 'is', 'are', 'to']:
                        self.claims["function_refs"].append({
                            "name": func_name,
                            "ref_type": ref_type,
                            "doc_line": line_num,
                            "context": line.strip()[:100]
                        })

    def _extract_class_refs(self):
        """Extract references to classes."""
        # Pattern: `ClassName` (PascalCase in backticks)
        pattern = r'`([A-Z][a-zA-Z0-9]+)`'

        # Also look for "the X class" or "class X"
        class_pattern = r'(?:[Tt]he\s+)?`?([A-Z][a-zA-Z0-9]+)`?\s+class'

        for line_num, line in enumerate(self.lines, 1):
            for match in re.finditer(pattern, line):
                class_name = match.group(1)
                # Filter common non-class words
                if class_name not in ['API', 'URL', 'JSON', 'HTTP', 'SQL', 'SSE', 'JWT', 'UUID']:
                    self.claims["class_refs"].append({
                        "name": class_name,
                        "doc_line": line_num,
                        "context": line.strip()[:100]
                    })

            for match in re.finditer(class_pattern, line):
                class_name = match.group(1)
                if class_name not in ['API', 'URL', 'JSON', 'HTTP', 'SQL', 'SSE', 'JWT', 'UUID']:
                    self.claims["class_refs"].append({
                        "name": class_name,
                        "doc_line": line_num,
                        "context": line.strip()[:100]
                    })

    def _extract_line_refs(self):
        """Extract specific line number references."""
        # Patterns: "line 123", "lines 123-456", "Line 123", ":123"
        patterns = [
            r'[Ll]ines?\s+(\d+)(?:\s*[-–]\s*(\d+))?',  # line(s) N or N-M
            r':(\d+)(?:-(\d+))?(?:\)|`|$|\s)',  # file.py:123 or :123-456
            r'\(line\s+(\d+)\)',  # (line 123)
        ]

        for line_num, line in enumerate(self.lines, 1):
            for pattern in patterns:
                for match in re.finditer(pattern, line):
                    start_line = int(match.group(1))
                    # Safely check for end_line group
                    try:
                        end_line = int(match.group(2)) if match.lastindex >= 2 and match.group(2) else None
                    except (IndexError, TypeError):
                        end_line = None

                    # Try to find associated file reference in same line
                    file_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*\.py)', line)
                    associated_file = file_match.group(1) if file_match else None

                    self.claims["line_refs"].append({
                        "start_line": start_line,
                        "end_line": end_line,
                        "doc_line": line_num,
                        "context": line.strip()[:100],
                        "associated_file": associated_file
                    })

    def _extract_count_claims(self):
        """Extract claims about counts/quantities."""
        # Patterns for counting claims
        patterns = [
            r'(\d+)\s+(tools?|functions?|methods?|classes?|endpoints?|parameters?|files?)',
            r'(one|two|three|four|five|six|seven|eight|nine|ten)\s+(tools?|functions?|methods?|classes?|endpoints?|parameters?)',
        ]

        word_to_num = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }

        for line_num, line in enumerate(self.lines, 1):
            for pattern in patterns:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    count_str = match.group(1).lower()
                    count = word_to_num.get(count_str, int(count_str) if count_str.isdigit() else None)

                    if count is not None:
                        self.claims["count_claims"].append({
                            "count": count,
                            "thing": match.group(2).lower(),
                            "doc_line": line_num,
                            "context": line.strip()[:100]
                        })

    def _extract_code_samples(self):
        """Extract code blocks from markdown."""
        in_code_block = False
        code_block_lang = None
        code_block_start = None
        code_block_content = []

        for line_num, line in enumerate(self.lines, 1):
            # Check for code block start/end
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Starting a code block
                    in_code_block = True
                    code_block_lang = line.strip()[3:].strip() or "unknown"
                    code_block_start = line_num
                    code_block_content = []
                else:
                    # Ending a code block
                    in_code_block = False
                    content = '\n'.join(code_block_content)

                    # Only include Python/relevant code samples
                    if code_block_lang in ['python', 'py', 'sql', 'json', 'bash', 'sh', '']:
                        self.claims["code_samples"].append({
                            "language": code_block_lang,
                            "start_line": code_block_start,
                            "end_line": line_num,
                            "content": content,
                            "line_count": len(code_block_content)
                        })
            elif in_code_block:
                code_block_content.append(line)

    def _extract_constant_refs(self):
        """Extract references to constants (UPPER_CASE names)."""
        # Pattern: `CONSTANT_NAME` or CONSTANT_NAME in context
        pattern = r'`([A-Z][A-Z0-9_]+)`'

        for line_num, line in enumerate(self.lines, 1):
            for match in re.finditer(pattern, line):
                const_name = match.group(1)
                # Filter out common acronyms that aren't constants
                if const_name not in ['API', 'URL', 'JSON', 'HTTP', 'SQL', 'SSE', 'JWT', 'UUID', 'HTML', 'CSS', 'GET', 'POST', 'PUT', 'DELETE']:
                    self.claims["constant_refs"].append({
                        "name": const_name,
                        "doc_line": line_num,
                        "context": line.strip()[:100]
                    })

    def _extract_behavior_claims(self):
        """Extract semantic behavior claims for adversarial verification."""
        # Look for strong behavior claims
        behavior_indicators = [
            r'(returns?|yields?)\s+(.{10,80})',
            r'(handles?|processes?)\s+(.{10,80})',
            r'(validates?|checks?|verifies?)\s+(.{10,80})',
            r'(creates?|generates?|builds?)\s+(.{10,80})',
            r'(calls?|invokes?|executes?)\s+(.{10,80})',
            r'(falls?\s+back|defaults?\s+to)\s+(.{10,80})',
        ]

        for line_num, line in enumerate(self.lines, 1):
            # Skip code blocks and headers
            if line.strip().startswith(('#', '```', '|', '-')):
                continue

            for pattern in behavior_indicators:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    self.claims["behavior_claims"].append({
                        "verb": match.group(1).lower(),
                        "claim": match.group(0)[:100],
                        "doc_line": line_num,
                        "full_line": line.strip()
                    })


def extract_doc_claims(filepath: str) -> dict:
    """Extract claims from a markdown documentation file."""
    with open(filepath, 'r') as f:
        content = f.read()

    extractor = DocClaimExtractor(content, filepath)
    return extractor.extract_all()


def extract_directory_claims(directory: str, pattern: str = "**/*.md") -> dict:
    """Extract claims from all markdown files in directory."""
    claims = {}
    base_path = Path(directory)

    for filepath in base_path.glob(pattern):
        # Skip planning/tracking files
        if '_planning' in str(filepath) or '_archive' in str(filepath):
            continue

        rel_path = str(filepath.relative_to(base_path))
        claims[rel_path] = extract_doc_claims(str(filepath))

    return claims


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract documentation claims")
    parser.add_argument("path", help="Markdown file or directory to analyze")
    parser.add_argument("--output", "-o", help="Output file (JSON)")
    parser.add_argument("--summary", "-s", action="store_true", help="Show summary only")

    args = parser.parse_args()

    if Path(args.path).is_file():
        result = extract_doc_claims(args.path)
    else:
        result = extract_directory_claims(args.path)

    if args.summary:
        if "claims" in result:
            # Single file
            print(f"\nClaims in {result['source_file']}:")
            for claim_type, claims in result['claims'].items():
                if claims:
                    print(f"  {claim_type}: {len(claims)}")
            print(f"\nTotal: {result['claim_count']} claims")
        else:
            # Directory
            total = 0
            for filepath, doc_result in result.items():
                count = doc_result.get('claim_count', 0)
                total += count
                if count > 0:
                    print(f"  {filepath}: {count} claims")
            print(f"\nTotal: {total} claims across {len(result)} files")
    elif args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Wrote claims to {args.output}")
    else:
        print(json.dumps(result, indent=2))
