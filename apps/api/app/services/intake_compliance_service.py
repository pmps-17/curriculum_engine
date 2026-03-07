"""Intake compliance service — pre-analysis quality gates.

Runs a deterministic set of checks against the raw input and the
normalised item **before** pillar mapping begins.  The service is
**pure**: no database writes, no side effects.

Each check is a small function that returns one ``CheckResult``.  The
overall ``IntakeVerdict`` is derived by rolling up individual results.

Design notes
------------
- Rules are intentionally simple and configurable via module-level
  constants.  Swap them for database-driven policy rows later if needed.
- Every check includes a human-readable ``message`` so the UI can
  display clear feedback.
- New checks are added by writing one function and appending it to
  ``_ALL_CHECKS``.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field

from app.models.enums import ComplianceCheckType, ComplianceStatus
from app.services.normalization_service import NormalizedItem

logger = logging.getLogger(__name__)


# =====================================================================
# Configuration — easy to tune, all in one place
# =====================================================================

#: Minimum character count for lesson_text to be considered analysable.
MIN_LESSON_TEXT_LENGTH: int = 50

#: Minimum character count for any single section body to be considered
#: substantive (non-vague).
MIN_SECTION_BODY_LENGTH: int = 20

#: Minimum number of substantive sections required.
MIN_SUBSTANTIVE_SECTIONS: int = 1


# =====================================================================
# Value objects
# =====================================================================


class IntakeVerdict(str, enum.Enum):
    """Overall intake outcome rolled up from individual checks.

    - ``PASS``               — all checks passed, proceed to analysis.
    - ``PASS_WITH_WARNINGS`` — analysis can proceed but output may be
                               limited (e.g. no rubric → weaker
                               assessment conclusions).
    - ``INSUFFICIENT``       — the content is too sparse for meaningful
                               analysis; advise the user to enrich it.
    - ``REJECTED``           — hard failure (e.g. empty input); do not
                               proceed.
    """

    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    INSUFFICIENT = "insufficient"
    REJECTED = "rejected"


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single compliance check."""

    check_type: ComplianceCheckType
    status: ComplianceStatus
    message: str
    detail: str | None = None


@dataclass(frozen=True)
class IntakeComplianceReport:
    """Full report returned by ``run_intake_checks``.

    Attributes:
        verdict:  Overall rollup.
        results:  Individual check outcomes.
    """

    verdict: IntakeVerdict
    results: list[CheckResult] = field(default_factory=list)


# =====================================================================
# Individual checks
# =====================================================================


def _check_text_presence(
    lesson_text: str,
    _item: NormalizedItem,
) -> CheckResult:
    """RULE: lesson_text must be present and non-empty.

    This is the hard gate — if there is literally no input, the
    submission is rejected outright.
    """
    stripped = lesson_text.strip()
    if not stripped:
        return CheckResult(
            check_type=ComplianceCheckType.FORMAT_VALIDATION,
            status=ComplianceStatus.FAIL,
            message="lesson_text is empty or contains only whitespace.",
        )
    return CheckResult(
        check_type=ComplianceCheckType.FORMAT_VALIDATION,
        status=ComplianceStatus.PASS,
        message="lesson_text is present.",
    )


def _check_minimum_length(
    lesson_text: str,
    _item: NormalizedItem,
) -> CheckResult:
    """RULE: lesson_text must have enough content for meaningful analysis.

    The threshold is ``MIN_LESSON_TEXT_LENGTH`` characters.  Very short
    submissions may produce unreliable scores.
    """
    length = len(lesson_text.strip())
    if length < MIN_LESSON_TEXT_LENGTH:
        return CheckResult(
            check_type=ComplianceCheckType.LENGTH_CHECK,
            status=ComplianceStatus.FAIL,
            message=(
                f"lesson_text is too short for reliable analysis "
                f"({length} chars < {MIN_LESSON_TEXT_LENGTH} minimum)."
            ),
            detail=f"Character count: {length}",
        )
    return CheckResult(
        check_type=ComplianceCheckType.LENGTH_CHECK,
        status=ComplianceStatus.PASS,
        message=f"lesson_text length is adequate ({length} chars).",
    )


def _check_rubric_present(
    _lesson_text: str,
    _item: NormalizedItem,
    *,
    rubric_text: str | None = None,
) -> CheckResult:
    """RULE: rubric_text is optional but its absence weakens assessment mapping.

    Analysis proceeds either way, but we emit a warning so the user
    knows that assessment-based conclusions will be less reliable.
    """
    rubric_stripped = (rubric_text or "").strip()
    if not rubric_stripped:
        return CheckResult(
            check_type=ComplianceCheckType.OTHER,
            status=ComplianceStatus.WARNING,
            message=(
                "No rubric text provided. Assessment-based conclusions "
                "may be weaker."
            ),
            detail="Consider attaching a rubric for richer analysis.",
        )
    return CheckResult(
        check_type=ComplianceCheckType.OTHER,
        status=ComplianceStatus.PASS,
        message="Rubric text is provided.",
    )


def _check_section_substance(
    _lesson_text: str,
    item: NormalizedItem,
) -> CheckResult:
    """RULE: at least some sections must contain substantive text.

    Iterates over the normalized sections and counts how many have a
    body longer than ``MIN_SECTION_BODY_LENGTH``.  If none do, the
    content is flagged as insufficient.
    """
    substantive_count = sum(
        1
        for s in item.sections
        if len(s.body.strip()) >= MIN_SECTION_BODY_LENGTH
    )

    if substantive_count == 0 and item.sections:
        return CheckResult(
            check_type=ComplianceCheckType.REQUIRED_SECTIONS,
            status=ComplianceStatus.FAIL,
            message=(
                "All sections are too short or vague for meaningful "
                f"analysis (minimum body length: {MIN_SECTION_BODY_LENGTH} chars)."
            ),
            detail=f"Sections found: {len(item.sections)}, substantive: 0",
        )

    if substantive_count < MIN_SUBSTANTIVE_SECTIONS:
        return CheckResult(
            check_type=ComplianceCheckType.REQUIRED_SECTIONS,
            status=ComplianceStatus.WARNING,
            message=(
                f"Only {substantive_count} substantive section(s) detected "
                f"(recommended ≥ {MIN_SUBSTANTIVE_SECTIONS})."
            ),
            detail=f"Sections found: {len(item.sections)}, substantive: {substantive_count}",
        )

    return CheckResult(
        check_type=ComplianceCheckType.REQUIRED_SECTIONS,
        status=ComplianceStatus.PASS,
        message=f"{substantive_count} substantive section(s) detected.",
    )


# ── Check registry ───────────────────────────────────────────────────
# To add a new check: write a function with the same signature and
# append it here.  That's it.

_STANDARD_CHECKS = [
    _check_text_presence,
    _check_minimum_length,
    _check_section_substance,
]


# =====================================================================
# Verdict roll-up
# =====================================================================


def _derive_verdict(results: list[CheckResult]) -> IntakeVerdict:
    """Compute the overall verdict from individual check results.

    Priority (highest → lowest):
    1. Any FAIL from ``FORMAT_VALIDATION``  →  REJECTED
    2. Any other FAIL                       →  INSUFFICIENT
    3. Any WARNING                          →  PASS_WITH_WARNINGS
    4. Otherwise                            →  PASS
    """
    has_hard_fail = any(
        r.status == ComplianceStatus.FAIL
        and r.check_type == ComplianceCheckType.FORMAT_VALIDATION
        for r in results
    )
    if has_hard_fail:
        return IntakeVerdict.REJECTED

    has_fail = any(r.status == ComplianceStatus.FAIL for r in results)
    if has_fail:
        return IntakeVerdict.INSUFFICIENT

    has_warning = any(r.status == ComplianceStatus.WARNING for r in results)
    if has_warning:
        return IntakeVerdict.PASS_WITH_WARNINGS

    return IntakeVerdict.PASS


# =====================================================================
# Public API
# =====================================================================


def run_intake_checks(
    *,
    lesson_text: str,
    item: NormalizedItem,
    rubric_text: str | None = None,
) -> IntakeComplianceReport:
    """Execute all intake compliance checks and return a report.

    Parameters
    ----------
    lesson_text:
        The raw lesson/activity text as submitted by the user.
    item:
        The ``NormalizedItem`` produced by the normalization service.
    rubric_text:
        Optional rubric text.  Absence triggers a warning, not a
        failure.

    Returns
    -------
    IntakeComplianceReport
        Contains the overall ``IntakeVerdict`` and a list of individual
        ``CheckResult`` objects.

    Notes
    -----
    The function is deterministic and side-effect-free.
    """
    results: list[CheckResult] = []

    # Run standard checks (lesson_text + normalized item)
    for check_fn in _STANDARD_CHECKS:
        results.append(check_fn(lesson_text, item))

    # Rubric check has an extra keyword argument
    results.append(_check_rubric_present(lesson_text, item, rubric_text=rubric_text))

    verdict = _derive_verdict(results)

    logger.debug(
        "Intake compliance verdict=%s  checks=%d  warnings=%d  fails=%d",
        verdict.value,
        len(results),
        sum(1 for r in results if r.status == ComplianceStatus.WARNING),
        sum(1 for r in results if r.status == ComplianceStatus.FAIL),
    )

    return IntakeComplianceReport(verdict=verdict, results=results)
