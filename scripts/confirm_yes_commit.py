"""Require an explicit YES before allowing a commit.

Intended to run as a git hook via pre-commit at the `prepare-commit-msg` stage.

Bypass options:
- Set env var SKIP_YES_COMMIT=1
- Use `git commit --no-verify` (skips all pre-commit hooks)
"""

from __future__ import annotations

import os
import sys


def should_skip(args: list[str]) -> bool:
    if os.environ.get("SKIP_YES_COMMIT") in {"1", "true", "TRUE", "yes", "YES"}:
        return True

    # prepare-commit-msg args: <commit-msg-file> [source] [sha]
    source = args[2] if len(args) >= 3 else ""
    # Avoid blocking merge/rebase/squash auto-generated messages.
    if source in {"merge", "squash", "commit", "template", "message", "rebase"}:
        return True

    return False


def main() -> int:
    args = sys.argv
    if should_skip(args):
        return 0

    print("\nPre-commit: strict checks passed.")
    print("Type YES to proceed with commit (anything else aborts):")
    try:
        ans = input("> ").strip()
    except EOFError:
        print("ABORT: no stdin available. Set SKIP_YES_COMMIT=1 to bypass.")
        return 1

    if ans != "YES":
        print("ABORT: commit cancelled.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
