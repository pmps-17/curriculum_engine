"""Normalization service — transforms raw curriculum input into structured sections.

This is a **pure** service: it takes plain data in, returns plain data
out, and performs **no** database writes.  The output is a
``NormalizedItem`` that downstream services (persistence, chunking,
analysis) consume.

Section detection uses lightweight regex heuristics today.  Each
heuristic helper is a small, individually testable function.  TODOs mark
where NLP / LLM-based parsing can replace or augment the rules later.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.models.enums import CurriculumItemType, SectionType

logger = logging.getLogger(__name__)

# =====================================================================
# Internal value objects (not ORM models, not API schemas)
# =====================================================================


@dataclass(frozen=True)
class NormalizedSection:
    """A single detected section within a curriculum item.

    Attributes:
        section_type: Semantic role of this section.
        heading:      The detected heading text, if any.
        body:         Full text content of the section.
        sequence:     0-based ordering within the parent item.
    """

    section_type: SectionType
    heading: str | None
    body: str
    sequence: int


@dataclass(frozen=True)
class NormalizedItem:
    """Structured representation of a normalized curriculum item.

    This is what the normalization service returns.  It is entirely
    independent of the database and of API schemas.
    """

    title: str | None
    item_type: CurriculumItemType
    subject: str | None
    grade_band: str | None
    unit_name: str | None
    sections: list[NormalizedSection] = field(default_factory=list)


# =====================================================================
# Header-pattern registry
# =====================================================================

# Each entry maps a compiled regex to a ``SectionType``.  Patterns are
# tried in order; the **first** match wins.  Keep the list small and
# explicit — more sophisticated detection belongs in a future NLP pass.

_HEADER_PATTERNS: list[tuple[re.Pattern[str], SectionType]] = [
    # Objectives / learning goals
    (re.compile(
        r"^#+\s*(learning\s+)?objectives?"
        r"|^objectives?"
        r"|^learning\s+(goals?|outcomes?)"
        r"|^goals?\s*:",
        re.IGNORECASE,
    ), SectionType.OBJECTIVE),

    # Assessment / evaluation
    (re.compile(
        r"^#+\s*assessments?"
        r"|^assessments?"
        r"|^evaluation"
        r"|^formative\s+assessment"
        r"|^summative\s+assessment",
        re.IGNORECASE,
    ), SectionType.ASSESSMENT),

    # Rubric (checked before activity so "rubric" isn't caught by the
    # broader "activity" pattern)
    (re.compile(
        r"^#+\s*rubrics?"
        r"|^rubrics?"
        r"|^scoring\s+(guide|criteria)",
        re.IGNORECASE,
    ), SectionType.RUBRIC),

    # Activity / instruction
    (re.compile(
        r"^#+\s*activit(y|ies)"
        r"|^activit(y|ies)"
        r"|^instruction"
        r"|^lesson\s+steps?"
        r"|^procedure"
        r"|^lesson\s+plan"
        r"|^teaching\s+activities",
        re.IGNORECASE,
    ), SectionType.ACTIVITY),

    # Generic content / instruction body
    (re.compile(
        r"^#+\s*content"
        r"|^content"
        r"|^materials?"
        r"|^resources?"
        r"|^introduction"
        r"|^overview",
        re.IGNORECASE,
    ), SectionType.CONTENT),
]


# =====================================================================
# Small helper functions (individually testable)
# =====================================================================


def _classify_heading(line: str) -> SectionType:
    """Return the ``SectionType`` for a heading line.

    Tries each pattern in ``_HEADER_PATTERNS`` in order.  Falls back to
    ``SectionType.OTHER`` if nothing matches.

    TODO: Replace with a lightweight classifier or LLM prompt for
          languages / formats where keyword matching is insufficient.
    """
    stripped = line.strip()
    for pattern, section_type in _HEADER_PATTERNS:
        if pattern.search(stripped):
            return section_type
    return SectionType.OTHER


def _is_heading(line: str) -> bool:
    """Heuristic: does this line look like a section heading?

    Current rules:
    - Markdown headings (``# …``, ``## …``, etc.)
    - ALL-CAPS lines of reasonable length
    - Lines ending with ``:`` and containing fewer than 80 chars

    TODO: Support numbered headings (``1. Objectives``), underline-style
          Markdown headings, and HTML ``<h*>`` tags.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return True
    if stripped.isupper() and 3 <= len(stripped) <= 80:
        return True
    if stripped.endswith(":") and len(stripped) < 80:
        return True
    return False


def _split_into_raw_sections(text: str) -> list[tuple[str | None, str]]:
    """Split *text* on detected headings.

    Returns a list of ``(heading_or_None, body_text)`` tuples.
    If the text starts with non-heading content, the first tuple's
    heading will be ``None``.
    """
    lines = text.splitlines()
    sections: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_body: list[str] = []

    for line in lines:
        if _is_heading(line):
            # Flush the previous section
            if current_body or current_heading is not None:
                sections.append((current_heading, current_body))
            current_heading = line.strip().lstrip("#").strip().rstrip(":")
            current_body = []
        else:
            current_body.append(line)

    # Flush the last section
    if current_body or current_heading is not None:
        sections.append((current_heading, current_body))

    # Join body lines back into strings
    return [
        (heading, "\n".join(body_lines).strip())
        for heading, body_lines in sections
    ]


def _build_section(
    heading: str | None,
    body: str,
    sequence: int,
) -> NormalizedSection:
    """Create a ``NormalizedSection`` from a raw heading + body pair."""
    if heading:
        section_type = _classify_heading(heading)
    else:
        section_type = SectionType.OTHER
    return NormalizedSection(
        section_type=section_type,
        heading=heading,
        body=body,
        sequence=sequence,
    )


# =====================================================================
# Public API
# =====================================================================


def normalize(
    *,
    title: str | None = None,
    item_type: CurriculumItemType = CurriculumItemType.LESSON,
    subject: str | None = None,
    grade_band: str | None = None,
    unit_name: str | None = None,
    lesson_text: str,
    rubric_text: str | None = None,
) -> NormalizedItem:
    """Normalize raw curriculum input into a ``NormalizedItem``.

    Parameters
    ----------
    title:
        Human-readable title of the lesson / activity.
    item_type:
        Granularity (lesson, activity, module, unit).
    subject:
        Subject area (e.g. ``"Mathematics"``).
    grade_band:
        Grade level or band (e.g. ``"Grade 5"``).
    unit_name:
        Parent unit name, if known.
    lesson_text:
        The raw curriculum / lesson text to parse.
    rubric_text:
        Optional rubric text.  If provided, an additional
        ``RUBRIC``-typed section is appended.

    Returns
    -------
    NormalizedItem
        Structured item with detected sections ready for persistence
        and chunking.

    Notes
    -----
    - If no headings are detected the entire ``lesson_text`` is
      preserved as a single ``OTHER`` section.
    - Empty ``lesson_text`` (after stripping) produces zero sections
      (plus a rubric section if ``rubric_text`` is provided).

    TODO: Add language detection and encoding normalisation.
    TODO: Add duplicate / near-duplicate detection across items.
    """
    sections: list[NormalizedSection] = []
    sequence = 0

    # ── Parse lesson text ────────────────────────────────────────────
    cleaned = lesson_text.strip()
    if cleaned:
        raw_sections = _split_into_raw_sections(cleaned)

        # If splitting produced nothing useful (all empty bodies and no
        # headings), fall back to one big section.
        has_content = any(body for _, body in raw_sections)
        if not has_content:
            raw_sections = [(None, cleaned)]

        for heading, body in raw_sections:
            if not body and heading is None:
                continue
            sections.append(_build_section(heading, body, sequence))
            sequence += 1

    # ── Append rubric section if provided ────────────────────────────
    rubric_cleaned = (rubric_text or "").strip()
    if rubric_cleaned:
        sections.append(
            NormalizedSection(
                section_type=SectionType.RUBRIC,
                heading="Rubric",
                body=rubric_cleaned,
                sequence=sequence,
            )
        )
        sequence += 1

    logger.debug(
        "Normalized '%s': %d section(s) detected.",
        title or "(untitled)",
        len(sections),
    )

    return NormalizedItem(
        title=title,
        item_type=item_type,
        subject=subject,
        grade_band=grade_band,
        unit_name=unit_name,
        sections=sections,
    )
