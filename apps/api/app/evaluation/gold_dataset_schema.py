"""Gold dataset schema — defines the format for evaluation items.

Each evaluation item represents a curriculum text with known expected
pillar (and optionally skill) alignment.  The evaluation harness loads
a JSON file conforming to this schema and compares predicted results
against the expected labels.

JSON file format (``gold_v1.json``)::

    [
        {
            "id": "eval-001",
            "title": "Lesson: Rock Cycle",
            "subject": "Science",
            "grade_band": "Grade 5",
            "lesson_text": "Students will explore the rock cycle...",
            "rubric_text": null,
            "expected_pillars": ["P2", "P3"],
            "expected_skills": ["P2-S1", "P3-S4"]
        },
        ...
    ]
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GoldItem(BaseModel):
    """A single evaluation item with ground-truth labels."""

    id: str = Field(description="Unique identifier for this eval item.")
    title: str = Field(description="Curriculum item title.")
    subject: str | None = Field(default=None, description="Subject area.")
    grade_band: str | None = Field(default=None, description="Grade band.")
    lesson_text: str = Field(
        min_length=1, description="Raw lesson/curriculum text."
    )
    rubric_text: str | None = Field(
        default=None, description="Optional rubric text."
    )
    expected_pillars: list[str] = Field(
        description="Expected pillar codes (e.g. ['P2', 'P3'])."
    )
    expected_skills: list[str] = Field(
        default_factory=list,
        description="Optional expected skill codes (e.g. ['P2-S1']).",
    )


class GoldDataset(BaseModel):
    """Container for a list of gold evaluation items."""

    items: list[GoldItem] = Field(description="The evaluation items.")
