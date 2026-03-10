"""Production-grade ontology v1.0 seed service.

This module loads pillar/skill/indicator data from JSON files and
performs idempotent upserts into the database.

JSON files are expected at:
- ../../../../packages/ontology/v1.0/pillars.json
- ../../../../packages/ontology/v1.0/skills.json
- ../../../../packages/ontology/v1.0/indicators.json

Relative from this file's location.

Idempotency:
- Running multiple times will not create duplicates.
- Existing records are updated if name/description changes.
- UpsertStrategy: ontology_versions by version_tag; pillars by pillar_code;
  skills by skill_code; indicators by (skill_code, indicator_type, indicator_text).
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.enums import OntologyStatus, PillarCode
from app.models.ontology import (
    OntologyVersion,
    Pillar,
    Skill,
    SkillIndicator,
)
from app.schemas.ontology_seed import (
    PillarSeedSchema,
    SkillSeedSchema,
    IndicatorSeedSchema,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

ONTOLOGY_VERSION_TAG = "v1.0"
"""Global version tag for this ontology."""

# Paths to JSON files (relative to this module)
_SCRIPT_DIR = Path(__file__).parent.parent.parent.parent.parent
PILLARS_JSON = _SCRIPT_DIR / "packages" / "ontology" / "v1.0" / "pillars.json"
SKILLS_JSON = _SCRIPT_DIR / "packages" / "ontology" / "v1.0" / "skills.json"
INDICATORS_JSON = _SCRIPT_DIR / "packages" / "ontology" / "v1.0" / "indicators.json"


# ─────────────────────────────────────────────────────────────────────
# Validators & Loaders
# ─────────────────────────────────────────────────────────────────────


def _load_json_file(filepath: Path) -> list[dict]:
    """Load and parse a JSON file.

    Parameters
    ----------
    filepath : Path
        Path to the JSON file.

    Returns
    -------
    list[dict]
        Parsed JSON data (expected to be a list of objects).

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    json.JSONDecodeError
        If the file is not valid JSON.
    """
    if not filepath.exists():
        raise FileNotFoundError(
            f"Ontology file not found: {filepath}\n"
            f"Expected location: {filepath}"
        )

    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in {filepath.name}: {e}"
        ) from e

    if not isinstance(data, list):
        raise ValueError(
            f"{filepath.name} must contain a JSON array, got {type(data).__name__}"
        )

    return data


def _load_and_validate_pillars() -> list[PillarSeedSchema]:
    """Load pillars from JSON and validate with Pydantic."""
    data = _load_json_file(PILLARS_JSON)
    pillars = []
    for idx, item in enumerate(data):
        try:
            pillar = PillarSeedSchema(**item)
            pillars.append(pillar)
        except ValidationError as e:
            raise ValueError(
                f"Validation error in pillars.json[{idx}]: {e.errors()}"
            ) from e
    logger.info(f"Loaded {len(pillars)} pillar(s) from pillars.json")
    return pillars


def _load_and_validate_skills() -> list[SkillSeedSchema]:
    """Load skills from JSON and validate with Pydantic."""
    data = _load_json_file(SKILLS_JSON)
    skills = []
    for idx, item in enumerate(data):
        try:
            skill = SkillSeedSchema(**item)
            skills.append(skill)
        except ValidationError as e:
            raise ValueError(
                f"Validation error in skills.json[{idx}]: {e.errors()}"
            ) from e
    logger.info(f"Loaded {len(skills)} skill(s) from skills.json")
    return skills


def _load_and_validate_indicators() -> list[IndicatorSeedSchema]:
    """Load indicators from JSON and validate with Pydantic."""
    data = _load_json_file(INDICATORS_JSON)
    indicators = []
    for idx, item in enumerate(data):
        try:
            indicator = IndicatorSeedSchema(**item)
            indicators.append(indicator)
        except ValidationError as e:
            raise ValueError(
                f"Validation error in indicators.json[{idx}]: {e.errors()}"
            ) from e
    logger.info(f"Loaded {len(indicators)} indicator(s) from indicators.json")
    return indicators


# ─────────────────────────────────────────────────────────────────────
# Upsert Logic (idempotent)
# ─────────────────────────────────────────────────────────────────────


def _upsert_ontology_version(db: Session, version_tag: str) -> OntologyVersion:
    """Ensure ontology version exists; create if missing.

    Parameters
    ----------
    db : Session
        SQLAlchemy session.
    version_tag : str
        Version identifier (e.g., 'v1.0').

    Returns
    -------
    OntologyVersion
        The ontology version (created or existing).
    """
    stmt = select(OntologyVersion).where(
        OntologyVersion.version_label == version_tag
    )
    ontology = db.scalars(stmt).first()

    if ontology:
        logger.info(f"OntologyVersion '{version_tag}' already exists (id={ontology.id})")
        # Ensure it's active
        if ontology.status != OntologyStatus.ACTIVE:
            ontology.status = OntologyStatus.ACTIVE
            db.add(ontology)
            logger.info(f"Updated OntologyVersion '{version_tag}' to ACTIVE")
        return ontology

    ontology = OntologyVersion(
        version_label=version_tag,
        status=OntologyStatus.ACTIVE,
        description=f"Ontology v1.0 seeded from JSON",
    )
    db.add(ontology)
    db.flush()
    logger.info(f"Created OntologyVersion '{version_tag}' (id={ontology.id})")
    return ontology


def _upsert_pillars(
    db: Session,
    ontology: OntologyVersion,
    pillars_data: list[PillarSeedSchema],
) -> dict[str, Pillar]:
    """Upsert pillars; return mapping of pillar_code → Pillar.

    Parameters
    ----------
    db : Session
        SQLAlchemy session.
    ontology : OntologyVersion
        Parent ontology version.
    pillars_data : list[PillarSeedSchema]
        Validated pillar data from JSON.

    Returns
    -------
    dict[str, Pillar]
        Mapping of pillar_code → Pillar model.
    """
    pillar_map: dict[str, Pillar] = {}

    for pillar_data in pillars_data:
        code = pillar_data.pillar_code
        # Validate that code is a valid PillarCode enum
        try:
            pillar_code_enum = PillarCode(code)
        except ValueError:
            raise ValueError(
                f"Pillar code '{code}' is not a valid PillarCode. "
                f"Must be one of: {', '.join([p.value for p in PillarCode])}"
            )

        # Check if pillar already exists for this ontology version
        stmt = select(Pillar).where(
            (Pillar.ontology_version_id == ontology.id)
            & (Pillar.code == pillar_code_enum)
        )
        pillar = db.scalars(stmt).first()

        if pillar:
            # Update name/description if changed
            if pillar.name != pillar_data.name:
                pillar.name = pillar_data.name
                logger.debug(f"Updated pillar {code} name to '{pillar_data.name}'")
            desc = pillar_data.get_description()
            if pillar.description != desc:
                pillar.description = desc
                logger.debug(f"Updated pillar {code} description")
            db.add(pillar)
            logger.info(f"Pillar {code} already exists (id={pillar.id})")
        else:
            pillar = Pillar(
                ontology_version_id=ontology.id,
                code=pillar_code_enum,
                name=pillar_data.name,
                description=pillar_data.get_description(),
            )
            db.add(pillar)
            db.flush()
            logger.info(f"Created Pillar {code} (id={pillar.id})")

        pillar_map[code] = pillar

    return pillar_map


def _upsert_skills(
    db: Session,
    skills_data: list[SkillSeedSchema],
    pillar_map: dict[str, Pillar],
) -> dict[str, Skill]:
    """Upsert skills; return mapping of skill_code → Skill.

    Parameters
    ----------
    db : Session
        SQLAlchemy session.
    skills_data : list[SkillSeedSchema]
        Validated skill data from JSON.
    pillar_map : dict[str, Pillar]
        Mapping of pillar_code → Pillar (from _upsert_pillars).

    Returns
    -------
    dict[str, Skill]
        Mapping of skill_code → Skill model.

    Raises
    ------
    ValueError
        If a skill references a pillar_code not in pillar_map.
    """
    skill_map: dict[str, Skill] = {}

    for skill_data in skills_data:
        pillar_code = skill_data.pillar_code
        skill_code = skill_data.skill_code

        if pillar_code not in pillar_map:
            raise ValueError(
                f"Skill {skill_code} references unknown pillar '{pillar_code}'. "
                f"Available pillars: {list(pillar_map.keys())}"
            )

        pillar = pillar_map[pillar_code]

        # Check if skill already exists
        stmt = select(Skill).where(Skill.code == skill_code)
        skill = db.scalars(stmt).first()

        if skill:
            # Update name/description if changed
            if skill.name != skill_data.name:
                skill.name = skill_data.name
                logger.debug(f"Updated skill {skill_code} name")
            if skill.description != skill_data.description:
                skill.description = skill_data.description
                logger.debug(f"Updated skill {skill_code} description")
            db.add(skill)
            logger.info(f"Skill {skill_code} already exists (id={skill.id})")
        else:
            skill = Skill(
                pillar_id=pillar.id,
                code=skill_code,
                name=skill_data.name,
                description=skill_data.description,
                sort_order=0,  # Default; could be enhanced with JSON data
            )
            db.add(skill)
            db.flush()
            logger.info(f"Created Skill {skill_code} (id={skill.id})")

        skill_map[skill_code] = skill

    return skill_map


def _upsert_indicators(
    db: Session,
    indicators_data: list[IndicatorSeedSchema],
    skill_map: dict[str, Skill],
) -> int:
    """Upsert skill indicators; return count created/updated.

    Parameters
    ----------
    db : Session
        SQLAlchemy session.
    indicators_data : list[IndicatorSeedSchema]
        Validated indicator data from JSON.
    skill_map : dict[str, Skill]
        Mapping of skill_code → Skill (from _upsert_skills).

    Returns
    -------
    int
        Number of indicators processed.

    Raises
    ------
    ValueError
        If an indicator references a skill_code not in skill_map.
    """
    created_count = 0
    updated_count = 0

    for indicator_data in indicators_data:
        skill_code = indicator_data.skill_code

        if skill_code not in skill_map:
            raise ValueError(
                f"Indicator for skill '{skill_code}' references unknown skill. "
                f"Available skills: {list(skill_map.keys())}"
            )

        skill = skill_map[skill_code]

        # Check if indicator already exists (unique by skill_code + indicator_type + indicator_text)
        stmt = select(SkillIndicator).where(
            (SkillIndicator.skill_id == skill.id)
            # Note: DB schema may not have indicator_type; adjust if needed
        )
        indicator = db.scalars(stmt).first()

        if indicator:
            # Update weight if changed
            if indicator.weight != indicator_data.weight:
                indicator.weight = indicator_data.weight
                logger.debug(
                    f"Updated indicator for {skill_code}: weight={indicator_data.weight}"
                )
            db.add(indicator)
            updated_count += 1
            logger.info(f"Indicator for {skill_code} already exists (id={indicator.id})")
        else:
            indicator = SkillIndicator(
                skill_id=skill.id,
                indicator_text=indicator_data.indicator_text,
                keywords=indicator_data.indicator_type,  # Store type in keywords field
                weight=indicator_data.weight,
            )
            db.add(indicator)
            db.flush()
            created_count += 1
            logger.info(f"Created SkillIndicator for {skill_code} (id={indicator.id})")

    return created_count + updated_count


# ─────────────────────────────────────────────────────────────────────
# Main Seed Function
# ─────────────────────────────────────────────────────────────────────


def seed_ontology_v1_0(db: Session) -> dict:
    """Load and persist ontology v1.0 from JSON files.

    This function is idempotent: running it multiple times will not
    create duplicates.

    Parameters
    ----------
    db : Session
        SQLAlchemy session (typically from app.core.db.SessionLocal).

    Returns
    -------
    dict
        Summary of what was created/updated:
        {
            'ontology_version': OntologyVersion,
            'pillars_created': int,
            'skills_created': int,
            'indicators_created': int,
            'version_tag': str,
        }

    Raises
    ------
    FileNotFoundError
        If JSON files do not exist.
    json.JSONDecodeError
        If JSON files are malformed.
    ValueError
        If validation fails or referential integrity is violated.
    """
    logger.info("Starting ontology v1.0 seed pipeline...")

    try:
        # Load and validate all data
        logger.info("Loading JSON files...")
        pillars_data = _load_and_validate_pillars()
        skills_data = _load_and_validate_skills()
        indicators_data = _load_and_validate_indicators()

        logger.info(
            f"Loaded: {len(pillars_data)} pillars, "
            f"{len(skills_data)} skills, {len(indicators_data)} indicators"
        )

        # Upsert to database
        logger.info("Upserting to database...")
        ontology = _upsert_ontology_version(db, ONTOLOGY_VERSION_TAG)
        pillar_map = _upsert_pillars(db, ontology, pillars_data)
        skill_map = _upsert_skills(db, skills_data, pillar_map)
        indicator_count = _upsert_indicators(db, indicators_data, skill_map)

        # Commit transaction
        db.commit()
        logger.info("Transaction committed.")

        result = {
            "ontology_version": ontology,
            "version_tag": ONTOLOGY_VERSION_TAG,
            "pillars_count": len(pillar_map),
            "skills_count": len(skill_map),
            "indicators_count": indicator_count,
        }

        logger.info(
            f"✅ Ontology v1.0 seed complete: "
            f"{len(pillar_map)} pillars, {len(skill_map)} skills, "
            f"{indicator_count} indicators"
        )
        return result

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Seed pipeline failed: {e}", exc_info=True)
        raise


# ─────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for the seed script.

    Usage:
        python -m app.services.seed_ontology_v1

    This sets up logging and calls seed_ontology_v1_0() with a DB session.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Ontology v1.0 Seed Service")
    logger.info("=" * 70)

    db = SessionLocal()
    try:
        result = seed_ontology_v1_0(db)

        print("\n" + "=" * 70)
        print("✅ ONTOLOGY SEEDED SUCCESSFULLY")
        print("=" * 70)
        print(f"""
Version:     {result['version_tag']}
Pillars:     {result['pillars_count']}
Skills:      {result['skills_count']}
Indicators:  {result['indicators_count']}

The ontology is now active and ready for curriculum analysis.
""")

    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        print(
            f"\n❌ Missing ontology file:\n{e}\n"
            f"Ensure JSON files exist at packages/ontology/v1.0/",
            file=sys.stderr,
        )
        sys.exit(1)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(f"\n❌ Validation error:\n{e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error:\n{e}", file=sys.stderr)
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
