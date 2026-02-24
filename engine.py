#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ALL-IN-ONE: Math Practice MVP (FastAPI backend + Engine in one file)
- 單檔可直接跑：含出題/判題/自訂題目解題(solve_custom)/作答記錄/報表
- 多學生（同一付費帳號下可綁多學生）
- 訂閱 gate（MVP：DB subscription.status=active 才能用）
- Auth（MVP：用 X-API-Key 對應 account）

啟動：
  pip install fastapi uvicorn
  uvicorn math_app:app --reload --port 8000
或：
  python3 math_app.py

測試：
  1) 建立測試帳號+訂閱+學生：
     curl -X POST "http://127.0.0.1:8000/admin/bootstrap?name=TestAccount"
  2) 查學生：
     curl -H "X-API-Key: <api_key>" "http://127.0.0.1:8000/v1/students"
  3) 出題：
     curl -X POST -H "X-API-Key: <api_key>" "http://127.0.0.1:8000/v1/questions/next?student_id=1"
  4) 交卷：
     curl -X POST -H "X-API-Key: <api_key>" -H "Content-Type: application/json" \
       -d '{"student_id":1,"question_id":1,"user_answer":"1/2","time_spent_sec":12}' \
       "http://127.0.0.1:8000/v1/answers/submit"
  5) 自訂題目解題：
     curl -X POST -H "X-API-Key: <api_key>" -H "Content-Type: application/json" \
       -d '{"question":"1/2 + 1/3"}' \
       "http://127.0.0.1:8000/v1/custom/solve"
  6) 自訂題目記錄作答（可用 auto 或手動答案）：
     curl -X POST -H "X-API-Key: <api_key>" -H "Content-Type: application/json" \
       -d '{"student_id":1,"question":"1/2+1/3","final_answer":"5/6","user_answer":"5/6","time_spent_sec":20}' \
       "http://127.0.0.1:8000/v1/custom/submit"
"""

import os
import re
import math
import json
import random
import sqlite3
from datetime import datetime, timedelta
from fractions import Fraction
from typing import Optional, Dict, Any, List, Tuple

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# -------------------------
# Optional: hint overrides (manual approval gate)
# -------------------------
try:
    from hint_overrides import HINT_OVERRIDES as _HINT_OVERRIDES
except Exception:
    _HINT_OVERRIDES = {}

# -------------------------
# Optional: SymPy
# -------------------------
try:
    import sympy as sp
    HAS_SYMPY = True
except Exception:
    HAS_SYMPY = False

if HAS_SYMPY:
    try:
        from sympy.parsing.sympy_parser import (
            parse_expr,
            standard_transformations,
            implicit_multiplication_application,
            convert_xor,
        )
        _HAS_SYMPY_PARSER = True
    except Exception:
        _HAS_SYMPY_PARSER = False
else:
    _HAS_SYMPY_PARSER = False

try:
    from fraction_word_g5 import generate_fraction_word_problem_g5
except Exception:
    generate_fraction_word_problem_g5 = None

# New isolated question type (pack-based, non-regression)
try:
    from question_types.g5s_web_concepts import type as g5s_web_concepts
except Exception:
    g5s_web_concepts = None

try:
    from question_types.g5s_good_concepts import type as g5s_good_concepts
except Exception:
    g5s_good_concepts = None


def _env_enabled(name: str) -> bool:
    val = str(os.environ.get(name, "")).strip().lower()
    return val in ("1", "true", "yes", "on")


EXTERNAL_WEB_QUESTION_BANK_ENABLED = _env_enabled("EXTERNAL_WEB_QUESTION_BANK")
EXTERNAL_WEB_FRACTION_DECIMAL_ENABLED = _env_enabled("EXTERNAL_WEB_FRACTION_DECIMAL")

try:
    from src.question_types.external_web_fraction_app_v1 import type as external_web_fraction_app_v1
except Exception:
    external_web_fraction_app_v1 = None

try:
    from src.question_types.fraction_decimal_application_web_v1 import type as fraction_decimal_application_web_v1
except Exception:
    fraction_decimal_application_web_v1 = None


# ======================================================================
# ENGINE (出題 / 判題 / 自訂題目解題)
# ======================================================================

MAX_2DIGIT = 99

def _within_2digit_int(x: int) -> bool:
    return abs(int(x)) <= MAX_2DIGIT

def _within_2digit_fraction(f: Fraction) -> bool:
    return abs(f.numerator) <= MAX_2DIGIT and abs(f.denominator) <= MAX_2DIGIT

def _lcm(a: int, b: int) -> int:
    return (a * b) // math.gcd(a, b)

def _lcm3(a: int, b: int, c: int) -> int:
    ab = _lcm(a, b)
    return _lcm(ab, c)

# -------------------------
# Answer parsing & checking
# -------------------------
def parse_answer(text: str) -> Optional[Fraction]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        # 帶分數 "1 1/2"
        if " " in text and "/" in text:
            parts = text.split()
            if len(parts) == 2:
                w = int(parts[0])
                f = Fraction(parts[1])
                return (Fraction(w, 1) + f) if w >= 0 else (Fraction(w, 1) - f)
        # 假分數/整數
        return Fraction(text)
    except Exception:
        return None


_NUMERIC_EXPR_MAX_LEN = 128
_ALGEBRA_EXPR_MAX_LEN = 256

_TIME_HHMM_RE = re.compile(r"^\s*(\d{1,2})\s*:\s*(\d{1,2})\s*$")
_MONTH_RE = re.compile(r"^\s*(\d{1,2})\s*月\s*$")
_IDENT_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _normalize_math_input(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    # Common math symbols / fullwidth variants.
    s = s.replace("×", "*")
    s = s.replace("÷", "/")
    s = s.replace("−", "-").replace("—", "-")
    s = s.replace("＋", "+")
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("，", ",").replace("、", ",")
    return s.strip()


def _normalize_text_answer(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    # Normalize common fullwidth punctuation/spaces; keep content otherwise.
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("＝", "=")
    s = s.replace("　", " ")
    s = re.sub(r"\s+", "", s)
    return s


def _normalize_ident(text: str) -> str:
    s = _normalize_text_answer(text)
    return s.upper()


def _normalize_time_hhmm(text: str) -> Optional[str]:
    s = (text or "").strip()
    m = _TIME_HHMM_RE.match(s)
    if not m:
        return None
    try:
        hh = int(m.group(1))
        mm = int(m.group(2))
    except Exception:
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return f"{hh:02d}:{mm:02d}"


def _normalize_month(text: str) -> Optional[int]:
    s = (text or "").strip()
    m = _MONTH_RE.match(s)
    if m:
        try:
            v = int(m.group(1))
            return v if 1 <= v <= 12 else None
        except Exception:
            return None
    if re.fullmatch(r"\d{1,2}", s):
        v = int(s)
        return v if 1 <= v <= 12 else None
    return None


def _canonical_choice(text: str) -> str:
    """Map common categorical answers to canonical tokens."""
    s = _normalize_text_answer(text)
    if not s:
        return ""

    s_lower = s.lower()

    yes_set = {"是", "對", "正确", "正確", "yes", "y", "true", "t", "1"}
    no_set = {"否", "不", "错", "錯", "no", "n", "false", "f", "0"}
    if s in yes_set or s_lower in yes_set:
        return "YES"
    if s in no_set or s_lower in no_set:
        return "NO"

    prime_set = {"質數", "质数", "prime"}
    comp_set = {"合數", "合数", "composite"}
    if s in prime_set or s_lower in prime_set:
        return "PRIME"
    if s in comp_set or s_lower in comp_set:
        return "COMPOSITE"

    up_set = {"上升", "增加", "變多", "up"}
    down_set = {"下降", "減少", "變少", "down"}
    flat_set = {"持平", "不變", "一樣", "flat"}
    if s in up_set or s_lower in up_set:
        return "UP"
    if s in down_set or s_lower in down_set:
        return "DOWN"
    if s in flat_set or s_lower in flat_set:
        return "FLAT"

    return s


def _eq_statement_equal(user_text: str, correct_text: str) -> Optional[bool]:
    """Check simple equality statements like 'PB=PF' order-insensitively."""
    u = _normalize_text_answer(user_text)
    c = _normalize_text_answer(correct_text)
    if not u or not c:
        return None
    if u.count("=") != 1 or c.count("=") != 1:
        return None
    u_left, u_right = u.split("=", 1)
    c_left, c_right = c.split("=", 1)

    # Only handle simple identifiers, not full algebra.
    if not (_IDENT_RE.fullmatch(u_left) and _IDENT_RE.fullmatch(u_right)):
        return None
    if not (_IDENT_RE.fullmatch(c_left) and _IDENT_RE.fullmatch(c_right)):
        return None

    u_pair = sorted([_normalize_ident(u_left), _normalize_ident(u_right)])
    c_pair = sorted([_normalize_ident(c_left), _normalize_ident(c_right)])
    return u_pair == c_pair


def _sympy_parse_numeric_expr(text: str):
    """Parse a numeric-only expression into a SymPy Expr.

    Safety goals:
    - Refuse any letters/symbols (no variables, no functions).
    - Refuse very long strings.
    - Allow only digits, whitespace, + - * / ( ) .
    """
    if not HAS_SYMPY:
        return None
    s = _normalize_math_input(text)
    # Treat 'x'/'X' as multiplication sign only in numeric contexts.
    # Examples: 2x3, 2 x 3, 2x(3+4), (2+1)x3
    s = re.sub(r"(?<=[0-9\)])\s*[xX]\s*(?=[0-9\(])", "*", s)
    if not s or len(s) > _NUMERIC_EXPR_MAX_LEN:
        return None
    if re.search(r"[A-Za-z_]", s):
        return None
    if re.search(r"[^0-9\s\+\-\*/\(\)\.,]", s):
        return None
    try:
        expr = sp.sympify(s, evaluate=True)
        if getattr(expr, "free_symbols", None):
            if len(expr.free_symbols) > 0:
                return None
        return expr
    except Exception:
        return None


def _sympy_parse_algebra_expr(text: str):
    """Parse an algebraic expression allowing only symbol x and basic safe functions.

    This is intended for checking student answers like:
      - "2x+2" vs "2*(x+1)"
      - "(x-3)^2" (xor converted to **)

    Safety constraints:
    - Hard length cap.
    - Forbid brackets/quotes/semicolons/colons/backslashes.
    - Only allow letters for known identifiers (x, sqrt, etc).
    """
    if not (HAS_SYMPY and _HAS_SYMPY_PARSER):
        return None
    s = _normalize_math_input(text)
    if not s or len(s) > _ALGEBRA_EXPR_MAX_LEN:
        return None
    # Disallow clearly dangerous / non-math tokens.
    if any(ch in s for ch in ["[", "]", "{", "}", "'", '"', ";", ":", "\\", "`", "@"]):
        return None
    # Basic character allowlist: digits, letters, underscore, operators, parens, dot, comma, space.
    if re.search(r"[^0-9A-Za-z_\s\+\-\*/\(\)\^\.=,]", s):
        return None
    # Quick reject double underscore / dunder patterns.
    if "__" in s:
        return None

    try:
        x = sp.Symbol("x")
        safe_global = {
            # Core constructors used by the parser's transformed code
            "Integer": sp.Integer,
            "Rational": sp.Rational,
            "Float": sp.Float,
            "Symbol": sp.Symbol,
            "Pow": sp.Pow,
            "Mul": sp.Mul,
            "Add": sp.Add,
        }
        local_dict = {
            "x": x,
            "sqrt": sp.sqrt,
            "abs": sp.Abs,
            "Abs": sp.Abs,
            "pi": sp.pi,
            "E": sp.E,
        }
        transformations = (
            standard_transformations
            + (implicit_multiplication_application, convert_xor)
        )
        expr = parse_expr(
            s,
            local_dict=local_dict,
            global_dict=safe_global,
            transformations=transformations,
            evaluate=True,
        )
        # Only allow symbol x (no other symbols).
        if getattr(expr, "free_symbols", None):
            for sym in expr.free_symbols:
                if str(sym) != "x":
                    return None
        return expr
    except Exception:
        return None


def _sympy_parse_equation(text: str):
    """Parse an equation string into (lhs, rhs) expressions."""
    s = _normalize_math_input(text)
    if not s or "=" not in s:
        return None
    if s.count("=") != 1:
        return None
    lhs_s, rhs_s = s.split("=", 1)
    lhs = _sympy_parse_algebra_expr(lhs_s)
    rhs = _sympy_parse_algebra_expr(rhs_s)
    if lhs is None or rhs is None:
        return None
    return lhs, rhs


def _sympy_symbolic_equiv(user_text: str, correct_text: str) -> Optional[bool]:
    """Symbolic equivalence for expressions or equations (x only)."""
    if not HAS_SYMPY:
        return None

    # Equation solving: correct can be equation, user can be numeric or expression.
    correct_eq = _sympy_parse_equation(correct_text)
    if correct_eq is not None:
        lhs, rhs = correct_eq
        try:
            x = sp.Symbol("x")
            sols = sp.solve(sp.Eq(lhs, rhs), x)
        except Exception:
            return None

        # Normalize user into sympy expr (prefer numeric-only first, then algebra).
        u_num = _sympy_parse_numeric_expr(user_text)
        u_expr = u_num if u_num is not None else _sympy_parse_algebra_expr(user_text)
        if u_expr is None:
            return None

        # If user provided an expression in x, check whether it matches a solution form.
        if getattr(u_expr, "free_symbols", None) and len(u_expr.free_symbols) > 0:
            for s in sols:
                try:
                    if sp.simplify(u_expr - s) == 0:
                        return True
                except Exception:
                    pass
            return False

        # User numeric: check membership.
        for s in sols:
            try:
                if sp.simplify(u_expr - s) == 0:
                    return True
            except Exception:
                continue
        return False

    # Expression equivalence (require both sides to involve x).
    u_expr = _sympy_parse_algebra_expr(user_text)
    c_expr = _sympy_parse_algebra_expr(correct_text)
    if u_expr is None or c_expr is None:
        return None

    u_syms = getattr(u_expr, "free_symbols", set()) or set()
    c_syms = getattr(c_expr, "free_symbols", set()) or set()
    if not u_syms and not c_syms:
        return None
    if u_syms != c_syms:
        return False

    try:
        return bool(sp.simplify(u_expr - c_expr) == 0)
    except Exception:
        return None


def _sympy_numeric_equal(a_expr, b_expr) -> Optional[bool]:
    if a_expr is None or b_expr is None or not HAS_SYMPY:
        return None
    try:
        diff = sp.simplify(a_expr - b_expr)
        if diff == 0:
            return True
        # For Float-y cases, fall back to numeric tolerance.
        try:
            return bool(abs(float(sp.N(diff))) < 1e-9)
        except Exception:
            return False
    except Exception:
        return None


def _split_multi(text: str) -> List[str]:
    s = _normalize_math_input(text)
    if not s:
        return []
    if "," in s:
        return [p.strip() for p in s.split(",") if p.strip()]
    return []

def check(user_answer: str, correct_answer: str) -> Optional[int]:
    """
    return:
      1 = correct
      0 = incorrect
      None = invalid format / cannot parse
    """
    user = (user_answer or "").strip()
    correct = (correct_answer or "").strip()

    # New types: JSON payload with type_key + validator.
    if correct.startswith("{"):
        try:
            payload = json.loads(correct)
            if isinstance(payload, dict):
                tkey = payload.get("type_key")
                if (
                    EXTERNAL_WEB_QUESTION_BANK_ENABLED
                    and external_web_fraction_app_v1 is not None
                    and tkey == getattr(external_web_fraction_app_v1, "TYPE_KEY", "")
                ):
                    return external_web_fraction_app_v1.check_answer(user, payload)
                if (
                    EXTERNAL_WEB_FRACTION_DECIMAL_ENABLED
                    and fraction_decimal_application_web_v1 is not None
                    and tkey == getattr(fraction_decimal_application_web_v1, "TYPE_KEY", "")
                ):
                    return fraction_decimal_application_web_v1.check_answer(user, payload)
                if g5s_web_concepts is not None and tkey == getattr(g5s_web_concepts, "TYPE_KEY", ""):
                    return g5s_web_concepts.check_answer(user, payload)
                if g5s_good_concepts is not None and tkey == getattr(g5s_good_concepts, "TYPE_KEY", ""):
                    return g5s_good_concepts.check_answer(user, payload)
        except Exception:
            pass

    # 多值答案（以空格分隔）：GCD LCM、通分、公分母 新分子...
    user_clean = re.sub(r'[^0-9\s]', '', user)
    correct_clean = re.sub(r'[^0-9\s]', '', correct)

    if correct_clean.count(' ') > 0:
        return 1 if ' '.join(user_clean.split()) == ' '.join(correct_clean.split()) else 0

    # Comma-separated multi answers (e.g., roots: "1,2").
    c_parts = _split_multi(correct)
    if c_parts:
        u_parts = _split_multi(user)
        if not u_parts:
            return None

        # Parse each part as Fraction first; if that fails, try safe SymPy numeric expr.
        def _parse_part(p: str):
            f = parse_answer(p)
            if f is not None:
                return ("frac", f)
            e = _sympy_parse_numeric_expr(p)
            if e is not None:
                return ("sym", e)
            return None

        u_vals = []
        c_vals = []
        for p in u_parts:
            pv = _parse_part(p)
            if pv is None:
                return None
            u_vals.append(pv)
        for p in c_parts:
            pv = _parse_part(p)
            if pv is None:
                return None
            c_vals.append(pv)

        if len(u_vals) != len(c_vals):
            return 0

        # If all Fractions, compare as unordered multiset.
        if all(t == "frac" for t, _ in u_vals) and all(t == "frac" for t, _ in c_vals):
            u_sorted = sorted([v for _, v in u_vals])
            c_sorted = sorted([v for _, v in c_vals])
            return 1 if u_sorted == c_sorted else 0

        # Mixed: compare by canonical SymPy form (order-insensitive).
        def _canon(tv):
            t, v = tv
            if t == "frac":
                return (0, str(v))
            return (1, sp.srepr(v) if HAS_SYMPY else str(v))

        u_sorted = sorted(u_vals, key=_canon)
        c_sorted = sorted(c_vals, key=_canon)
        for (ut, uv), (ct, cv) in zip(u_sorted, c_sorted):
            if ut == "frac" and ct == "frac":
                if uv != cv:
                    return 0
                continue
            # Compare via SymPy numeric equivalence if possible.
            u_expr = uv if ut == "sym" else sp.Rational(uv.numerator, uv.denominator)
            c_expr = cv if ct == "sym" else sp.Rational(cv.numerator, cv.denominator)
            eq = _sympy_numeric_equal(u_expr, c_expr)
            if eq is not True:
                return 0
        return 1

    u = parse_answer(user)
    c = parse_answer(correct)
    if u is not None and c is not None:
        return 1 if u == c else 0

    # Non-numeric formats (time / month / categorical / simple equality statements)
    t_u = _normalize_time_hhmm(user)
    t_c = _normalize_time_hhmm(correct)
    if t_u is not None or t_c is not None:
        if t_u is None or t_c is None:
            return None
        return 1 if t_u == t_c else 0

    m_c = _normalize_month(correct)
    if m_c is not None:
        m_u = _normalize_month(user)
        if m_u is None:
            return None
        return 1 if m_u == m_c else 0

    eq_stmt = _eq_statement_equal(user, correct)
    if eq_stmt is not None:
        return 1 if eq_stmt else 0

    cu = _canonical_choice(user)
    cc = _canonical_choice(correct)
    if cc in {"YES", "NO", "PRIME", "COMPOSITE", "UP", "DOWN", "FLAT"}:
        return 1 if cu == cc else 0

    # Guarded SymPy symbolic equivalence for algebra-type answers.
    if HAS_SYMPY and _HAS_SYMPY_PARSER:
        # Only try when it looks symbolic/equation-like.
        if re.search(r"[A-Za-z_]", user) or re.search(r"[A-Za-z_]", correct) or ("=" in user) or ("=" in correct) or ("^" in user) or ("^" in correct):
            sym_ok = _sympy_symbolic_equiv(user, correct)
            if sym_ok is not None:
                return 1 if sym_ok else 0

    # Safe SymPy fallback for numeric expressions like "(1/2)+(1/3)".
    u_expr = _sympy_parse_numeric_expr(user)
    c_expr = _sympy_parse_numeric_expr(correct)
    eq = _sympy_numeric_equal(u_expr, c_expr)
    if eq is None:
        return None
    return 1 if eq else 0


# -------------------------
# Weakness diagnosis (internal)
# -------------------------
def _ints_from_text(text: str) -> List[int]:
    return [int(x) for x in re.findall(r"-?\d+", (text or ""))]


def _hint_pack(*levels: str) -> List[str]:
    packed = [l.strip() for l in levels if l and l.strip()]
    # Always provide 3 levels for API simplicity.
    while len(packed) < 3:
        packed.append(packed[-1] if packed else "請先整理題意，逐步計算。")
    return packed[:3]


def _fmt_frac_cn(fr: Fraction) -> str:
    fr = Fraction(fr)
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"{fr.numerator}/{fr.denominator}"


def _fmt_mixed_cn(fr: Fraction) -> str:
    fr = Fraction(fr)
    if fr.denominator == 1:
        return str(fr.numerator)
    sign = -1 if fr < 0 else 1
    n = abs(fr.numerator)
    d = fr.denominator
    whole = n // d
    rem = n % d
    if whole == 0:
        out = f"{rem}/{d}"
    else:
        out = f"{whole} 又 {rem}/{d}"
    return f"-{out}" if sign < 0 else out


def _extract_ratio_reverse_case(qtext: str) -> Optional[Dict[str, Any]]:
    """Parse 『全程的 a/b 用了 c/d 時間，求全程』類題型。"""
    q = str(qtext or "").strip()
    if not q:
        return None

    patterns = [
        r"(?:走了全程的|做了全程的)\s*(\d+)\s*/\s*(\d+)(?:\s*時|\s*路程)?[^。；]*?用(?:了)?\s*(\d+)\s*/\s*(\d+)\s*(小時|分鐘)",
        r"完成了\s*(\d+)\s*/\s*(\d+)\s*路程[^。；]*?用(?:了)?\s*(\d+)\s*/\s*(\d+)\s*(小時|分鐘)",
    ]
    m = None
    for pat in patterns:
        m = re.search(pat, q)
        if m:
            break
    if not m:
        return None

    a = int(m.group(1))
    b = int(m.group(2))
    c = int(m.group(3))
    d = int(m.group(4))
    unit = str(m.group(5) or "小時")
    if b == 0 or d == 0:
        return None

    frac_part = Fraction(a, b)
    used_time = Fraction(c, d)
    if frac_part == 0:
        return None
    total_time = used_time / frac_part
    return {
        "a": a,
        "b": b,
        "c": c,
        "d": d,
        "unit": unit,
        "frac_part": frac_part,
        "used_time": used_time,
        "total_time": total_time,
    }


def build_ratio_reverse_hint_ladder(qobj: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """7-step structured hint ladder for 比例反推（已走分率/已用時間→全程）."""
    parsed = _extract_ratio_reverse_case(str(qobj.get("question") or ""))
    if not parsed:
        return None

    a, b = parsed["a"], parsed["b"]
    c, d = parsed["c"], parsed["d"]
    unit = parsed["unit"]
    frac_part = parsed["frac_part"]
    total_time = parsed["total_time"]
    reciprocal = Fraction(b, a)
    verify = total_time * frac_part

    return [
        {
            "title": "Step 1｜抓未知數",
            "prompt": "先把全程時間設成 T，題目問的就是 T。",
            "expected_answer": "T",
            "explanation": "全程未知，所以用 T 表示。",
            "formula": "全程時間 = T",
        },
        {
            "title": "Step 2｜翻譯語句",
            "prompt": f"『全程的 {a}/{b}』就是 T×{a}/{b}，這裡要用乘法。",
            "expected_answer": "乘",
            "explanation": "某個量的幾分之幾，就是乘法。",
            "formula": f"T × {a}/{b}",
        },
        {
            "title": "Step 3｜列式",
            "prompt": f"把已知時間 {c}/{d}{unit} 放右邊，完成：T×{a}/{b}={c}/{d}。",
            "expected_answer": f"T×{a}/{b}={c}/{d}",
            "explanation": "已走部分對應已知時間。",
            "formula": f"T × {a}/{b} = {c}/{d}",
        },
        {
            "title": "Step 4｜倒回去算",
            "prompt": f"T 乘 {a}/{b} 才會變 {c}/{d}，要倒回去算 T，就用 {c}/{d} ÷ {a}/{b}。",
            "expected_answer": f"T=({c}/{d})÷({a}/{b})",
            "explanation": "除以分數，等於乘它的倒數。",
            "formula": f"T = ({c}/{d}) ÷ ({a}/{b})",
        },
        {
            "title": "Step 5｜找倒數",
            "prompt": f"{a}/{b} 的倒數是什麼？",
            "expected_answer": _fmt_frac_cn(reciprocal),
            "explanation": "倒數就是分子分母交換。",
            "formula": f"{a}/{b} 的倒數 = {b}/{a}",
        },
        {
            "title": "Step 6｜計算",
            "prompt": f"T = {c}/{d} × {b}/{a}，算出答案並約分。",
            "expected_answer": _fmt_frac_cn(total_time),
            "explanation": f"T = {_fmt_frac_cn(total_time)}{unit}，也可寫成 {_fmt_mixed_cn(total_time)}{unit}。",
            "formula": f"T = {c}/{d} × {b}/{a} = {_fmt_frac_cn(total_time)} = {_fmt_mixed_cn(total_time)}",
        },
        {
            "title": "Step 7｜驗算（必做）",
            "prompt": f"把 T 代回：{_fmt_frac_cn(total_time)} × {a}/{b} 是否等於 {c}/{d}？",
            "expected_answer": f"{_fmt_frac_cn(verify)}={c}/{d}",
            "explanation": "左右相等，表示反推正確。",
            "formula": f"驗算：{_fmt_frac_cn(total_time)} × {a}/{b} = {_fmt_frac_cn(verify)} = {c}/{d}",
        },
    ]


def _drill(topic_key: str, count: int, note: str = "") -> Dict[str, Any]:
    name = GENERATORS.get(topic_key, (topic_key, None))[0]
    return {"topic_key": topic_key, "topic_name": name, "count": int(count), "note": note}


def _get_approved_hint_override(qobj: Dict[str, Any]) -> Optional[Dict[str, str]]:
    try:
        template_id = str(qobj.get("template_id") or qobj.get("topic_key") or "").strip()
    except Exception:
        template_id = ""
    if not template_id:
        return None

    entry = _HINT_OVERRIDES.get(template_id)
    if not isinstance(entry, dict) or not entry.get("approved"):
        return None

    l1 = str(entry.get("level1") or "").strip()
    l2 = str(entry.get("level2") or "").strip()
    l3 = str(entry.get("level3") or "").strip()
    if not (l1 and l2 and l3):
        return None

    # Safety: avoid revealing the exact final answer string in Hint1.
    ans = str(qobj.get("answer") or "").strip()
    if ans and ans in l1:
        return None

    return {"level1": l1, "level2": l2, "level3": l3}


def get_question_hints(qobj: Dict[str, Any]) -> Dict[str, str]:
    """Generate 3-level hint strings WITHOUT revealing the final answer."""
    override = _get_approved_hint_override(qobj)
    if override:
        return override

    topic = str(qobj.get("topic") or "")
    qtext = str(qobj.get("question") or "")
    steps = qobj.get("steps")

    ratio_ladder = build_ratio_reverse_hint_ladder(qobj)
    if ratio_ladder:
        return {
            "level1": str(ratio_ladder[0].get("prompt") or "先把全程時間設成 T。"),
            "level2": str(ratio_ladder[2].get("formula") or "T × a/b = c/d"),
            "level3": str(ratio_ladder[6].get("formula") or "把算出的 T 代回去驗算。"),
        }

    def _fraction_guidance() -> Optional[Dict[str, str]]:
        # 詳細分數引導（小學五年級）
        if "分數" not in topic and not re.search(r"\d+\s*/\s*\d+", qtext):
            return None

        # 通分
        if "通分" in topic or "依序輸入：公分母" in qtext:
            h = _hint_pack(
                "先圈出每個分數的分母，這題的第一步是找到共同分母。",
                "用倍數表或質因數分解求 LCM(分母1, 分母2)。",
                "把每個分數放大到 LCM：分母乘幾倍，分子也乘幾倍。",
            )
            return {"level1": h[0], "level2": h[1], "level3": h[2]}

        # 約分
        if "約分" in topic or "約分到最簡" in qtext:
            h = _hint_pack(
                "先找分子與分母的最大公因數(GCD)。",
                "分子、分母同時除以同一個 GCD。",
                "檢查是否還能再同時被 2, 3, 5 整除，直到最簡。",
            )
            return {"level1": h[0], "level2": h[1], "level3": h[2]}

        # 帶分數
        if "帶分數" in topic or re.search(r"\d+\s+\d+\s*/\s*\d+", qtext):
            h = _hint_pack(
                "先把帶分數轉成假分數：整數×分母 + 分子。",
                "再依題目做通分或運算，分母不同一定要先通分。",
                "最後約分，必要時再換回帶分數。",
            )
            return {"level1": h[0], "level2": h[1], "level3": h[2]}

        # 分數乘除
        if re.search(r"\d+\s*/\s*\d+\s*[×x\*]\s*\d+\s*/\s*\d+", qtext):
            h = _hint_pack(
                "分數相乘：分子相乘、分母相乘。",
                "可先約分再乘，數字會變小更好算。",
                "算完再約分到最簡。",
            )
            return {"level1": h[0], "level2": h[1], "level3": h[2]}

        if re.search(r"\d+\s*/\s*\d+\s*[÷]\s*\d+\s*/\s*\d+", qtext):
            h = _hint_pack(
                "分數相除：除以一個分數等於乘上它的倒數。",
                "把後面的分數顛倒(互換分子分母)後做乘法。",
                "算完約分到最簡。",
            )
            return {"level1": h[0], "level2": h[1], "level3": h[2]}

        # 分數加減/連續
        if "分數加減" in topic or "分數連續加減" in topic or re.search(r"\d+\s*/\s*\d+\s*[\+\-]", qtext):
            h = _hint_pack(
                "先判斷是加或減；分母不同一定要先通分。",
                "用 LCM 當共同分母，把每個分數換成同分母後再加減分子。",
                "算完約分，若是假分數可換回帶分數。",
            )
            return {"level1": h[0], "level2": h[1], "level3": h[2]}

        return None

    # If explicit steps are provided (New Detailed Guidance System)
    if isinstance(steps, list) and len(steps) >= 1:
        # Use steps as hints logic
        # Hint 1: First step
        h1 = steps[0]
        # Hint 2: Second step if available
        h2 = steps[1] if len(steps) > 1 else steps[0]
        # Hint 3: Third step or "almost done"
        if len(steps) > 2:
            h3 = steps[2]
        else:
            h3 = "請完成計算檢查答案。"

        return {
            "level1": h1,
            "level2": h2,
            "level3": h3
        }

    # 詳細分數引導優先
    detailed_fraction_hints = _fraction_guidance()
    if detailed_fraction_hints:
        return detailed_fraction_hints

    # 通分
    if "通分" in topic or "依序輸入：公分母" in qtext:
        h = _hint_pack(
            "先找兩個分母的最小公倍數(LCM)，當作公分母。",
            "把每個分數的分母乘到 LCM；分子也要乘同樣倍數。",
            "檢查：新分母都一樣(=LCM)，再確認新分子是否同步乘上倍數。",
        )
        return {"level1": h[0], "level2": h[1], "level3": h[2]}

    # 約分
    if "約分" in topic or "約分到最簡" in qtext:
        h = _hint_pack(
            "找分子與分母的最大公因數(GCD)。",
            "分子、分母同時除以同一個 GCD。",
            "做到最簡：分子與分母不能再同時被 2,3,5... 整除。",
        )
        return {"level1": h[0], "level2": h[1], "level3": h[2]}

    # 分數加減/連續
    if "分數加減" in topic or "分數連續加減" in topic or re.search(r"\d+/\d+\s*[\+\-]", qtext):
        h = _hint_pack(
            "分母不同不能直接加減分子：先通分。",
            "用 LCM 當共同分母；把每個分數換成同分母後再做分子加減。",
            "最後記得約分到最簡(能約就約)。",
        )
        return {"level1": h[0], "level2": h[1], "level3": h[2]}

    # Generic fallback
    h = _hint_pack(
        "先圈出題目中的分數與總量（或剩下量）。",
        "把文字轉成算式：『幾分之幾』通常用乘法；『平均分』通常用除法。",
        "算完記得約分到最簡，必要時再換成帶分數。",
    )
    return {"level1": h[0], "level2": h[1], "level3": h[2]}


def get_next_step_hint(qobj: Dict[str, Any], student_state: str = "", level: int = 1) -> Dict[str, Any]:
    """Generate a next-step hint based on student's current state.

    Safety: do NOT reveal the final numeric answer.
    Returns: {hint: str, level: int, mode: str}
    """

    try:
        level_int = int(level)
    except Exception:
        level_int = 1
    if level_int not in (1, 2, 3):
        level_int = 1

    topic = str(qobj.get("topic") or "")
    qtext = str(qobj.get("question") or "")
    state = str(student_state or "").strip()
    s = state.lower()

    # Very lightweight stage inference (0=read,1=setup,2=compute,3=simplify)
    stage = 0
    if state:
        stage = 1
        if any(k in s for k in ("=", "×", "*", "乘", "÷", "除")):
            stage = 2
        if any(k in s for k in ("約分", "最簡", "帶分數", "化簡", "simpl")):
            stage = 3

    def _sanitize_hint_text(text: str) -> str:
        """Post-process hint to reduce answer leakage and improve readability.

        Safety: must not contain explicit final answer patterns.
        """
        t = str(text or "").strip()
        if not t:
            return ""

        # Remove explicit answer reveal wording.
        t = t.replace("答案", "")
        t = t.replace("所以答案", "所以")
        t = t.replace("因此答案", "因此")

        # Replace direct numeric results after '=' with a placeholder.
        # Examples to catch: 'x = -1', '= 5/6', '= 12'
        t = re.sub(r"=\s*-?\d+\s*(?:/\s*\d+)?\b", "=（算出結果）", t)

        # Avoid overly long hints.
        if len(t) > 240:
            t = t[:240].rstrip() + "…"

        # Encourage structure if it's a single long line.
        if "\n" not in t and len(t) > 80 and "。" in t:
            parts = [p.strip() for p in t.split("。") if p.strip()]
            if len(parts) >= 2:
                t = "。\n".join(parts[:3]) + "。"

        return t.strip()

    def _pack_and_sanitize(level1: str, level2: str, level3: str) -> str:
        return _sanitize_hint_text(_hint_pack(level1, level2, level3)[level_int - 1])

    topic_s = topic.strip()
    q_s = qtext.strip()
    topic_l = topic_s.lower()
    q_l = q_s.lower()

    def _is_fraction_topic() -> bool:
        return ("分數" in topic_s) or bool(re.search(r"\d+\s*/\s*\d+", q_s))

    def _is_decimal_topic() -> bool:
        return ("小數" in topic_s) or bool(re.search(r"\d+\.\d+", q_s))

    def _is_equation_topic() -> bool:
        return ("方程" in topic_s) or bool(re.search(r"\bx\b", q_l)) or ("求 x" in q_s)

    def _is_geometry_topic() -> bool:
        return any(k in topic_s for k in ("體積", "表面積", "面積", "長方體", "正方體"))

    def _is_order_ops_topic() -> bool:
        return ("四則" in topic_s) or bool(re.search(r"[\(\)\+\-\*/]", q_s) and ("括號" in topic_s or "(" in q_s or ")" in q_s))

    # 0) Broad topic coverage first (so non-fraction topics don't fall into fraction word defaults)
    if _is_equation_topic():
        hint = _pack_and_sanitize(
            "先把含 x 的項留在同一邊、常數移到另一邊（移項要改符號）。",
            "下一步：同加/同減把常數移走，再同乘/同除把 x 的係數消掉。",
            "檢查：把你算到的 x 代回原式，左右兩邊要相等；最常錯是移項符號。",
        )
        # If student already wrote an equation, guide the next algebraic action.
        if stage >= 2:
            hint = _pack_and_sanitize(
                "你已經列出等式了，下一步是先消掉常數項（移項要改符號）。",
                "再把係數消掉：兩邊同除以 x 的係數。",
                "最後代回檢查，特別看負號與括號。",
            )
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    if _is_geometry_topic():
        # Distinguish volume vs surface area by keywords.
        if "體積" in topic_s or "立方" in q_s:
            hint = _pack_and_sanitize(
                "先確認題目要的是『體積』：長方體用 長×寬×高；正方體用 邊長³。",
                "把數值代進公式，先算乘法，再寫上正確單位（立方公分/立方公尺）。",
                "檢查：單位是否是『立方』；不要把體積和表面積公式混用。",
            )
        else:
            hint = _pack_and_sanitize(
                "先確認題目要的是『表面積』：正方體用 6×邊長²；長方體用 2×(長寬+長高+寬高)。",
                "先算每一個面（或每一組乘積），再加總、最後乘 2（長方體）。",
                "檢查：單位要是『平方』；最常錯是漏乘 2 或少算一組面。",
            )
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    if _is_decimal_topic():
        hint = _pack_and_sanitize(
            "先對齊小數點再運算：加減要直式對齊小數點。",
            "下一步：乘法先忽略小數點計算，最後再把小數位數補回去。",
            "下一步：除法若除數是小數，可先同乘 10/100… 變成整數再除，最後檢查小數點位置。",
        )
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    if _is_order_ops_topic():
        hint = _pack_and_sanitize(
            "先找括號：有括號先算括號內。",
            "下一步：再算乘除、最後加減（同級運算由左到右）。",
            "檢查：負號與括號最容易錯，建議每一步算完就把中間結果寫出來。",
        )
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    # Detect question kind (focused on G5 fraction applications)
    kind = "generic_fraction_word" if _is_fraction_topic() else "generic"
    if re.search(r"平均.*(杯|份|段|人|盒|袋|盤)", qtext):
        kind = "average_division"
    elif _extract_ratio_reverse_case(qtext):
        kind = "ratio_reverse_total_time"
    elif re.search(r"(原來|原價|全程(長|需要)|原本)", qtext) and re.search(r"(還剩|折後|剩)", qtext):
        kind = "reverse_fraction"
    elif re.search(r"剩下的又", qtext) or (
        re.search(r"剩下的", qtext)
        and re.search(r"(又|再)", qtext)
        and re.search(r"\d+\s*/\s*\d+", qtext)
    ):
        kind = "remain_then_fraction"
    elif re.search(r"(先|又).*(吃|用|看|走).*(先|又)", qtext):
        kind = "two_steps_used"
    elif re.search(r"其中的", qtext) and re.search(r"占", qtext):
        kind = "fraction_of_fraction"
    elif re.search(r"(倒出|用了|吃了|看了).*(剩下多少|還剩|剩多少)", qtext):
        kind = "remaining_after_fraction"
    elif re.search(r"(倒出|走了|用掉|占).*(\d+\s*/\s*\d+)", qtext):
        kind = "fraction_of_quantity"

    # If the student already mentions an operation, bias toward action-oriented guidance.
    state_has_fraction = bool(re.search(r"\d+\s*/\s*\d+", state))
    state_has_setup_words = any(k in s for k in ("先", "所以", "因為", "列式", "算式"))

    def _base(level1: str, level2: str, level3: str) -> str:
        return _hint_pack(level1, level2, level3)[level_int - 1]

    if kind == "ratio_reverse_total_time":
        ladder = build_ratio_reverse_hint_ladder(qobj) or []
        if ladder:
            idx = 0
            if level_int == 2:
                idx = 2
            elif level_int == 3:
                idx = 5
            if stage >= 2:
                idx = min(idx + 1, len(ladder) - 1)
            step_obj = ladder[idx]
            hint = str(step_obj.get("prompt") or "先列式再倒回去算。")
            return {
                "hint": _sanitize_hint_text(hint),
                "level": level_int,
                "mode": "offline_rule",
                "hint_ladder": ladder,
                "current_step": step_obj,
            }
        hint = _pack_and_sanitize(
            "先把全程時間設成 T，再找出已知是『全程的幾分之幾』。",
            "列式：T × (已走分率) = 已用時間。",
            "倒回去算：T = 已用時間 ÷ 已走分率；除以分數等於乘倒數，最後記得驗算。",
        )
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    # Student-aware next step guidance per kind
    if kind == "average_division":
        hint = _sanitize_hint_text(_base(
            "這是『平均分』：把總量（可能是分數）÷ 平均分成的份數。",
            "先把題目圈出：總量是什麼？要分成幾份？再列式：總量 ÷ 份數。",
            "除以整數可寫成乘倒數：總量 × (1/份數)，算完再約分到最簡。",
        ))
        if stage >= 2:
            hint = _sanitize_hint_text(_base(
                "你已列式了，下一步是把除法做完並寫成最簡分數。",
                "檢查是否能先約分（分子分母同除公因數）再算，會更快。",
                "最後確認單位（每杯/每份/每段）與題目一致。",
            ))
        elif state_has_fraction and state_has_setup_words:
            hint = _sanitize_hint_text(_base(
                "你已經開始列式了，下一步把『平均』寫成 ÷ 份數，避免用加減。",
                "把『÷ 份數』改寫成『× 1/份數』會更好算。",
                "最後只化簡到最簡分數，不要急著換帶分數（除非題目要）。",
            ))
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    if kind == "reverse_fraction":
        hint = _sanitize_hint_text(_base(
            "題目給的是『剩下（或折後）是多少』，要反推『原來是多少』。",
            "先求『剩下的比例』：通常是 1 - 用掉比例（或 1 - 折扣比例）。",
            "原來的量 = 已知剩下量 ÷ 剩下比例；列式後再計算並化簡。",
        ))
        if stage >= 2:
            hint = _sanitize_hint_text(_base(
                "下一步：把『÷ 分數』改成『× 倒數』再算。",
                "計算後若是假分數可換回帶分數（看題目要不要）。",
                "最後做合理性檢查：原來的量要比剩下的量大。",
            ))
        elif state_has_fraction and ("1" in s and "-" in s):
            hint = _sanitize_hint_text(_base(
                "你在做『1 - 分數』很好，下一步把它當成『剩下比例』，不要直接去乘。",
                "接著用：原來 = 已知剩下 ÷ 剩下比例（用除法反推）。",
                "把除法改成乘倒數後，再約分到最簡。",
            ))
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    if kind == "remain_then_fraction":
        hint = _sanitize_hint_text(_base(
            "這題是『先用掉一些 → 剩下一些 → 再用掉剩下的一部分』，要分兩段想。",
            "第一段（先剩下）：列式：第一次剩下比例 = 1 − 第一次用掉分數（把 1 通分成同分母再做減法）。",
            "第二段（再用掉／最後剩下）：列式：第二次用掉 = 第一次剩下 × 第二次用掉分數；最後剩下 = 第一次剩下 − 第二次用掉（或 第一次剩下 × (1 − 第二次用掉分數)）。",
        ))
        if stage >= 2:
            hint = _sanitize_hint_text(_base(
                "你已經把第一段或第二段列式了，下一步是照順序算：先算第一次剩下，再算第二次變化。",
                "過程中不要急著算到最後，先把『每一步的量』寫清楚（第一次剩下量、第二次用掉量、最後剩下量）。",
                "最後只要寫出『剩多少（頁/公升/公尺）』，並把分數約分。",
            ))
        elif state_has_setup_words and ("剩" in s or "1" in s):
            hint = _sanitize_hint_text(_base(
                "先把『第一次剩下』寫成一個量（或比例），用它當作第二次的『基準』。",
                "第二次如果是『剩下的又看了/又用掉』，就是用乘法取其中一部分。",
                "最後做減法得到『最後剩下』，不要把第二次看成加法。",
            ))
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    if kind == "two_steps_used":
        hint = _sanitize_hint_text(_base(
            "這題是『同一個整體』連續兩次用掉（先…又…），先把兩次用掉分開看。",
            "列式（不急著算）：總用掉 = 第一次用掉分數 + 第二次用掉分數（先通分再相加）。",
            "看題目問什麼：若問『剩下』→ 剩下 = 1 − 總用掉；若問『用掉』→ 答案就是總用掉（都要約分）。",
        ))
        if stage >= 2:
            hint = _sanitize_hint_text(_base(
                "你已列式了，下一步是先通分再相加，算出『總用掉』並約分。",
                "若題目問『剩下』，再做 1 − 總用掉（把 1 通分成同分母再減）。",
                "最後確認答案是『剩下幾分之幾』或『用掉幾分之幾』，不要寫反。",
            ))
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    if kind == "fraction_of_fraction":
        hint = _base(
            "看到『其中的…』或『…的…』，通常是『分數的分數』：用乘法。",
            "先找：第一個分數是占全體多少；第二個分數是在那一部分裡又占多少。",
            "占全體 = 第一個分數 × 第二個分數；算完約分到最簡。",
        )
        if stage >= 2:
            hint = _base(
                "下一步：把兩個分數相乘，能先約分就先約分。",
                "相乘後把結果化為最簡分數。",
                "最後確認題目問的是『占全體幾分之幾』而不是其中一部分。",
            )
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    if kind == "remaining_after_fraction":
        hint = _base(
            "題目問『剩下』，先求剩下的比例：1 - 用掉的分數。",
            "再用 總量 × 剩下比例，得到剩下的量（不要先算出用掉多少也可以）。",
            "最後把結果約分到最簡，並確認單位。",
        )
        if stage >= 2:
            hint = _base(
                "你已經寫出 1 - 分數 或乘法式了，下一步是完成乘法並約分。",
                "若看到帶分數，先轉成假分數再算會更穩。",
                "算完做合理性檢查：剩下的量要小於總量。",
            )
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    if kind == "fraction_of_quantity":
        hint = _base(
            "題目是『某個量的幾分之幾』：用 乘法（總量 × 分數）。",
            "先圈出總量與分數，再列式：總量 × (分子/分母)。",
            "可先做約分（總量和分母先除公因數）再乘，最後化為最簡。",
        )
        if stage >= 2:
            hint = _base(
                "下一步：把乘法做完，並把分數約分到最簡。",
                "檢查是否漏寫單位（公升/公里/公斤/人數）。",
                "最後確認你算的是『倒出/走了/用掉』而不是『剩下』。",
            )
        return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    # Generic fraction word problem guidance
    hint = _base(
        "先圈出題目中的分數與總量（或剩下量），再決定要用乘法或除法。",
        "把文字翻成算式：『幾分之幾的…』→ 乘法；『剩下』→ 1-分數；『原來』→ 用除法反推。",
        "算完務必約分到最簡，必要時再換回帶分數並檢查合理性。",
    )
    if stage >= 2:
        hint = _base(
            "你已列式了，下一步是完成計算並約分。",
            "計算前先找可約分的地方（分子分母同除公因數）。",
            "最後做合理性檢查：答案的大小要符合題意（剩下 < 總量；原來 > 剩下）。",
        )
    return {"hint": hint, "level": level_int, "mode": "offline_rule"}

    # 帶分數
    if "帶分數" in topic or re.search(r"\d+\s+\d+/\d+", qtext):
        h = _hint_pack(
            "先把帶分數轉成假分數再運算。",
            "假分數：整數×分母 + 分子，分母不變。",
            "算完可再換回帶分數(整數 + 真分數)，並約分。",
        )
        return {"level1": h[0], "level2": h[1], "level3": h[2]}

    # 四則運算(順序)
    if "括號" in qtext or "×" in qtext or "÷" in qtext:
        h = _hint_pack(
            "口訣：括號 → 乘除 → 加減。",
            "先把括號算完，再做乘除，最後由左到右做加減。",
            "每一步寫出中間結果，避免跳步算錯。",
        )
        return {"level1": h[0], "level2": h[1], "level3": h[2]}

    h = _hint_pack("先整理題意，逐步計算。", "寫出中間步驟再檢查。", "若不確定，先把題目拆成小步驟。")
    return {"level1": h[0], "level2": h[1], "level3": h[2]}


def diagnose_attempt(qobj: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
    """Classify common mistake patterns for G5 fractions + order-of-ops.

    Returns: {error_tag, error_detail, hint_plan, drill_reco}
    """
    topic = str(qobj.get("topic") or "")
    qtext = str(qobj.get("question") or "")
    correct = str(qobj.get("correct_answer") or qobj.get("answer") or "").strip()
    user = (user_answer or "").strip()

    # Default drill recos: keep small set.
    base_recos: List[Dict[str, Any]] = []

    # 通分題：答案格式：lcm na1 na2
    if "通分" in topic or "依序輸入：公分母" in qtext:
        c_parts = _ints_from_text(correct)
        u_parts = _ints_from_text(user)
        if len(u_parts) < 3:
            return {
                "error_tag": "FORMAT_INVALID",
                "error_detail": "通分題需要輸入 3 個整數：公分母 新分子1 新分子2。",
                "hint_plan": _hint_pack(
                    "請輸入三個數字，用空格分開：LCM 新分子1 新分子2。",
                    "先求 LCM(分母1, 分母2)。",
                    "用 LCM 通分：分母乘幾倍，分子也乘幾倍。",
                ),
                "drill_reco": [_drill("2", 8, "先把通分練熟")],
            }
        if len(c_parts) >= 3:
            c_lcm, c_na1, c_na2 = c_parts[0], c_parts[1], c_parts[2]
        else:
            c_lcm, c_na1, c_na2 = 0, 0, 0

        u_lcm, u_na1, u_na2 = u_parts[0], u_parts[1], u_parts[2]
        if u_lcm != c_lcm:
            return {
                "error_tag": "LCM_WRONG",
                "error_detail": f"公分母(LCM) 應為 {c_lcm}，你填的是 {u_lcm}。",
                "hint_plan": _hint_pack(
                    "先只做一件事：找兩個分母的 LCM。",
                    "列倍數法：寫出兩個分母的倍數，找到第一個相同的。",
                    "用 gcd：LCM(a,b) = a*b/gcd(a,b)。",
                ),
                "drill_reco": [_drill("2", 10, "加強 LCM/通分")],
            }
        if (u_na1, u_na2) != (c_na1, c_na2):
            return {
                "error_tag": "COMMON_DENOM_WRONG",
                "error_detail": "公分母對了，但至少一個新分子不對（可能倍數沒有同步乘到分子）。",
                "hint_plan": _hint_pack(
                    "先算倍數：LCM ÷ 原分母 = 要乘的倍數。",
                    "新分子 = 原分子 × 倍數（兩個分數都要做）。",
                    "檢查：換成新分數後，分母都等於 LCM。",
                ),
                "drill_reco": [_drill("2", 8, "通分的倍數要一致")],
            }

        return {
            "error_tag": "OTHER",
            "error_detail": "與典型通分錯誤模式不匹配。",
            "hint_plan": _hint_pack("再檢查一次倍數是否正確。", "把每一步寫出來。", "確認新分母都等於 LCM。"),
            "drill_reco": [_drill("2", 5, "再練幾題通分")],
        }

    # 約分題：答案格式：num den
    if "約分" in topic or "約分到最簡" in qtext:
        c_parts = _ints_from_text(correct)
        u_parts = _ints_from_text(user)
        # Extract original from question: first fraction in text.
        m = re.search(r"(\d+)\s*/\s*(\d+)", qtext)
        orig = Fraction(int(m.group(1)), int(m.group(2))) if m else None

        if len(u_parts) < 2:
            return {
                "error_tag": "FORMAT_INVALID",
                "error_detail": "約分題需要輸入 2 個整數：分子 分母。",
                "hint_plan": _hint_pack(
                    "請輸入兩個數字，用空格分開：分子 分母。",
                    "找分子分母的 GCD。",
                    "同除以 GCD，直到最簡。",
                ),
                "drill_reco": [_drill("3", 10, "先把約分練熟")],
            }

        try:
            u_frac = Fraction(int(u_parts[0]), int(u_parts[1]))
        except Exception:
            u_frac = None

        # If numerically correct but not simplest, tag REDUCTION_MISSED.
        if orig is not None and u_frac is not None:
            if u_frac == orig and math.gcd(int(u_parts[0]), int(u_parts[1])) != 1:
                return {
                    "error_tag": "REDUCTION_MISSED",
                    "error_detail": "分數等值，但還沒有約到最簡。",
                    "hint_plan": _hint_pack(
                        "還可以再約：找出分子分母共同因數。",
                        "用 GCD 直接一次約到最簡。",
                        "最簡檢查：gcd(分子,分母)=1。",
                    ),
                    "drill_reco": [_drill("3", 12, "約到最簡")],
                }

        # If user used a divisor but applied incorrectly.
        if m and len(u_parts) >= 2:
            on, od = int(m.group(1)), int(m.group(2))
            un, ud = int(u_parts[0]), int(u_parts[1])
            if un != 0 and ud != 0:
                if on % un == 0:
                    d = on // un
                    if d > 1 and od % d == 0 and ud != od // d:
                        return {
                            "error_tag": "COMMON_DENOM_WRONG",
                            "error_detail": "你似乎有除以同一個數，但分母沒有同步除對。",
                            "hint_plan": _hint_pack(
                                "約分要『分子分母同除以同一個數』。",
                                "先求 GCD，再同除一次就到最簡。",
                                "算完用 gcd(分子,分母)=1 做檢查。",
                            ),
                            "drill_reco": [_drill("3", 10, "分子分母要同步除")],
                        }

        return {
            "error_tag": "OTHER",
            "error_detail": "與典型約分錯誤模式不匹配。",
            "hint_plan": _hint_pack("再找一次 GCD。", "分子分母同除。", "確認已最簡。"),
            "drill_reco": [_drill("3", 6, "再練幾題約分")],
        }

    # 分數加減（含連續）與帶分數：用 Fraction 比較 + 典型錯誤模式
    if ("分數加減" in topic) or ("分數連續加減" in topic) or ("帶分數" in topic) or re.search(r"\d+/\d+\s*[\+\-]", qtext):
        u_frac = parse_answer(user)
        c_frac = parse_answer(correct)
        if u_frac is None:
            return {
                "error_tag": "FORMAT_INVALID",
                "error_detail": "答案格式無法解析（可用：整數、a/b、或帶分數 '1 1/2'）。",
                "hint_plan": _hint_pack(
                    "先確認你輸入的是整數或分數，例如 5/6。",
                    "分母不同先通分，不能直接分子相加減。",
                    "算完記得約分到最簡。",
                ),
                "drill_reco": [_drill("4", 8, "分數加減格式與通分")],
            }
        if c_frac is None:
            return {
                "error_tag": "OTHER",
                "error_detail": "系統題目答案解析失敗（請回報）。",
                "hint_plan": _hint_pack("先跳過這題。", "再出一題試試。", "若持續發生請回報。"),
                "drill_reco": [],
            }

        # Try to parse two-term add/sub from question for pattern checks.
        m2 = re.search(r"(\d+)\s*/\s*(\d+)\s*([\+\-])\s*(\d+)\s*/\s*(\d+)", qtext)
        if m2:
            a1, b1, op, a2, b2 = int(m2.group(1)), int(m2.group(2)), m2.group(3), int(m2.group(4)), int(m2.group(5))
            sgn = 1 if op == "+" else -1
            naive_keep_b1 = Fraction(a1 + sgn * a2, b1)
            naive_keep_b2 = Fraction(a1 + sgn * a2, b2)
            naive_add_den = Fraction(a1 + sgn * a2, b1 + b2)
            naive_mul_den = Fraction(a1 + sgn * a2, b1 * b2)
            if u_frac in (naive_keep_b1, naive_keep_b2, naive_add_den, naive_mul_den):
                return {
                    "error_tag": "COMMON_DENOM_WRONG",
                    "error_detail": "看起來你直接在不同分母下做分子加減（或分母處理不正確）。",
                    "hint_plan": _hint_pack(
                        "分母不同不能直接算分子：先通分。",
                        "用 LCM 當共同分母，再做分子加減。",
                        "最後再約分到最簡。",
                    ),
                    "drill_reco": [_drill("2", 6, "先練通分"), _drill("4", 8, "再練分數加減")],
                }
            if u_frac == -c_frac:
                return {
                    "error_tag": "SIGN_OR_ORDER_WRONG",
                    "error_detail": "結果正負號可能顛倒（加減方向或換位錯）。",
                    "hint_plan": _hint_pack(
                        "先判斷答案應該是正還是負/大小。",
                        "減法通常要用『較大的減較小的』(本題設計為正數)。",
                        "通分後再做分子相減，留意符號。",
                    ),
                    "drill_reco": [_drill("4", 8, "加減方向與比較")],
                }
            # Numerator slip when denominator seems right
            if u_frac.denominator == c_frac.denominator and u_frac != c_frac:
                return {
                    "error_tag": "NUMERATOR_OP_WRONG",
                    "error_detail": "分母看起來對，但分子加減可能算錯。",
                    "hint_plan": _hint_pack(
                        "通分後只做分子加減，分母保持不變。",
                        "把通分後的兩個新分子寫出來再運算。",
                        "算完再檢查是否需要約分。",
                    ),
                    "drill_reco": [_drill("4", 10, "分子加減熟練")],
                }

        return {
            "error_tag": "OTHER",
            "error_detail": "與任何典型錯誤模式不匹配。",
            "hint_plan": _hint_pack(
                "先把每一項通分成同分母。",
                "再做分子加減，最後約分。",
                "把中間步驟寫出來通常就能找到錯在哪。",
            ),
            "drill_reco": [_drill("2", 5, "通分"), _drill("4", 6, "分數加減")],
        }

    # 四則運算(順序)：偵測典型忽略乘除/括號
    if "(" in qtext and ("×" in qtext or "÷" in qtext):
        u_val = parse_answer(user)
        c_val = parse_answer(correct)
        if u_val is None:
            return {
                "error_tag": "FORMAT_INVALID",
                "error_detail": "答案格式無法解析（請輸入整數）。",
                "hint_plan": _hint_pack("先算括號。", "再算乘除。", "最後算加減(由左到右)。"),
                "drill_reco": [_drill("1", 8, "運算順序")],
            }
        if c_val is None:
            return {
                "error_tag": "OTHER",
                "error_detail": "系統答案解析失敗。",
                "hint_plan": _hint_pack("先跳過。", "再出一題。", "若持續請回報。"),
                "drill_reco": [],
            }

        # Pattern: (a ? b) op1 (x × y) op2 e  OR (x ÷ y)
        m3 = re.search(r"\((\d+)\s*([\+\-])\s*(\d+)\)\s*([\+\-])\s*(\d+)\s*[×\*]\s*(\d+)\s*([\+\-])\s*(\d+)", qtext)
        if m3:
            a, op_p, b, op1, x, y, op2, e = int(m3.group(1)), m3.group(2), int(m3.group(3)), m3.group(4), int(m3.group(5)), int(m3.group(6)), m3.group(7), int(m3.group(8))
            par = a + b if op_p == "+" else a - b
            mul = x * y
            # Wrong: left-to-right ignoring × priority: ((par op1 x) × y) op2 e
            tmp = (par + x) if op1 == "+" else (par - x)
            wrong_lr = (tmp * y)
            wrong_lr = (wrong_lr + e) if op2 == "+" else (wrong_lr - e)
            if u_val == wrong_lr:
                return {
                    "error_tag": "ORDER_OF_OPS_WRONG",
                    "error_detail": "看起來你把乘法當成跟加減同級，直接由左到右算了。",
                    "hint_plan": _hint_pack(
                        "先括號，再乘除，最後加減。",
                        "括號算完後，下一步要先算 ×/÷。",
                        "每一步把算式『改寫』成新的一行。",
                    ),
                    "drill_reco": [_drill("1", 10, "運算順序")],
                }

            # Wrong: treat as (par op1 mul) then op2 e but par computed wrong? Hard; skip.

        # Division variant
        m4 = re.search(r"\((\d+)\s*([\+\-])\s*(\d+)\)\s*([\+\-])\s*(\d+)\s*[÷\/]\s*(\d+)\s*([\+\-])\s*(\d+)", qtext)
        if m4:
            a, op_p, b, op1, x, y, op2, e = int(m4.group(1)), m4.group(2), int(m4.group(3)), m4.group(4), int(m4.group(5)), int(m4.group(6)), m4.group(7), int(m4.group(8))
            par = a + b if op_p == "+" else a - b
            # Wrong left-to-right: ((par op1 x) ÷ y) op2 e
            tmp = (par + x) if op1 == "+" else (par - x)
            try:
                wrong_lr = tmp / y
            except Exception:
                wrong_lr = None
            if wrong_lr is not None:
                wrong_lr2 = (wrong_lr + e) if op2 == "+" else (wrong_lr - e)
                if u_val == Fraction(wrong_lr2).limit_denominator():
                    return {
                        "error_tag": "ORDER_OF_OPS_WRONG",
                        "error_detail": "看起來你忽略了乘除優先，直接由左到右算了。",
                        "hint_plan": _hint_pack(
                            "先括號，再乘除，最後加減。",
                            "除法也屬於乘除，要先處理。",
                            "把每一步中間結果寫出來再繼續。",
                        ),
                        "drill_reco": [_drill("1", 10, "運算順序")],
                    }

        return {
            "error_tag": "OTHER",
            "error_detail": "與典型運算順序錯誤模式不匹配。",
            "hint_plan": _hint_pack("先括號。", "再乘除。", "最後加減。"),
            "drill_reco": [_drill("1", 6, "運算順序")],
        }

    # --- ADVANCED HINT INTEGRATION (RAG + Topic Specific) ---
    if "一元一次" in topic or "linear" in topic.lower():
        return {
            "error_tag": "LINEAR_ERR",
            "error_detail": "一元一次方程式解題建議。",
            "hint_plan": _get_rag_enhanced_hints(topic, qtext, [
                "移項法則：把含 x 的項移到一邊，常數移到另一邊（記得變號）。",
                "合併同類項：整理兩邊的算式。",
                "係數化為一：同除以 x 前面的係數。",
            ]),
            "drill_reco": [],
        }

    if "一元二次" in topic or "quadratic" in topic.lower():
        return {
            "error_tag": "QUAD_ERR",
            "error_detail": "一元二次方程式解題建議。",
            "hint_plan": _get_rag_enhanced_hints(topic, qtext, [
                "判斷題型：可因式分解？還是要用公式解？",
                "十字交乘法：試著分解成 (ax+b)(cx+d) = 0。",
                "公式解：x = [-b ± sqrt(b^2 - 4ac)] / 2a。",
            ]),
            "drill_reco": [],
        }

    # RAG Fallback for OTHER
    return {
        "error_tag": "OTHER",
        "error_detail": "與任何典型錯誤模式不匹配。",
        "hint_plan": _get_rag_enhanced_hints(topic, qtext, [
            "先整理題意。",
            "寫出中間步驟。",
            "逐步檢查運算。",
        ]),
        "drill_reco": base_recos,
    }

def _get_rag_enhanced_hints(topic: str, text: str, default_hints: List[str]) -> List[str]:
    """Try to fetch hints from RAG based on topic/text. If fail, use default."""
    try:
        # Lazy import of Retriever to avoid circular deps or init cost if unused
        # Assuming rag_backend.py is in the same folder or path
        try:
            from rag_backend import Retriever
        except ImportError:
            return default_hints

        # We assume Retriever() initialization is relatively cheap or handles its own caching
        # In a real app, this should be a reliable global instance
        retriever = Retriever()
        results = retriever.search(topic + " " + text, topk=1)
        if results:
            rag_text = results[0].get('text', '')
            # Truncate context to avoid overwhelming student
            rag_hint = f"參考觀念：{rag_text[:60]}..."
            # Append as an extra hint
            return default_hints + [rag_hint]
    except Exception:
        pass
    return default_hints

# -------------------------
# Custom solver (solve_custom)
# -------------------------
def solve_custom(question_text: str) -> Tuple[Optional[str], str]:
    """
    支援：
      - 方程式：2*x + 3 = 9   (需要 SymPy)
      - 算式：1/2 + 1/3, 3*(2+5), 0.25+1.2, 12 ÷ 3 (會轉換符號)

    return (answer_str_or_None, explanation_str)
    """
    q = (question_text or "").strip()
    if not q:
        return None, "空題目"

    # Normalize symbols
    clean_q = q.replace("×", "*").replace("÷", "/").replace(",", "")

    # Equation
    if "=" in clean_q:
        if not HAS_SYMPY:
            return None, "未安裝 SymPy，無法自動解方程式（建議：pip install sympy）"
        try:
            lhs_str, rhs_str = clean_q.split("=", 1)
            x = sp.Symbol('x')
            lhs = sp.sympify(lhs_str)
            rhs = sp.sympify(rhs_str)
            sol = sp.solve(sp.Eq(lhs, rhs), x)
            if not sol:
                return None, "無解或無限多解"

            # Convert to Fraction for consistent display
            f_ans = Fraction(sol[0]).limit_denominator()
            ans_str = str(f_ans.numerator) if f_ans.denominator == 1 else f"{f_ans.numerator}/{f_ans.denominator}"
            return ans_str, f"系統自動解題 (SymPy): x = {ans_str}"
        except Exception as e:
            return None, f"方程式解析失敗: {e}"

    # Expression
    try:
        if HAS_SYMPY:
            expr = sp.sympify(clean_q)
            f_ans = Fraction(expr).limit_denominator()
            ans_str = str(f_ans.numerator) if f_ans.denominator == 1 else f"{f_ans.numerator}/{f_ans.denominator}"
            return ans_str, f"系統自動計算 (SymPy): {ans_str}"
        else:
            # Safe-ish eval for arithmetic only
            # Allowed chars: digits, operators, parentheses, dot, slash, whitespace
            if not re.fullmatch(r"[0-9\.\+\-\*\/\(\)\s]+", clean_q):
                return None, "算式包含不允許的字元（僅支援數字與 + - * / ( )）"
            ans = eval(clean_q, {"__builtins__": {}}, {})
            f_ans = Fraction(ans).limit_denominator()
            ans_str = str(f_ans.numerator) if f_ans.denominator == 1 else f"{f_ans.numerator}/{f_ans.denominator}"
            return ans_str, f"系統自動計算 (Fraction): {ans_str}"
    except Exception as e:
        return None, f"無法計算: {e}"


# -------------------------
# Generators
# -------------------------
def gen_order_of_ops_arith():
    op_mul_div = random.choice(["*", "/"])
    if op_mul_div == "*":
        b = random.randint(2, 10)
        c = random.randint(2, 10)
        result_mul_div = b * c
        sub_expr_md = f"{b} × {c}"
    else:
        result_div = random.randint(2, 5)
        c = random.randint(2, 10)
        b = result_div * c
        result_mul_div = result_div
        sub_expr_md = f"{b} ÷ {c}"

    a1 = random.randint(5, 30)
    a2 = random.randint(5, 30)
    op_add_sub_paren = random.choice(["+", "-"])
    if op_add_sub_paren == "+":
        paren_result = a1 + a2
        op_text_paren = "+"
    else:
        if a1 < a2:
            a1, a2 = a2, a1
        paren_result = a1 - a2
        op_text_paren = "-"

    paren_expr = f"({a1} {op_text_paren} {a2})"
    e = random.randint(1, 10)
    op1 = random.choice(["+", "-"])
    op2 = random.choice(["+", "-"])

    question = f"{paren_expr} {op1} {sub_expr_md} {op2} {e} = ?"
    ans = eval(f"({a1} {op_text_paren} {a2}) {op1} ({b} {op_mul_div} {c}) {op2} {e}")

    explanation_steps = [
        "步驟 1: **先算括號**",
        f"   -> {a1} {op_text_paren} {a2} = {paren_result}",
        f"   -> 算式變為: {paren_result} {op1} {sub_expr_md} {op2} {e}",
        "步驟 2: **再算乘除**",
        f"   -> {sub_expr_md} = {result_mul_div}",
        f"   -> 算式變為: {paren_result} {op1} {result_mul_div} {op2} {e}",
        "步驟 3: **最後算加減** (從左到右)",
        f"   -> 第一部分: {paren_result} {op1} {result_mul_div} = {eval(f'{paren_result} {op1} {result_mul_div}')}",
        f"   -> 第二部分: {eval(f'{paren_result} {op1} {result_mul_div}')} {op2} {e} = {ans}",
        f"最終答案: {ans}",
        "\n💡 口訣：括號 → 乘除 → 加減；同級運算由左到右。"
    ]

    return {
        "topic": "四則運算 (順序)",
        "difficulty": "medium",
        "question": question,
        "answer": str(ans),
        "explanation": "\n".join(explanation_steps),
    }

def gen_fraction_commondenom():
    """分數通分（LCM、新分子兩位數內）"""
    den_pool = [2, 3, 4, 5, 6, 8, 9, 10, 12]
    for _ in range(500):
        b1 = random.choice(den_pool)
        b2 = random.choice(den_pool)
        if b1 == b2:
            continue
        a1 = random.randint(1, b1 - 1)
        a2 = random.randint(1, b2 - 1)
        if a1 / b1 == a2 / b2:
            continue

        lcm_val = _lcm(b1, b2)
        if lcm_val > MAX_2DIGIT:
            continue

        m1 = lcm_val // b1
        m2 = lcm_val // b2
        na1 = a1 * m1
        na2 = a2 * m2
        if not (_within_2digit_int(na1) and _within_2digit_int(na2)):
            continue

        question = f"請將 {a1}/{b1} 和 {a2}/{b2} 通分。\n請依序輸入：公分母 新分子1 新分子2"
        answer = f"{lcm_val} {na1} {na2}"
        explanation = [
            f"LCM({b1}, {b2}) = {lcm_val}",
            f"{a1}/{b1} -> {na1}/{lcm_val}",
            f"{a2}/{b2} -> {na2}/{lcm_val}",
            f"答案：{answer}"
        ]
        return {
            "topic": "分數通分",
            "difficulty": "easy",
            "question": question,
            "answer": answer,
            "explanation": "\n".join(explanation),
        }

    return {"topic": "分數通分", "difficulty": "easy", "question": "（生成失敗）請重試。", "answer": "0 0 0", "explanation": "生成失敗"}

def gen_fraction_reduction():
    simplified_num = random.randint(1, 15)
    simplified_den = random.randint(simplified_num + 1, 20)
    while math.gcd(simplified_num, simplified_den) != 1:
        simplified_num = random.randint(1, 15)
        simplified_den = random.randint(simplified_num + 1, 20)

    multiplier = random.randint(2, 5)
    original_num = simplified_num * multiplier
    original_den = simplified_den * multiplier
    gcd_val = multiplier

    question = f"請將分數 {original_num}/{original_den} 約分到最簡。\n請輸入：分子 分母"
    answer = f"{simplified_num} {simplified_den}"
    explanation = [
        f"GCD({original_num}, {original_den}) = {gcd_val}",
        f"{original_num}/{original_den} -> {simplified_num}/{simplified_den}",
        f"答案：{answer}"
    ]
    return {"topic": "分數約分", "difficulty": "easy", "question": question, "answer": answer, "explanation": "\n".join(explanation)}

def _fraction_core(a1, b1, a2, b2, op):
    f1 = Fraction(a1, b1)
    f2 = Fraction(a2, b2)
    if op == "-" and f1 < f2:
        f1, f2 = f2, f1
        a1, b1, a2, b2 = f1.numerator, f1.denominator, f2.numerator, f2.denominator

    result = f1 + f2 if op == "+" else f1 - f2
    gcd_val = math.gcd(b1, b2)
    lcm_val = (b1 * b2) // gcd_val
    m1 = lcm_val // b1
    m2 = lcm_val // b2
    na1 = a1 * m1
    na2 = a2 * m2
    ns = na1 + na2 if op == "+" else na1 - na2

    expl = [
        f"LCM({b1}, {b2}) = {lcm_val}",
        f"{a1}/{b1} -> {na1}/{lcm_val}",
        f"{a2}/{b2} -> {na2}/{lcm_val}",
        f"分子運算：{na1} {'+' if op=='+' else '-'} {na2} = {ns}",
        f"得到：{ns}/{lcm_val}",
        f"約分：{result.numerator}/{result.denominator}"
    ]
    return result, expl

def gen_fraction_add():
    """分數加減（LCM<=99、通分分子<=99、結果<=99）"""
    den_pool = [2, 3, 4, 5, 6, 8, 9, 10, 12]
    for _ in range(500):
        b1 = random.choice(den_pool)
        b2 = random.choice(den_pool)
        a1 = random.randint(1, b1 - 1)
        a2 = random.randint(1, b2 - 1)
        op = random.choice(["+", "-"])

        lcm_val = _lcm(b1, b2)
        if lcm_val > MAX_2DIGIT:
            continue
        m1 = lcm_val // b1
        m2 = lcm_val // b2
        na1 = a1 * m1
        na2 = a2 * m2
        if not (_within_2digit_int(na1) and _within_2digit_int(na2)):
            continue

        f1 = Fraction(a1, b1)
        f2 = Fraction(a2, b2)
        if op == "-" and f1 < f2:
            f1, f2 = f2, f1
            a1, b1 = f1.numerator, f1.denominator
            a2, b2 = f2.numerator, f2.denominator

        result = f1 + f2 if op == "+" else f1 - f2
        if result <= 0:
            continue
        if not _within_2digit_fraction(result):
            continue

        _, expl = _fraction_core(a1, b1, a2, b2, op)
        question = f"{a1}/{b1} {op} {a2}/{b2} = ?"
        return {"topic": "分數加減", "difficulty": "medium", "question": question,
                "answer": f"{result.numerator}/{result.denominator}", "explanation": "\n".join(expl)}

    return {"topic": "分數加減", "difficulty": "medium", "question": "（生成失敗）請重試。", "answer": "0/1", "explanation": "生成失敗"}

def gen_fraction_mixed():
    w1 = random.randint(1, 5)
    w2 = random.randint(1, 5)
    b1 = random.randint(2, 9)
    b2 = random.randint(2, 9)
    a1 = random.randint(1, b1 - 1)
    a2 = random.randint(1, b2 - 1)
    op = random.choice(["+", "-"])

    F1 = Fraction(w1 * b1 + a1, b1)
    F2 = Fraction(w2 * b2 + a2, b2)
    result, expl = _fraction_core(F1.numerator, F1.denominator, F2.numerator, F2.denominator, op)

    whole = result.numerator // result.denominator
    remain = result.numerator % result.denominator
    ans_str = f"{whole} {remain}/{result.denominator}" if remain != 0 and whole != 0 else f"{result.numerator}/{result.denominator}"

    explanation = [
        f"先化成假分數：{w1} {a1}/{b1} -> {F1.numerator}/{F1.denominator}",
        f"             {w2} {a2}/{b2} -> {F2.numerator}/{F2.denominator}",
        "再做通分/運算：",
        *expl,
        f"答案(可寫帶分數)：{ans_str}"
    ]
    return {"topic": "帶分數運算", "difficulty": "medium",
            "question": f"{w1} {a1}/{b1} {op} {w2} {a2}/{b2} = ?",
            "answer": ans_str, "explanation": "\n".join(explanation)}

def gen_fraction_chain():
    """分數連續加減（2~3 項；LCM<=99、通分分子<=99、結果<=99）"""
    den_pool = [2, 3, 4, 5, 6, 8, 9, 10, 12]
    terms = random.choice([2, 3])

    for _ in range(800):
        fracs: List[Fraction] = []
        dens: List[int] = []
        for _i in range(terms):
            b = random.choice(den_pool)
            a = random.randint(1, b - 1)
            fracs.append(Fraction(a, b))
            dens.append(b)

        ops = [random.choice(["+", "-"]) for _ in range(terms - 1)]
        l = _lcm(dens[0], dens[1]) if terms == 2 else _lcm3(dens[0], dens[1], dens[2])
        if l > MAX_2DIGIT:
            continue

        result = fracs[0]
        for i, op in enumerate(ops, start=1):
            result = result + fracs[i] if op == "+" else result - fracs[i]
        if result <= 0 or (not _within_2digit_fraction(result)):
            continue

        scaled = []
        ok = True
        for f in fracs:
            m = l // f.denominator
            sn = f.numerator * m
            if not _within_2digit_int(sn):
                ok = False
                break
            scaled.append((f, m, sn))
        if not ok:
            continue

        parts = [f"{fracs[0].numerator}/{fracs[0].denominator}"]
        for i, op in enumerate(ops, start=1):
            parts.append(f"{op} {fracs[i].numerator}/{fracs[i].denominator}")
        question = " ".join(parts) + " = ?"

        expl = [
            f"LCM(所有分母) = {l}",
            "通分後："
        ]
        for (f, m, sn) in scaled:
            expl.append(f"{f.numerator}/{f.denominator} -> {sn}/{l}")

        cur = scaled[0][2]
        expr = f"{scaled[0][2]}"
        for i, op in enumerate(ops, start=1):
            if op == "+":
                cur += scaled[i][2]
                expr += f" + {scaled[i][2]}"
            else:
                cur -= scaled[i][2]
                expr += f" - {scaled[i][2]}"
        expl.append(f"分子：{expr} = {cur}")
        expl.append(f"得到：{cur}/{l}，約分 -> {result.numerator}/{result.denominator}")

        return {"topic": "分數連續加減(三項內)", "difficulty": "medium",
                "question": question, "answer": f"{result.numerator}/{result.denominator}",
                "explanation": "\n".join(expl)}

    return {"topic": "分數連續加減(三項內)", "difficulty": "medium",
            "question": "（生成失敗）請重試。", "answer": "0/1", "explanation": "生成失敗"}

def gen_fraction_word_problem_g5():
    """小學五年級分數應用題（離線題庫 18+ 題型）"""
    if generate_fraction_word_problem_g5 is None:
        return {
            "topic": "分數應用題(五年級)",
            "difficulty": "medium",
            "question": "（離線題庫載入失敗）請檢查 fraction_word_g5.py。",
            "answer": "0",
            "explanation": "離線題庫載入失敗",
            "steps": ["請確認 fraction_word_g5.py 是否存在且可匯入。"],
        }
    return generate_fraction_word_problem_g5()

def gen_gcd_lcm():
    count = random.choice([2, 3])
    if count == 2:
        a = random.randint(10, 50)
        b = random.randint(10, 50)
        gcd_val = math.gcd(a, b)
        lcm_val = (a * b) // gcd_val
        question = f"數字 {a} 和 {b} 的最大公因數(GCD)和最小公倍數(LCM)各是多少？\n請依序輸入：GCD LCM"
        answer = f"{gcd_val} {lcm_val}"
        explanation = f"GCD={gcd_val}\nLCM=({a}×{b})/GCD={lcm_val}\n答案：{answer}"
        topic = "GCD/LCM (二數)"
    else:
        a = random.randint(5, 20)
        b = random.randint(5, 20)
        c = random.randint(5, 20)
        gcd_val = math.gcd(a, math.gcd(b, c))
        lcm_ab = (a * b) // math.gcd(a, b)
        lcm_val = (lcm_ab * c) // math.gcd(lcm_ab, c)
        question = f"數字 {a}, {b}, {c} 的最大公因數(GCD)和最小公倍數(LCM)各是多少？\n請依序輸入：GCD LCM"
        answer = f"{gcd_val} {lcm_val}"
        explanation = f"GCD={gcd_val}\nLCM={lcm_val}\n答案：{answer}"
        topic = "GCD/LCM (三數)"

    return {"topic": topic, "difficulty": "medium", "question": question, "answer": answer, "explanation": explanation}

def gen_decimal_arith():
    a = round(random.uniform(0.5, 20.0), random.randint(1, 2))
    b = round(random.uniform(0.5, 10.0), random.randint(1, 2))
    op = random.choice(["+", "-", "×", "÷"])

    if op == '+':
        ans = a + b
    elif op == '-':
        if a < b:
            a, b = b, a
        ans = a - b
    elif op == '×':
        ans = a * b
    else:
        ans_target = round(random.uniform(1.0, 5.0), 2)
        b = round(random.uniform(1.0, 5.0), 1)
        a = round(b * ans_target, 2)
        ans = a / b

    final_ans = round(ans, 2)
    question = f"計算並將結果四捨五入到小數點後兩位：\n{a} {op} {b} = ?"
    explanation = f"先算出約 {ans}\n再四捨五入到小數點後兩位 -> {final_ans}"
    return {"topic": "小數四則運算", "difficulty": "medium",
            "question": question, "answer": str(final_ans), "explanation": explanation}

def gen_volume_area():
    length = random.randint(2, 10)
    width = random.randint(2, 10)
    height = random.randint(2, 10)
    q_type = random.choice(["volume", "surface_area"])

    if length == width == height:
        shape = "正方體"
        if q_type == "volume":
            ans = length ** 3
            q_text = f"邊長為 {length} 公分的{shape}，體積是多少立方公分？"
            expl = f"體積=邊長³={length}×{length}×{length}={ans}"
        else:
            ans = 6 * (length ** 2)
            q_text = f"邊長為 {length} 公分的{shape}，表面積是多少平方公分？"
            expl = f"表面積=6×邊長²=6×({length}×{length})={ans}"
    else:
        shape = "長方體"
        dims = f"長 {length}、寬 {width}、高 {height}"
        if q_type == "volume":
            ans = length * width * height
            q_text = f"{dims} 公分的{shape}，體積是多少立方公分？"
            expl = f"體積=長×寬×高={length}×{width}×{height}={ans}"
        else:
            lw = length * width
            lh = length * height
            wh = width * height
            ans = 2 * (lw + lh + wh)
            q_text = f"{dims} 公分的{shape}，表面積是多少平方公分？"
            expl = f"表面積=2×(長寬+長高+寬高)=2×({lw}+{lh}+{wh})={ans}"

    return {"topic": f"{shape} {q_type.replace('_',' ')}", "difficulty": "easy",
            "question": q_text, "answer": str(ans), "explanation": expl}

def gen_linear_equation():
    x_val = random.randint(-9, 9)
    a = random.randint(2, 9)
    b = random.randint(-10, 10)
    c = a * x_val + b
    question = f"{a}x + {b} = {c}, 求 x"

    rhs = c - b

    explanation = f"移項：{a}x = {c} - ({b}) = {c - b}\n兩邊除以 {a}：x = {x_val}"

    steps = [
        f"步驟 1: 將常數項移到等號右邊。 {a}x = {c} - ({b})",
        f"步驟 2: 計算右邊的值。 {a}x = {rhs}",
        f"步驟 3: 將兩邊同除以 x 的係數 {a}。 x = {rhs} ÷ {a} = {x_val}"
    ]

    return {
        "topic": "一元一次方程",
        "difficulty": "medium",
        "question": question,
        "answer": str(x_val),
        "explanation": explanation,
        "steps": steps
    }

def gen_quadratic_equation():
    # Simple quadratic: (x - r1)(x - r2) = 0 => x^2 - (r1+r2)x + r1*r2 = 0
    r1 = random.randint(-5, 5)
    r2 = random.randint(-5, 5)
    if r1 == 0: r1 = 1
    if r2 == 0: r2 = 2

    b = -(r1 + r2)
    c = r1 * r2

    # Format: x^2 + bx + c = 0
    # Simplify signs
    def fmt(n, var=""):
        if n == 0: return ""
        if var == "": return f"{n:+}"
        if n == 1: return f"+{var}"
        if n == -1: return f"-{var}"
        return f"{n:+}{var}"

    term_b = fmt(b, "x")
    term_c = fmt(c)

    eq = f"x^2 {term_b} {term_c} = 0".replace(" +", " +").replace(" -", " -").strip()
    if eq.startswith("+"): eq = eq[1:]

    question = f"解方程式: {eq}"
    ans = f"{min(r1,r2)},{max(r1,r2)}" if r1!=r2 else f"{r1}"
    explanation = f"因式分解: (x - ({r1}))(x - ({r2})) = 0\n根為: {r1}, {r2}"

    steps = [
        "步驟 1: 觀察方程式形式，嘗試使用因式分解法。",
        f"步驟 2: 尋找兩個數，相乘為 {c}，相加為 {b}。",
        f"步驟 3: 這兩個數是 {-r1} 和 {-r2}。所以分解為 (x {fmt(-r1)}) (x {fmt(-r2)}) = 0。",
        f"步驟 4: 令每個括號為 0。 x = {r1} 或 x = {r2}。"
    ]

    return {
        "topic": "一元二次方程式",
        "difficulty": "hard",
        "question": question,
        "answer": ans,
        "explanation": explanation,
        "steps": steps
    }

# -------------------------
# GENERATORS
# -------------------------
GENERATORS: Dict[str, Tuple[str, Any]] = {
    "1": ("四則運算 (含括號/乘除)", gen_order_of_ops_arith),
    "2": ("分數通分", gen_fraction_commondenom),
    "3": ("分數約分", gen_fraction_reduction),
    "4": ("分數加減", gen_fraction_add),
    "5": ("帶分數運算", gen_fraction_mixed),
    "6": ("GCD/LCM", gen_gcd_lcm),
    "7": ("小數四則運算", gen_decimal_arith),
    "8": ("長/正方體積/面積", gen_volume_area),
    "10": ("分數連續加減(三項內)", gen_fraction_chain),
    "11": ("分數應用題(五年級)", gen_fraction_word_problem_g5),
    "linear": ("一元一次方程", gen_linear_equation),
    "quadratic": ("一元二次方程式", gen_quadratic_equation)
}

# Register new isolated type_key (pack-based)
if g5s_web_concepts is not None:
    GENERATORS["g5s_web_concepts_v1"] = ("20260203 小五下網路精選", g5s_web_concepts.next_question)
if g5s_good_concepts is not None:
    GENERATORS["g5s_good_concepts_v1"] = ("20260203 小五下數學好的觀念題型", g5s_good_concepts.next_question)
if EXTERNAL_WEB_QUESTION_BANK_ENABLED and external_web_fraction_app_v1 is not None:
    GENERATORS["external_web_fraction_app_v1"] = (
        "新的外網題型出題解題（分數應用）",
        external_web_fraction_app_v1.next_question,
    )
if EXTERNAL_WEB_FRACTION_DECIMAL_ENABLED and fraction_decimal_application_web_v1 is not None:
    GENERATORS["fraction_decimal_application_web_v1"] = (
        "分數小數活用題型（外網增強）",
        fraction_decimal_application_web_v1.next_question,
    )
if HAS_SYMPY:
    GENERATORS["9"] = ("一元一次方程", gen_linear_equation)
    GENERATORS["linear"] = GENERATORS["9"]


def get_random_generator(topic_filter: Optional[str] = None):
    if topic_filter and topic_filter in GENERATORS:
        return GENERATORS[topic_filter][1]
    k = random.choice(list(GENERATORS.keys()))
    return GENERATORS[k][1]


def get_random_generator_key_and_func(topic_filter: Optional[str] = None) -> Tuple[str, Any]:
    if topic_filter and topic_filter in GENERATORS:
        return topic_filter, GENERATORS[topic_filter][1]
    k = random.choice(list(GENERATORS.keys()))
    return k, GENERATORS[k][1]

def next_question(topic_key: Optional[str] = None) -> Dict[str, Any]:
    chosen_key, gen_func = get_random_generator_key_and_func(topic_key)
    q = gen_func()
    if not isinstance(q, dict):
        q = {"question": str(q)}

    # Attach keys so downstream QA/review can map back to the template reliably.
    q.setdefault("template_id", str(chosen_key))
    q.setdefault("topic_key", str(chosen_key))
    if str(q.get("topic") or "").strip() == "":
        q["topic"] = GENERATORS.get(chosen_key, (str(chosen_key), None))[0]
    return q


# ======================================================================
# SERVER (FastAPI + DB + Subscription Gate)
# ======================================================================

DB_PATH = os.environ.get("DB_PATH", "app.db")
app = FastAPI(title="Math Practice MVP API (All-in-One)", version="0.2")

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        api_key TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        display_name TEXT NOT NULL,
        grade TEXT DEFAULT 'G5',
        created_at TEXT NOT NULL,
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        status TEXT NOT NULL,              -- active / inactive / past_due
        plan TEXT DEFAULT 'basic',
        seats INTEGER DEFAULT 1,
        current_period_end TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS question_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT,
        difficulty TEXT,
        question TEXT,
        correct_answer TEXT,
        explanation TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        mode TEXT NOT NULL,                -- auto/custom
        question_id INTEGER,
        topic TEXT,
        difficulty TEXT,
        question TEXT,
        correct_answer TEXT,
        user_answer TEXT,
        is_correct INTEGER,                -- 1/0/NULL
        time_spent_sec INTEGER DEFAULT 0,
        ts TEXT NOT NULL,
        explanation TEXT,
        FOREIGN KEY(account_id) REFERENCES accounts(id),
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(question_id) REFERENCES question_cache(id)
    )
    """)

    conn.commit()
    conn.close()

init_db()

def get_account_by_api_key(api_key: str) -> sqlite3.Row:
    conn = db()
    row = conn.execute("SELECT * FROM accounts WHERE api_key = ?", (api_key,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return row

def ensure_subscription_active(account_id: int):
    conn = db()
    sub = conn.execute(
        "SELECT * FROM subscriptions WHERE account_id = ? ORDER BY updated_at DESC LIMIT 1",
        (account_id,)
    ).fetchone()
    conn.close()
    if not sub or sub["status"] != "active":
        raise HTTPException(status_code=402, detail="Subscription required (inactive)")

def ensure_student_belongs(account_id: int, student_id: int) -> sqlite3.Row:
    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (student_id, account_id)).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")
    return st

@app.get("/health")
def health():
    return {"ok": True, "ts": now_iso(), "has_sympy": HAS_SYMPY}

@app.post("/admin/bootstrap")
def admin_bootstrap(name: str = "TestAccount"):
    """
    MVP 用：建立一個 account + active 訂閱 + 預設 1 個學生，回傳 api_key
    上線後應替換為：正式登入 + Stripe webhook 寫入 subscriptions
    """
    import secrets
    api_key = secrets.token_urlsafe(24)

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO accounts(name, api_key, created_at) VALUES (?,?,?)", (name, api_key, now_iso()))
    account_id = cur.lastrowid

    cur.execute("""INSERT INTO subscriptions(account_id,status,plan,seats,current_period_end,updated_at)
                   VALUES (?,?,?,?,?,?)""",
                (account_id, "active", "basic", 3,
                 (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds"),
                 now_iso()))

    cur.execute("""INSERT INTO students(account_id, display_name, grade, created_at)
                   VALUES (?,?,?,?)""",
                (account_id, "Student-1", "G5", now_iso()))
    conn.commit()
    conn.close()

    return {"account_id": account_id, "api_key": api_key}

@app.get("/v1/students")
def list_students(x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    conn = db()
    rows = conn.execute("SELECT * FROM students WHERE account_id = ? ORDER BY id ASC", (acc["id"],)).fetchall()
    conn.close()
    return {"students": [dict(r) for r in rows]}

@app.post("/v1/students")
def create_student(display_name: str, grade: str = "G5", x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    conn = db()
    conn.execute("""INSERT INTO students(account_id, display_name, grade, created_at)
                    VALUES (?,?,?,?)""", (acc["id"], display_name, grade, now_iso()))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.post("/v1/questions/next")
def api_next_question(student_id: int, topic_key: Optional[str] = None, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    ensure_student_belongs(acc["id"], student_id)

    q = next_question(topic_key)

    conn = db()
    cur = conn.cursor()
    cur.execute("""INSERT INTO question_cache(topic,difficulty,question,correct_answer,explanation,created_at)
                   VALUES (?,?,?,?,?,?)""",
                (q["topic"], q["difficulty"], q["question"], q["answer"], q["explanation"], now_iso()))
    qid = cur.lastrowid
    conn.commit()
    conn.close()

    # 不回傳 answer，避免作弊
    return {
        "question_id": qid,
        "topic": q["topic"],
        "difficulty": q["difficulty"],
        "question": q["question"],
        "explanation_preview": "（交卷後顯示）"
    }

@app.post("/v1/answers/submit")
async def api_submit_answer(request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
    """
    body:
      {
        "student_id": 1,
        "question_id": 123,
        "user_answer": "3/4",
        "time_spent_sec": 25
      }
    """
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    body = await request.json()
    student_id = int(body["student_id"])
    question_id = int(body["question_id"])
    user_answer = str(body.get("user_answer", "")).strip()
    time_spent = int(body.get("time_spent_sec", 0))

    ensure_student_belongs(acc["id"], student_id)

    conn = db()
    q = conn.execute("SELECT * FROM question_cache WHERE id=?", (question_id,)).fetchone()
    if not q:
        conn.close()
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = check(user_answer, q["correct_answer"])

    conn.execute("""INSERT INTO attempts(account_id, student_id, mode, question_id, topic, difficulty,
                    question, correct_answer, user_answer, is_correct, time_spent_sec, ts, explanation)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (acc["id"], student_id, "auto", question_id, q["topic"], q["difficulty"],
                  q["question"], q["correct_answer"], user_answer, is_correct, time_spent, now_iso(), q["explanation"]))
    conn.commit()
    conn.close()

    return {
        "is_correct": is_correct,
        "correct_answer": q["correct_answer"],
        "explanation": q["explanation"],
        "topic": q["topic"],
        "difficulty": q["difficulty"]
    }

@app.post("/v1/custom/solve")
async def api_custom_solve(request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
    """
    body:
      { "question": "1/2 + 1/3" }
      { "question": "2*x + 3 = 9" }
    """
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    body = await request.json()
    q = str(body.get("question", "")).strip()
    ans, expl = solve_custom(q)
    return {"question": q, "auto_answer": ans, "explanation": expl, "has_sympy": HAS_SYMPY}

@app.post("/v1/custom/submit")
async def api_custom_submit(request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
    """
    body:
      {
        "student_id": 1,
        "question": "1/2 + 1/3",
        "final_answer": "5/6",        # 可用 solve_custom 的答案或手動輸入
        "user_answer": "5/6",
        "time_spent_sec": 18
      }
    """
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    body = await request.json()

    student_id = int(body["student_id"])
    ensure_student_belongs(acc["id"], student_id)

    q_text = str(body.get("question", "")).strip()
    final_answer = str(body.get("final_answer", "")).strip()
    user_answer = str(body.get("user_answer", "")).strip()
    time_spent = int(body.get("time_spent_sec", 0))

    is_correct = None
    if user_answer and final_answer:
        is_correct = check(user_answer, final_answer)

    # 若 final_answer 空，嘗試用 solver 自動算
    explanation = "使用者提供標準答案"
    if not final_answer:
        auto_ans, auto_expl = solve_custom(q_text)
        if auto_ans:
            final_answer = auto_ans
            explanation = auto_expl
            if user_answer:
                is_correct = check(user_answer, final_answer)
        else:
            explanation = f"無法自動解題：{auto_expl}"

    conn = db()
    conn.execute("""INSERT INTO attempts(account_id, student_id, mode, question_id, topic, difficulty,
                    question, correct_answer, user_answer, is_correct, time_spent_sec, ts, explanation)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (acc["id"], student_id, "custom", None, "custom", "unknown",
                  q_text, final_answer, user_answer, is_correct, time_spent, now_iso(), explanation))
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "is_correct": is_correct,
        "final_answer": final_answer,
        "explanation": explanation
    }

@app.get("/v1/reports/summary")
def api_report_summary(student_id: int, days: int = 30, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    ensure_student_belongs(acc["id"], student_id)

    since = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")

    conn = db()
    totals = conn.execute("""
        SELECT
          SUM(CASE WHEN is_correct IN (0,1) THEN 1 ELSE 0 END) AS valid_total,
          SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
          SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong,
          SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) AS invalid
        FROM attempts
        WHERE student_id = ? AND ts >= ?
    """, (student_id, since)).fetchone()

    topics = conn.execute("""
        SELECT
          topic,
          COUNT(*) AS total,
          SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
          SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong,
          SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) AS invalid
        FROM attempts
        WHERE student_id = ? AND ts >= ?
        GROUP BY topic
        ORDER BY total DESC
    """, (student_id, since)).fetchall()

    wrongs = conn.execute("""
        SELECT ts, mode, topic, question, correct_answer, user_answer
        FROM attempts
        WHERE student_id = ? AND ts >= ? AND is_correct = 0
        ORDER BY ts DESC
        LIMIT 20
    """, (student_id, since)).fetchall()

    conn.close()

    valid_total = int(totals["valid_total"] or 0)
    correct_cnt = int(totals["correct"] or 0)
    acc_rate = (correct_cnt / valid_total * 100.0) if valid_total else 0.0

    return {
        "student_id": student_id,
        "window_days": days,
        "summary": {
            "valid_total": valid_total,
            "correct": correct_cnt,
            "wrong": int(totals["wrong"] or 0),
            "invalid": int(totals["invalid"] or 0),
            "accuracy": round(acc_rate, 2)
        },
        "topics": [dict(r) for r in topics],
        "recent_wrongs": [dict(r) for r in wrongs]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("math_app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=True)
