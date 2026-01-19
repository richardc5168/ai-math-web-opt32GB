"""One-shot local verification.

Runs:
- docs vs dist sync check (hash-based)
- FastAPI TestClient smoke-check for key endpoints

Exit code:
- 0 if all OK
- 1 otherwise

Note: pytest is intentionally not run here; run it separately:
  python -m pytest -q
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

# Allow importing top-level modules like server.py when running from scripts/
ROOT = Path(__file__).resolve().parents[1]
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
            msg.append("only_a: " + ", ".join(only_a[:10]) + (" ..." if len(only_a) > 10 else ""))
        if only_b:
            msg.append("only_b: " + ", ".join(only_b[:10]) + (" ..." if len(only_b) > 10 else ""))
        if changed:
            msg.append("changed: " + ", ".join(changed[:10]) + (" ..." if len(changed) > 10 else ""))
        return False, " | ".join(msg)

    return True, f"OK: docs/dist identical ({len(a)} files)"


def smoke_test_api() -> tuple[bool, str]:
    try:
        from fastapi.testclient import TestClient
        import server

        c = TestClient(server.app)
        r = c.get("/health")
        if r.status_code != 200:
            return False, f"/health status={r.status_code}"

        r = c.get("/verify")
        if r.status_code != 200:
            return False, f"/verify status={r.status_code}"

        r = c.get("/quadratic")
        if r.status_code != 200:
            return False, f"/quadratic status={r.status_code}"

        r = c.get("/mixed-multiply")
        if r.status_code != 200:
            return False, f"/mixed-multiply status={r.status_code}"

        rr = c.post(
            "/api/mixed-multiply/diagnose",
            json={
                "left": "2 1/3",
                "right": "2",
                "step1": "7/3",
                "step2": "14/3",
                "step3": "4 2/3",
            },
        )
        if rr.status_code != 200:
            return False, f"/api/mixed-multiply/diagnose status={rr.status_code}"

        code = (rr.json() or {}).get("diagnosis_code")
        if not code:
            return False, "diagnose response missing diagnosis_code"

        return True, f"OK: endpoints healthy (diagnosis_code={code})"
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}"


def main() -> int:
    root = ROOT

    ok1, msg1 = docs_dist_identical(root)
    ok2, msg2 = smoke_test_api()

    print(msg1)
    print(msg2)

    if ok1 and ok2:
        print("OK: verify_all")
        return 0

    print("NOT OK: verify_all")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
