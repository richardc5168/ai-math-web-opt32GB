import json
from pathlib import Path


def test_apply_question_reviews_smoke(tmp_path, monkeypatch):
    # Create a minimal hint_overrides.py copy.
    hint_overrides = tmp_path / "hint_overrides.py"
    hint_overrides.write_text(
        "from __future__ import annotations\n\nfrom typing import Any, Dict\n\nHINT_OVERRIDES: Dict[str, Dict[str, Any]] = {\n}\n",
        encoding="utf-8",
    )

    reviews_path = tmp_path / "question_reviews.jsonl"
    good = {
        "template_id": "11",
        "seed": 123,
        "scores": {
            "question_quality": 3,
            "answer_correctness": 3,
            "hint_clarity_for_kids": 5,
            "stepwise_guidance": 5,
            "math_rigor": 4,
        },
        "issues": [],
        "rewrite_hints": [
            "先看題目是在說『用掉/剩下』還是『平均分』。",
            "把題目變成算式（先...再...）。",
            "算出答案，最後檢查單位和合理性。",
        ],
    }
    reviews_path.write_text(json.dumps(good, ensure_ascii=False) + "\n", encoding="utf-8")

    from scripts.apply_question_reviews import build_hint_override_patch

    patch = build_hint_override_patch(
        hint_overrides_path=Path(hint_overrides),
        new_entries={
            "11": {
                "level1": good["rewrite_hints"][0],
                "level2": good["rewrite_hints"][1],
                "level3": good["rewrite_hints"][2],
                "source": "external_llm",
                "note": "candidate",
            }
        },
    )

    assert "HINT_OVERRIDES" in patch
    assert '"11"' in patch
    assert "approved" in patch
