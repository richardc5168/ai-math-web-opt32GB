#!/usr/bin/env python3
"""Pre-commit hook: detect obvious secrets in staged files.

Scans staged file content for patterns that look like API keys,
personal access tokens, or other secrets that must never be committed.

Exit 0 = clean, Exit 1 = secrets detected.
"""

import re
import subprocess
import sys

# Patterns that indicate a secret value (not just a variable name referencing one)
SECRET_PATTERNS = [
    # OpenAI API keys
    (r"sk-proj-[A-Za-z0-9_-]{20,}", "OpenAI project API key"),
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI API key"),
    # GitHub tokens
    (r"ghp_[A-Za-z0-9]{36}", "GitHub personal access token"),
    (r"gho_[A-Za-z0-9]{36}", "GitHub OAuth token"),
    (r"github_pat_[A-Za-z0-9_]{22,}", "GitHub fine-grained PAT"),
    (r"ghu_[A-Za-z0-9]{36}", "GitHub user-to-server token"),
    (r"ghs_[A-Za-z0-9]{36}", "GitHub server-to-server token"),
    # Generic long base64 secrets (in assignment or value context)
    (r'(?:api[_-]?key|secret|token|password)\s*[:=]\s*["\'][A-Za-z0-9+/=_-]{40,}["\']', "Possible hardcoded secret"),
    # AWS
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    # Slack
    (r"xox[bpors]-[0-9]{10,}-[A-Za-z0-9-]+", "Slack token"),
]

# Files to skip entirely
SKIP_PATTERNS = [
    r"\.gitignore$",
    r"\.pre-commit-config\.yaml$",
    r"tools/check_no_secrets\.py$",  # this file itself
    r"node_modules/",
    r"\.venv/",
    r"dist_ai_math_web_pages/",  # mirror of docs/
]


def get_staged_files():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def should_skip(filepath):
    for pat in SKIP_PATTERNS:
        if re.search(pat, filepath):
            return True
    return False


def scan_file(filepath):
    findings = []
    try:
        # Read staged content from git index
        result = subprocess.run(
            ["git", "show", f":{filepath}"],
            capture_output=True,
        )
        content = result.stdout.decode("utf-8", errors="replace")
    except Exception:
        return findings

    if not content:
        return findings

    for line_no, line in enumerate(content.split("\n"), 1):
        for pattern, description in SECRET_PATTERNS:
            if re.search(pattern, line):
                # Truncate the matched line for display
                display = line.strip()[:80]
                findings.append((filepath, line_no, description, display))
    return findings


def main():
    files = get_staged_files()
    all_findings = []

    for f in files:
        if should_skip(f):
            continue
        findings = scan_file(f)
        all_findings.extend(findings)

    if all_findings:
        print("🚨 SECRET SCAN FAILED — potential secrets detected in staged files:\n")
        for filepath, line_no, desc, display in all_findings:
            print(f"  {filepath}:{line_no} [{desc}]")
            print(f"    {display}...")
            print()
        print("Action required:")
        print("  1. Remove the secret from the file")
        print("  2. Use environment variables or .env (which is gitignored)")
        print("  3. If this is a false positive, add an exception to tools/check_no_secrets.py")
        print()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
