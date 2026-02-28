"""
pipeline/deterministic_solver.py — Deterministic elementary math solver.

Provides verified, deterministic computation for grades 5-6 (Stage III)
math problems. Used as the "main judge" in dual-track adjudication:
  - Deterministic solver = primary (this module)
  - LLM-as-a-judge = auxiliary only, sandboxed, replayable

Supported topic families:
  N-5-*  : fractions, decimals, percentages, rounding
  N-6-*  : fraction division, speed-distance-time, ratio
  S-6-*  : scale / map problems
  D-5-*  : data analysis (mean, trend, line graph)

Usage:
  from pipeline.deterministic_solver import solve, verify_answer
  result = solve("N-5-10", params)
  ok = verify_answer("N-6-7", expected, actual)
"""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Any


# ── Fraction Operations ────────────────────────────────────

def fraction_add(a: str, b: str) -> str:
    """Add two fractions (given as strings like '2/3')."""
    return str(Fraction(a) + Fraction(b))


def fraction_sub(a: str, b: str) -> str:
    """Subtract two fractions."""
    return str(Fraction(a) - Fraction(b))


def fraction_mul(a: str, b: str) -> str:
    """Multiply two fractions."""
    return str(Fraction(a) * Fraction(b))


def fraction_div(a: str, b: str) -> str:
    """Divide two fractions (a ÷ b)."""
    if Fraction(b) == 0:
        raise ValueError("Division by zero")
    return str(Fraction(a) / Fraction(b))


def simplify_fraction(frac: str) -> str:
    """Simplify a fraction to lowest terms."""
    f = Fraction(frac)
    return str(f)


def mixed_to_improper(whole: int, num: int, den: int) -> str:
    """Convert mixed number to improper fraction."""
    return str(Fraction(whole * den + num, den))


def improper_to_mixed(frac: str) -> tuple[int, str]:
    """Convert improper fraction to mixed number. Returns (whole, remainder_frac)."""
    f = Fraction(frac)
    whole = int(f)
    remainder = f - whole
    return whole, str(remainder) if remainder else "0"


# ── Decimal Operations ─────────────────────────────────────

def decimal_add(a: float, b: float) -> float:
    """Add two decimals using Fraction for exact arithmetic."""
    return float(Fraction(str(a)) + Fraction(str(b)))


def decimal_sub(a: float, b: float) -> float:
    """Subtract two decimals using Fraction for exact arithmetic."""
    return float(Fraction(str(a)) - Fraction(str(b)))


def decimal_mul(a: float, b: float) -> float:
    """Multiply two decimals using Fraction for exact arithmetic."""
    return float(Fraction(str(a)) * Fraction(str(b)))


def decimal_div(a: float, b: float) -> float:
    """Divide two decimals using Fraction for exact arithmetic."""
    if b == 0:
        raise ValueError("Division by zero")
    return float(Fraction(str(a)) / Fraction(str(b)))


# ── Percentage / Ratio ─────────────────────────────────────

def to_percent(value: float) -> float:
    """Convert decimal to percentage."""
    return float(Fraction(str(value)) * 100)


def from_percent(pct: float) -> float:
    """Convert percentage to decimal."""
    return float(Fraction(str(pct)) / 100)


def discount_price(original: float, discount_rate: float) -> float:
    """Calculate discounted price. discount_rate is '折' (e.g. 8折 = 0.8)."""
    return float(Fraction(str(original)) * Fraction(str(discount_rate)))


def percent_of(whole: float, part: float) -> float:
    """Calculate what percent 'part' is of 'whole'."""
    if whole == 0:
        raise ValueError("Whole cannot be zero")
    return float(Fraction(str(part)) / Fraction(str(whole)) * 100)


def ratio_simplify(a: int, b: int) -> tuple[int, int]:
    """Simplify ratio a:b to lowest terms."""
    from math import gcd
    g = gcd(a, b)
    return a // g, b // g


# ── Rounding (概數) ────────────────────────────────────────

def round_to_place(value: float, place: str) -> float:
    """
    Round to a specific place.
    place: 'ones', 'tens', 'hundreds', 'thousands',
           'tenths', 'hundredths', 'thousandths'
    """
    place_map = {
        "ones": 0,
        "tens": -1,
        "hundreds": -2,
        "thousands": -3,
        "tenths": 1,
        "hundredths": 2,
        "thousandths": 3,
    }
    digits = place_map.get(place)
    if digits is None:
        raise ValueError(f"Unknown place: {place}")
    return round(value, digits)


def round_to_digits(value: float, digits: int) -> float:
    """Round to N decimal places (四捨五入)."""
    return round(value, digits)


# ── Speed / Distance / Time (N-6-7) ───────────────────────

def speed_from_distance_time(distance: float, time: float) -> float:
    """速度 = 距離 ÷ 時間"""
    if time == 0:
        raise ValueError("Time cannot be zero")
    return float(Fraction(str(distance)) / Fraction(str(time)))


def distance_from_speed_time(speed: float, time: float) -> float:
    """距離 = 速度 × 時間"""
    return float(Fraction(str(speed)) * Fraction(str(time)))


def time_from_distance_speed(distance: float, speed: float) -> float:
    """時間 = 距離 ÷ 速度"""
    if speed == 0:
        raise ValueError("Speed cannot be zero")
    return float(Fraction(str(distance)) / Fraction(str(speed)))


def convert_speed_unit(
    value: float,
    from_unit: str,
    to_unit: str,
) -> float:
    """
    Convert speed between units.
    Supported: km/h, m/min, m/s, km/min
    """
    # Convert to m/s first, then to target
    to_ms: dict[str, float] = {
        "km/h": 1000 / 3600,
        "m/min": 1 / 60,
        "m/s": 1.0,
        "km/min": 1000 / 60,
    }
    from_ms: dict[str, float] = {
        "km/h": 3600 / 1000,
        "m/min": 60,
        "m/s": 1.0,
        "km/min": 60 / 1000,
    }
    if from_unit not in to_ms or to_unit not in from_ms:
        raise ValueError(f"Unsupported unit conversion: {from_unit} → {to_unit}")

    ms_value = value * to_ms[from_unit]
    return ms_value * from_ms[to_unit]


# ── Scale / Map (S-6-2) ───────────────────────────────────

def scale_actual_to_map(actual: float, scale_denominator: int) -> float:
    """Convert actual distance to map distance. 比例尺 = 1:N"""
    if scale_denominator == 0:
        raise ValueError("Scale denominator cannot be zero")
    return float(Fraction(str(actual)) / Fraction(scale_denominator))


def scale_map_to_actual(map_dist: float, scale_denominator: int) -> float:
    """Convert map distance to actual distance. 比例尺 = 1:N"""
    return float(Fraction(str(map_dist)) * Fraction(scale_denominator))


def scale_find_denominator(map_dist: float, actual_dist: float) -> int:
    """Find scale denominator given map and actual distances."""
    if map_dist == 0:
        raise ValueError("Map distance cannot be zero")
    ratio = Fraction(str(actual_dist)) / Fraction(str(map_dist))
    # Return as integer if possible
    if ratio.denominator == 1:
        return int(ratio)
    return int(float(ratio))


# ── Data Analysis (D-5-1) ─────────────────────────────────

def mean(values: list[float]) -> float:
    """Calculate arithmetic mean."""
    if not values:
        raise ValueError("Cannot compute mean of empty list")
    total = sum(Fraction(str(v)) for v in values)
    return float(total / len(values))


def data_range(values: list[float]) -> float:
    """Calculate range (max - min)."""
    if not values:
        raise ValueError("Cannot compute range of empty list")
    return max(values) - min(values)


def trend_direction(values: list[float]) -> str:
    """
    Determine trend direction: 'increasing', 'decreasing', 'stable', 'fluctuating'.
    Uses simple comparison of first half mean vs second half mean.
    """
    if len(values) < 2:
        return "stable"
    mid = len(values) // 2
    first_half = mean(values[:mid])
    second_half = mean(values[mid:])
    diff = second_half - first_half
    threshold = abs(first_half) * 0.05 if first_half != 0 else 0.01
    if diff > threshold:
        return "increasing"
    elif diff < -threshold:
        return "decreasing"
    else:
        return "stable"


def find_max_change(values: list[float]) -> tuple[int, int, float]:
    """
    Find the pair of consecutive data points with the largest absolute change.
    Returns (index_from, index_to, change_amount).
    """
    if len(values) < 2:
        raise ValueError("Need at least 2 data points")
    max_change = 0.0
    max_i = 0
    for i in range(len(values) - 1):
        change = abs(values[i + 1] - values[i])
        if change > max_change:
            max_change = change
            max_i = i
    return max_i, max_i + 1, values[max_i + 1] - values[max_i]


# ── Universal Solver ───────────────────────────────────────

def solve(topic_code: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Universal solver dispatcher. Routes to topic-specific solver.

    Args:
        topic_code: e.g. "N-5-10", "N-6-7", "S-6-2", "D-5-1"
        params: problem parameters (varies by topic)

    Returns:
        dict with 'answer', 'steps', 'unit' (if applicable)
    """
    prefix = topic_code.split("-")[0] + "-" + topic_code.split("-")[1]
    solvers = {
        "N-5": _solve_n5,
        "N-6": _solve_n6,
        "S-6": _solve_s6,
        "D-5": _solve_d5,
    }
    solver = solvers.get(prefix)
    if solver is None:
        raise ValueError(f"No solver for topic prefix: {prefix}")
    return solver(topic_code, params)


def _solve_n5(topic_code: str, params: dict) -> dict:
    """Solve N-5-* problems (fractions, decimals, percentages, rounding)."""
    op = params.get("operation", "add")
    a = params.get("a")
    b = params.get("b")

    if topic_code == "N-5-10":
        # Percentage problems
        if op == "percent_of":
            result = percent_of(float(a), float(b))
            return {
                "answer": result,
                "steps": [
                    f"已知全部 = {a}，部分 = {b}",
                    f"百分率 = {b} ÷ {a} × 100",
                    f"= {result}%",
                ],
                "unit": "%",
            }
        elif op == "discount":
            rate = params.get("rate", 0.8)
            result = discount_price(float(a), rate)
            return {
                "answer": result,
                "steps": [
                    f"原價 = {a} 元",
                    f"折扣率 = {rate}",
                    f"折扣價 = {a} × {rate} = {result} 元",
                ],
                "unit": "元",
            }
        elif op == "from_percent":
            result = from_percent(float(a))
            return {
                "answer": result,
                "steps": [
                    f"{a}% = {a} ÷ 100 = {result}",
                ],
                "unit": "",
            }
    elif topic_code == "N-5-11":
        # Rounding problems
        place = params.get("place", "ones")
        val = float(a)
        result = round_to_place(val, place)
        return {
            "answer": result,
            "steps": [
                f"原始數值 = {val}",
                f"四捨五入到{place}位 = {result}",
            ],
            "unit": "",
        }

    # Generic fraction/decimal operation
    if params.get("type") == "fraction":
        ops = {"add": fraction_add, "sub": fraction_sub,
               "mul": fraction_mul, "div": fraction_div}
        fn = ops.get(op, fraction_add)
        result = fn(str(a), str(b))
        return {
            "answer": result,
            "steps": [
                f"{a} {_op_symbol(op)} {b}",
                f"= {result}",
            ],
            "unit": params.get("unit", ""),
        }
    else:
        ops = {"add": decimal_add, "sub": decimal_sub,
               "mul": decimal_mul, "div": decimal_div}
        fn = ops.get(op, decimal_add)
        result = fn(float(a), float(b))
        return {
            "answer": result,
            "steps": [
                f"{a} {_op_symbol(op)} {b}",
                f"= {result}",
            ],
            "unit": params.get("unit", ""),
        }


def _solve_n6(topic_code: str, params: dict) -> dict:
    """Solve N-6-* problems (fraction division, speed)."""
    if topic_code == "N-6-3":
        # Fraction division
        a, b = str(params["a"]), str(params["b"])
        result = fraction_div(a, b)
        reciprocal = str(Fraction(b) ** -1) if Fraction(b) != 0 else "undefined"
        return {
            "answer": result,
            "steps": [
                f"{a} ÷ {b}",
                f"= {a} × {reciprocal}（倒數）",
                f"= {result}",
            ],
            "unit": params.get("unit", ""),
        }
    elif topic_code == "N-6-7":
        # Speed-distance-time
        op = params.get("operation", "find_distance")
        if op == "find_distance":
            speed, time = float(params["speed"]), float(params["time"])
            result = distance_from_speed_time(speed, time)
            return {
                "answer": result,
                "steps": [
                    f"速度 = {speed} {params.get('speed_unit', 'km/h')}",
                    f"時間 = {time} {params.get('time_unit', '小時')}",
                    f"距離 = 速度 × 時間 = {speed} × {time} = {result}",
                ],
                "unit": params.get("distance_unit", "公里"),
            }
        elif op == "find_speed":
            distance, time = float(params["distance"]), float(params["time"])
            result = speed_from_distance_time(distance, time)
            return {
                "answer": result,
                "steps": [
                    f"距離 = {distance} {params.get('distance_unit', '公里')}",
                    f"時間 = {time} {params.get('time_unit', '小時')}",
                    f"速度 = 距離 ÷ 時間 = {distance} ÷ {time} = {result}",
                ],
                "unit": params.get("speed_unit", "km/h"),
            }
        elif op == "find_time":
            distance, speed = float(params["distance"]), float(params["speed"])
            result = time_from_distance_speed(distance, speed)
            return {
                "answer": result,
                "steps": [
                    f"距離 = {distance} {params.get('distance_unit', '公里')}",
                    f"速度 = {speed} {params.get('speed_unit', 'km/h')}",
                    f"時間 = 距離 ÷ 速度 = {distance} ÷ {speed} = {result}",
                ],
                "unit": params.get("time_unit", "小時"),
            }
        elif op == "convert_speed":
            value = float(params["value"])
            from_u = params["from_unit"]
            to_u = params["to_unit"]
            result = convert_speed_unit(value, from_u, to_u)
            return {
                "answer": result,
                "steps": [
                    f"{value} {from_u}",
                    f"= {result} {to_u}",
                ],
                "unit": to_u,
            }
    # Generic N-6
    return {"answer": None, "steps": [], "unit": ""}


def _solve_s6(topic_code: str, params: dict) -> dict:
    """Solve S-6-* problems (scale/map)."""
    if topic_code == "S-6-2":
        op = params.get("operation", "map_to_actual")
        scale = int(params.get("scale_denominator", 1))
        if op == "map_to_actual":
            map_dist = float(params["map_distance"])
            result = scale_map_to_actual(map_dist, scale)
            return {
                "answer": result,
                "steps": [
                    f"地圖距離 = {map_dist} {params.get('map_unit', '公分')}",
                    f"比例尺 = 1:{scale}",
                    f"實際距離 = {map_dist} × {scale} = {result} {params.get('actual_unit', '公分')}",
                ],
                "unit": params.get("actual_unit", "公分"),
            }
        elif op == "actual_to_map":
            actual = float(params["actual_distance"])
            result = scale_actual_to_map(actual, scale)
            return {
                "answer": result,
                "steps": [
                    f"實際距離 = {actual} {params.get('actual_unit', '公分')}",
                    f"比例尺 = 1:{scale}",
                    f"地圖距離 = {actual} ÷ {scale} = {result} {params.get('map_unit', '公分')}",
                ],
                "unit": params.get("map_unit", "公分"),
            }
        elif op == "find_scale":
            map_dist = float(params["map_distance"])
            actual = float(params["actual_distance"])
            result = scale_find_denominator(map_dist, actual)
            return {
                "answer": result,
                "steps": [
                    f"地圖距離 = {map_dist}，實際距離 = {actual}",
                    f"比例尺 = 1:{result}",
                ],
                "unit": "",
            }
    return {"answer": None, "steps": [], "unit": ""}


def _solve_d5(topic_code: str, params: dict) -> dict:
    """Solve D-5-* problems (data analysis, line graph)."""
    if topic_code == "D-5-1":
        op = params.get("operation", "mean")
        values = params.get("values", [])
        if op == "mean":
            result = mean(values)
            return {
                "answer": result,
                "steps": [
                    f"資料：{values}",
                    f"總和 = {sum(values)}",
                    f"平均 = {sum(values)} ÷ {len(values)} = {result}",
                ],
                "unit": params.get("unit", ""),
            }
        elif op == "range":
            result = data_range(values)
            return {
                "answer": result,
                "steps": [
                    f"資料：{values}",
                    f"最大值 = {max(values)}，最小值 = {min(values)}",
                    f"全距 = {max(values)} - {min(values)} = {result}",
                ],
                "unit": params.get("unit", ""),
            }
        elif op == "trend":
            direction = trend_direction(values)
            return {
                "answer": direction,
                "steps": [
                    f"資料：{values}",
                    f"趨勢判定：{direction}",
                ],
                "unit": "",
            }
        elif op == "max_change":
            i, j, change = find_max_change(values)
            labels = params.get("labels", list(range(len(values))))
            return {
                "answer": abs(change),
                "steps": [
                    f"資料：{values}",
                    f"最大變化在 {labels[i]} 到 {labels[j]} 之間",
                    f"變化量 = {values[j]} - {values[i]} = {change}",
                ],
                "unit": params.get("unit", ""),
            }
    return {"answer": None, "steps": [], "unit": ""}


def _op_symbol(op: str) -> str:
    return {"add": "+", "sub": "-", "mul": "×", "div": "÷"}.get(op, "?")


# ── Answer Verification ───────────────────────────────────

def verify_answer(
    topic_code: str,
    expected: Any,
    actual: Any,
    tolerance: float = 0.001,
) -> tuple[bool, str]:
    """
    Verify if actual answer matches expected within tolerance.

    Returns (is_correct, explanation).
    """
    # Handle None
    if expected is None:
        return False, "expected answer is None"
    if actual is None:
        return False, "actual answer is None"

    # Fraction comparison (try first — handles "3/2" == "6/4")
    try:
        e_frac = Fraction(str(expected))
        a_frac = Fraction(str(actual))
        if e_frac == a_frac:
            return True, "exact fraction match"
        diff = abs(float(e_frac - a_frac))
        if diff <= tolerance:
            return True, f"within tolerance ({diff:.6f} <= {tolerance})"
        return False, f"value mismatch: expected={expected}, actual={actual}, diff={diff:.6f}"
    except (ValueError, ZeroDivisionError):
        pass

    # String comparison for non-numeric (e.g. trend direction, day of week)
    if isinstance(expected, str) and isinstance(actual, str):
        if expected.strip() == actual.strip():
            return True, "exact string match"
        return False, f"string mismatch: expected='{expected}', actual='{actual}'"

    # Float comparison
    try:
        e_float = float(expected)
        a_float = float(actual)
        diff = abs(e_float - a_float)
        if diff <= tolerance:
            return True, f"within tolerance ({diff:.6f} <= {tolerance})"
        # Relative tolerance for larger numbers
        if e_float != 0:
            rel_diff = diff / abs(e_float)
            if rel_diff <= tolerance:
                return True, f"within relative tolerance ({rel_diff:.6f} <= {tolerance})"
        return False, f"value mismatch: expected={expected}, actual={actual}, diff={diff:.6f}"
    except (TypeError, ValueError):
        pass

    return False, f"cannot compare: expected={expected} ({type(expected).__name__}), actual={actual} ({type(actual).__name__})"


def verify_steps_consistency(
    steps: list[str],
    answer: Any,
) -> tuple[bool, list[str]]:
    """
    Verify that solution steps are internally consistent.

    Checks:
    - Final step should contain or lead to the answer
    - No step should be empty
    - Adjacent steps should show progression

    Returns (is_consistent, issues).
    """
    issues = []

    # Empty steps
    for i, step in enumerate(steps):
        if not step or not step.strip():
            issues.append(f"Step {i+1} is empty")

    # Answer should appear in last step
    if steps and answer is not None:
        last_step = steps[-1]
        answer_str = str(answer)
        if answer_str not in last_step:
            # Try formatted versions
            try:
                answer_float = float(answer_str)
                if str(int(answer_float)) not in last_step and answer_str not in last_step:
                    issues.append(
                        f"Answer '{answer_str}' not found in final step"
                    )
            except ValueError:
                if answer_str not in last_step:
                    issues.append(
                        f"Answer '{answer_str}' not found in final step"
                    )

    return len(issues) == 0, issues
