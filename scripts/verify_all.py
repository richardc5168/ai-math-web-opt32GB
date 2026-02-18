"""One-shot local verification.

Runs:
- docs vs dist sync check (hash-based)
- FastAPI TestClient smoke-check for key endpoints
- focused pytest smoke suite for hints-next contract stability

Exit code:
- 0 if all OK
- 1 otherwise
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
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


def smoke_test_pytest_contracts() -> tuple[bool, str]:
    tests = [
        "tests/test_hints_next_api_ratio_reverse.py",
        "tests/test_fraction_word_g5_ratio_reverse_ui_smoke.py",
        "tests/test_fraction_word_g5_clarity.py",
    ]
    with tempfile.NamedTemporaryFile(prefix="verify_all_pytest_", suffix=".xml", delete=False) as f:
        xml_path = Path(f.name)

    cmd = [sys.executable, "-m", "pytest", *tests, "-q", f"--junitxml={xml_path}"]

    def _summary_from_xml(path: Path) -> str:
        if not path.exists():
            return "tests=unknown"
        root = ET.fromstring(path.read_text(encoding="utf-8", errors="ignore"))
        def _is_testsuite_tag(tag: str) -> bool:
            return str(tag).endswith("testsuite")

        suite = root if _is_testsuite_tag(root.tag) else next((n for n in root.iter() if _is_testsuite_tag(getattr(n, "tag", ""))), None)
        if suite is None:
            return "tests=unknown"
        total = int(suite.attrib.get("tests", "0"))
        failed = int(suite.attrib.get("failures", "0"))
        errors = int(suite.attrib.get("errors", "0"))
        skipped = int(suite.attrib.get("skipped", "0"))
        passed = max(0, total - failed - errors - skipped)
        if failed == 0 and errors == 0:
            if skipped > 0:
                return f"{passed}/{total} passed (skipped={skipped})"
            return f"{passed}/{total} passed"
        return f"{passed}/{total} passed (failed={failed}, errors={errors}, skipped={skipped})"

    try:
        p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        summary = _summary_from_xml(xml_path)
        if p.returncode != 0:
            details = summary
            if details == "tests=unknown":
                combined = "\n".join([(p.stdout or "").strip(), (p.stderr or "").strip()]).strip()
                details = combined or "pytest failed"
            return False, f"pytest smoke failed: {details}"
        return True, f"OK: pytest smoke ({summary})"
    except Exception as e:
        return False, f"Exception running pytest smoke: {type(e).__name__}: {e}"
    finally:
        try:
            xml_path.unlink(missing_ok=True)
        except Exception:
            pass


def main() -> int:
    root = ROOT

    ok1, msg1 = docs_dist_identical(root)
    ok2, msg2 = smoke_test_api()
    ok3, msg3 = smoke_test_pytest_contracts()

    print(f"1/3 {msg1}")
    print(f"2/3 {msg2}")
    print(f"3/3 {msg3}")

    if ok1 and ok2 and ok3:
        print("OK: verify_all")
        return 0

    print("NOT OK: verify_all")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
