from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_teacher_dashboard_mentions_high_risk_and_before_after():
    html = _read("docs/school-first/teacher-dashboard/index.html")
    assert "High-risk students" in html
    assert "Before / After" in html
    assert "risk_score" in html


def test_parent_view_is_single_child_only():
    html = _read("docs/school-first/parent-view/index.html")
    assert "single-child" in html
    assert "class-wide" in html


def test_admin_dashboard_is_global():
    html = _read("docs/school-first/admin-dashboard/index.html")
    assert "Platform-wide" in html
    assert "Teacher / class rollup" in html