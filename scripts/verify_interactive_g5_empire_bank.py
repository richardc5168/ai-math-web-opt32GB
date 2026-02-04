"""Verify docs/interactive-g5-empire/bank.js for correctness.

Checks:
- bank.js contains window.INTERACTIVE_G5_EMPIRE_BANK = [...];
- Each item has required fields and valid answer_mode
- Answers parse according to answer_mode
- Key meta requirements exist for tool-driven kinds
- Fraction answers are in simplest terms when answer_mode='fraction'

Exit code:
  0 = ok
  1 = failed
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from math import gcd
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "docs" / "interactive-g5-empire" / "bank.js"


ALLOWED_MODES = {"number", "fraction", "hhmm", "exact"}


@dataclass
class Fail:
    idx: int
    qid: str
    msg: str


def _load_bank_js(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"window\.INTERACTIVE_G5_EMPIRE_BANK\s*=\s*(\[.*\])\s*;\s*$", text, re.S)
    if not m:
        raise ValueError("Could not find window.INTERACTIVE_G5_EMPIRE_BANK = [...] ;")
    payload = m.group(1)
    data = json.loads(payload)
    if not isinstance(data, list):
        raise TypeError("Bank payload is not a list")
    return data


def _parse_number(s: str) -> float:
    ss = str(s).strip().replace(",", "")
    v = float(ss)
    if v != v or v in (float("inf"), float("-inf")):
        raise ValueError("not finite")
    return v


def _parse_fraction(s: str) -> Tuple[int, int]:
    ss = str(s).strip()
    if "/" not in ss:
        # allow integer
        n = int(ss)
        return n, 1
    a, b = ss.split("/", 1)
    n = int(a.strip())
    d = int(b.strip())
    if d == 0:
        raise ValueError("denominator=0")
    if d < 0:
        n, d = -n, -d
    g = gcd(abs(n), abs(d))
    return n // g, d // g


def _is_simplest_fraction(s: str) -> bool:
    ss = str(s).strip()
    if "/" not in ss:
        return True
    a, b = ss.split("/", 1)
    n = int(a.strip())
    d = int(b.strip())
    if d == 0:
        return False
    return gcd(abs(n), abs(d)) == 1


def _parse_hhmm(s: str) -> str:
    ss = str(s).strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{1,2})", ss)
    if not m:
        raise ValueError("format")
    hh = int(m.group(1))
    mm = int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError("range")
    return f"{hh:02d}:{mm:02d}"


def verify() -> List[Fail]:
    bank = _load_bank_js(BANK_PATH)
    fails: List[Fail] = []

    required = {"id", "kind", "question", "answer", "answer_mode", "hints", "steps", "explanation", "meta"}

    for i, q in enumerate(bank):
        qid = str(q.get("id", ""))
        kind = str(q.get("kind", ""))

        missing = sorted(required - set(q.keys()))
        if missing:
            fails.append(Fail(i, qid, f"missing fields: {missing}"))
            continue

        mode = str(q.get("answer_mode") or "")
        if mode not in ALLOWED_MODES:
            fails.append(Fail(i, qid, f"invalid answer_mode={mode}"))
            continue

        try:
            ans = q.get("answer")
            if mode == "number":
                _parse_number(ans)
            elif mode == "fraction":
                _parse_fraction(ans)
                if not _is_simplest_fraction(ans):
                    fails.append(Fail(i, qid, f"fraction answer not simplest: {ans}"))
            elif mode == "hhmm":
                _parse_hhmm(ans)
            elif mode == "exact":
                if str(ans).strip() == "":
                    raise ValueError("empty exact")
        except Exception as e:  # noqa: BLE001
            fails.append(Fail(i, qid, f"answer parse failed ({mode}): {e}"))
            continue

        meta = q.get("meta")
        if not isinstance(meta, dict):
            fails.append(Fail(i, qid, "meta is not object"))
            continue

        # Tool-driven meta requirements
        if kind == "fraction_addsub":
            for k in ("a", "b", "lcm", "op"):
                if k not in meta:
                    fails.append(Fail(i, qid, f"fraction_addsub meta missing {k}"))
        if kind == "fraction_mul":
            for k in ("a", "b"):
                if k not in meta:
                    fails.append(Fail(i, qid, f"fraction_mul meta missing {k}"))
        if kind == "percent_of":
            for k in ("base", "p"):
                if k not in meta:
                    fails.append(Fail(i, qid, f"percent_of meta missing {k}"))
        if kind == "time_add":
            for k in ("start", "add_m", "end"):
                if k not in meta:
                    fails.append(Fail(i, qid, f"time_add meta missing {k}"))
        if kind == "unit_convert":
            if "convert_kind" not in meta:
                fails.append(Fail(i, qid, "unit_convert meta missing convert_kind"))
        if kind == "volume_rect_prism":
            for k in ("l", "w", "h"):
                if k not in meta:
                    fails.append(Fail(i, qid, f"volume_rect_prism meta missing {k}"))

    return fails


def main() -> int:
    if not BANK_PATH.exists():
        print(f"Missing bank file: {BANK_PATH}")
        return 1

    fails = verify()
    if not fails:
        bank = _load_bank_js(BANK_PATH)
        kinds = sorted({str(q.get('kind')) for q in bank})
        print(f"OK: {BANK_PATH} (n={len(bank)} kinds={len(kinds)}: {', '.join(kinds)})")
        return 0

    print(f"FAILED: {len(fails)} issues")
    for f in fails[:30]:
        print(f"- #{f.idx} id={f.qid}: {f.msg}")
    if len(fails) > 30:
        print(f"... and {len(fails)-30} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
