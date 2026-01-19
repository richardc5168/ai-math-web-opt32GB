import pytest

import fraction_logic


def test_parse_rational_mixed():
    r = fraction_logic.parse_rational("2 1/3")
    assert int(r.p) == 7
    assert int(r.q) == 3


def test_parse_rational_fraction():
    r = fraction_logic.parse_rational("14/15")
    assert int(r.p) == 14
    assert int(r.q) == 15


def test_diagnose_step1_missing_flags_E3():
    rep = fraction_logic.diagnose_mixed_multiply(left="2 1/4", right="3", step1="", step2="", step3="")
    assert rep.ok is False
    assert rep.weak_id == "E3"


def test_diagnose_step2_wrong_flags_E4():
    # correct step1: 2 1/4 = 9/4
    rep = fraction_logic.diagnose_mixed_multiply(left="2 1/4", right="3/5", step1="9/4", step2="27/25", step3="")
    assert rep.ok is False
    assert rep.weak_id == "E4"


def test_diagnose_step2_common_wrong_multiply_denominator_only_has_hint():
    # A common kid mistake for (a/b)×k is to do a/(b*k).
    rep = fraction_logic.diagnose_mixed_multiply(left="2 1/4", right="3", step1="9/4", step2="9/12", step3="")
    assert rep.ok is False
    assert rep.weak_id == "E4"
    assert "分子" in rep.message


def test_diagnose_all_correct_ok():
    rep = fraction_logic.diagnose_mixed_multiply(left="1 1/2", right="2 2/3", step1="3/2", step2="24/6", step3="4")
    assert rep.ok is True
    assert rep.weak_id == "E5"


def test_diagnose_E2_reduce_numerator_only():
    # Correct: (3/2)×(8/3) = 24/6 = 4
    # Wrong reduce: divide only numerator 24/6 -> 12/6 (=2)
    rep = fraction_logic.diagnose_mixed_multiply(left="1 1/2", right="2 2/3", step1="3/2", step2="24/6", step3="12/6")
    assert rep.ok is False
    assert rep.weak_id == "E2"
    assert rep.diagnosis_code == "E2_REDUCE_NUM_ONLY"
    assert "分子" in rep.message


def test_diagnose_E2_reduce_denominator_only():
    # Wrong reduce: divide only denominator 24/6 -> 24/3 (=8)
    rep = fraction_logic.diagnose_mixed_multiply(left="1 1/2", right="2 2/3", step1="3/2", step2="24/6", step3="24/3")
    assert rep.ok is False
    assert rep.weak_id == "E2"
    assert rep.diagnosis_code == "E2_REDUCE_DEN_ONLY"
    assert "分母" in rep.message


def test_diagnose_E2_reduce_by_different_numbers():
    # Wrong reduce: numerator ÷2, denominator ÷3 (different divisors)
    rep = fraction_logic.diagnose_mixed_multiply(left="1 1/2", right="2 2/3", step1="3/2", step2="24/6", step3="12/2")
    assert rep.ok is False
    assert rep.weak_id == "E2"
    assert rep.diagnosis_code == "E2_REDUCE_DIFFERENT_DIVISORS"
    assert "同除" in rep.message
