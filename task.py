from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi.testclient import TestClient

from server import app


ROOT = Path(__file__).resolve().parent
DEFAULT_OUT_MD = ROOT / "outputs" / "hint_triage.md"
DEFAULT_OUT_JSON = ROOT / "outputs" / "hint_triage.json"


@dataclass
class HintEvalItem:
    topic_key: str
    topic_name: str
    question_id: int
    topic: str
    question: str
    level: int
    student_state: str
    hint: str
    score: float
    issues: List[str]


def _ensure_out_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _bootstrap_get_api_key(client: TestClient) -> str:
    r = client.post("/admin/bootstrap?name=HintEval")
    r.raise_for_status()
    api_key = r.json().get("api_key")
    if not api_key:
        raise RuntimeError("bootstrap missing api_key")
    return str(api_key)


def _create_student(client: TestClient, api_key: str) -> int:
    r = client.post(
        "/v1/students?display_name=hint-eval&grade=G5",
        headers={"X-API-Key": api_key},
    )
    r.raise_for_status()

    r = client.get("/v1/students", headers={"X-API-Key": api_key})
    r.raise_for_status()
    rows = r.json().get("students") or []
    if not rows:
        raise RuntimeError("no students")
    return int(rows[-1]["id"])


def _topic_name(topic_key: str) -> str:
    try:
        import engine

        t = engine.GENERATORS.get(str(topic_key))
        return str(t[0]) if t else str(topic_key)
    except Exception:
        return str(topic_key)


def _score_hint(hint: str) -> Tuple[float, List[str]]:
    issues: List[str] = []
    s = str(hint or "").strip()
    if not s:
        return 0.0, ["empty"]

    # Hard safety checks.
    if "答案" in s:
        issues.append("contains_answer_word")
    if re.search(r"=\s*-?\d+\s*(?:/\s*\d+)?\b", s):
        issues.append("looks_like_direct_result")

    # Soft quality heuristics.
    if len(s) < 12:
        issues.append("too_short")
    # Consider common imperative/step words as actionable.
    if not any(k in s for k in ("先", "再", "最後", "下一步", "檢查", "注意", "把", "用", "列式", "對齊", "通分", "約分")):
        issues.append("not_actionable")

    # Score: start from 1, subtract penalties.
    score = 1.0
    if "contains_answer_word" in issues:
        score -= 0.6
    if "looks_like_direct_result" in issues:
        score -= 0.6
    if "too_short" in issues:
        score -= 0.2
    if "not_actionable" in issues:
        score -= 0.2

    if score < 0:
        score = 0.0
    return score, issues


def hint_eval(*, top: int, out_md: Path, out_json: Path, per_topic: int) -> int:
    client = TestClient(app)
    api_key = _bootstrap_get_api_key(client)
    sid = _create_student(client, api_key)

    try:
        import engine

        topic_keys = list(engine.GENERATORS.keys())
    except Exception:
        topic_keys = ["1", "2", "3", "4", "7", "8", "linear", "quadratic"]

    items: List[HintEvalItem] = []

    for topic_key in topic_keys:
        for _ in range(int(per_topic)):
            q = client.post(
                f"/v1/questions/next?student_id={sid}&topic_key={topic_key}",
                headers={"X-API-Key": api_key},
            )
            if q.status_code != 200:
                continue
            qj = q.json()
            qid = int(qj.get("question_id"))

            # Different student states to exercise the student-aware logic.
            state_variants = [
                "",
                "我先把題目圈重點，準備列式",
                "我已列出算式但算到一半卡住",
            ]

            for level in (1, 2, 3):
                for st in state_variants:
                    h = client.post(
                        "/v1/hints/next",
                        headers={"X-API-Key": api_key},
                        json={
                            "question_id": qid,
                            "student_state": st,
                            "level": level,
                        },
                    )
                    if h.status_code != 200:
                        continue
                    hj = h.json()
                    hint = str(hj.get("hint") or "")
                    score, issues = _score_hint(hint)
                    items.append(
                        HintEvalItem(
                            topic_key=str(topic_key),
                            topic_name=_topic_name(str(topic_key)),
                            question_id=qid,
                            topic=str(qj.get("topic") or ""),
                            question=str(qj.get("question") or ""),
                            level=level,
                            student_state=st,
                            hint=hint,
                            score=score,
                            issues=issues,
                        )
                    )

    items.sort(key=lambda x: (x.score, x.topic_key, x.question_id, x.level))
    worst = items[: max(1, int(top))]

    out_rows: List[Dict[str, Any]] = []
    for it in worst:
        out_rows.append(
            {
                "topic_key": it.topic_key,
                "topic_name": it.topic_name,
                "question_id": it.question_id,
                "topic": it.topic,
                "question": it.question,
                "level": it.level,
                "student_state": it.student_state,
                "hint": it.hint,
                "score": it.score,
                "issues": it.issues,
            }
        )

    _ensure_out_dir(out_md)
    _ensure_out_dir(out_json)

    out_json.write_text(
        json.dumps({"generated_at": time.time(), "worst": out_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md_lines: List[str] = []
    md_lines.append("# Hint triage (worst items)\n")
    md_lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_lines.append(f"Items scanned: {len(items)} | Worst shown: {len(worst)}\n")

    for idx, it in enumerate(worst, 1):
        md_lines.append(f"## {idx}. {it.topic_key} {it.topic_name} | qid={it.question_id} | L{it.level} | score={it.score:.2f}\n")
        if it.issues:
            md_lines.append(f"- Issues: {', '.join(it.issues)}\n")
        md_lines.append(f"- Topic: {it.topic}\n")
        md_lines.append(f"- Question: {it.question}\n")
        md_lines.append(f"- Student state: {it.student_state or '(empty)'}\n")
        md_lines.append("- Hint:\n")
        md_lines.append("\n```")
        md_lines.append(it.hint)
        md_lines.append("```\n")

    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Wrote: {out_md}")
    print(f"Wrote: {out_json}")
    return 0


def hint_watch(
    *,
    minutes: int,
    top: int,
    out_md: Path,
    out_json: Path,
    per_topic: int,
    poll_sec: int,
    stamp: bool,
) -> int:
    start = time.time()
    deadline = start + max(1, int(minutes)) * 60

    cycle = 0
    while time.time() < deadline:
        cycle += 1
        now = time.strftime("%Y%m%d_%H%M%S")
        print(f"\n[hint_watch] cycle {cycle} @ {time.strftime('%H:%M:%S')}")

        # Always update the 'latest' files.
        hint_eval(top=top, out_md=out_md, out_json=out_json, per_topic=per_topic)

        # Optionally write timestamped snapshots for long runs.
        if stamp:
            stamped_md = out_md.with_name(f"{out_md.stem}_{now}{out_md.suffix}")
            stamped_json = out_json.with_name(f"{out_json.stem}_{now}{out_json.suffix}")
            hint_eval(top=top, out_md=stamped_md, out_json=stamped_json, per_topic=per_topic)
        if time.time() >= deadline:
            break
        time.sleep(max(1, int(poll_sec)))

    print("[hint_watch] done")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Hint QA tools for RAGWEB")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_eval = sub.add_parser("hint_eval", help="evaluate hint quality and write triage report")
    ap_eval.add_argument("--top", type=int, default=25)
    ap_eval.add_argument("--per-topic", type=int, default=3, dest="per_topic")
    ap_eval.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    ap_eval.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)

    ap_watch = sub.add_parser("hint_watch", help="run hint_eval repeatedly for a long time")
    ap_watch.add_argument("--minutes", type=int, default=480)
    ap_watch.add_argument("--top", type=int, default=25)
    ap_watch.add_argument("--per-topic", type=int, default=3, dest="per_topic")
    ap_watch.add_argument("--poll", type=int, default=30, dest="poll_sec")
    ap_watch.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    ap_watch.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap_watch.add_argument("--stamp", action="store_true", help="also write timestamped per-cycle reports")

    args = ap.parse_args()

    if args.cmd == "hint_eval":
        return hint_eval(top=args.top, out_md=args.out_md, out_json=args.out_json, per_topic=args.per_topic)

    if args.cmd == "hint_watch":
        return hint_watch(
            minutes=args.minutes,
            top=args.top,
            out_md=args.out_md,
            out_json=args.out_json,
            per_topic=args.per_topic,
            poll_sec=args.poll_sec,
            stamp=bool(args.stamp),
        )

    raise SystemExit("unknown cmd")


if __name__ == "__main__":
    raise SystemExit(main())
