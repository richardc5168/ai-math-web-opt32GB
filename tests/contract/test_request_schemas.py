"""Contract tests for Pydantic request models across all routers.

Validates that every request model:
  - Accepts valid input (happy path)
  - Rejects invalid input (missing required fields, out-of-range, etc.)
  - Has expected default values
  - Field constraints (min_length, ge/le, etc.) are enforced

These tests import models directly — no server or DB dependency.
"""
import pytest
from pydantic import ValidationError

# ── Auth models ─────────────────────────────────────────────────────────

from routers.auth import (
    AppAuthLoginRequest,
    AppAuthProvisionRequest,
    BootstrapRequest,
    ExchangeRequest,
)

# ── Learning models ─────────────────────────────────────────────────────

from routers.learning import (
    BeforeAfterRequest,
    ConceptNextRequest,
    PracticeNextRequest,
    RemediationPlanRequest,
    WeeklyReportRequest,
)

# ── Server models ──────────────────────────────────────────────────────

from server import (
    HintNextRequest,
    LinearCheckRequest,
    LinearGenRequest,
    MixedMultiplyDiagnoseRequest,
    ParentReportFetchRequest,
    ParentReportUpsertRequest,
    PracticeEventWriteRequest,
    QuadraticCheckRequest,
    QuadraticGenRequest,
    QuadraticPipelineValidateRequest,
    ReportSnapshotReadRequest,
    ReportSnapshotWriteRequest,
    StudentSubmission,
    TeacherAddStudentRequest,
    TeacherCreateClassRequest,
)


# =====================================================================
# Auth Models
# =====================================================================


class TestAppAuthLoginRequest:
    def test_valid(self):
        m = AppAuthLoginRequest(username="abc", password="1234")
        assert m.username == "abc"
        assert m.password == "1234"

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            AppAuthLoginRequest(username="ab", password="1234")

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            AppAuthLoginRequest(username="abc", password="123")

    def test_missing_username(self):
        with pytest.raises(ValidationError):
            AppAuthLoginRequest(password="1234")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            AppAuthLoginRequest(username="abc")


class TestAppAuthProvisionRequest:
    def test_defaults(self):
        m = AppAuthProvisionRequest(username="usr", password="pass")
        assert m.account_name == "APP User"
        assert m.student_name == "學生"
        assert m.grade == "G5"
        assert m.plan == "basic"
        assert m.seats == 1

    def test_seats_range(self):
        m = AppAuthProvisionRequest(username="usr", password="pass", seats=200)
        assert m.seats == 200
        with pytest.raises(ValidationError):
            AppAuthProvisionRequest(username="usr", password="pass", seats=0)
        with pytest.raises(ValidationError):
            AppAuthProvisionRequest(username="usr", password="pass", seats=201)


class TestBootstrapRequest:
    def test_valid(self):
        m = BootstrapRequest(student_id=1)
        assert m.student_id == 1

    def test_missing(self):
        with pytest.raises(ValidationError):
            BootstrapRequest()


class TestExchangeRequest:
    def test_valid(self):
        m = ExchangeRequest(bootstrap_token="a" * 10)
        assert len(m.bootstrap_token) == 10

    def test_too_short(self):
        with pytest.raises(ValidationError):
            ExchangeRequest(bootstrap_token="short")


# =====================================================================
# Learning Models
# =====================================================================


class TestWeeklyReportRequest:
    def test_defaults(self):
        m = WeeklyReportRequest(student_id=1)
        assert m.window_days == 7
        assert m.top_k == 3
        assert m.questions_per_skill == 3

    def test_window_days_range(self):
        WeeklyReportRequest(student_id=1, window_days=1)
        WeeklyReportRequest(student_id=1, window_days=60)
        with pytest.raises(ValidationError):
            WeeklyReportRequest(student_id=1, window_days=0)
        with pytest.raises(ValidationError):
            WeeklyReportRequest(student_id=1, window_days=61)

    def test_student_id_required(self):
        with pytest.raises(ValidationError):
            WeeklyReportRequest()

    def test_student_id_positive(self):
        with pytest.raises(ValidationError):
            WeeklyReportRequest(student_id=0)


class TestPracticeNextRequest:
    def test_defaults(self):
        m = PracticeNextRequest(student_id=1, skill_tag="fraction")
        assert m.window_days == 14
        assert m.topic_key is None
        assert m.seed is None

    def test_valid_with_seed(self):
        m = PracticeNextRequest(student_id=1, skill_tag="fraction", seed=42)
        assert m.seed == 42

    def test_missing_skill_tag(self):
        with pytest.raises(ValidationError):
            PracticeNextRequest(student_id=1)


class TestRemediationPlanRequest:
    def test_defaults(self):
        m = RemediationPlanRequest(student_id=1)
        assert m.dataset_name is None
        assert m.window_days == 14

    def test_window_days_range(self):
        with pytest.raises(ValidationError):
            RemediationPlanRequest(student_id=1, window_days=0)
        with pytest.raises(ValidationError):
            RemediationPlanRequest(student_id=1, window_days=61)


class TestBeforeAfterRequest:
    def test_defaults(self):
        m = BeforeAfterRequest(student_id=1)
        assert m.intervention_date is None
        assert m.pre_window_days == 14
        assert m.post_window_days == 14

    def test_window_range(self):
        BeforeAfterRequest(student_id=1, pre_window_days=1, post_window_days=90)
        with pytest.raises(ValidationError):
            BeforeAfterRequest(student_id=1, pre_window_days=0)
        with pytest.raises(ValidationError):
            BeforeAfterRequest(student_id=1, post_window_days=91)


class TestConceptNextRequest:
    def test_defaults(self):
        m = ConceptNextRequest(student_id=1)
        assert m.domain is None
        assert m.recent_item_ids is None

    def test_with_recent_items(self):
        m = ConceptNextRequest(student_id=1, recent_item_ids=["q1", "q2"])
        assert m.recent_item_ids == ["q1", "q2"]


# =====================================================================
# Server Models — Question Generation
# =====================================================================


class TestQuadraticGenRequest:
    def test_defaults(self):
        m = QuadraticGenRequest()
        assert m.topic_id == "A3"
        assert m.difficulty == 2

    def test_difficulty_range(self):
        QuadraticGenRequest(difficulty=1)
        QuadraticGenRequest(difficulty=5)
        with pytest.raises(ValidationError):
            QuadraticGenRequest(difficulty=0)
        with pytest.raises(ValidationError):
            QuadraticGenRequest(difficulty=6)


class TestQuadraticCheckRequest:
    def test_valid(self):
        m = QuadraticCheckRequest(user_answer="x=1", question_data={"a": 1})
        assert m.user_answer == "x=1"
        assert m.question_data == {"a": 1}

    def test_missing_fields(self):
        with pytest.raises(ValidationError):
            QuadraticCheckRequest(user_answer="x=1")
        with pytest.raises(ValidationError):
            QuadraticCheckRequest(question_data={"a": 1})


class TestLinearGenRequest:
    def test_defaults(self):
        m = LinearGenRequest()
        assert m.difficulty == 1

    def test_difficulty_range(self):
        with pytest.raises(ValidationError):
            LinearGenRequest(difficulty=0)
        with pytest.raises(ValidationError):
            LinearGenRequest(difficulty=6)


class TestLinearCheckRequest:
    def test_valid(self):
        m = LinearCheckRequest(user_answer="3", question_data={"x": 3})
        assert m.user_answer == "3"


class TestQuadraticPipelineValidateRequest:
    def test_defaults(self):
        m = QuadraticPipelineValidateRequest()
        assert m.count == 1
        assert m.roots == "integer"
        assert m.difficulty == 3
        assert m.style == "factoring_then_formula"
        assert m.offline is True

    def test_count_range(self):
        with pytest.raises(ValidationError):
            QuadraticPipelineValidateRequest(count=0)
        with pytest.raises(ValidationError):
            QuadraticPipelineValidateRequest(count=6)


# =====================================================================
# Server Models — Hint & Submission
# =====================================================================


class TestHintNextRequest:
    def test_defaults(self):
        m = HintNextRequest()
        assert m.question_id is None
        assert m.question_data is None
        assert m.student_state == ""
        assert m.level == 1
        assert m.student_id is None
        assert m.concept_id is None

    def test_level_range(self):
        HintNextRequest(level=1)
        HintNextRequest(level=3)
        with pytest.raises(ValidationError):
            HintNextRequest(level=0)
        with pytest.raises(ValidationError):
            HintNextRequest(level=4)

    def test_question_id_positive(self):
        with pytest.raises(ValidationError):
            HintNextRequest(question_id=0)


class TestStudentSubmission:
    def test_valid(self):
        m = StudentSubmission(
            student_id="s1",
            concept_tag="fraction",
            student_answer="3/4",
            correct_answer="3/4",
        )
        assert m.question_id == ""
        assert m.process_text == ""

    def test_student_id_required(self):
        with pytest.raises(ValidationError):
            StudentSubmission(
                concept_tag="fraction",
                student_answer="3/4",
                correct_answer="3/4",
            )

    def test_student_id_min_length(self):
        with pytest.raises(ValidationError):
            StudentSubmission(
                student_id="",
                concept_tag="fraction",
                student_answer="3/4",
                correct_answer="3/4",
            )

    def test_concept_tag_min_length(self):
        with pytest.raises(ValidationError):
            StudentSubmission(
                student_id="s1",
                concept_tag="",
                student_answer="3/4",
                correct_answer="3/4",
            )


class TestMixedMultiplyDiagnoseRequest:
    def test_required_fields(self):
        m = MixedMultiplyDiagnoseRequest(left="2 1/3", right="4")
        assert m.step1 is None
        assert m.step2 is None
        assert m.step3 is None

    def test_missing_left(self):
        with pytest.raises(ValidationError):
            MixedMultiplyDiagnoseRequest(right="4")

    def test_missing_right(self):
        with pytest.raises(ValidationError):
            MixedMultiplyDiagnoseRequest(left="2 1/3")


# =====================================================================
# Server Models — Teacher
# =====================================================================


class TestTeacherCreateClassRequest:
    def test_valid(self):
        m = TeacherCreateClassRequest(class_name="5A")
        assert m.grade == 5
        assert m.school_name is None
        assert m.school_code is None

    def test_class_name_required(self):
        with pytest.raises(ValidationError):
            TeacherCreateClassRequest()

    def test_class_name_too_long(self):
        with pytest.raises(ValidationError):
            TeacherCreateClassRequest(class_name="x" * 81)

    def test_grade_range(self):
        TeacherCreateClassRequest(class_name="5A", grade=5)
        TeacherCreateClassRequest(class_name="6A", grade=6)
        with pytest.raises(ValidationError):
            TeacherCreateClassRequest(class_name="4A", grade=4)
        with pytest.raises(ValidationError):
            TeacherCreateClassRequest(class_name="7A", grade=7)


class TestTeacherAddStudentRequest:
    def test_defaults(self):
        m = TeacherAddStudentRequest()
        assert m.student_id is None
        assert m.display_name is None
        assert m.grade == "G5"


# =====================================================================
# Server Models — Reports & Snapshots
# =====================================================================


class TestParentReportFetchRequest:
    def test_valid(self):
        m = ParentReportFetchRequest(name="Parent", pin="1234")
        assert m.name == "Parent"

    def test_pin_too_short(self):
        with pytest.raises(ValidationError):
            ParentReportFetchRequest(name="Parent", pin="123")

    def test_pin_too_long(self):
        with pytest.raises(ValidationError):
            ParentReportFetchRequest(name="Parent", pin="1234567")

    def test_name_required(self):
        with pytest.raises(ValidationError):
            ParentReportFetchRequest(pin="1234")


class TestParentReportUpsertRequest:
    def test_valid_minimal(self):
        m = ParentReportUpsertRequest(name="P", pin="1234")
        assert m.report_data is None
        assert m.practice_event is None

    def test_with_data(self):
        m = ParentReportUpsertRequest(
            name="P", pin="1234",
            report_data={"score": 90},
            practice_event={"type": "quiz"},
        )
        assert m.report_data["score"] == 90


class TestReportSnapshotWriteRequest:
    def test_valid(self):
        m = ReportSnapshotWriteRequest(
            student_id=1, report_payload={"data": True}
        )
        assert m.source == "frontend"

    def test_missing_payload(self):
        with pytest.raises(ValidationError):
            ReportSnapshotWriteRequest(student_id=1)


class TestReportSnapshotReadRequest:
    def test_valid(self):
        m = ReportSnapshotReadRequest(student_id=1)
        assert m.student_id == 1


class TestPracticeEventWriteRequest:
    def test_valid(self):
        m = PracticeEventWriteRequest(student_id=1, event={"type": "practice"})
        assert m.event["type"] == "practice"

    def test_missing_event(self):
        with pytest.raises(ValidationError):
            PracticeEventWriteRequest(student_id=1)
