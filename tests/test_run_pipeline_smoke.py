"""Smoke test for scripts/run_pipeline.py — verifies end-to-end pipeline."""
import json
from pathlib import Path

from scripts.run_pipeline import run_pipeline


def test_run_pipeline_smoke(tmp_path):
    out_dir = tmp_path / "pipeline_out"

    summary = run_pipeline(
        out_dir=out_dir,
        per_template=2,
        seed=42,
        limit_templates=3,
    )

    # Output files exist
    assert (out_dir / "questions_dump.jsonl").exists()
    assert (out_dir / "questions_dump.md").exists()
    assert (out_dir / "pipeline_report.md").exists()
    assert (out_dir / "pipeline_summary.json").exists()

    # Summary structure
    assert "ok" in summary
    assert "export" in summary
    assert "schema" in summary
    assert "math" in summary
    assert "hints" in summary

    # Schema must pass (hard requirement)
    assert summary["schema"]["failed"] == 0

    # At least some items were generated
    assert summary["export"]["total_items"] >= 6

    # JSONL is parseable
    lines = (out_dir / "questions_dump.jsonl").read_text(encoding="utf-8").splitlines()
    for line in lines:
        obj = json.loads(line)
        assert "question" in obj
        assert "answer" in obj
        assert "hints" in obj
        assert len(obj["hints"]) == 3


def test_pipeline_summary_json_roundtrip(tmp_path):
    out_dir = tmp_path / "pipeline_rt"

    run_pipeline(
        out_dir=out_dir,
        per_template=1,
        seed=99,
        limit_templates=2,
    )

    summary_path = out_dir / "pipeline_summary.json"
    assert summary_path.exists()
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    assert isinstance(s["ok"], bool)
    assert isinstance(s["schema"]["passed"], int)
