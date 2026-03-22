from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple


def _group_meta(question_metadata: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(m["question_id"]): m for m in question_metadata}


def _bucket(records: Iterable[Dict[str, Any]], meta_map: Dict[str, Dict[str, Any]]) -> Dict[Tuple[str, str, str], List[Dict[str, Any]]]:
    groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        meta = meta_map.get(str(record["question_id"]))
        if not meta:
            continue
        key = (
            str(meta["equivalent_group_id"]),
            str(meta["skill_tag"]),
            str(meta["knowledge_point"]),
        )
        groups[key].append(record)
    return groups


def _accuracy(rows: List[Dict[str, Any]]) -> float:
    total = len(rows)
    if total <= 0:
        return 0.0
    correct = sum(1 for row in rows if bool(row.get("correctness")))
    return round(correct / total, 4)


def compare_pre_post(
    *,
    question_metadata: Iterable[Dict[str, Any]],
    pre_records: Iterable[Dict[str, Any]],
    post_records: Iterable[Dict[str, Any]],
    min_groups: int = 2,
) -> Dict[str, Any]:
    meta_map = _group_meta(question_metadata)
    pre_groups = _bucket(pre_records, meta_map)
    post_groups = _bucket(post_records, meta_map)

    comparable_keys = sorted(set(pre_groups) & set(post_groups))
    compared_groups: List[Dict[str, Any]] = []
    deltas: List[float] = []

    for key in comparable_keys:
        pre_acc = _accuracy(pre_groups[key])
        post_acc = _accuracy(post_groups[key])
        delta = round(post_acc - pre_acc, 4)
        deltas.append(delta)
        compared_groups.append(
            {
                "equivalent_group_id": key[0],
                "skill_tag": key[1],
                "knowledge_point": key[2],
                "pre_accuracy": pre_acc,
                "post_accuracy": post_acc,
                "delta": delta,
                "pre_question_ids": sorted({str(r["question_id"]) for r in pre_groups[key]}),
                "post_question_ids": sorted({str(r["question_id"]) for r in post_groups[key]}),
            }
        )

    if len(comparable_keys) < min_groups:
        label = "insufficient_evidence"
    else:
        avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
        if avg_delta >= 0.15:
            label = "improved"
        elif avg_delta <= -0.15:
            label = "regressed"
        else:
            label = "flat"

    return {
        "label": label,
        "compared_group_count": len(comparable_keys),
        "groups": compared_groups,
        "uncertainty": [] if len(comparable_keys) >= min_groups else ["Not enough equivalent groups to claim a reliable before/after result."],
    }


def build_parent_summary(student_name: str, result: Dict[str, Any]) -> str:
    label = result.get("label", "insufficient_evidence")
    mapping = {
        "improved": f"{student_name} shows clear improvement after the intervention period.",
        "flat": f"{student_name} is mostly stable; more targeted support is still needed.",
        "regressed": f"{student_name} needs additional support because post-test evidence is weaker than pre-test evidence.",
        "insufficient_evidence": f"There is not enough matched evidence yet to make a strong before/after claim for {student_name}.",
    }
    return mapping[label]


def build_teacher_summary(class_name: str, student_reports: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {"improved": 0, "flat": 0, "regressed": 0, "insufficient_evidence": 0}
    high_risk: List[str] = []
    for report in student_reports:
        label = str(report.get("label", "insufficient_evidence"))
        counts[label] = counts.get(label, 0) + 1
        if label in ("regressed", "insufficient_evidence"):
            high_risk.append(str(report.get("student_id", "unknown")))
    return {
        "class_name": class_name,
        "status_counts": counts,
        "high_risk_students": high_risk,
    }