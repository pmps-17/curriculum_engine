# Ontology v1.0 Seeding System

This document describes the production-grade ontology seeding pipeline for the Curriculum Engine.

## Overview

The ontology defines the skills framework that curriculum is mapped against. It consists of:

- **Pillars**: High-level competency areas (P1, P2, P3)
- **Skills**: Discrete skills under each pillar (P2-S1, P2-S2, etc.)
- **Indicators**: Observables or keywords that signal skill presence

## Directory Structure

```
packages/ontology/v1.0/
├── pillars.json       ← Pillar definitions
├── skills.json        ← Skill definitions
└── indicators.json    ← Skill indicator definitions

apps/api/app/
├── schemas/ontology_seed.py          ← Pydantic validation schemas
└── services/seed_ontology_v1.py      ← Main seed service
```

## JSON Schema

### pillars.json

Each pillar object must have:

```json
{
  "pillar_code": "P2",
  "name": "Analysis & Analytical Thinking",
  "description": "Long-form description...",
  "boundaries": "(optional) scope boundaries"
}
```

**Fields:**
- `pillar_code` (required): Unique code; must match `PillarCode` enum (P1, P2, P3)
- `name` (required): Display name
- `description` (optional): Detailed description
- `definition` (optional): Alternative to `description` (falls back if description missing)
- `boundaries` (optional): Scope/boundaries

**Example:**
```json
[
  {
    "pillar_code": "P2",
    "name": "Analysis & Analytical Thinking",
    "description": "Students demonstrate the ability to analyze information, break down complex concepts, and evaluate evidence systematically."
  },
  {
    "pillar_code": "P3",
    "name": "Critical Thinking & Problem Solving",
    "description": "Students apply critical thinking skills to solve problems, make decisions, and develop innovative solutions."
  }
]
```

### skills.json

Each skill object must have:

```json
{
  "pillar_code": "P2",
  "skill_code": "P2-S1",
  "name": "Breaking Down Complex Information",
  "description": "Ability to decompose complex ideas..."
}
```

**Fields:**
- `pillar_code` (required): Parent pillar code
- `skill_code` (required): Unique skill code
- `name` (required): Display name
- `description` (required): What this skill entails

**Example:**
```json
[
  {
    "pillar_code": "P2",
    "skill_code": "P2-S1",
    "name": "Breaking Down Complex Information",
    "description": "Ability to decompose complex ideas, texts, or problems into component parts for deeper understanding."
  },
  {
    "pillar_code": "P2",
    "skill_code": "P2-S2",
    "name": "Comparing & Evaluating Evidence",
    "description": "Ability to compare different viewpoints, evaluate evidence quality, and assess credibility."
  }
]
```

### indicators.json

Each indicator object must have:

```json
{
  "skill_code": "P2-S1",
  "indicator_type": "keyword",
  "indicator_text": "analyze, break down, decompose, identify parts",
  "weight": 1.0
}
```

**Fields:**
- `skill_code` (required): Parent skill code
- `indicator_type` (required): Type of indicator (e.g., `keyword`, `behavior`, `observable`)
- `indicator_text` (required): The actual indicator content
- `weight` (optional): Indicator weight in scoring (default: 1.0, range: 0.0-2.0)
- `strength` (optional): Ignored; kept for format compatibility

**Example:**
```json
[
  {
    "skill_code": "P2-S1",
    "indicator_type": "keyword",
    "indicator_text": "analyze, break down, decompose, identify parts, component, structure, element",
    "weight": 1.0
  },
  {
    "skill_code": "P2-S2",
    "indicator_type": "keyword",
    "indicator_text": "compare, contrast, evaluate, assess, judge, credibility, evidence, quality",
    "weight": 1.0
  }
]
```

## Running the Seed Script

### From the apps/api directory:

```bash
# Using conda environment
conda run -n curriculum-engine python -m app.services.seed_ontology_v1

# Or if conda is already activated
python -m app.services.seed_ontology_v1
```

### Expected Output:

```
======================================================================
✅ ONTOLOGY SEEDED SUCCESSFULLY
======================================================================

Version:     v1.0
Pillars:     3
Skills:      6
Indicators:  6

The ontology is now active and ready for curriculum analysis.
```

## Idempotency

The seeding pipeline is **idempotent** — you can run it multiple times without creating duplicates:

1. **OntologyVersion**: Creates only if `version_tag="v1.0"` doesn't exist
2. **Pillars**: Unique by `pillar_code` within the version
3. **Skills**: Unique by `skill_code` across all pillars
4. **Indicators**: Unique by `(skill_id, indicator_text)`

Existing records are updated if name/description fields change.

## Architecture

### Data Flow

```
pillars.json ─┐
skills.json  ─┼→ [Pydantic Validation] ─→ [Upsert to DB]
indicators.json┘
```

### Key Components

**Schemas** (`app/schemas/ontology_seed.py`):
- `PillarSeedSchema`: Validates pillar JSON structure
- `SkillSeedSchema`: Validates skill JSON structure
- `IndicatorSeedSchema`: Validates indicator JSON structure

**Service** (`app/services/seed_ontology_v1.py`):
- `_load_json_file()`: Load and parse JSON with error handling
- `_load_and_validate_*()`: Load JSON and validate with Pydantic
- `_upsert_ontology_version()`: Ensure version exists
- `_upsert_pillars()`: Upsert pillars and return mapping
- `_upsert_skills()`: Upsert skills and return mapping
- `_upsert_indicators()`: Upsert indicators
- `seed_ontology_v1_0()`: Main orchestration function
- `main()`: CLI entry point

## Error Handling

The service provides clear error messages for common issues:

### Missing Files
```
❌ Missing ontology file:
Ontology file not found: /path/to/packages/ontology/v1.0/pillars.json
Expected location: /path/to/packages/ontology/v1.0/pillars.json
```

### Invalid JSON
```
❌ Invalid JSON in pillars.json: Expecting value: line 1 column 1 (char 0)
```

### Validation Error
```
❌ Validation error:
Validation error in skills.json[0]: [{'type': 'value_error', ...}]
```

### Missing Pillar Reference
```
❌ Skill P2-S1 references unknown pillar 'P99'.
Available pillars: ['P1', 'P2', 'P3']
```

## Logging

The service logs all operations:

```
2026-03-09 10:30:15,123 [INFO] app.services.seed_ontology_v1: Starting ontology v1.0 seed pipeline...
2026-03-09 10:30:15,145 [INFO] app.services.seed_ontology_v1: Loaded 3 pillar(s) from pillars.json
2026-03-09 10:30:15,167 [INFO] app.services.seed_ontology_v1: Loaded 6 skill(s) from skills.json
2026-03-09 10:30:15,189 [INFO] app.services.seed_ontology_v1: Loaded 6 indicator(s) from indicators.json
2026-03-09 10:30:15,201 [INFO] app.services.seed_ontology_v1: Created OntologyVersion 'v1.0' (id=...)
2026-03-09 10:30:15,215 [INFO] app.services.seed_ontology_v1: Created Pillar P2 (id=...)
...
2026-03-09 10:30:15,312 [INFO] app.services.seed_ontology_v1: ✅ Ontology v1.0 seed complete: 3 pillars, 6 skills, 6 indicators
```

## Next Steps

1. **Populate JSON files** with your pillar/skill/indicator definitions
2. **Run the seed script**:
   ```bash
   cd /Users/monikap/Downloads/my-curriculum-engine/apps/api
   python -m app.services.seed_ontology_v1
   ```
3. **Verify in database**:
   ```sql
   SELECT * FROM ontology_versions WHERE version_label='v1.0';
   SELECT * FROM pillars WHERE ontology_version_id = <id>;
   SELECT * FROM skills WHERE pillar_id IN (...);
   SELECT * FROM skill_indicators WHERE skill_id IN (...);
   ```

## Implementation Notes

- **Thread-safe**: Each invocation gets a new `SessionLocal()` instance
- **No hardcoded data**: All data comes from JSON files (easy to maintain, version control friendly)
- **Validation first**: Pydantic validates before any DB writes
- **Transaction safety**: All DB operations in one transaction (rollback on error)
- **Type hints**: Full type annotations for IDE support and mypy compatibility
- **Docstrings**: Comprehensive module and function documentation

## Troubleshooting

### Error: "Ontology file not found"
- Check that `packages/ontology/v1.0/` directory exists
- Verify file paths are correct (relative to repo root)
- Ensure files are named exactly: `pillars.json`, `skills.json`, `indicators.json`

### Error: "Invalid JSON"
- Validate JSON using a linter: `python -m json.tool packages/ontology/v1.0/pillars.json`
- Check for trailing commas, missing quotes, etc.

### Error: "Pillar code 'P99' is not valid"
- Check `PillarCode` enum in `app/models/enums.py`
- Currently only P1, P2, P3 are supported; expand enum if needed

### Error: "Skill P2-S1 references unknown pillar 'P2'"
- Ensure pillar_code in skills.json matches a pillar_code in pillars.json
- Check for case sensitivity (codes are uppercased automatically)

### Script runs but no output
- Check database connection: `sqlalchemy` settings in `app/core/config.py`
- Check logs: `tail -f app.log` or enable DEBUG logging

---

**Version**: v1.0  
**Created**: March 9, 2026  
**Maintainer**: Curriculum Engine Team
