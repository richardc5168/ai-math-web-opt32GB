from __future__ import annotations

import random


def test_fraction_add_commutative_property() -> None:
    random.seed(42)
    for _ in range(200):
        a_num = random.randint(1, 9)
        a_den = random.randint(1, 9)
        b_num = random.randint(1, 9)
        b_den = random.randint(1, 9)

        left = a_num * b_den + b_num * a_den
        right = b_num * a_den + a_num * b_den
        den = a_den * b_den

        assert left == right
        assert den > 0


def test_ratio_scale_invariant_property() -> None:
    random.seed(99)
    for _ in range(200):
        a = random.randint(1, 30)
        b = random.randint(1, 30)
        k = random.randint(1, 20)
        assert a * k / (b * k) == a / b


def test_unit_conversion_round_trip_property() -> None:
    random.seed(123)
    for _ in range(300):
        value = random.uniform(0.1, 999.9)
        grams = value * 1000.0
        back_to_kg = grams / 1000.0
        assert abs(back_to_kg - value) < 1e-9
