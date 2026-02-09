from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DIST_DOCS = ROOT / "dist_ai_math_web_pages" / "docs"

TMP_SRC = ROOT / ".tmp_math_offline" / "content" / "gold_bank" / "gold_bank.jsonl"

OUT_DIR = DOCS / "offline-math"
OUT_DIR_DIST = DIST_DOCS / "offline-math"

OUT_JS = OUT_DIR / "bank.js"
OUT_JS_DIST = OUT_DIR_DIST / "bank.js"

WINDOW_VAR = "OFFLINE_MATH_BANK"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing source jsonl: {path}")

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _normalize_item(q: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    qid = str(q.get("id") or "").strip()
    out["id"] = f"offline_{qid}" if qid else "offline_"

    out["grade"] = q.get("grade")
    out["topic"] = q.get("topic")
    out["type"] = q.get("type")
    out["params"] = q.get("params") or {}

    out["prompt"] = q.get("prompt") or ""
    out["answer"] = q.get("answer")

    # Keep teacherSteps verbatim (this is the core of hints/guide).
    ts = q.get("teacherSteps")
    out["teacherSteps"] = ts if isinstance(ts, list) else []

    out["source"] = q.get("source") or {}
    out["meta"] = q.get("meta") or {}

    return out


def write_bank_js(items: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(items, ensure_ascii=False, indent=2)
    out_path.write_text(
        f"/* Auto-generated from math-offline gold_bank.jsonl (vendored). */\nwindow.{WINDOW_VAR} = {payload};\n",
        encoding="utf-8",
    )


def main() -> int:
    rows = _load_jsonl(TMP_SRC)
    items = [_normalize_item(q) for q in rows]

    write_bank_js(items, OUT_JS)
    write_bank_js(items, OUT_JS_DIST)

    print(f"Wrote {len(items)} items")
    print(f"- {OUT_JS}")
    print(f"- {OUT_JS_DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
