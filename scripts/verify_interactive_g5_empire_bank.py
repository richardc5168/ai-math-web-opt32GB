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

import argparse
import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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


def _parse_decimal(s: str) -> Decimal:
    try:
        return Decimal(str(s).strip().replace(",", ""))
    except InvalidOperation as e:
        raise ValueError("not decimal") from e


def _expected_from_int_places(n: int, places: int) -> Decimal:
    p = int(places)
    if p <= 0:
        return Decimal(int(n))
    return Decimal(int(n)) / (Decimal(10) ** p)


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


def verify_bank(bank: List[Dict[str, Any]]) -> List[Fail]:
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
        if kind == "decimal_mul":
            for k in ("a", "b", "a_int", "b_int", "a_places", "raw_int_product", "total_places"):
                if k not in meta:
                    fails.append(Fail(i, qid, f"decimal_mul meta missing {k}"))
            if not any(f.idx == i for f in fails):
                try:
                    a_int = int(meta["a_int"])
                    b_int = int(meta["b_int"])
                    a_places = int(meta["a_places"])
                    raw = int(meta["raw_int_product"])
                    total_places = int(meta["total_places"])
                    if a_places != total_places:
                        fails.append(Fail(i, qid, "decimal_mul a_places != total_places"))
                    if raw != a_int * b_int:
                        fails.append(Fail(i, qid, "decimal_mul raw_int_product mismatch"))
                    # Validate displayed a matches a_int/a_places, and answer matches raw/total_places
                    a_val = _parse_decimal(meta["a"])
                    exp_a = _expected_from_int_places(a_int, a_places)
                    if a_val != exp_a:
                        fails.append(Fail(i, qid, "decimal_mul meta a mismatch (a_int/a_places)"))
                    ans_val = _parse_decimal(q["answer"])
                    exp_ans = _expected_from_int_places(raw, total_places)
                    if ans_val != exp_ans:
                        fails.append(Fail(i, qid, "decimal_mul answer mismatch (raw_int_product/places)"))
                except Exception as e:  # noqa: BLE001
                    fails.append(Fail(i, qid, f"decimal_mul meta validation failed: {e}"))

        if kind == "decimal_div":
            for k in ("a", "b", "a_int", "a_places", "ans_int", "ans_places"):
                if k not in meta:
                    fails.append(Fail(i, qid, f"decimal_div meta missing {k}"))
            if not any(f.idx == i for f in fails):
                try:
                    b_int = int(meta["b"])
                    a_int = int(meta["a_int"])
                    a_places = int(meta["a_places"])
                    ans_int = int(meta["ans_int"])
                    ans_places = int(meta["ans_places"])
                    if ans_places != a_places:
                        fails.append(Fail(i, qid, "decimal_div ans_places != a_places"))
                    if a_int != b_int * ans_int:
                        fails.append(Fail(i, qid, "decimal_div a_int != b*ans_int"))
                    a_val = _parse_decimal(meta["a"])
                    exp_a = _expected_from_int_places(a_int, a_places)
                    if a_val != exp_a:
                        fails.append(Fail(i, qid, "decimal_div meta a mismatch (a_int/a_places)"))
                    ans_val = _parse_decimal(q["answer"])
                    exp_ans = _expected_from_int_places(ans_int, ans_places)
                    if ans_val != exp_ans:
                        fails.append(Fail(i, qid, "decimal_div answer mismatch (ans_int/ans_places)"))
                except Exception as e:  # noqa: BLE001
                    fails.append(Fail(i, qid, f"decimal_div meta validation failed: {e}"))

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


def verify_path(path: Path) -> Tuple[List[Dict[str, Any]], List[Fail]]:
    bank = _load_bank_js(path)
    fails = verify_bank(bank)
    return bank, fails


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Verify interactive-g5-empire bank.js")
    p.add_argument("--path", type=str, default=str(BANK_PATH), help="Path to bank.js")
    args = p.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"Missing bank file: {path}")
        return 1

    bank, fails = verify_path(path)
    if not fails:
        kinds = sorted({str(q.get('kind')) for q in bank})
        print(f"OK: {path} (n={len(bank)} kinds={len(kinds)}: {', '.join(kinds)})")
        return 0

    print(f"FAILED: {len(fails)} issues")
    for f in fails[:30]:
        print(f"- #{f.idx} id={f.qid}: {f.msg}")
    if len(fails) > 30:
        print(f"... and {len(fails)-30} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
