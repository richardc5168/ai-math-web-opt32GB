from __future__ import annotations

import json
from pathlib import Path

from coach_report import aggregate, classify_quadrant, hint_depth_key


def test_quadrant_classification_and_depth_keys() -> None:
    items = json.loads(Path("coaching_meta/attempts.sample.json").read_text(encoding="utf-8"))

    qa = classify_quadrant(items[0])
    qb = classify_quadrant(items[1])
    qc = classify_quadrant(items[2])
    qd = classify_quadrant(items[3])

    assert qa == "A"
    assert qb == "B"
    assert qc == "C"
    assert qd == "D"

    assert hint_depth_key(items[0]) == "none"
    assert hint_depth_key(items[1]) == "L2"
    assert hint_depth_key(items[2]) == "solution"


def test_aggregate_outputs_kpi_and_by_kind_counts() -> None:
    items = json.loads(Path("coaching_meta/attempts.sample.json").read_text(encoding="utf-8"))
    out = aggregate(items)

    assert out["kpi"]["total"] == 4
    assert out["overall"]["n"] == 4
    assert out["overall"]["correct"] == 2

    # By kind should include all 4 kinds.
    kinds = {x["kind"]: x for x in out["by_kind"]}
    assert set(kinds.keys()) == {"ratio_part_total", "x10_shift", "add_like", "buy_many"}

    assert kinds["ratio_part_total"]["independent_correct"] == 1
    assert kinds["x10_shift"]["hint_correct"] == 1
    assert kinds["add_like"]["hint_wrong"] == 1
    assert kinds["buy_many"]["nohint_wrong"] == 1

    # Histogram sanity
    assert out["overall"]["hint_level_hist"]["none"] == 2
    assert out["overall"]["hint_level_hist"]["L2"] == 1
    assert out["overall"]["hint_level_hist"]["solution"] == 1
