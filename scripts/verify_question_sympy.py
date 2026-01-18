from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class VerifyResult:
    ok: bool
    message: str
    solutions: list[str]


def _normalize_answer(x: Any) -> str:
    return str(x).strip()


def verify_equation_question(equation_expr: str, student_answer: Any, symbol: str = "x") -> VerifyResult:
    """Verify whether student_answer is a solution to equation_expr == 0.

    equation_expr examples:
      - "x**2 - 5*x + 6"  (interpreted as x**2 - 5*x + 6 = 0)
      - "(x-3)**2 - 16"

    Returns stringified solutions for reporting.
    """

    try:
        import sympy as sp
    except Exception as e:  # pragma: no cover
        return VerifyResult(False, f"sympy not installed: {e}", [])

    x = sp.symbols(symbol)

    try:
        expr = sp.sympify(equation_expr)
    except Exception as e:
        return VerifyResult(False, f"解析失敗: {e}", [])

    try:
        sols = sp.solve(expr, x)
    except Exception as e:
        return VerifyResult(False, f"求解失敗: {e}", [])

    # Normalize student answer into sympy value if possible.
    try:
        ans_val = sp.sympify(student_answer)
    except Exception:
        ans_val = _normalize_answer(student_answer)

    def _eq(a, b) -> bool:
        try:
            return bool(sp.simplify(a - b) == 0)
        except Exception:
            return str(a) == str(b)

    ok = False
    for s in sols:
        if _eq(s, ans_val):
            ok = True
            break

    sol_strs = [str(s) for s in sols]
    if ok:
        return VerifyResult(True, "正確", sol_strs)
    return VerifyResult(False, f"錯誤，正確解應為 {sol_strs}", sol_strs)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify equation question via sympy")
    ap.add_argument("--expr", required=True, help="Expression interpreted as == 0")
    ap.add_argument("--answer", required=True, help="Student answer")
    ap.add_argument("--symbol", default="x")
    args = ap.parse_args()

    res = verify_equation_question(args.expr, args.answer, symbol=args.symbol)
    print({"ok": res.ok, "message": res.message, "solutions": res.solutions})
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
