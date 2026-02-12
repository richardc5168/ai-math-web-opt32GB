"""Run a strict checklist spec (JSON; YAML optional).

This turns "we once broke something" into a repeatable gate:
- docs/dist mirror must be identical
- API smoke endpoints must respond
- forbidden patterns must not appear (e.g., root-home links that break back button)
- optional pytest subset

Usage:
  python scripts/run_checklist.py --spec tests/specs/precommit_checklist.json

Exit code:
  0 if all enabled checks pass
  1 otherwise
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]

# Allow importing top-level modules like server.py when running from scripts/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def docs_dist_identical(root: Path) -> tuple[bool, str]:
    docs = root / "docs"
    dist = root / "dist_ai_math_web_pages" / "docs"

    if not docs.exists() or not dist.exists():
        return False, f"Missing folder: docs={docs.exists()} dist={dist.exists()}"

    def build_map(base: Path) -> dict[str, tuple[int, str]]:
        out: dict[str, tuple[int, str]] = {}
        for p in base.rglob("*"):
            if p.is_file():
                rel = p.relative_to(base).as_posix()
                out[rel] = (p.stat().st_size, sha256_file(p))
        return out

    a = build_map(docs)
    b = build_map(dist)

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])

    if only_a or only_b or changed:
        msg = [
            f"docs files={len(a)} dist files={len(b)}",
            f"only in docs={len(only_a)} only in dist={len(only_b)} mismatches={len(changed)}",
        ]
        if only_a:
            msg.append("only_docs: " + ", ".join(only_a[:10]) + (" ..." if len(only_a) > 10 else ""))
        if only_b:
            msg.append("only_dist: " + ", ".join(only_b[:10]) + (" ..." if len(only_b) > 10 else ""))
        if changed:
            msg.append("changed: " + ", ".join(changed[:10]) + (" ..." if len(changed) > 10 else ""))
        return False, " | ".join(msg)

    return True, f"OK: docs/dist identical ({len(a)} files)"


def api_smoke(paths: list[str]) -> tuple[bool, str]:
    try:
        # Local imports so the runner can still be used for non-API checks.
        from fastapi.testclient import TestClient
        import server

        c = TestClient(server.app)
        for p in paths:
            r = c.get(p)
            if r.status_code != 200:
                return False, f"{p} status={r.status_code}"
        return True, "OK: api_smoke"
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}"


def iter_files_from_globs(globs: Iterable[str]) -> list[Path]:
    files: set[Path] = set()
    for g in globs:
        # Keep paths workspace-relative in spec.
        for p in ROOT.glob(g):
            if p.is_file():
                files.add(p)
    return sorted(files)


def forbid_string(globs: list[str], forbid: list[str]) -> tuple[bool, str]:
    files = iter_files_from_globs(globs)
    if not files:
        return False, f"No files matched globs: {globs}"

    violations: list[str] = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for needle in forbid:
            if needle in text:
                rel = p.relative_to(ROOT).as_posix()
                violations.append(f"{rel} contains {needle!r}")
                break

    if violations:
        head = " | ".join(violations[:8])
        more = f" (+{len(violations) - 8} more)" if len(violations) > 8 else ""
        return False, f"Forbidden pattern(s) found: {head}{more}"

    return True, "OK: forbid_string"


def run_pytest(args: list[str]) -> tuple[bool, str]:
    cmd = [sys.executable, "-m", "pytest", *args]
    p = subprocess.run(cmd, cwd=str(ROOT))
    return (p.returncode == 0, f"pytest exit={p.returncode}")


@dataclass
class CheckResult:
    ok: bool
    check_id: str
    message: str


def load_spec(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))

    if path.suffix.lower() in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "YAML spec requires PyYAML. Install with: pip install pyyaml"
            ) from e
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    raise ValueError(f"Unsupported spec extension: {path.suffix}")


def run_check(item: dict[str, Any]) -> CheckResult:
    check_id = str(item.get("id") or item.get("type") or "unknown")
    check_type = str(item.get("type") or "")

    if not item.get("enabled", True):
        return CheckResult(True, check_id, "SKIP")

    if check_type == "docs_dist_identical":
        ok, msg = docs_dist_identical(ROOT)
        return CheckResult(ok, check_id, msg)

    if check_type == "api_smoke":
        paths = item.get("paths") or []
        ok, msg = api_smoke([str(x) for x in paths])
        return CheckResult(ok, check_id, msg)

    if check_type == "forbid_string":
        globs = [str(x) for x in (item.get("globs") or [])]
        forbid = [str(x) for x in (item.get("forbid") or [])]
        ok, msg = forbid_string(globs, forbid)
        if not ok and item.get("message"):
            msg = f"{msg}\nHint: {item.get('message')}"
        return CheckResult(ok, check_id, msg)

    if check_type == "pytest":
        args = [str(x) for x in (item.get("args") or [])]
        ok, msg = run_pytest(args)
        return CheckResult(ok, check_id, msg)

    return CheckResult(False, check_id, f"Unknown check type: {check_type}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spec",
        default="tests/specs/precommit_checklist.json",
        help="Checklist spec path (.json; .yaml if PyYAML installed)",
    )
    args = ap.parse_args()

    spec_path = (ROOT / args.spec).resolve() if not Path(args.spec).is_absolute() else Path(args.spec)
    if not spec_path.exists():
        print(f"ERROR: spec not found: {spec_path}")
        return 1

    try:
        spec = load_spec(spec_path)
    except Exception as e:
        print(f"ERROR: failed to load spec: {type(e).__name__}: {e}")
        return 1

    checks = spec.get("checks") if isinstance(spec, dict) else None
    if not isinstance(checks, list) or not checks:
        print("ERROR: spec missing 'checks' list")
        return 1

    results: list[CheckResult] = [run_check(item or {}) for item in checks]

    all_ok = True
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        print(f"[{status}] {r.check_id}: {r.message}")
        if not r.ok:
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
