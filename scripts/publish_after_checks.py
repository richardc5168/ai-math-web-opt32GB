"""Run strict checks, then (optionally) commit + push and print the web URL.

This script is intentionally interactive:
- It refuses to commit/push unless checks pass.
- It asks for an explicit YES.

Usage:
  python scripts/publish_after_checks.py -m "your message"

Notes:
- You still need to have git remote set (origin) and be authenticated.
- GitHub Pages URL is printed at the end.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# When GitHub Pages is configured to deploy from /docs, the site root is:
#   https://<user>.github.io/<repo>/
PAGES_URL = "https://richardc5168.github.io/ai-math-web/"


def run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message", default="docs: quality gate pass", help="git commit message")
    ap.add_argument(
        "--spec",
        default="tests/specs/precommit_checklist.json",
        help="checklist spec path",
    )
    args = ap.parse_args()

    # 1) Strict checklist
    rc = run([sys.executable, "scripts/run_checklist.py", "--spec", args.spec])
    if rc != 0:
        print("\nABORT: checklist failed; not committing.")
        return rc

    # 2) Optional: run pre-commit (if available)
    if shutil.which("pre-commit"):
        rc = run(["pre-commit", "run", "--all-files"])
        if rc != 0:
            print("\nABORT: pre-commit hooks failed; not committing.")
            return rc

    # 3) Show status and ask for explicit approval
    run(["git", "-c", "core.pager=cat", "status", "-sb"])
    print("\nType YES to commit+push, anything else to abort:")
    if input("> ").strip() != "YES":
        print("ABORT: not committing.")
        return 1

    # 4) Commit + push
    rc = run(["git", "add", "-A"])
    if rc != 0:
        return rc

    rc = run(["git", "commit", "-m", args.message])
    if rc != 0:
        return rc

    rc = run(["git", "push", "origin", "main"])
    if rc != 0:
        return rc

    print("\nPUBLISHED:")
    print(PAGES_URL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
