"""Tests for pipeline/oer_fetcher.py"""
from __future__ import annotations

import pytest
from pipeline.oer_fetcher import (
    STAGE_III_TOPICS,
    SEED_TEMPLATES,
    generate_seed_problems,
    OERFetcher,
    normalize_to_problem_schema,
    compute_topic_coverage,
)


# ── Curriculum Structure ──────────────────────────────────

class TestStageIIITopics:
    def test_topics_exist(self):
        assert len(STAGE_III_TOPICS) > 0

    def test_all_topics_have_required_fields(self):
        required = {"name", "performance", "grade", "keywords", "problem_types"}
        for code, info in STAGE_III_TOPICS.items():
            for field in required:
                assert field in info, f"{code} missing field: {field}"

    def test_grades_are_5_or_6(self):
        for code, info in STAGE_III_TOPICS.items():
            assert info["grade"] in (5, 6), f"{code} has invalid grade: {info['grade']}"

    def test_performance_codes_valid(self):
        valid_prefixes = {"n-III", "s-III", "r-III", "d-III"}
        for code, info in STAGE_III_TOPICS.items():
            perf = info["performance"]
            prefix = "-".join(perf.split("-")[:2])
            assert prefix in valid_prefixes, f"{code}: invalid performance code {perf}"

    def test_core_topics_present(self):
        assert "N-5-10" in STAGE_III_TOPICS  # 百分率
        assert "N-6-7" in STAGE_III_TOPICS   # 速度
        assert "N-6-3" in STAGE_III_TOPICS   # 分數除法
        assert "S-6-2" in STAGE_III_TOPICS   # 比例尺
        assert "D-5-1" in STAGE_III_TOPICS   # 折線圖


# ── Seed Templates ────────────────────────────────────────

class TestSeedTemplates:
    def test_templates_exist_for_core(self):
        core = ["N-5-10", "N-5-11", "N-6-3", "N-6-7", "S-6-2", "D-5-1"]
        for code in core:
            assert code in SEED_TEMPLATES, f"No template for {code}"

    def test_templates_have_required_fields(self):
        for code, templates in SEED_TEMPLATES.items():
            for tmpl in templates:
                assert "template" in tmpl
                assert "operation" in tmpl
                assert "answer_type" in tmpl


# ── Seed Generation ───────────────────────────────────────

class TestGenerateSeedProblems:
    def test_generates_correct_count(self):
        problems = generate_seed_problems("N-5-10", count=3, seed=42)
        assert len(problems) == 3

    def test_deterministic_with_same_seed(self):
        a = generate_seed_problems("N-5-10", count=3, seed=42)
        b = generate_seed_problems("N-5-10", count=3, seed=42)
        for pa, pb in zip(a, b):
            assert pa["question"] == pb["question"]
            assert pa["id"] == pb["id"]

    def test_different_with_different_seed(self):
        a = generate_seed_problems("N-5-10", count=3, seed=42)
        b = generate_seed_problems("N-5-10", count=3, seed=99)
        # At least some should differ
        questions_a = {p["question"] for p in a}
        questions_b = {p["question"] for p in b}
        assert questions_a != questions_b

    def test_problem_structure(self):
        problems = generate_seed_problems("N-5-10", count=1, seed=42)
        p = problems[0]
        assert "id" in p
        assert "grade" in p
        assert "stage" in p
        assert p["stage"] == "III"
        assert "topic_codes" in p
        assert "question" in p
        assert "source" in p
        assert "_solver_params" in p

    def test_source_is_public_domain(self):
        problems = generate_seed_problems("N-5-10", count=1, seed=42)
        src = problems[0]["source"]
        assert src["license_type"] == "public-domain"
        assert src["license_decision"] == "allow"

    def test_unknown_topic_returns_empty(self):
        problems = generate_seed_problems("X-9-9", count=3, seed=42)
        assert problems == []

    def test_n6_7_speed_problems(self):
        problems = generate_seed_problems("N-6-7", count=2, seed=42)
        assert len(problems) == 2
        for p in problems:
            assert "N-6-7" in p["topic_codes"]

    def test_d5_1_data_problems(self):
        problems = generate_seed_problems("D-5-1", count=2, seed=42)
        assert len(problems) == 2
        for p in problems:
            params = p.get("_solver_params", {})
            assert "values" in params


# ── OER Fetcher ───────────────────────────────────────────

class TestOERFetcher:
    def test_offline_mode(self):
        fetcher = OERFetcher(offline=True)
        seeds = fetcher.fetch_topic_seeds("N-5-10", count=3)
        assert len(seeds) == 3

    def test_cache_roundtrip(self, tmp_path):
        fetcher = OERFetcher(offline=True)
        fetcher.cache_dir = tmp_path
        items = [{"id": "test-1", "question": "test?"}]
        fetcher.save_to_cache("TEST-1", items)
        loaded = fetcher.get_cached("TEST-1")
        assert len(loaded) == 1
        assert loaded[0]["id"] == "test-1"

    def test_cache_empty(self, tmp_path):
        fetcher = OERFetcher(offline=True)
        fetcher.cache_dir = tmp_path
        loaded = fetcher.get_cached("NONEXISTENT")
        assert loaded == []


# ── Content Normalization ─────────────────────────────────

class TestNormalizeToProblemSchema:
    def test_basic_normalization(self):
        raw = {
            "question": "1/2 + 1/3 = ?",
            "answer": "5/6",
            "answer_type": "fraction",
        }
        result = normalize_to_problem_schema(
            raw, "N-5-5",
            "https://market.cloud.edu.tw/test",
            "CC BY 4.0",
        )
        assert "error" not in result
        assert result["grade"] == 5
        assert result["stage"] == "III"
        assert result["source"]["license_type"] == "CC BY 4.0"

    def test_textbook_reproduction_blocked(self):
        raw = {
            "question": "翰林版課本第5頁第3題",
        }
        result = normalize_to_problem_schema(
            raw, "N-5-5",
            "https://example.com",
            "CC BY 4.0",
        )
        assert result.get("blocked") is True

    def test_license_included(self):
        raw = {"question": "2 + 3 = ?"}
        result = normalize_to_problem_schema(
            raw, "N-5-1",
            "https://market.cloud.edu.tw/math",
            "CC BY-NC-SA 4.0",
        )
        assert result["source"]["license_decision"] == "allow"


# ── Topic Coverage ────────────────────────────────────────

class TestTopicCoverage:
    def test_empty_coverage(self):
        coverage = compute_topic_coverage([])
        assert coverage["covered_count"] == 0
        assert len(coverage["missing_topics"]) == coverage["total_topics"]

    def test_partial_coverage(self):
        problems = [
            {"topic_codes": ["n-III-9", "N-5-10"]},
            {"topic_codes": ["n-III-11", "N-6-7"]},
        ]
        coverage = compute_topic_coverage(problems)
        assert coverage["covered_count"] >= 2
        assert coverage["coverage_rate"] > 0

    def test_counts_correct(self):
        problems = [
            {"topic_codes": ["N-5-10"]},
            {"topic_codes": ["N-5-10"]},
            {"topic_codes": ["N-6-7"]},
        ]
        coverage = compute_topic_coverage(problems)
        assert coverage["topic_counts"]["N-5-10"] == 2
        assert coverage["topic_counts"]["N-6-7"] == 1
