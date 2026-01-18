from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class TaggingResult(BaseModel):
    """Normalized schema for automated content tagging."""

    core_concept: str = Field(..., description="Must be one entry from the provided knowledge point list")
    prerequisites: list[str] = Field(default_factory=list)
    difficulty: int = Field(..., ge=1, le=5)
    estimated_time_sec: int = Field(..., ge=15, le=3600)
    rationale: Optional[str] = Field(
        default=None,
        description="Optional short rationale explaining why the tags were chosen",
    )


class MisconceptionOption(BaseModel):
    key: Literal["A", "B", "C", "D"]
    text: str
    values: Optional[list[str]] = Field(
        default=None,
        description="Structured values represented by this option (e.g., roots). Used for automated verification.",
    )
    misconception_tag: Optional[str] = Field(
        default=None,
        description="For wrong options: a short misconception tag; for correct: null/empty",
    )


class VerificationEquation(BaseModel):
    """A minimal payload to let Sympy validate correctness."""

    symbol: str = Field(default="x", description="Main variable symbol")
    expr: str = Field(
        ...,
        description="Sympy expression interpreted as expr == 0. Example: 'x**2 - 5*x + 6'",
    )
    solution_set: list[str] = Field(
        default_factory=list,
        description="Expected solutions as strings, normalized. Example: ['2','3']",
    )


class MisconceptionMCQ(BaseModel):
    concept_tag: str
    stem: str
    verification: VerificationEquation
    options: list[MisconceptionOption]
    correct: Literal["A", "B", "C", "D"]

    solution: str = Field(
        ..., description="Step-by-step solution or key reasoning (teacher-facing)"
    )
    diagnostics: dict[str, str] = Field(
        ...,
        description="Map option key -> what it implies about the student's misconception",
    )
    hints: dict[str, str] = Field(
        ...,
        description=(
            "Textbook-style hint system. Prefer 4 layers with keys: level1, level2, level3, level4 "
            "(整理→因式分解→零乘積→公式驗算). For backward compatibility, level4 may be omitted."
        ),
    )


class GeneratedMCQSet(BaseModel):
    items: list[MisconceptionMCQ]
