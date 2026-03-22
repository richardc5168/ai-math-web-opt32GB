from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List


def _iso(days_offset: int, minutes: int = 0) -> str:
    base = datetime(2026, 3, 1, 8, 0, 0) + timedelta(days=days_offset, minutes=minutes)
    return base.isoformat(timespec="seconds")


def build_school_first_fixture() -> Dict[str, Any]:
    question_metadata: List[Dict[str, Any]] = []
    for skill_idx, skill in enumerate((
        ("fraction_add", "fractions", "common_denom", "EQ-FR-1"),
        ("fraction_compare", "fractions", "compare_size", "EQ-FR-2"),
        ("decimal_place", "decimals", "place_value", "EQ-DE-1"),
        ("ratio_reasoning", "ratio", "unit_rate", "EQ-RA-1"),
        ("area_rect", "geometry", "area", "EQ-GE-1"),
        ("word_multi", "word_problem", "multi_step", "EQ-WP-1"),
    )):
        skill_tag, topic, knowledge_point, eq = skill
        for diff in (2, 3):
            question_metadata.append(
                {
                    "question_id": f"q-{eq}-{diff}",
                    "topic": topic,
                    "subtopic": skill_tag,
                    "skill_tag": skill_tag,
                    "knowledge_point": knowledge_point,
                    "difficulty": diff,
                    "pattern_type": "school_first_mock",
                    "equivalent_group_id": eq,
                }
            )

    fixture: Dict[str, Any] = {
        "admin": {"admin_id": "admin-001", "display_name": "System Owner"},
        "teachers": [],
        "parents": [],
        "students": [],
        "assessments": [],
        "interventions": [],
        "question_metadata": question_metadata,
        "answer_records": [],
    }

    meta_ids = [m["question_id"] for m in question_metadata]

    for teacher_num, teacher_name in ((1, "Teacher Hsu"), (2, "Teacher Lin")):
        teacher_id = f"teacher-{teacher_num:03d}"
        class_id = f"class-{teacher_num:03d}"
        fixture["teachers"].append(
            {"teacher_id": teacher_id, "display_name": teacher_name, "class_id": class_id}
        )

        pre_ids = []
        post_ids = []
        target_students: List[str] = []

        for student_num in range(1, 59):
            absolute_idx = (teacher_num - 1) * 58 + student_num
            band = ("high", "mid", "low")[(absolute_idx - 1) % 3]
            student_id = f"student-{absolute_idx:03d}"
            parent_id = f"parent-{absolute_idx:03d}"
            display_name = f"Student {absolute_idx:03d}"
            fixture["students"].append(
                {
                    "student_id": student_id,
                    "class_id": class_id,
                    "parent_id": parent_id,
                    "teacher_id": teacher_id,
                    "display_name": display_name,
                    "grade": "G5" if teacher_num == 1 else "G6",
                    "band": band,
                }
            )
            fixture["parents"].append(
                {"parent_id": parent_id, "student_id": student_id, "display_name": f"Parent {absolute_idx:03d}"}
            )

            pre_id = f"pre-{student_id}"
            post_id = f"post-{student_id}"
            pre_ids.append(pre_id)
            post_ids.append(post_id)
            fixture["assessments"].extend(
                [
                    {
                        "assessment_id": pre_id,
                        "student_id": student_id,
                        "class_id": class_id,
                        "assessment_type": "pre_test",
                        "assigned_at": _iso(0),
                        "completed_at": _iso(0, absolute_idx),
                    },
                    {
                        "assessment_id": post_id,
                        "student_id": student_id,
                        "class_id": class_id,
                        "assessment_type": "post_test",
                        "assigned_at": _iso(10),
                        "completed_at": _iso(10, absolute_idx),
                    },
                ]
            )

            if band != "high":
                target_students.append(student_id)

            for q_idx, question_id in enumerate(meta_ids):
                meta = question_metadata[q_idx]
                pre_correct = 1 if ((absolute_idx + q_idx) % 5) < (3 if band == "high" else 2 if band == "mid" else 1) else 0
                if band == "high":
                    post_correct = 1 if ((absolute_idx + q_idx) % 5) < 4 else 0
                elif band == "mid":
                    post_correct = 1 if ((absolute_idx + q_idx) % 5) < 3 else 0
                else:
                    post_correct = 1 if ((absolute_idx + q_idx) % 5) < 1 else 0

                fixture["answer_records"].append(
                    {
                        "assessment_id": pre_id,
                        "student_id": student_id,
                        "class_id": class_id,
                        "question_id": question_id,
                        "answer": str((absolute_idx + q_idx) % 9),
                        "correctness": bool(pre_correct),
                        "response_time": 18 + (q_idx % 5),
                        "hint_used": band != "high" and q_idx % 2 == 0,
                        "attempt_count": 1 if pre_correct else 2,
                        "error_type": "COMMON_DENOM_WRONG" if not pre_correct and meta["topic"] == "fractions" else "READ" if not pre_correct else "",
                        "timestamp": _iso(0, absolute_idx + q_idx),
                    }
                )
                fixture["answer_records"].append(
                    {
                        "assessment_id": post_id,
                        "student_id": student_id,
                        "class_id": class_id,
                        "question_id": question_id,
                        "answer": str((absolute_idx + q_idx + 1) % 9),
                        "correctness": bool(post_correct),
                        "response_time": 15 + (q_idx % 4),
                        "hint_used": band == "low" and q_idx % 3 == 0,
                        "attempt_count": 1 if post_correct else 2,
                        "error_type": "CARE" if not post_correct and meta["topic"] == "word_problem" else "CAL" if not post_correct else "",
                        "timestamp": _iso(10, absolute_idx + q_idx),
                    }
                )

        fixture["interventions"].append(
            {
                "intervention_id": f"intervention-{class_id}-01",
                "class_id": class_id,
                "teacher_id": teacher_id,
                "date": _iso(5),
                "target_students": target_students,
                "target_skills": ["fraction_add", "word_multi"],
                "teaching_method": "small_group_reteach",
                "notes": "Focus on denominator alignment and multi-step reading.",
                "linked_pretest_id": pre_ids[0],
                "linked_posttest_id": post_ids[0],
            }
        )

    return fixture