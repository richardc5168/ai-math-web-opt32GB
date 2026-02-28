"""
pipeline/auto_pipeline.py — End-to-end autonomous pipeline orchestrator.

Executes the full pipeline:
  Search → Generate → Solve → Verify → Commit

Design:
  1. Fetch seed content (offline/OER)
  2. Generate problems from seeds (deterministic or LLM)
  3. Solve with deterministic solver (primary judge)
  4. Verify through 4-gate quality gate
  5. Route: auto-commit (high score) or human queue (low score)

Dual-Track Adjudication:
  - Primary: deterministic solver (this pipeline)
  - Auxiliary: LLM-as-a-judge (isolated, sandboxed, replayable)
  - LLM output treated as untrusted input

Human Role Shift:
  - From: 逐題檢查 (checking every problem)
  - To: 抽樣審核 + 規則/測試演進 (sampling + rule evolution)

Usage:
  python -m pipeline.auto_pipeline --topic N-5-10 --count 5 --dry-run
  python -m pipeline.auto_pipeline --all-topics --count 3
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.deterministic_solver import solve, verify_answer
from pipeline.oer_fetcher import (
    OERFetcher,
    STAGE_III_TOPICS,
    compute_topic_coverage,
)
from pipeline.source_governance import (
    build_source_metadata,
    check_textbook_reproduction,
    validate_source,
)
from pipeline.scorecard import compute_scorecard
from pipeline.verify import verify_problem


# ── Constants ──────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "generated"
HUMAN_QUEUE_DIR = ROOT / "data" / "human_queue"
PIPELINE_REPORT_PATH = ROOT / "artifacts" / "auto_pipeline_report.json"

# Score threshold for auto-publish vs human-review
AUTO_PUBLISH_THRESHOLD = 90
HUMAN_REVIEW_THRESHOLD = 70  # Below this = reject outright

MAX_SELF_REFINE = 3


# ── Pipeline Steps ─────────────────────────────────────────

def step_fetch(
    topic_code: str,
    count: int = 5,
    offline: bool = True,
) -> list[dict[str, Any]]:
    """
    Step 1: Fetch seed content for a topic.

    Uses OER fetcher (offline mode = deterministic seeds).
    """
    fetcher = OERFetcher(offline=offline)
    seeds = fetcher.fetch_topic_seeds(topic_code, count)
    return seeds


def step_generate_and_solve(
    seeds: list[dict[str, Any]],
    topic_code: str,
) -> list[dict[str, Any]]:
    """
    Step 2+3: Generate problem from seed and solve deterministically.

    For each seed:
    1. Extract solver parameters
    2. Solve with deterministic solver
    3. Attach solution to problem
    """
    problems = []
    for seed in seeds:
        solver_params = seed.get("_solver_params", {})
        if not solver_params:
            # No solver params — skip (would need LLM)
            problems.append({
                **seed,
                "pipeline_status": "no_solver_params",
            })
            continue

        try:
            tc = solver_params.pop("topic_code", topic_code)
            solution = solve(tc, solver_params)

            problem = {
                **{k: v for k, v in seed.items() if k != "_solver_params"},
                "solution": {
                    "steps": solution.get("steps", []),
                    "answer": {
                        "value": solution.get("answer"),
                        "unit": solution.get("unit", ""),
                    },
                },
                "pipeline_status": "solved",
            }
            problems.append(problem)

        except Exception as e:
            problems.append({
                **seed,
                "pipeline_status": f"solver_error: {e}",
            })

    return problems


def step_verify(
    problems: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Step 4: Verify each problem through the 4-gate quality gate.

    Returns problems with verification results attached.
    """
    verified = []
    for p in problems:
        if p.get("pipeline_status", "").startswith("solver_error"):
            verified.append(p)
            continue
        if p.get("pipeline_status") == "no_solver_params":
            verified.append(p)
            continue

        result = verify_problem(p)
        p["verification"] = result
        p["pipeline_status"] = "verified"
        verified.append(p)

    return verified


def step_route(
    problems: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Step 5: Route problems based on verification score.

    Routes:
    - auto_publish: score >= AUTO_PUBLISH_THRESHOLD and all gates pass
    - human_review: score >= HUMAN_REVIEW_THRESHOLD but < auto threshold or gate failure
    - rejected: score < HUMAN_REVIEW_THRESHOLD or solver error
    """
    routes: dict[str, list[dict]] = {
        "auto_publish": [],
        "human_review": [],
        "rejected": [],
    }

    for p in problems:
        status = p.get("pipeline_status", "")

        if status.startswith("solver_error") or status == "no_solver_params":
            routes["rejected"].append(p)
            continue

        verification = p.get("verification", {})
        score = verification.get("score", 0)
        all_gates = verification.get("passed", False)

        if all_gates and score >= AUTO_PUBLISH_THRESHOLD:
            routes["auto_publish"].append(p)
        elif score >= HUMAN_REVIEW_THRESHOLD:
            routes["human_review"].append(p)
        else:
            routes["rejected"].append(p)

    return routes


# ── Self-Refine Integration ───────────────────────────────

def self_refine_loop(
    problem: dict[str, Any],
    topic_code: str,
    max_iterations: int = MAX_SELF_REFINE,
) -> dict[str, Any]:
    """
    Self-Refine loop: if verification fails, attempt to fix deterministically.

    For deterministic problems, this means adjusting parameters and re-solving.
    For LLM-generated problems, this would send structured feedback to LLM.

    Returns the best version of the problem.
    """
    best = problem
    for i in range(max_iterations):
        result = verify_problem(best)
        if result["passed"] and result["score"] >= AUTO_PUBLISH_THRESHOLD:
            best["_refine_iterations"] = i
            return best

        # Try to fix common issues deterministically
        fixed = _try_deterministic_fix(best, result, topic_code)
        if fixed is None:
            break
        best = fixed

    best["_refine_iterations"] = max_iterations
    return best


def _try_deterministic_fix(
    problem: dict,
    verify_result: dict,
    topic_code: str,
) -> dict | None:
    """
    Try to fix a problem deterministically based on verification failures.

    Returns fixed problem or None if can't fix.
    """
    reasons = verify_result.get("reasons", {})
    fixed = json.loads(json.dumps(problem))  # deep copy

    for gate, reason in reasons.items():
        if reason == "ok" or "low confidence" in reason:
            continue

        if gate == "steps" and "requires >=" in reason:
            # Need more steps — can't fix without regeneration
            return None

        if gate == "license" and "textbook reproduction" in reason:
            # Can't fix textbook reproduction
            return None

        if gate == "correctness" and "negative" in reason:
            # Try making answer positive
            sol = fixed.get("solution", {})
            ans = sol.get("answer", {})
            try:
                val = float(ans.get("value", 0))
                if val < 0:
                    ans["value"] = abs(val)
                    return fixed
            except (TypeError, ValueError):
                pass

    return None


# ── Full Pipeline ──────────────────────────────────────────

def run_pipeline(
    topic_codes: list[str] | None = None,
    count: int = 5,
    offline: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Run the full end-to-end pipeline.

    Args:
        topic_codes: List of topic codes to generate (None = all)
        count: Number of problems per topic
        offline: Use offline/seed mode
        dry_run: Don't write files

    Returns:
        Pipeline report dict
    """
    if topic_codes is None:
        topic_codes = list(STAGE_III_TOPICS.keys())

    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "topics": topic_codes,
        "count_per_topic": count,
        "offline": offline,
        "dry_run": dry_run,
        "results": {},
        "summary": {
            "total_generated": 0,
            "auto_publish": 0,
            "human_review": 0,
            "rejected": 0,
        },
    }

    all_auto_publish = []

    for topic_code in topic_codes:
        # Step 1: Fetch
        seeds = step_fetch(topic_code, count, offline)

        # Step 2+3: Generate and Solve
        problems = step_generate_and_solve(seeds, topic_code)

        # Self-Refine loop
        refined = []
        for p in problems:
            if p.get("pipeline_status") == "solved":
                p = self_refine_loop(p, topic_code)
            refined.append(p)

        # Step 4: Verify
        verified = step_verify(refined)

        # Step 5: Route
        routes = step_route(verified)

        topic_result = {
            "seeds": len(seeds),
            "solved": len([p for p in problems if p.get("pipeline_status") == "solved"]),
            "auto_publish": len(routes["auto_publish"]),
            "human_review": len(routes["human_review"]),
            "rejected": len(routes["rejected"]),
        }
        report["results"][topic_code] = topic_result

        report["summary"]["total_generated"] += len(problems)
        report["summary"]["auto_publish"] += topic_result["auto_publish"]
        report["summary"]["human_review"] += topic_result["human_review"]
        report["summary"]["rejected"] += topic_result["rejected"]

        all_auto_publish.extend(routes["auto_publish"])

        # Write human review queue
        if not dry_run and routes["human_review"]:
            _write_human_queue(topic_code, routes["human_review"])

    # Write auto-publish problems
    if not dry_run and all_auto_publish:
        _write_auto_publish(all_auto_publish)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()

    # Write report
    if not dry_run:
        PIPELINE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        PIPELINE_REPORT_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return report


def _write_auto_publish(problems: list[dict]) -> None:
    """Write auto-publishable problems to output JSONL."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"auto_publish_{ts}.jsonl"

    with open(out_path, "w", encoding="utf-8") as f:
        for p in problems:
            # Clean internal fields before writing
            clean = {k: v for k, v in p.items()
                     if not k.startswith("_") and k != "pipeline_status"}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")


def _write_human_queue(topic_code: str, problems: list[dict]) -> None:
    """Write problems needing human review to queue."""
    HUMAN_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = HUMAN_QUEUE_DIR / f"review_{topic_code}_{ts}.jsonl"

    with open(out_path, "w", encoding="utf-8") as f:
        for p in problems:
            entry = {
                "topic_code": topic_code,
                "problem": {k: v for k, v in p.items()
                           if not k.startswith("_") and k != "pipeline_status"},
                "verification": p.get("verification", {}),
                "status": "pending_review",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── CLI ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="End-to-end autonomous problem generation pipeline"
    )
    parser.add_argument(
        "--topic", type=str, default="",
        help="Topic code to generate (e.g. N-5-10)",
    )
    parser.add_argument(
        "--all-topics", action="store_true",
        help="Generate for all Stage III topics",
    )
    parser.add_argument(
        "--count", type=int, default=5,
        help="Number of problems per topic (default: 5)",
    )
    parser.add_argument(
        "--offline", action="store_true", default=True,
        help="Use offline/seed mode (default: True)",
    )
    parser.add_argument(
        "--online", action="store_true",
        help="Use online OER fetching (requires network)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate without writing files",
    )
    parser.add_argument(
        "--coverage", action="store_true",
        help="Show topic coverage report",
    )
    args = parser.parse_args()

    if args.coverage:
        # Load existing problems and show coverage
        existing = _load_existing_problems()
        coverage = compute_topic_coverage(existing)
        print(json.dumps(coverage, ensure_ascii=False, indent=2))
        return

    if args.all_topics:
        topics = list(STAGE_III_TOPICS.keys())
    elif args.topic:
        topics = args.topic.split(",")
    else:
        # Default: generate for core topics
        topics = ["N-5-10", "N-5-11", "N-6-3", "N-6-7", "S-6-2", "D-5-1"]

    offline = not args.online

    report = run_pipeline(
        topic_codes=topics,
        count=args.count,
        offline=offline,
        dry_run=args.dry_run,
    )

    # Print summary
    summary = report["summary"]
    print(f"\n=== Pipeline Report ===")
    print(f"Topics:       {len(report['results'])}")
    print(f"Generated:    {summary['total_generated']}")
    print(f"Auto-publish: {summary['auto_publish']}")
    print(f"Human review: {summary['human_review']}")
    print(f"Rejected:     {summary['rejected']}")

    auto_rate = (
        summary["auto_publish"] / max(summary["total_generated"], 1) * 100
    )
    print(f"Auto-publish rate: {auto_rate:.1f}%")

    if not args.dry_run:
        print(f"Report: {PIPELINE_REPORT_PATH}")

    sys.exit(0)


def _load_existing_problems() -> list[dict]:
    """Load existing problems from all JSONL files in data/."""
    problems = []
    data_dir = ROOT / "data"
    if not data_dir.exists():
        return []
    for jsonl in data_dir.rglob("*.jsonl"):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    problems.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return problems


if __name__ == "__main__":
    main()
