#!/usr/bin/env python3
"""
Conceptual Documentation Verification Tool

Verifies that documentation CONCEPTUALLY and ACCURATELY describes what the code does.
The code is the source of truth. We don't care about:
- Line numbers (they shouldn't be in docs anyway)
- Exact code snippets
- Precise counts

We DO care about:
- Whether docs give developers the correct mental model
- Architectural descriptions being accurate
- Behavioral claims matching reality
- API endpoint descriptions being correct
- Conceptual alignment (e.g., doc says "sessions" but code uses "JWT")

Approach (based on research to avoid confirmation bias):
1. LLM reads ONLY the code → generates description of what it does
2. LLM reads ONLY the doc → extracts what it claims
3. Compare the two descriptions semantically with adversarial prompting
4. Find what developers would misunderstand

Usage:
    python scripts/doc-verify/conceptual_verify.py docs/path/to/doc.md --code-dir app

Environment:
    ANTHROPIC_API_KEY - Required for LLM calls
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

# Check for API key early
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("Error: ANTHROPIC_API_KEY environment variable required", file=sys.stderr)
    print("Set it with: export ANTHROPIC_API_KEY=your-key-here", file=sys.stderr)
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("Error: anthropic package required. Install with: pip install anthropic", file=sys.stderr)
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# Prompts - The core of the verification approach
# ═══════════════════════════════════════════════════════════════════════════

PROMPT_CODE_DESCRIPTION = """You are analyzing source code to describe what it ACTUALLY does.
Do NOT assume anything from documentation - only describe what the code implements.

Describe in plain English:
1. What is the primary purpose of this module/file?
2. What are the main public classes/functions and what do they do?
3. What authentication/authorization approach does it use (if any)?
4. What external services, databases, or APIs does it interact with?
5. What are the key data structures and their purposes?
6. What configuration or environment variables does it require?
7. Any notable patterns, caching, or performance considerations visible in code?

Be specific and factual. Only describe what the code actually implements.
Do NOT mention line numbers - they are irrelevant.

CODE:
{code}

DESCRIPTION:"""

PROMPT_DOC_CLAIMS = """You are analyzing documentation to extract what it CLAIMS about the code.
Do NOT assume the documentation is accurate. Extract claims skeptically.

Extract specific claims about:
1. What the documentation says the module's purpose is
2. What classes/functions it claims exist and what they do
3. What authentication/authorization it claims is used
4. What external services/databases it claims are used
5. What data structures or schemas it describes
6. What configuration it claims is needed
7. Any performance claims or patterns described

Be specific. Quote the documentation where relevant.
IGNORE any line number references - they are meaningless.

DOCUMENTATION:
{doc}

CLAIMS:"""

PROMPT_COMPARE_ADVERSARIAL = """You are a skeptical code reviewer comparing what code ACTUALLY does
versus what documentation CLAIMS it does.

Your job is to find CONCEPTUAL MISALIGNMENT - places where a developer
reading the documentation would get the WRONG mental model of how
the code works.

Focus on finding where developers would be MISLED:
- Architectural mismatches (doc says X pattern, code uses Y)
- Behavioral differences (doc says it caches, but no caching visible)
- API differences (doc shows endpoints that don't exist or work differently)
- Security model differences (doc says sessions, code uses JWT)
- Data flow differences (doc says sync, code is async)
- Missing features (doc describes features that aren't implemented)
- Outdated information (doc describes old approach, code has evolved)

IGNORE completely:
- Line numbers being wrong (they shouldn't be in docs)
- Minor wording differences
- Formatting issues

WHAT THE CODE ACTUALLY DOES:
{code_description}

WHAT THE DOCUMENTATION CLAIMS:
{doc_claims}

For each discrepancy found, provide:
1. **Issue**: Brief title
2. **Doc says**: What the documentation claims
3. **Code does**: What the code actually does
4. **Developer impact**: What would a developer misunderstand?
5. **Severity**: CRITICAL (wrong mental model) | MODERATE (misleading) | MINOR (imprecise)

If there are no significant discrepancies, say "No significant conceptual discrepancies found."

DISCREPANCIES:"""


@dataclass
class VerificationResult:
    """Result of conceptual verification."""
    doc_path: str
    relevant_code: List[str]
    code_description: str
    doc_claims: str
    discrepancies: str
    verdict: str  # ACCURATE, NEEDS_UPDATE, CRITICALLY_WRONG, NEEDS_REVIEW


class ConceptualVerifier:
    """Verifies documentation conceptually matches code behavior."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize with Anthropic client.

        Args:
            model: Claude model to use (default: claude-sonnet for balance of speed/quality)
        """
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = 4096

    def _call_llm(self, prompt: str) -> str:
        """Call Claude with a prompt."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def describe_code(self, code_files: List[Path]) -> str:
        """
        Have LLM read ONLY the code and describe what it does.

        This is step 1: Generate ground truth from code without doc influence.
        """
        # Combine code from all files
        code_sections = []
        for code_file in code_files:
            try:
                content = code_file.read_text()
                # Truncate very large files to avoid context limits
                if len(content) > 50000:
                    content = content[:50000] + "\n\n... [truncated for length] ..."
                code_sections.append(f"### File: {code_file.name}\n```python\n{content}\n```")
            except Exception as e:
                code_sections.append(f"### File: {code_file.name}\n[Error reading: {e}]")

        combined_code = "\n\n".join(code_sections)
        prompt = PROMPT_CODE_DESCRIPTION.format(code=combined_code)
        return self._call_llm(prompt)

    def extract_doc_claims(self, doc_path: Path) -> str:
        """
        Have LLM read ONLY the doc and extract what it claims.

        This is step 2: Extract claims without code influence.
        """
        doc = doc_path.read_text()
        # Truncate very large docs
        if len(doc) > 30000:
            doc = doc[:30000] + "\n\n... [truncated for length] ..."
        prompt = PROMPT_DOC_CLAIMS.format(doc=doc)
        return self._call_llm(prompt)

    def find_discrepancies(self, code_description: str, doc_claims: str) -> str:
        """
        Compare code description to doc claims using adversarial prompting.

        This is step 3: Find conceptual misalignment.
        """
        prompt = PROMPT_COMPARE_ADVERSARIAL.format(
            code_description=code_description,
            doc_claims=doc_claims
        )
        return self._call_llm(prompt)

    def find_relevant_code(self, doc_path: Path, code_base: Path) -> List[Path]:
        """
        Find code files that the documentation is describing.

        Looks for:
        - Explicit file references in the doc
        - Module names mentioned
        - Service names that map to directories
        """
        doc_content = doc_path.read_text()
        doc_content_lower = doc_content.lower()
        relevant_files = []

        # Extract file references from doc
        file_patterns = [
            r'`([a-zA-Z_][a-zA-Z0-9_/]*\.py)`',  # `path/to/file.py`
            r'`app/([a-zA-Z_][a-zA-Z0-9_/]*\.py)`',  # `app/module/file.py`
            r'\(app/([a-zA-Z_][a-zA-Z0-9_/]*\.py)\)',  # (app/module/file.py)
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, doc_content)
            for match in matches:
                # Try to find the file
                if match.startswith("app/"):
                    match = match[4:]  # Remove app/ prefix
                potential_paths = [
                    code_base / match,
                    code_base / "app" / match,
                    code_base / "app" / "services" / match,
                ]
                for p in potential_paths:
                    if p.exists() and p.is_file():
                        relevant_files.append(p)

        # Also look for service directories mentioned
        service_keywords = ['auth', 'chat', 'gateway', 'kb', 'asset', 'web', 'llm']
        for service in service_keywords:
            if service in doc_content_lower:
                # Check multiple possible locations
                service_dirs = [
                    code_base / "app" / "services" / service,
                    code_base / "app" / service,
                ]
                for service_dir in service_dirs:
                    if service_dir.exists() and service_dir.is_dir():
                        # Add main service files (not __init__.py, not tests)
                        for py_file in service_dir.glob("*.py"):
                            if py_file.name not in ("__init__.py", "test_*.py"):
                                relevant_files.append(py_file)

        # Check shared modules
        if "shared" in doc_content_lower or "config" in doc_content_lower:
            shared_dir = code_base / "app" / "shared"
            if shared_dir.exists():
                for py_file in shared_dir.glob("*.py"):
                    if py_file.name not in ("__init__.py",):
                        relevant_files.append(py_file)

        # Deduplicate and limit
        unique_files = list(set(relevant_files))
        # Sort by relevance (files mentioned explicitly first, then alphabetically)
        unique_files.sort(key=lambda p: (not any(p.name in doc_content for _ in [1]), p.name))

        return unique_files[:15]  # Limit to avoid context overflow

    def verify_document(self, doc_path: Path, code_base: Path) -> VerificationResult:
        """
        Full verification of a single document.

        Returns VerificationResult with all analysis and verdict.
        """
        print(f"\n📄 Verifying: {doc_path}")

        # Find relevant code files
        print("  🔍 Finding relevant code files...")
        code_files = self.find_relevant_code(doc_path, code_base)

        if not code_files:
            print("  ⚠️  No relevant code files found")
            return VerificationResult(
                doc_path=str(doc_path),
                relevant_code=[],
                code_description="No relevant code files found",
                doc_claims="",
                discrepancies="Cannot verify - no code files identified. Doc may describe external systems or be purely conceptual.",
                verdict="NEEDS_REVIEW"
            )

        print(f"  📁 Found {len(code_files)} code files:")
        for f in code_files[:5]:
            print(f"      - {f.relative_to(code_base)}")
        if len(code_files) > 5:
            print(f"      ... and {len(code_files) - 5} more")

        # Step 1: Describe what code actually does
        print("  🤖 Step 1: Analyzing code (LLM describing what code does)...")
        code_description = self.describe_code(code_files)

        # Step 2: Extract what doc claims
        print("  🤖 Step 2: Extracting doc claims (LLM reading doc)...")
        doc_claims = self.extract_doc_claims(doc_path)

        # Step 3: Find discrepancies with adversarial prompting
        print("  🤖 Step 3: Finding discrepancies (adversarial comparison)...")
        discrepancies = self.find_discrepancies(code_description, doc_claims)

        # Determine verdict based on discrepancies
        verdict = self._determine_verdict(discrepancies)
        print(f"  📊 Verdict: {verdict}")

        return VerificationResult(
            doc_path=str(doc_path),
            relevant_code=[str(f) for f in code_files],
            code_description=code_description,
            doc_claims=doc_claims,
            discrepancies=discrepancies,
            verdict=verdict
        )

    def _determine_verdict(self, discrepancies: str) -> str:
        """Determine overall verdict from discrepancy analysis."""
        lower = discrepancies.lower()
        if "critical" in lower:
            return "CRITICALLY_WRONG"
        elif "moderate" in lower:
            return "NEEDS_UPDATE"
        elif "minor" in lower:
            return "NEEDS_UPDATE"
        elif "no significant" in lower or "no discrepancies" in lower:
            return "ACCURATE"
        else:
            return "NEEDS_REVIEW"


def main():
    parser = argparse.ArgumentParser(
        description="Verify documentation conceptually matches code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Verify a single doc
    python scripts/doc-verify/conceptual_verify.py docs/reference/chat/chat-service-implementation.md

    # Verify with JSON output
    python scripts/doc-verify/conceptual_verify.py docs/api/auth.md --output json

    # Use a different model
    python scripts/doc-verify/conceptual_verify.py docs/api/auth.md --model claude-3-5-haiku-latest
        """
    )
    parser.add_argument("doc_path", help="Path to documentation file")
    parser.add_argument(
        "--code-dir",
        default=".",
        help="Base directory for code (default: current directory)"
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Claude model to use (default: claude-sonnet-4-20250514)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show full LLM responses"
    )

    args = parser.parse_args()

    doc_path = Path(args.doc_path)
    code_base = Path(args.code_dir)

    if not doc_path.exists():
        print(f"Error: Doc not found: {doc_path}", file=sys.stderr)
        sys.exit(1)

    verifier = ConceptualVerifier(model=args.model)
    result = verifier.verify_document(doc_path, code_base)

    if args.output == "json":
        output = {
            "doc_path": result.doc_path,
            "relevant_code": result.relevant_code,
            "verdict": result.verdict,
            "discrepancies": result.discrepancies,
        }
        if args.verbose:
            output["code_description"] = result.code_description
            output["doc_claims"] = result.doc_claims
        print(json.dumps(output, indent=2))
    else:
        print("\n" + "=" * 70)
        print(f"📄 Document: {result.doc_path}")
        print(f"📊 Verdict: {result.verdict}")
        print("=" * 70)

        print(f"\n📁 Relevant Code Files ({len(result.relevant_code)}):")
        for f in result.relevant_code[:10]:
            print(f"   - {f}")
        if len(result.relevant_code) > 10:
            print(f"   ... and {len(result.relevant_code) - 10} more")

        if args.verbose:
            print("\n" + "-" * 70)
            print("🔍 CODE DESCRIPTION (what code actually does):")
            print("-" * 70)
            print(result.code_description)

            print("\n" + "-" * 70)
            print("📝 DOC CLAIMS (what documentation says):")
            print("-" * 70)
            print(result.doc_claims)

        print("\n" + "-" * 70)
        print("⚠️  DISCREPANCIES:")
        print("-" * 70)
        print(result.discrepancies)


if __name__ == "__main__":
    main()
