#!/usr/bin/env python3
"""
Discrepancy Detector

Compares documentation claims against code specifications to find mismatches.
This is the core verification logic that detects documentation inaccuracies.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from extract_code_specs import extract_directory_specs, find_in_specs
from extract_doc_claims import extract_doc_claims


class DiscrepancyDetector:
    """Detect discrepancies between documentation claims and code reality."""

    def __init__(self, code_specs: dict, doc_claims: dict):
        self.code_specs = code_specs
        self.doc_claims = doc_claims
        self.discrepancies = {
            "definite_errors": [],   # Mechanically verified wrong
            "likely_errors": [],     # High confidence wrong
            "warnings": [],          # Potential issues
            "verified_accurate": [], # Confirmed correct
            "unverifiable": [],      # Can't check mechanically
        }

    def verify_all(self) -> dict:
        """Run all verification checks."""
        claims = self.doc_claims.get("claims", {})

        self._verify_file_refs(claims.get("file_refs", []))
        self._verify_function_refs(claims.get("function_refs", []))
        self._verify_class_refs(claims.get("class_refs", []))
        self._verify_line_refs(claims.get("line_refs", []))
        self._verify_count_claims(claims.get("count_claims", []))
        self._verify_constant_refs(claims.get("constant_refs", []))
        self._verify_code_samples(claims.get("code_samples", []))
        self._flag_behavior_claims(claims.get("behavior_claims", []))

        return {
            "source_doc": self.doc_claims.get("source_file"),
            "total_claims": self.doc_claims.get("claim_count", 0),
            "discrepancies": self.discrepancies,
            "summary": self._generate_summary()
        }

    def _verify_file_refs(self, file_refs: list):
        """Verify that referenced files exist."""
        for ref in file_refs:
            file_path = ref["file_path"]

            # Check if file exists in code specs
            found = False
            for spec_path in self.code_specs.keys():
                if file_path in spec_path or spec_path.endswith(file_path):
                    found = True
                    self.discrepancies["verified_accurate"].append({
                        "type": "file_exists",
                        "claim": f"File {file_path} exists",
                        "doc_line": ref["doc_line"],
                        "actual": spec_path
                    })
                    break

            if not found:
                # Try filesystem check for non-Python files
                # Build possible paths
                possible_paths = [
                    file_path,
                    f"app/{file_path}",
                    f"app/services/{file_path}",
                ]

                for possible in possible_paths:
                    if os.path.exists(possible):
                        found = True
                        self.discrepancies["verified_accurate"].append({
                            "type": "file_exists",
                            "claim": f"File {file_path} exists",
                            "doc_line": ref["doc_line"],
                            "actual": possible
                        })
                        break

            if not found:
                self.discrepancies["definite_errors"].append({
                    "type": "file_not_found",
                    "claim": f"References file: {file_path}",
                    "doc_line": ref["doc_line"],
                    "context": ref["context"],
                    "error": f"File not found in codebase"
                })

    def _verify_function_refs(self, function_refs: list):
        """Verify that referenced functions exist."""
        for ref in function_refs:
            func_name = ref["name"]

            # Handle method references like "ClassName.method_name"
            if '.' in func_name:
                parts = func_name.split('.')
                class_name = parts[0]
                method_name = parts[1]

                matches = find_in_specs(self.code_specs, method_name)
                class_matches = [m for m in matches if m.get("class") == class_name]

                if class_matches:
                    self.discrepancies["verified_accurate"].append({
                        "type": "method_exists",
                        "claim": f"Method {func_name} exists",
                        "doc_line": ref["doc_line"],
                        "actual_location": f"{class_matches[0]['file']}:{class_matches[0]['line']}"
                    })
                elif matches:
                    self.discrepancies["likely_errors"].append({
                        "type": "method_wrong_class",
                        "claim": f"Method {func_name}",
                        "doc_line": ref["doc_line"],
                        "error": f"Method '{method_name}' exists but in different class(es)",
                        "actual_classes": [m.get("class", "top-level") for m in matches]
                    })
                else:
                    self.discrepancies["definite_errors"].append({
                        "type": "method_not_found",
                        "claim": f"References method: {func_name}",
                        "doc_line": ref["doc_line"],
                        "context": ref["context"],
                        "error": f"Method not found in codebase"
                    })
            else:
                # Simple function name
                matches = find_in_specs(self.code_specs, func_name)

                if matches:
                    self.discrepancies["verified_accurate"].append({
                        "type": "function_exists",
                        "claim": f"Function/method {func_name} exists",
                        "doc_line": ref["doc_line"],
                        "locations": [f"{m['file']}:{m['line']}" for m in matches]
                    })
                else:
                    # Could be a false positive from extraction
                    self.discrepancies["warnings"].append({
                        "type": "function_not_found",
                        "claim": f"References: {func_name}",
                        "doc_line": ref["doc_line"],
                        "context": ref["context"],
                        "note": "Function not found - may be external, renamed, or false extraction"
                    })

    def _verify_class_refs(self, class_refs: list):
        """Verify that referenced classes exist."""
        seen = set()  # Deduplicate

        for ref in class_refs:
            class_name = ref["name"]
            if class_name in seen:
                continue
            seen.add(class_name)

            matches = find_in_specs(self.code_specs, class_name)
            class_matches = [m for m in matches if m["type"] == "class"]

            if class_matches:
                self.discrepancies["verified_accurate"].append({
                    "type": "class_exists",
                    "claim": f"Class {class_name} exists",
                    "doc_line": ref["doc_line"],
                    "locations": [f"{m['file']}:{m['line']}" for m in class_matches]
                })
            else:
                self.discrepancies["warnings"].append({
                    "type": "class_not_found",
                    "claim": f"References class: {class_name}",
                    "doc_line": ref["doc_line"],
                    "context": ref["context"],
                    "note": "Class not found - may be external, renamed, or false extraction"
                })

    def _verify_line_refs(self, line_refs: list):
        """Verify specific line number references."""
        for ref in line_refs:
            start_line = ref["start_line"]
            end_line = ref.get("end_line")
            context = ref["context"]

            # Use associated file if extracted, otherwise try to find in context
            associated_file = ref.get("associated_file")
            if associated_file:
                file_match = type('Match', (), {'group': lambda self, n: associated_file})()
            else:
                file_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_/\-]*\.py)', context)
            func_match = re.search(r'`([a-z_][a-z0-9_]*)`', context)

            if file_match:
                file_path = file_match.group(1)
                # Find the actual file
                for spec_path, spec in self.code_specs.items():
                    if file_path in spec_path or spec_path.endswith(file_path):
                        # Check if line reference is plausible
                        total_lines = spec.get("line_count", 0)

                        if start_line > total_lines:
                            self.discrepancies["definite_errors"].append({
                                "type": "line_out_of_range",
                                "claim": f"Line {start_line} in {file_path}",
                                "doc_line": ref["doc_line"],
                                "error": f"File only has {total_lines} lines"
                            })
                        elif func_match:
                            # Check if function is actually at that line
                            func_name = func_match.group(1)
                            matches = find_in_specs({spec_path: spec}, func_name)

                            if matches:
                                actual_line = matches[0]["line"]
                                drift = abs(actual_line - start_line)

                                if drift == 0:
                                    self.discrepancies["verified_accurate"].append({
                                        "type": "line_accurate",
                                        "claim": f"{func_name} at line {start_line}",
                                        "doc_line": ref["doc_line"]
                                    })
                                elif drift <= 10:
                                    self.discrepancies["warnings"].append({
                                        "type": "line_drift_minor",
                                        "claim": f"{func_name} at line {start_line}",
                                        "doc_line": ref["doc_line"],
                                        "actual_line": actual_line,
                                        "drift": drift
                                    })
                                else:
                                    self.discrepancies["definite_errors"].append({
                                        "type": "line_drift_major",
                                        "claim": f"{func_name} at line {start_line}",
                                        "doc_line": ref["doc_line"],
                                        "actual_line": actual_line,
                                        "drift": drift,
                                        "error": f"Actual location is line {actual_line} (drift of {drift} lines)"
                                    })
                        else:
                            # No function match - try to verify line content directly
                            # Look for code pattern in the context (e.g., "all_tools = ...")
                            code_pattern = re.search(r'`([^`]+)`|#\s*(.+)', context)
                            if code_pattern:
                                pattern_text = code_pattern.group(1) or code_pattern.group(2)
                                # Search for this pattern in the actual file
                                actual_file_path = os.path.join(os.path.dirname(list(self.code_specs.keys())[0]).split('/app')[0] if self.code_specs else '.', spec_path)
                                self._verify_line_content(ref, spec_path, start_line, pattern_text, total_lines)
                            else:
                                self.discrepancies["unverifiable"].append({
                                    "type": "line_ref_no_pattern",
                                    "claim": f"Line {start_line} in {file_path}",
                                    "doc_line": ref["doc_line"],
                                    "context": context,
                                    "reason": "No code pattern found to verify"
                                })
                        break
            else:
                # Can't verify without knowing which file
                self.discrepancies["unverifiable"].append({
                    "type": "line_ref_no_file",
                    "claim": f"Line {start_line}" + (f"-{end_line}" if end_line else ""),
                    "doc_line": ref["doc_line"],
                    "context": context,
                    "reason": "No file reference found in context"
                })

    def _verify_line_content(self, ref: dict, spec_path: str, claimed_line: int, pattern: str, total_lines: int):
        """Verify that specific content exists at claimed line number."""
        # Read the actual file to check
        try:
            # Construct file path - try multiple locations
            possible_paths = [
                spec_path,
                f"app/{spec_path}",
                spec_path.replace("services/", "app/services/")
            ]

            file_content = None
            actual_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        file_content = f.read()
                    actual_path = path
                    break

            if file_content is None:
                self.discrepancies["warnings"].append({
                    "type": "line_content_file_not_readable",
                    "claim": f"Line {claimed_line}: {pattern[:50]}",
                    "doc_line": ref["doc_line"],
                    "note": f"Could not read file to verify"
                })
                return

            lines = file_content.split('\n')

            # Clean up pattern for comparison
            clean_pattern = pattern.strip().rstrip(':').strip()
            if clean_pattern.startswith('Line '):
                # Extract the actual code pattern after "Line NNN in file.py:"
                clean_pattern = clean_pattern.split(':', 1)[-1].strip() if ':' in clean_pattern else ''

            if not clean_pattern:
                self.discrepancies["unverifiable"].append({
                    "type": "line_content_no_pattern",
                    "claim": f"Line {claimed_line}",
                    "doc_line": ref["doc_line"],
                    "reason": "Could not extract code pattern to verify"
                })
                return

            # Search for the pattern in the file
            found_lines = []
            for i, line in enumerate(lines, 1):
                if clean_pattern in line:
                    found_lines.append(i)

            if not found_lines:
                self.discrepancies["definite_errors"].append({
                    "type": "line_content_not_found",
                    "claim": f"Line {claimed_line}: {clean_pattern[:60]}",
                    "doc_line": ref["doc_line"],
                    "error": f"Pattern not found anywhere in {spec_path}"
                })
            elif claimed_line in found_lines:
                self.discrepancies["verified_accurate"].append({
                    "type": "line_content_accurate",
                    "claim": f"Line {claimed_line}: {clean_pattern[:40]}",
                    "doc_line": ref["doc_line"]
                })
            else:
                # Pattern exists but at different line(s)
                closest_line = min(found_lines, key=lambda x: abs(x - claimed_line))
                drift = abs(closest_line - claimed_line)

                if drift <= 10:
                    self.discrepancies["warnings"].append({
                        "type": "line_content_drift_minor",
                        "claim": f"Line {claimed_line}: {clean_pattern[:40]}",
                        "doc_line": ref["doc_line"],
                        "actual_lines": found_lines,
                        "closest": closest_line,
                        "drift": drift
                    })
                else:
                    self.discrepancies["definite_errors"].append({
                        "type": "line_content_drift_major",
                        "claim": f"Line {claimed_line}: {clean_pattern[:40]}",
                        "doc_line": ref["doc_line"],
                        "actual_lines": found_lines,
                        "closest": closest_line,
                        "drift": drift,
                        "error": f"Pattern found at line(s) {found_lines}, not {claimed_line} (drift: {drift})"
                    })

        except Exception as e:
            self.discrepancies["warnings"].append({
                "type": "line_content_verification_error",
                "claim": f"Line {claimed_line}",
                "doc_line": ref["doc_line"],
                "note": f"Error during verification: {str(e)}"
            })

    def _verify_count_claims(self, count_claims: list):
        """Verify claims about counts (e.g., 'six tools')."""
        for ref in count_claims:
            claimed_count = ref["count"]
            thing = ref["thing"]
            context = ref["context"]

            # Try to identify what's being counted
            # Look for nearby constant references
            const_match = re.search(r'`([A-Z][A-Z0-9_]+)`', context)

            if const_match:
                const_name = const_match.group(1)
                matches = find_in_specs(self.code_specs, const_name)

                if matches:
                    spec = matches[0].get("spec", {})
                    actual_count = spec.get("length")

                    if actual_count is not None:
                        if actual_count == claimed_count:
                            self.discrepancies["verified_accurate"].append({
                                "type": "count_accurate",
                                "claim": f"{claimed_count} {thing} in {const_name}",
                                "doc_line": ref["doc_line"]
                            })
                        else:
                            self.discrepancies["definite_errors"].append({
                                "type": "count_mismatch",
                                "claim": f"{claimed_count} {thing}",
                                "doc_line": ref["doc_line"],
                                "actual_count": actual_count,
                                "constant": const_name,
                                "error": f"Claimed {claimed_count} but actual count is {actual_count}"
                            })
                    else:
                        self.discrepancies["unverifiable"].append({
                            "type": "count_no_length",
                            "claim": f"{claimed_count} {thing}",
                            "doc_line": ref["doc_line"],
                            "reason": f"Found {const_name} but couldn't determine length"
                        })
                else:
                    self.discrepancies["warnings"].append({
                        "type": "count_constant_not_found",
                        "claim": f"{claimed_count} {thing}",
                        "doc_line": ref["doc_line"],
                        "context": context,
                        "note": f"Constant {const_name} not found"
                    })
            else:
                # Can't mechanically verify
                self.discrepancies["unverifiable"].append({
                    "type": "count_no_reference",
                    "claim": f"{claimed_count} {thing}",
                    "doc_line": ref["doc_line"],
                    "context": context,
                    "reason": "No specific constant/list referenced"
                })

    def _verify_constant_refs(self, constant_refs: list):
        """Verify that referenced constants exist."""
        seen = set()

        for ref in constant_refs:
            const_name = ref["name"]
            if const_name in seen:
                continue
            seen.add(const_name)

            matches = find_in_specs(self.code_specs, const_name)

            if matches:
                self.discrepancies["verified_accurate"].append({
                    "type": "constant_exists",
                    "claim": f"Constant {const_name} exists",
                    "doc_line": ref["doc_line"],
                    "locations": [f"{m['file']}:{m['line']}" for m in matches]
                })
            else:
                self.discrepancies["warnings"].append({
                    "type": "constant_not_found",
                    "claim": f"References constant: {const_name}",
                    "doc_line": ref["doc_line"],
                    "context": ref["context"],
                    "note": "Constant not found - may be in non-Python file or renamed"
                })

    def _verify_code_samples(self, code_samples: list):
        """Verify code samples in documentation."""
        for sample in code_samples:
            if sample["language"] not in ["python", "py", ""]:
                continue

            content = sample["content"]

            # Detect if this is pseudocode/comments rather than real code
            lines = content.strip().split('\n')
            comment_lines = sum(1 for line in lines if line.strip().startswith('#') or line.strip().startswith('//'))
            numbered_lines = sum(1 for line in lines if re.match(r'^\s*\d+\.', line.strip()))

            # If mostly comments or numbered steps, skip verification
            if len(lines) > 0 and (comment_lines / len(lines) > 0.5 or numbered_lines / len(lines) > 0.3):
                self.discrepancies["unverifiable"].append({
                    "type": "code_sample_pseudocode",
                    "doc_line": sample["start_line"],
                    "reason": "Appears to be pseudocode or comments, not executable Python"
                })
                continue

            # Look for specific patterns that should exist in code
            # Pattern 1: Assignment with specific variable names
            assignments = re.findall(r'([a-z_][a-z0-9_]*)\s*=\s*', content)
            # Pattern 2: Function calls - must have actual parentheses with content or empty
            calls = re.findall(r'([a-z_][a-z0-9_]*)\s*\([^)]*\)', content)
            # Extract just the function names
            call_names = [re.match(r'([a-z_][a-z0-9_]*)', c).group(1) for c in calls if re.match(r'([a-z_][a-z0-9_]*)', c)]
            # Pattern 3: Class references
            classes = re.findall(r'([A-Z][a-zA-Z0-9]+)(?:\(|\.)', content)

            issues = []
            verified = []

            # Common builtins and keywords to skip
            builtins = {'print', 'len', 'str', 'int', 'dict', 'list', 'await', 'async', 'return',
                       'if', 'for', 'while', 'def', 'class', 'import', 'from', 'try', 'except',
                       'type', 'isinstance', 'hasattr', 'getattr', 'setattr', 'open', 'range',
                       'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed', 'any', 'all',
                       'get', 'set', 'append', 'extend', 'update', 'items', 'keys', 'values',
                       'format', 'replace', 'split', 'join', 'strip', 'lower', 'upper'}

            # Check if referenced items exist
            for func in call_names:
                if func not in builtins:
                    matches = find_in_specs(self.code_specs, func)
                    if matches:
                        verified.append(func)
                    else:
                        issues.append(f"Function '{func}' not found")

            common_classes = {'True', 'False', 'None', 'Optional', 'List', 'Dict', 'Any', 'Set',
                             'Tuple', 'Union', 'Callable', 'Type', 'Mapping', 'Sequence', 'Iterable',
                             'Exception', 'Error', 'Response', 'Request', 'Session'}

            for cls in classes:
                if cls not in common_classes:
                    matches = find_in_specs(self.code_specs, cls)
                    class_matches = [m for m in matches if m["type"] == "class"]
                    if class_matches:
                        verified.append(cls)
                    else:
                        issues.append(f"Class '{cls}' not found")

            # Only report if we found actual verifiable references
            if issues and len(issues) > len(verified):
                self.discrepancies["likely_errors"].append({
                    "type": "code_sample_references_missing",
                    "doc_line": sample["start_line"],
                    "issues": issues[:5],
                    "verified": verified[:5],
                    "sample_preview": content[:100]
                })
            elif verified:
                self.discrepancies["verified_accurate"].append({
                    "type": "code_sample_references_exist",
                    "doc_line": sample["start_line"],
                    "verified_items": verified[:5]
                })

    def _flag_behavior_claims(self, behavior_claims: list):
        """Flag behavior claims for adversarial verification."""
        for claim in behavior_claims:
            self.discrepancies["unverifiable"].append({
                "type": "behavior_claim",
                "claim": claim["claim"],
                "verb": claim["verb"],
                "doc_line": claim["doc_line"],
                "reason": "Semantic claim requires adversarial verification",
                "full_context": claim["full_line"]
            })

    def _generate_summary(self) -> dict:
        """Generate verification summary."""
        return {
            "definite_errors": len(self.discrepancies["definite_errors"]),
            "likely_errors": len(self.discrepancies["likely_errors"]),
            "warnings": len(self.discrepancies["warnings"]),
            "verified_accurate": len(self.discrepancies["verified_accurate"]),
            "unverifiable": len(self.discrepancies["unverifiable"]),
            "accuracy_rate": self._calculate_accuracy_rate()
        }

    def _calculate_accuracy_rate(self) -> str:
        """Calculate accuracy rate of verifiable claims."""
        verified = len(self.discrepancies["verified_accurate"])
        errors = len(self.discrepancies["definite_errors"]) + len(self.discrepancies["likely_errors"])
        total = verified + errors

        if total == 0:
            return "N/A (no verifiable claims)"

        rate = (verified / total) * 100
        return f"{rate:.1f}% ({verified}/{total} verifiable claims accurate)"


def verify_document(doc_path: str, code_dir: str = "app") -> dict:
    """Verify a single documentation file against codebase."""
    # Extract code specs
    code_specs = extract_directory_specs(code_dir)

    # Extract doc claims
    doc_claims = extract_doc_claims(doc_path)

    # Detect discrepancies
    detector = DiscrepancyDetector(code_specs, doc_claims)
    return detector.verify_all()


def format_report(result: dict) -> str:
    """Format verification result as readable report."""
    lines = []
    lines.append(f"\n{'='*70}")
    lines.append(f"VERIFICATION REPORT: {result['source_doc']}")
    lines.append(f"{'='*70}")

    summary = result["summary"]
    lines.append(f"\nSUMMARY:")
    lines.append(f"  Total claims extracted: {result['total_claims']}")
    lines.append(f"  Accuracy rate: {summary['accuracy_rate']}")
    lines.append(f"")
    lines.append(f"  ❌ Definite errors:   {summary['definite_errors']}")
    lines.append(f"  ⚠️  Likely errors:     {summary['likely_errors']}")
    lines.append(f"  📋 Warnings:          {summary['warnings']}")
    lines.append(f"  ✅ Verified accurate: {summary['verified_accurate']}")
    lines.append(f"  ❓ Unverifiable:      {summary['unverifiable']}")

    discrepancies = result["discrepancies"]

    if discrepancies["definite_errors"]:
        lines.append(f"\n{'─'*70}")
        lines.append("❌ DEFINITE ERRORS (must fix)")
        lines.append(f"{'─'*70}")
        for err in discrepancies["definite_errors"]:
            lines.append(f"\n  Line {err['doc_line']}: {err['type']}")
            lines.append(f"    Claim: {err.get('claim', 'N/A')}")
            lines.append(f"    Error: {err.get('error', 'N/A')}")
            if 'actual_line' in err:
                lines.append(f"    Actual: line {err['actual_line']}")

    if discrepancies["likely_errors"]:
        lines.append(f"\n{'─'*70}")
        lines.append("⚠️  LIKELY ERRORS (review needed)")
        lines.append(f"{'─'*70}")
        for err in discrepancies["likely_errors"]:
            lines.append(f"\n  Line {err['doc_line']}: {err['type']}")
            lines.append(f"    Claim: {err.get('claim', 'N/A')}")
            if 'issues' in err:
                for issue in err['issues']:
                    lines.append(f"    - {issue}")

    if discrepancies["warnings"]:
        lines.append(f"\n{'─'*70}")
        lines.append("📋 WARNINGS (may need attention)")
        lines.append(f"{'─'*70}")
        for warn in discrepancies["warnings"][:10]:  # Limit to 10
            lines.append(f"\n  Line {warn['doc_line']}: {warn['type']}")
            lines.append(f"    {warn.get('claim', warn.get('note', 'N/A'))}")

        if len(discrepancies["warnings"]) > 10:
            lines.append(f"\n  ... and {len(discrepancies['warnings']) - 10} more warnings")

    lines.append(f"\n{'='*70}\n")

    return '\n'.join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verify documentation against code")
    parser.add_argument("doc_path", help="Path to markdown documentation file")
    parser.add_argument("--code-dir", "-c", default="app", help="Code directory to verify against")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    result = verify_document(args.doc_path, args.code_dir)

    if args.json:
        print(json.dumps(result, indent=2))
    elif args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Wrote results to {args.output}")
        print(format_report(result))
    else:
        print(format_report(result))
