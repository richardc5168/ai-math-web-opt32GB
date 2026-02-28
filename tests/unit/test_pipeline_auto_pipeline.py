"""Tests for pipeline/auto_pipeline.py"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pipeline.auto_pipeline import (
    step_fetch,
    step_generate_and_solve,
    step_verify,
    step_route,
    self_refine_loop,
    run_pipeline,
    AUTO_PUBLISH_THRESHOLD,
    HUMAN_REVIEW_THRESHOLD,
)


# ── Step Functions ────────────────────────────────────────

class TestStepFetch:
    def test_returns_list(self):
        result = step_fetch("N-5-10", count=2, offline=True)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_each_has_question(self):
        result = step_fetch("N-5-10", count=1, offline=True)
        for item in result:
            assert "question" in item

    def test_unknown_topic(self):
        result = step_fetch("X-9-9", count=1, offline=True)
        assert result == []


class TestStepGenerateAndSolve:
    def test_adds_pipeline_status(self):
        raw = step_fetch("N-5-10", count=1, offline=True)
        if not raw:
            pytest.skip("no seed for topic")
        solved = step_generate_and_solve(raw, "N-5-10")
        for item in solved:
            assert "pipeline_status" in item

    def test_preserves_question(self):
        raw = step_fetch("N-5-10", count=1, offline=True)
        if not raw:
            pytest.skip("no seed for topic")
        solved = step_generate_and_solve(raw, "N-5-10")
        assert solved[0]["question"] == raw[0]["question"]


class TestStepVerify:
    def test_returns_verified(self):
        raw = step_fetch("N-5-10", count=1, offline=True)
        if not raw:
            pytest.skip("no seed for topic")
        solved = step_generate_and_solve(raw, "N-5-10")
        verified = step_verify(solved)
        for item in verified:
            if item.get("pipeline_status") == "verified":
                assert "verification" in item

    def test_pipeline_status_set(self):
        raw = step_fetch("N-5-10", count=1, offline=True)
        if not raw:
            pytest.skip("no seed for topic")
        solved = step_generate_and_solve(raw, "N-5-10")
        verified = step_verify(solved)
        for item in verified:
            assert "pipeline_status" in item


class TestStepRoute:
    def test_auto_publish_high_score(self):
        items = [{
            "id": "test-1", "question": "q?",
            "pipeline_status": "verified",
            "verification": {"score": 95, "passed": True},
        }]
        routed = step_route(items)
        assert routed["auto_publish"]
        assert not routed["human_review"]

    def test_human_review_mid_score(self):
        items = [{
            "id": "test-1", "question": "q?",
            "pipeline_status": "verified",
            "verification": {"score": 75, "passed": False},
        }]
        routed = step_route(items)
        assert not routed["auto_publish"]
        assert routed["human_review"]

    def test_rejected_low_score(self):
        items = [{
            "id": "test-1", "question": "q?",
            "pipeline_status": "verified",
            "verification": {"score": 50, "passed": False},
        }]
        routed = step_route(items)
        assert not routed["auto_publish"]
        assert not routed["human_review"]
        assert routed["rejected"]

    def test_solver_error_rejected(self):
        items = [{
            "id": "test-1", "question": "q?",
            "pipeline_status": "solver_error: oops",
        }]
        routed = step_route(items)
        assert routed["rejected"]

    def test_thresholds(self):
        assert AUTO_PUBLISH_THRESHOLD >= HUMAN_REVIEW_THRESHOLD


# ── Self Refine ───────────────────────────────────────────

class TestSelfRefineLoop:
    def test_returns_problem_dict(self):
        problem = {"id": "t1", "question": "q?", "answer": "a",
                   "pipeline_status": "solved"}
        refined = self_refine_loop(problem, "N-5-10", max_iterations=1)
        assert isinstance(refined, dict)

    def test_sets_refine_iterations(self):
        problem = {"id": "t1", "question": "q?", "answer": "a",
                   "pipeline_status": "solved"}
        refined = self_refine_loop(problem, "N-5-10", max_iterations=2)
        assert "_refine_iterations" in refined


# ── Full Pipeline ─────────────────────────────────────────

class TestRunPipeline:
    def test_dry_run(self):
        result = run_pipeline(
            topic_codes=["N-5-10"],
            count=2,
            offline=True,
            dry_run=True,
        )
        assert "results" in result
        assert "N-5-10" in result["results"]

    def test_summary_fields(self):
        result = run_pipeline(
            topic_codes=["N-5-10"],
            count=2,
            offline=True,
            dry_run=True,
        )
        summary = result["summary"]
        assert "total_generated" in summary
        assert "auto_publish" in summary
        assert "human_review" in summary
        assert "rejected" in summary

    def test_multi_topic(self):
        result = run_pipeline(
            topic_codes=["N-5-10", "N-6-7"],
            count=1,
            offline=True,
            dry_run=True,
        )
        assert len(result["results"]) >= 1

    def test_unknown_topic_produces_empty(self):
        result = run_pipeline(
            topic_codes=["X-9-9"],
            count=1,
            offline=True,
            dry_run=True,
        )
        # Unknown topic: fetch returns empty → no results
        assert result["summary"]["total_generated"] == 0
