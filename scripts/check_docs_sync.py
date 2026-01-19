"""Check docs/ and dist_ai_math_web_pages/docs/ are identical.

Outputs:
- Counts
- Missing/extra files
- Hash mismatches (SHA256)

Exit code:
- 0 if identical
- 1 if any mismatch
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_map(base: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for p in sorted(base.rglob("*")):
        if p.is_file():
            rel = p.relative_to(base).as_posix()
            result[rel] = (p.stat().st_size, sha256_file(p))
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    docs = root / "docs"
    dist = root / "dist_ai_math_web_pages" / "docs"

    if not docs.exists():
        print(f"ERROR: missing folder: {docs}")
        return 1
    if not dist.exists():
        print(f"ERROR: missing folder: {dist}")
        return 1

    a = build_map(docs)
    b = build_map(dist)

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])

    print(f"docs files: {len(a)}")
    print(f"dist files: {len(b)}")
    print(f"only in docs: {len(only_a)}")
    print(f"only in dist: {len(only_b)}")
    print(f"content mismatches: {len(changed)}")

    if only_a:
        print("\nOnly in docs:")
        for k in only_a:
            print("  +", k)

    if only_b:
        print("\nOnly in dist:")
        for k in only_b:
            print("  -", k)

    if changed:
        print("\nMismatched content:")
        for k in changed:
            sa, ha = a[k]
            sb, hb = b[k]
            print(f"  * {k}\n      docs: {sa}B {ha}\n      dist: {sb}B {hb}")

    ok = not only_a and not only_b and not changed
    if ok:
        print("\nOK: docs and dist are identical")
        return 0

    print("\nNOT OK: docs and dist differ")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
