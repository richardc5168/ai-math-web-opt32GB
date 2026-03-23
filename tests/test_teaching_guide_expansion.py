"""R33/EXP-P3-08: Tests for teaching guide expansion — all 10 domains covered."""

from __future__ import annotations

import pytest

from learning.teaching import TeachingGuide, get_teaching_guide


# All 10 taxonomy domains must have non-fallback guides
ALL_DOMAINS_EN = [
    "arithmetic",
    "fraction",
    "decimal",
    "percent",
    "unit_conversion",
    "volume",
    "geometry",
    "application",
    "linear",
    "quadratic",
]

ALL_DOMAINS_ZH = [
    "四則運算",
    "分數/小數",
    "小數",
    "比例",
    "單位換算",
    "路程時間",
    "折扣",
    "體積",
    "幾何",
    "一元方程",
    "二次方程",
    "平均/應用",
]


class TestAllDomainsHaveGuides:
    """Every taxonomy domain should return a non-fallback guide."""

    @pytest.mark.parametrize("domain", ALL_DOMAINS_EN)
    def test_english_domain_has_guide(self, domain):
        guide = get_teaching_guide(domain)
        assert isinstance(guide, TeachingGuide)
        # Fallback title starts with "加強："; a real guide should not
        assert not guide.title.startswith("加強："), f"Domain '{domain}' still falls back to generic guide"

    @pytest.mark.parametrize("skill_tag", ALL_DOMAINS_ZH)
    def test_chinese_skill_tag_has_guide(self, skill_tag):
        guide = get_teaching_guide(skill_tag)
        assert isinstance(guide, TeachingGuide)
        assert not guide.title.startswith("加強："), f"Skill tag '{skill_tag}' still falls back to generic guide"


class TestGuideStructure:
    """TeachingGuide fields should be non-empty."""

    @pytest.mark.parametrize("domain", ALL_DOMAINS_EN)
    def test_guide_has_content(self, domain):
        guide = get_teaching_guide(domain)
        assert len(guide.key_ideas) >= 2, f"'{domain}' has too few key_ideas"
        assert len(guide.common_mistakes) >= 2, f"'{domain}' has too few common_mistakes"
        assert guide.practice_goal
        assert guide.mastery_check


class TestFallbackStillWorks:
    """Unknown skill tags should still return a generic fallback."""

    def test_unknown_tag_gives_fallback(self):
        guide = get_teaching_guide("nonexistent_skill")
        assert guide.title.startswith("加強：")
        assert guide.skill_tag == "nonexistent_skill"

    def test_empty_tag_gives_fallback(self):
        guide = get_teaching_guide("")
        assert isinstance(guide, TeachingGuide)

    def test_none_tag_gives_fallback(self):
        guide = get_teaching_guide(None)
        assert isinstance(guide, TeachingGuide)


class TestNewGuides:
    """Spot-check newly added guides."""

    def test_decimal_guide_has_conversion_idea(self):
        guide = get_teaching_guide("小數")
        assert any("小數" in idea for idea in guide.key_ideas)

    def test_volume_guide_mentions_cube(self):
        guide = get_teaching_guide("體積")
        assert any("長方體" in idea or "正方體" in idea for idea in guide.key_ideas)

    def test_geometry_guide_mentions_area(self):
        guide = get_teaching_guide("幾何")
        assert any("面積" in idea or "長方形" in idea for idea in guide.key_ideas)

    def test_linear_guide_mentions_equation(self):
        guide = get_teaching_guide("一元方程")
        assert any("移項" in idea or "方程" in idea for idea in guide.key_ideas)

    def test_quadratic_guide_mentions_formula(self):
        guide = get_teaching_guide("二次方程")
        assert any("因式" in idea or "公式" in idea for idea in guide.key_ideas)

    def test_application_guide_mentions_average(self):
        guide = get_teaching_guide("平均/應用")
        assert any("平均" in idea for idea in guide.key_ideas)

    def test_english_alias_returns_same_object(self):
        """English alias must return same TeachingGuide object as Chinese key."""
        assert get_teaching_guide("decimal") is get_teaching_guide("小數")
        assert get_teaching_guide("volume") is get_teaching_guide("體積")
        assert get_teaching_guide("geometry") is get_teaching_guide("幾何")
        assert get_teaching_guide("linear") is get_teaching_guide("一元方程")
        assert get_teaching_guide("quadratic") is get_teaching_guide("二次方程")
        assert get_teaching_guide("application") is get_teaching_guide("平均/應用")
