"""Chunking service — splits normalized sections into smaller analysable units.

Chunks are the atomic text fragments fed into the candidate-matching
and scoring pipelines.  This service is **pure**: no DB writes, no
side effects.

Splitting strategy (v1)
-----------------------
1. Split each section body on **blank-line boundaries** (paragraph
   split).  This preserves natural paragraph grouping.
2. If a paragraph exceeds ``MAX_CHUNK_CHARS`` it is further split on
   **single newlines** (line-block split) as a fallback.
3. Leading/trailing whitespace is stripped from every chunk.
4. Empty or whitespace-only fragments are discarded.

Each resulting ``Chunk`` carries forward the ``SectionType`` and a
``chunk_index`` so that downstream code can trace the chunk back to its
source section and ordering.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.models.enums import SectionType
from app.services.normalization_service import NormalizedSection

logger = logging.getLogger(__name__)


# =====================================================================
# Configuration
# =====================================================================

#: Maximum character length for a single chunk.  Paragraphs longer than
#: this are further split on line boundaries.
MAX_CHUNK_CHARS: int = 1500

#: Regex that matches one or more blank lines (paragraph boundary).
_PARAGRAPH_SPLIT_RE: re.Pattern[str] = re.compile(r"\n\s*\n")


# =====================================================================
# Value object
# =====================================================================


@dataclass(frozen=True)
class Chunk:
    """An atomic text fragment ready for matching and persistence.

    Attributes:
        section_type:    Inherited from the parent section.
        section_sequence: 0-based index of the parent section.
        chunk_index:     0-based index within the parent section.
        text:            The chunk content (stripped, non-empty).
        token_estimate:  Rough word-count estimate (for future use).
    """

    section_type: SectionType
    section_sequence: int
    chunk_index: int
    text: str
    token_estimate: int


# =====================================================================
# Small helpers
# =====================================================================


def _estimate_tokens(text: str) -> int:
    """Return a rough word-count proxy for token estimation.

    Good enough for length budgeting.  Replace with a proper tokeniser
    (e.g. tiktoken) when embedding models are integrated.

    TODO: Swap for a real tokeniser once we add embedding support.
    """
    return len(text.split())


def _split_paragraphs(text: str) -> list[str]:
    """Split *text* on blank-line boundaries and strip each fragment.

    Returns only non-empty fragments.
    """
    parts = _PARAGRAPH_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _split_lines(text: str) -> list[str]:
    """Split *text* on single newlines and strip each fragment.

    Used as a fallback when a paragraph exceeds ``MAX_CHUNK_CHARS``.
    Returns only non-empty fragments.
    """
    return [line.strip() for line in text.splitlines() if line.strip()]


def _split_large_paragraph(paragraph: str) -> list[str]:
    """Break an oversized paragraph into smaller pieces.

    Strategy: split on newlines first.  If the paragraph is a single
    long line with no newlines the text is returned as-is (we don't
    mid-sentence split in v1).

    TODO: Add sentence-boundary splitting for very long single-line
          paragraphs when an NLP sentence tokeniser is available.
    """
    if len(paragraph) <= MAX_CHUNK_CHARS:
        return [paragraph]

    lines = _split_lines(paragraph)
    # If splitting didn't help (single long line), return as-is.
    if len(lines) <= 1:
        return [paragraph]
    return lines


# =====================================================================
# Public API
# =====================================================================


def chunk_section(section: NormalizedSection) -> list[Chunk]:
    """Split a single ``NormalizedSection`` into ``Chunk`` objects.

    Parameters
    ----------
    section:
        A normalized section produced by the normalization service.

    Returns
    -------
    list[Chunk]
        Zero or more chunks.  An empty list means the section body was
        blank or contained only whitespace.
    """
    body = section.body.strip()
    if not body:
        return []

    # Step 1: paragraph split
    paragraphs = _split_paragraphs(body)

    # Step 2: break oversized paragraphs
    fragments: list[str] = []
    for para in paragraphs:
        fragments.extend(_split_large_paragraph(para))

    # Step 3: build Chunk objects
    chunks: list[Chunk] = []
    for idx, text in enumerate(fragments):
        chunks.append(
            Chunk(
                section_type=section.section_type,
                section_sequence=section.sequence,
                chunk_index=idx,
                text=text,
                token_estimate=_estimate_tokens(text),
            )
        )

    return chunks


def chunk_sections(sections: list[NormalizedSection]) -> list[Chunk]:
    """Chunk every section in a list and return a flat list of ``Chunk``s.

    This is the main entry point used by the orchestration layer.
    Empty sections are silently skipped.

    Parameters
    ----------
    sections:
        Sections from a ``NormalizedItem.sections``.

    Returns
    -------
    list[Chunk]
        All chunks across all sections, preserving section ordering.
    """
    all_chunks: list[Chunk] = []
    for section in sections:
        all_chunks.extend(chunk_section(section))

    logger.debug(
        "Chunked %d section(s) → %d chunk(s).",
        len(sections),
        len(all_chunks),
    )
    return all_chunks
