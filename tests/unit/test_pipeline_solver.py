"""Tests for pipeline/deterministic_solver.py"""
from __future__ import annotations

import pytest
from fractions import Fraction
from pipeline.deterministic_solver import (
    fraction_add, fraction_sub, fraction_mul, fraction_div,
    simplify_fraction, mixed_to_improper, improper_to_mixed,
    decimal_add, decimal_sub, decimal_mul, decimal_div,
    to_percent, from_percent, discount_price, percent_of, ratio_simplify,
    round_to_place, round_to_digits,
    speed_from_distance_time, distance_from_speed_time, time_from_distance_speed,
    convert_speed_unit,
    scale_actual_to_map, scale_map_to_actual, scale_find_denominator,
    mean, data_range, trend_direction, find_max_change,
    solve, verify_answer, verify_steps_consistency,
)


# ── Fraction Operations ───────────────────────────────────

class TestFractionOperations:
    def test_add(self):
        assert fraction_add("1/3", "1/6") == "1/2"

    def test_add_whole(self):
        assert fraction_add("2", "1/2") == "5/2"

    def test_sub(self):
        assert fraction_sub("3/4", "1/4") == "1/2"

    def test_mul(self):
        assert fraction_mul("2/3", "3/4") == "1/2"

    def test_div(self):
        assert fraction_div("2/3", "4/3") == "1/2"

    def test_div_by_zero(self):
        with pytest.raises(ValueError):
            fraction_div("1/2", "0")

    def test_simplify(self):
        assert simplify_fraction("4/8") == "1/2"

    def test_mixed_to_improper(self):
        assert mixed_to_improper(2, 1, 3) == "7/3"

    def test_improper_to_mixed(self):
        whole, rem = improper_to_mixed("7/3")
        assert whole == 2
        assert Fraction(rem) == Fraction(1, 3)


# ── Decimal Operations ────────────────────────────────────

class TestDecimalOperations:
    def test_add(self):
        assert decimal_add(0.1, 0.2) == pytest.approx(0.3)

    def test_sub(self):
        assert decimal_sub(0.5, 0.2) == pytest.approx(0.3)

    def test_mul(self):
        assert decimal_mul(0.3, 0.4) == pytest.approx(0.12)

    def test_div(self):
        assert decimal_div(0.6, 0.3) == pytest.approx(2.0)

    def test_div_by_zero(self):
        with pytest.raises(ValueError):
            decimal_div(1.0, 0.0)


# ── Percentage / Ratio ─────────────────────────────────────

class TestPercentRatio:
    def test_to_percent(self):
        assert to_percent(0.25) == pytest.approx(25.0)

    def test_from_percent(self):
        assert from_percent(75) == pytest.approx(0.75)

    def test_discount_price(self):
        assert discount_price(1000, 0.8) == pytest.approx(800.0)

    def test_percent_of(self):
        assert percent_of(50, 10) == pytest.approx(20.0)

    def test_percent_of_zero_whole(self):
        with pytest.raises(ValueError):
            percent_of(0, 10)

    def test_ratio_simplify(self):
        assert ratio_simplify(12, 8) == (3, 2)

    def test_ratio_simplify_coprime(self):
        assert ratio_simplify(7, 3) == (7, 3)


# ── Rounding ──────────────────────────────────────────────

class TestRounding:
    def test_round_ones(self):
        assert round_to_place(3.14, "ones") == 3

    def test_round_tenths(self):
        assert round_to_place(3.14, "tenths") == pytest.approx(3.1)

    def test_round_tens(self):
        assert round_to_place(345, "tens") == 340  # Python rounds 345 to 340

    def test_round_to_digits(self):
        assert round_to_digits(3.14159, 2) == pytest.approx(3.14)

    def test_round_unknown_place(self):
        with pytest.raises(ValueError):
            round_to_place(1.0, "galaxies")


# ── Speed / Distance / Time ───────────────────────────────

class TestSpeedDistanceTime:
    def test_speed(self):
        assert speed_from_distance_time(100, 2) == pytest.approx(50.0)

    def test_distance(self):
        assert distance_from_speed_time(60, 3) == pytest.approx(180.0)

    def test_time(self):
        assert time_from_distance_speed(150, 50) == pytest.approx(3.0)

    def test_speed_zero_time(self):
        with pytest.raises(ValueError):
            speed_from_distance_time(100, 0)

    def test_time_zero_speed(self):
        with pytest.raises(ValueError):
            time_from_distance_speed(100, 0)

    def test_convert_km_h_to_m_s(self):
        result = convert_speed_unit(36, "km/h", "m/s")
        assert result == pytest.approx(10.0)

    def test_convert_unsupported(self):
        with pytest.raises(ValueError):
            convert_speed_unit(1, "miles/h", "m/s")


# ── Scale / Map ───────────────────────────────────────────

class TestScale:
    def test_actual_to_map(self):
        assert scale_actual_to_map(5000, 50000) == pytest.approx(0.1)

    def test_map_to_actual(self):
        assert scale_map_to_actual(3, 25000) == pytest.approx(75000.0)

    def test_find_denominator(self):
        assert scale_find_denominator(1, 50000) == 50000

    def test_zero_scale(self):
        with pytest.raises(ValueError):
            scale_actual_to_map(100, 0)

    def test_zero_map_dist(self):
        with pytest.raises(ValueError):
            scale_find_denominator(0, 100)


# ── Data Analysis ─────────────────────────────────────────

class TestDataAnalysis:
    def test_mean(self):
        assert mean([10, 20, 30]) == pytest.approx(20.0)

    def test_mean_empty(self):
        with pytest.raises(ValueError):
            mean([])

    def test_data_range(self):
        assert data_range([5, 15, 10, 25, 20]) == 20

    def test_trend_increasing(self):
        assert trend_direction([10, 12, 14, 16, 18]) == "increasing"

    def test_trend_decreasing(self):
        assert trend_direction([20, 18, 16, 14, 12]) == "decreasing"

    def test_trend_stable(self):
        assert trend_direction([10, 10, 10, 10]) == "stable"

    def test_max_change(self):
        i, j, change = find_max_change([10, 12, 20, 22, 15])
        assert abs(change) >= 7  # 22→15 or 12→20

    def test_max_change_too_few(self):
        with pytest.raises(ValueError):
            find_max_change([1])


# ── Universal Solver ──────────────────────────────────────

class TestSolve:
    def test_n5_10_discount(self):
        result = solve("N-5-10", {
            "operation": "discount",
            "a": 1000,
            "rate": 0.8,
        })
        assert result["answer"] == pytest.approx(800.0)
        assert len(result["steps"]) >= 2

    def test_n5_10_percent_of(self):
        result = solve("N-5-10", {
            "operation": "percent_of",
            "a": 50,
            "b": 10,
        })
        assert result["answer"] == pytest.approx(20.0)

    def test_n5_11_round(self):
        result = solve("N-5-11", {
            "a": 3.14159,
            "place": "tenths",
        })
        assert result["answer"] == pytest.approx(3.1)

    def test_n6_3_fraction_div(self):
        result = solve("N-6-3", {
            "a": "3/4",
            "b": "1/2",
        })
        assert Fraction(result["answer"]) == Fraction(3, 2)

    def test_n6_7_find_distance(self):
        result = solve("N-6-7", {
            "operation": "find_distance",
            "speed": 60,
            "time": 3,
        })
        assert result["answer"] == pytest.approx(180.0)

    def test_n6_7_find_speed(self):
        result = solve("N-6-7", {
            "operation": "find_speed",
            "distance": 200,
            "time": 4,
        })
        assert result["answer"] == pytest.approx(50.0)

    def test_s6_2_map_to_actual(self):
        result = solve("S-6-2", {
            "operation": "map_to_actual",
            "map_distance": 5,
            "scale_denominator": 10000,
        })
        assert result["answer"] == pytest.approx(50000.0)

    def test_d5_1_mean(self):
        result = solve("D-5-1", {
            "operation": "mean",
            "values": [10, 20, 30, 40, 50],
        })
        assert result["answer"] == pytest.approx(30.0)

    def test_d5_1_trend(self):
        result = solve("D-5-1", {
            "operation": "trend",
            "values": [10, 15, 20, 25, 30],
        })
        assert result["answer"] == "increasing"

    def test_unsupported_prefix(self):
        with pytest.raises(ValueError):
            solve("X-9-1", {"a": 1})


# ── Answer Verification ──────────────────────────────────

class TestVerifyAnswer:
    def test_exact_match(self):
        ok, _ = verify_answer("N-5-10", 25, 25)
        assert ok

    def test_fraction_match(self):
        ok, _ = verify_answer("N-6-3", "3/2", "6/4")
        assert ok

    def test_within_tolerance(self):
        ok, _ = verify_answer("N-5-11", 3.14, 3.1401, tolerance=0.001)
        assert ok

    def test_mismatch(self):
        ok, _ = verify_answer("N-5-10", 25, 30)
        assert not ok

    def test_string_match(self):
        ok, _ = verify_answer("D-5-1", "increasing", "increasing")
        assert ok

    def test_string_mismatch(self):
        ok, _ = verify_answer("D-5-1", "increasing", "decreasing")
        assert not ok

    def test_none_expected(self):
        ok, _ = verify_answer("N-5-10", None, 5)
        assert not ok

    def test_none_actual(self):
        ok, _ = verify_answer("N-5-10", 5, None)
        assert not ok


# ── Steps Consistency ─────────────────────────────────────

class TestVerifyStepsConsistency:
    def test_consistent(self):
        ok, issues = verify_steps_consistency(
            ["60 × 3", "= 180"],
            180,
        )
        assert ok

    def test_empty_step(self):
        ok, issues = verify_steps_consistency(
            ["Step 1", "", "= 180"],
            180,
        )
        assert not ok
        assert any("empty" in i.lower() for i in issues)

    def test_answer_in_last_step(self):
        ok, issues = verify_steps_consistency(
            ["60 × 3", "= 180"],
            180,
        )
        assert ok
