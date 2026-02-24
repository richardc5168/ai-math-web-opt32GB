import json
from pathlib import Path


NOTES_PATH = Path("data/external_web_notes/fraction_decimal_notes.jsonl")
PACK_PATH = Path("data/fraction_decimal_application_web_v1_pack.json")


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def test_fraction_decimal_notes_contract():
    notes = _read_jsonl(NOTES_PATH)
    assert len(notes) >= 10

    for note in notes:
        assert str(note.get("source_url") or "")
        assert str(note.get("title") or "")
        assert str(note.get("retrieved_at") or "")
        assert str(note.get("grade") or "") in ("5", "6")
        tags = note.get("topic_tags") or []
        assert isinstance(tags, list) and len(tags) >= 1
        assert str(note.get("summary") or "")
        steps = note.get("key_steps") or []
        assert isinstance(steps, list) and len(steps) >= 3
        mistakes = note.get("common_mistakes") or []
        assert isinstance(mistakes, list) and len(mistakes) >= 5
        patterns = note.get("example_patterns") or []
        assert isinstance(patterns, list) and len(patterns) >= 4


def test_fraction_decimal_pack_contract():
    data = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    items = data.get("items") or []
    assert data.get("type_key") == "fraction_decimal_application_web_v1"
    assert len(items) >= 30

    categories = set()
    for item in items:
        categories.add(str(item.get("category") or ""))
        assert str(item.get("question") or "")
        assert str(item.get("answer") or "")
        ladder = item.get("hint_ladder") or {}
        assert str(ladder.get("h1_strategy") or "")
        assert str(ladder.get("h2_equation") or "")
        assert str(ladder.get("h3_compute") or "")
        assert str(ladder.get("h4_check_reflect") or "")

        diagnostics = item.get("error_diagnostics") or []
        assert isinstance(diagnostics, list) and len(diagnostics) >= 5

    assert {"shopping_discount", "average_distribution", "unit_conversion", "distance_time"}.issubset(categories)
