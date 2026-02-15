import json

from scripts.question_review import iter_reviews_jsonl_lines, validate_review_item


def test_validate_review_item_ok():
    obj = {
        "template_id": "t1",
        "seed": 123,
        "scores": {
            "question_quality": 4,
            "answer_correctness": 5,
            "hint_clarity_for_kids": 4,
            "stepwise_guidance": 4,
            "math_rigor": 5,
        },
        "issues": [{"type": "wording", "detail": "用字稍微難"}],
        "rewrite_hints": ["先想要用什麼運算。", "把題目變成算式。", "算出答案並檢查單位。"],
        "rewrite_solution_steps": ["列式", "計算"],
    }

    assert validate_review_item(obj) == []


def test_iter_reviews_jsonl_lines_flags_errors():
    good = {
        "template_id": "t1",
        "seed": 1,
        "scores": {
            "question_quality": 3,
            "answer_correctness": 3,
            "hint_clarity_for_kids": 3,
            "stepwise_guidance": 3,
            "math_rigor": 3,
        },
        "issues": [],
        "rewrite_hints": ["a", "b", "c"],
    }
    bad = {"template_id": "", "seed": "x"}

    text = json.dumps(good, ensure_ascii=False) + "\n" + json.dumps(bad, ensure_ascii=False) + "\n"

    rows = list(iter_reviews_jsonl_lines(text))
    assert len(rows) == 2

    _, _, err1 = rows[0]
    assert err1 == []

    _, _, err2 = rows[1]
    assert err2
