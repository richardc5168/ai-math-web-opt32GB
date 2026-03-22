"""Tests for student concept state CRUD operations."""

import os
import sqlite3
import tempfile

import pytest

from learning.concept_state import (
    MasteryLevel,
    StudentConceptState,
    get_concept_state,
    get_all_states,
    get_class_states,
    upsert_concept_state,
    get_students_needing_review,
)
from learning.db import connect, ensure_learning_schema


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = connect(path)
    ensure_learning_schema(conn)
    conn.close()
    yield path
    os.unlink(path)


def test_get_default_state(db_path):
    state = get_concept_state("s1", "frac_multiply", db_path=db_path)
    assert state.mastery_level == MasteryLevel.UNBUILT
    assert state.mastery_score == 0.0
    assert state.attempts_total == 0


def test_upsert_and_read(db_path):
    state = StudentConceptState(
        student_id="s1",
        concept_id="frac_multiply",
        mastery_level=MasteryLevel.DEVELOPING,
        mastery_score=0.35,
        attempts_total=5,
        correct_total=3,
        correct_no_hint=2,
        correct_with_hint=1,
        consecutive_correct=2,
    )
    upsert_concept_state(state, db_path=db_path)

    loaded = get_concept_state("s1", "frac_multiply", db_path=db_path)
    assert loaded.mastery_level == MasteryLevel.DEVELOPING
    assert loaded.mastery_score == 0.35
    assert loaded.attempts_total == 5
    assert loaded.correct_no_hint == 2


def test_upsert_overwrites(db_path):
    state1 = StudentConceptState(
        student_id="s1", concept_id="c1",
        mastery_level=MasteryLevel.DEVELOPING, mastery_score=0.3,
    )
    upsert_concept_state(state1, db_path=db_path)

    state2 = StudentConceptState(
        student_id="s1", concept_id="c1",
        mastery_level=MasteryLevel.APPROACHING_MASTERY, mastery_score=0.65,
    )
    upsert_concept_state(state2, db_path=db_path)

    loaded = get_concept_state("s1", "c1", db_path=db_path)
    assert loaded.mastery_level == MasteryLevel.APPROACHING_MASTERY
    assert loaded.mastery_score == 0.65


def test_get_all_states(db_path):
    for concept_id in ["c1", "c2", "c3"]:
        upsert_concept_state(
            StudentConceptState(student_id="s1", concept_id=concept_id, mastery_score=0.5),
            db_path=db_path,
        )

    states = get_all_states("s1", db_path=db_path)
    assert len(states) == 3
    assert "c1" in states
    assert "c3" in states


def test_get_class_states(db_path):
    for sid in ["s1", "s2"]:
        for cid in ["c1", "c2"]:
            upsert_concept_state(
                StudentConceptState(student_id=sid, concept_id=cid, mastery_score=0.5),
                db_path=db_path,
            )

    result = get_class_states(["s1", "s2"], db_path=db_path)
    assert len(result) == 2
    assert len(result["s1"]) == 2
    assert len(result["s2"]) == 2


def test_get_students_needing_review(db_path):
    upsert_concept_state(
        StudentConceptState(
            student_id="s1", concept_id="c1",
            needs_review=True, mastery_level=MasteryLevel.REVIEW_NEEDED,
        ),
        db_path=db_path,
    )
    upsert_concept_state(
        StudentConceptState(
            student_id="s1", concept_id="c2",
            needs_review=False, mastery_level=MasteryLevel.MASTERED,
        ),
        db_path=db_path,
    )

    reviews = get_students_needing_review(db_path=db_path)
    assert len(reviews) == 1
    assert reviews[0].concept_id == "c1"


def test_accuracy_calculation():
    s = StudentConceptState(student_id="s1", concept_id="c1", attempts_total=10, correct_total=7)
    assert abs(s.accuracy() - 0.7) < 1e-9

    s2 = StudentConceptState(student_id="s1", concept_id="c1")
    assert s2.accuracy() == 0.0


def test_to_dict():
    s = StudentConceptState(
        student_id="s1", concept_id="c1",
        mastery_level=MasteryLevel.MASTERED,
        needs_review=True,
    )
    d = s.to_dict()
    assert d["mastery_level"] == "mastered"
    assert d["needs_review"] == 1
