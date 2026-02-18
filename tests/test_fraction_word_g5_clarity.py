from __future__ import annotations

import random
import re

from fraction_word_g5 import _is_ambiguous_wording, generate_fraction_word_problem_g5


def test_ambiguous_wording_detector_hits_target_pattern():
    bad = "一本書有 126 頁，先看了 1/3，剩下的又看了 1，還剩多少頁？"
    assert _is_ambiguous_wording(bad) is True


def test_ambiguous_wording_detector_hits_one_over_one_pattern():
    bad = "一本書有 126 頁，先看了 1/3，剩下的又看了 1/1，還剩多少頁？"
    assert _is_ambiguous_wording(bad) is True


def test_generator_avoids_ambiguous_wording():
    pattern = re.compile(r"剩下的又(?:看了|用掉|用了)\s*1(?:\s*/\s*1)?(?=[\s，。；！？])")
    random.seed(20260218)

    for _ in range(400):
        q = generate_fraction_word_problem_g5().get("question", "")
        assert not pattern.search(str(q)), q
