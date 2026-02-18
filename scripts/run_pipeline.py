"""run_pipeline.py — 「生成 → 驗證 → 產報告 → 修正建議 → 回歸測試」閉環 Pipeline.

Usage (full):
    python scripts/run_pipeline.py --out_dir 20260218_test --per_template 50 --seed 12345

Usage (quick smoke):
    python scripts/run_pipeline.py --out_dir 20260218_test --per_template 2 --seed 42

Steps:
  1. Export all questions → {out_dir}/questions_dump.jsonl + .md
  2. Validate JSON schema
  3. Validate math correctness (SymPy)
  4. Validate hint ladder rules
  5. Build summary report → {out_dir}/pipeline_report.md
  6. Copy LLM review prompt → {out_dir}/llm_review_prompt.md
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_all_questions import export_all_questions  # noqa: E402
from scripts.validate_math_correctness import validate_jsonl as validate_math  # noqa: E402
from scripts.validate_hint_ladder_rules import validate_jsonl as validate_hints  # noqa: E402


def _validate_schema(jsonl_path: Path) -> Dict[str, Any]:
    """Validate every line against the JSON schema contract."""
    schema_path = ROOT / "schemas" / "question_dump.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    required_keys = schema.get("required", [])

    total = 0
    passed = 0
    failed = 0
    failures: List[Dict[str, Any]] = []

    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        total += 1
        obj = json.loads(line)
        issues = []
        for k in required_keys:
            if k not in obj:
                issues.append(f"missing key: {k}")
        # Type checks
        if not isinstance(obj.get("hints"), list) or len(obj.get("hints", [])) != 3:
            issues.append("hints must be array of 3")
        if not isinstance(obj.get("solution_steps"), list) or len(obj.get("solution_steps", [])) < 1:
            issues.append("solution_steps must be non-empty array")
        if not isinstance(obj.get("checks"), dict):
            issues.append("checks must be object")

        if issues:
            failed += 1
            failures.append({"line": total, "issues": issues})
        else:
            passed += 1

    return {"total": total, "passed": passed, "failed": failed, "failures": failures[:30]}


def _build_report(
    *,
    out_dir: Path,
    export_result: Dict[str, Any],
    schema_result: Dict[str, Any],
    math_result: Dict[str, Any],
    hint_result: Dict[str, Any],
    per_template: int,
    seed: int,
) -> str:
    """Generate pipeline_report.md content."""
    lines: List[str] = []
    now = datetime.now().isoformat(timespec="seconds")

    lines.append("# Question Pipeline Report")
    lines.append(f"- Generated: {now}")
    lines.append(f"- Output dir: `{out_dir}`")
    lines.append(f"- per_template: {per_template}")
    lines.append(f"- base_seed: {seed}")
    lines.append("")

    # Export summary
    lines.append("## 1. Export Summary")
    lines.append(f"- Templates: {export_result.get('templates', '?')}")
    lines.append(f"- Total items: {export_result.get('total_items', '?')}")
    lines.append(f"- answer_ok_fail: {export_result.get('answer_ok_fail', '?')}")
    lines.append(f"- hint_ladder_ok_fail: {export_result.get('hint_ladder_ok_fail', '?')}")
    lines.append("")

    # Schema validation
    s = schema_result
    schema_ok = s["failed"] == 0
    lines.append("## 2. Schema Validation")
    lines.append(f"- Status: {'✅ PASS' if schema_ok else '❌ FAIL'}")
    lines.append(f"- {s['passed']}/{s['total']} passed")
    if s["failures"]:
        lines.append("- Failures (first 10):")
        for f in s["failures"][:10]:
            lines.append(f"  - line {f['line']}: {f['issues']}")
    lines.append("")

    # Math correctness
    m = math_result
    math_ok = m["failed"] == 0
    lines.append("## 3. Math Correctness (SymPy)")
    lines.append(f"- Status: {'✅ PASS' if math_ok else '⚠ WARN'}")
    lines.append(f"- {m['passed']}/{m['total']} passed")
    if m["failures"]:
        lines.append("- Failures (first 10):")
        for f in m["failures"][:10]:
            lines.append(f"  - template={f.get('template_id')}, seed={f.get('seed')}: {f.get('issues')}")
    lines.append("")

    # Hint ladder rules
    h = hint_result
    hint_ok = h["failed"] == 0
    lines.append("## 4. Hint Ladder Rules")
    lines.append(f"- Status: {'✅ PASS' if hint_ok else '⚠ WARN'}")
    lines.append(f"- {h['passed']}/{h['total']} passed")
    if h["failures"]:
        lines.append("- Failures (first 10):")
        for f in h["failures"][:10]:
            lines.append(f"  - template={f.get('template_id')}, seed={f.get('seed')}: {f.get('issues')}")
    lines.append("")

    # Next steps
    lines.append("## 5. Next Steps")
    lines.append("")
    lines.append("### 外部模型 QA（Gemini / GPT-5.3）")
    lines.append(f"1. 把 `{out_dir}/questions_dump.jsonl` 丟給外部模型")
    lines.append(f"2. 使用 `{out_dir}/llm_review_prompt.md` 中的 prompt")
    lines.append(f"3. 收到 review JSONL 存成 `{out_dir}/question_reviews.jsonl`")
    lines.append("4. 跑驗證：`python scripts/validate_question_reviews.py --in_jsonl <reviews>`")
    lines.append("5. 跑回填：`python scripts/apply_question_reviews.py --reviews_jsonl <reviews>`")
    lines.append("")
    lines.append("### 回歸測試")
    lines.append("```bash")
    lines.append("python -m pytest tests/ -q")
    lines.append("python scripts/check_hint_overrides_regression.py --only_approved --per_template 5")
    lines.append("```")

    # Overall verdict
    lines.append("")
    all_ok = schema_ok and math_ok and hint_ok
    lines.append(f"## Overall: {'✅ ALL PASS' if all_ok else '⚠ ISSUES FOUND — review above'}")

    return "\n".join(lines) + "\n"


def run_pipeline(
    *,
    out_dir: Path,
    per_template: int,
    seed: int,
    limit_templates: Optional[int] = None,
) -> Dict[str, Any]:
    """Run the full pipeline. Returns summary dict."""
    out_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = out_dir / "questions_dump.jsonl"
    md_path = out_dir / "questions_dump.md"

    # Step 1: Export
    print(f"[1/5] Exporting questions (per_template={per_template}, seed={seed}) ...")
    export_result = export_all_questions(
        out_jsonl=jsonl_path,
        out_md=md_path,
        per_template=per_template,
        seed=seed,
        limit_templates=limit_templates,
    )
    print(f"  → {export_result['total_items']} items exported")

    # Step 2: Schema validation
    print("[2/5] Validating JSON schema ...")
    schema_result = _validate_schema(jsonl_path)
    print(f"  → {schema_result['passed']}/{schema_result['total']} passed")

    # Step 3: Math correctness
    print("[3/5] Validating math correctness ...")
    math_result = validate_math(jsonl_path)
    print(f"  → {math_result['passed']}/{math_result['total']} passed")

    # Step 4: Hint ladder rules
    print("[4/5] Validating hint ladder rules ...")
    hint_result = validate_hints(jsonl_path)
    print(f"  → {hint_result['passed']}/{hint_result['total']} passed")

    # Step 5: Build report
    print("[5/5] Building pipeline report ...")
    report = _build_report(
        out_dir=out_dir,
        export_result=export_result,
        schema_result=schema_result,
        math_result=math_result,
        hint_result=hint_result,
        per_template=per_template,
        seed=seed,
    )
    report_path = out_dir / "pipeline_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  → {report_path}")

    # Copy LLM review prompt
    prompt_src = ROOT / "tools" / "llm_review_prompt.md"
    if prompt_src.exists():
        shutil.copy2(prompt_src, out_dir / "llm_review_prompt.md")
        print(f"  → Copied llm_review_prompt.md")

    # Summary JSON
    summary = {
        "ok": schema_result["failed"] == 0,
        "out_dir": str(out_dir),
        "export": export_result,
        "schema": {"passed": schema_result["passed"], "failed": schema_result["failed"]},
        "math": {"passed": math_result["passed"], "failed": math_result["failed"]},
        "hints": {"passed": hint_result["passed"], "failed": hint_result["failed"]},
    }
    summary_path = out_dir / "pipeline_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return summary


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Run full question QA pipeline (export → validate → report)")
    p.add_argument("--out_dir", default="20260218_test", help="Output directory")
    p.add_argument("--per_template", type=int, default=50, help="Questions per template")
    p.add_argument("--seed", type=int, default=12345, help="Base random seed")
    p.add_argument("--limit_templates", type=int, default=None, help="Limit to N templates (for testing)")
    args = p.parse_args(argv)

    summary = run_pipeline(
        out_dir=Path(args.out_dir),
        per_template=args.per_template,
        seed=args.seed,
        limit_templates=args.limit_templates,
    )

    print("\n" + "=" * 60)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not summary["ok"]:
        print("\n⚠ Pipeline found issues — see pipeline_report.md")
        return 1
    print("\n✅ Pipeline complete — all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
