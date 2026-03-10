# Curriculum Engine

> Research-grade curriculum governance and pillar-mapping engine — automatically analyzes school curriculum documents against a skills ontology, scores alignment, and provides evidence-based findings.

---

## What It Does

Schools upload curriculum documents (scope & sequence, unit plans, assessments, etc.). The engine:

1. **Normalizes** the document into structured sections (objectives, activities, assessments…).
2. **Checks intake compliance** — rejects documents that are too short, empty, or lack substance.
3. **Chunks** sections into analysis-ready text segments.
4. **Matches** chunks against ontology skill indicators using keyword matching (embedding-based matching planned).
5. **Scores** each skill on a 0–1 scale with section-type weighting (assessments worth more than plain content).
6. **Builds evidence** — extracts the top supporting text snippets for each skill score.
7. **Produces findings** — pillar-level and skill-level scores with confidence levels and taught/assessed flags.
8. **Supports human review** — reviewers can override scores with justifications, all changes are audit-logged.

### Pillars Analyzed

| Code | Pillar |
|------|--------|
| P1   | &mdash; |
| P2   | &mdash; |
| P3   | &mdash; |

---

## Tech Stack

| Layer          | Technology                     |
|----------------|--------------------------------|
| API Framework  | FastAPI 0.100+                 |
| ORM            | SQLAlchemy 2.0 (mapped_column) |
| Migrations     | Alembic                        |
| Database       | PostgreSQL 16                  |
| Validation     | Pydantic v2 + pydantic-settings|
| Runtime        | Python 3.12+                   |
| Containerization | Docker Compose               |

---

## Project Structure

```
my-curriculum-engine/
├── docker-compose.yml          # PostgreSQL 16 container
├── README.md
├── apps/
│   ├── api/                    # FastAPI backend (this is the main app)
│   │   ├── requirements.txt
│   │   ├── alembic.ini
│   │   ├── alembic/            # Database migrations
│   │   │   └── env.py
│   │   └── app/
│   │       ├── main.py                     # FastAPI entry point
│   │       ├── core/
│   │       │   ├── config.py               # Settings from env vars
│   │       │   └── db.py                   # Engine, session, Base
│   │       ├── models/
│   │       │   ├── enums.py                # 20 enums (SectionType, PillarCode, etc.)
│   │       │   ├── mixins.py               # TimestampMixin
│   │       │   ├── curriculum.py           # School, Document, Section, Chunk…
│   │       │   ├── ontology.py             # OntologyVersion, Pillar, Skill, Indicator
│   │       │   ├── analysis.py             # AnalysisRun, CandidateMatch, SkillScore…
│   │       │   ├── compliance.py           # IntakeComplianceResult, CoverageControl…
│   │       │   └── review.py               # Review, ReviewEdit, AuditLog
│   │       ├── schemas/
│   │       │   ├── base.py                 # CamelModel (camelCase responses)
│   │       │   ├── analysis.py             # AnalyzeRequest / AnalyzeResponse
│   │       │   ├── results.py              # ResultResponse
│   │       │   └── review.py               # ReviewRequest / ReviewResponse
│   │       ├── repositories/
│   │       │   ├── base.py                 # Generic BaseRepository[T]
│   │       │   └── ...                     # 11 domain-specific repositories
│   │       ├── services/
│   │       │   ├── normalization_service.py
│   │       │   ├── intake_compliance_service.py
│   │       │   ├── chunking_service.py
│   │       │   ├── candidate_matching_service.py
│   │       │   ├── scoring_service.py
│   │       │   ├── evidence_service.py
│   │       │   ├── analyze_service.py      # Orchestrator (owns DB transaction)
│   │       │   ├── results_service.py
│   │       │   └── review_service.py
│   │       └── routers/
│   │           ├── analyze.py              # POST /api/v1/analyze
│   │           ├── health.py               # GET  /health, GET /health/db
│   │           ├── results.py              # GET  /api/v1/results/{id}
│   │           └── review.py               # POST & GET /api/v1/reviews
│   └── web/                    # Frontend (future)
├── packages/
│   ├── ontology/               # Shared ontology definitions
│   └── shared/                 # Shared utilities
└── docker/                     # Dockerfiles (future)
```

---

## Architecture

```
Router (thin)  →  Service (thick)  →  Repository (thin)  →  Database
```

- **Routers** handle HTTP concerns: parse requests, call services, map exceptions to status codes.
- **Services** contain all business logic. Pure services (normalization, scoring, evidence) have zero DB dependencies. The `analyze_service` orchestrator owns the transaction.
- **Repositories** are a thin generic wrapper over SQLAlchemy — `flush` but never `commit` (the orchestrator commits).

---

## API Endpoints

| Method | Path                              | Description                          |
|--------|-----------------------------------|--------------------------------------|
| GET    | `/health`                         | Liveness check                       |
| GET    | `/health/db`                      | Readiness check (DB connectivity)    |
| POST   | `/api/v1/analyze`                 | Run a full curriculum analysis       |
| GET    | `/api/v1/results/{analysis_run_id}` | Retrieve analysis results          |
| POST   | `/api/v1/reviews`                 | Submit a human review with overrides |
| GET    | `/api/v1/reviews/{analysis_run_id}` | List reviews for an analysis run   |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- pip

### 1. Start the database

```bash
docker compose up -d
```

### 2. Set up the API

```bash
cd apps/api
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in `apps/api/`:

```env
DATABASE_URL=postgresql://appuser:apppass@localhost:5432/curriculum_engine
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

The API will be available at **http://localhost:8000**. Interactive docs at **http://localhost:8000/docs**.

---

## Analysis Pipeline (Step by Step)

```
Document Text
     │
     ▼
┌─────────────────────┐
│ 1. Normalize         │  → Split into sections, classify types
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 2. Intake Compliance │  → Reject if too short / empty / no substance
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 3. Chunk             │  → Break sections into ~1500-char segments
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 4. Candidate Match   │  → Keyword-match chunks to skill indicators
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 5. Score             │  → Weighted scoring per skill (0–1 scale)
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 6. Evidence          │  → Extract top-5 supporting snippets per skill
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 7. Persist & Return  │  → Save all results, return response
└─────────────────────┘
```

---

## License

Private — internal use only.
