# Curriculum Engine

> Research-grade curriculum governance and pillar-mapping engine — automatically analyzes school curriculum documents against a skills ontology, scores alignment, and provides evidence-based findings.

---

## What It Does

Schools upload curriculum documents (scope & sequence, unit plans, assessments, etc.). The engine:

1. **Normalizes** the document into structured sections (objectives, activities, assessments…).
2. **Checks intake compliance** — rejects documents that are too short, empty, or lack substance.
3. **Chunks** sections into analysis-ready text segments.
4. **Matches** chunks against ontology skills using **semantic embeddings** (with keyword fallback).
5. **Scores** each skill on a 0–1 scale with section-type weighting (assessments worth more than plain content).
6. **Builds evidence** — extracts the top supporting text snippets for each skill score.
7. **Produces findings** — pillar-level and skill-level scores with confidence levels and taught/assessed flags.
8. **Supports human review** — reviewers can override scores with justifications, all changes are audit-logged.

### Pillars Analyzed

| Code | Pillar |
|------|--------|
| P1   | — |
| P2   | — |
| P3   | — |

---

## Tech Stack

| Layer              | Technology                                |
|--------------------|-------------------------------------------|
| **API Framework**  | FastAPI 0.100+                            |
| **ORM**            | SQLAlchemy 2.0 (`mapped_column`)          |
| **Migrations**     | Alembic                                   |
| **Database**       | PostgreSQL 16 + pgvector                  |
| **Embeddings**     | sentence-transformers (local) or OpenAI   |
| **Validation**     | Pydantic v2 + pydantic-settings           |
| **Runtime**        | Python 3.12+                              |
| **Frontend**       | Next.js 16 + TypeScript + TanStack Query  |
| **Auth (frontend)**| NextAuth v5 (Auth.js) — Google provider   |
| **Auth (backend)** | Dual-mode: Google JWT / dev_header        |
| **Styling**        | Tailwind CSS                              |
| **Containerization** | Docker Compose                          |

---

## Project Structure

```
my-curriculum-engine/
├── docker-compose.yml              # PostgreSQL 16 + pgvector (port 5433)
├── README.md
├── AUDIT.md                        # Architecture audit report
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── .env                    # Local env vars (not committed)
│   │   ├── requirements.txt
│   │   ├── alembic.ini
│   │   ├── alembic/                # Database migrations (0001 → 0004)
│   │   ├── storage/                # On-disk file uploads (gitignored)
│   │   └── app/
│   │       ├── main.py             # FastAPI entry point (8 routers)
│   │       ├── core/
│   │       │   ├── config.py       # pydantic-settings (AUTH_MODE, DB, embeddings)
│   │       │   ├── db.py           # Engine, SessionLocal, Base
│   │       │   ├── auth.py         # get_current_user (dual-mode: JWT / header)
│   │       │   ├── security.py     # Google JWKS verification
│   │       │   └── dependencies.py # Embedding provider + vector store DI
│   │       ├── models/             # SQLAlchemy ORM models
│   │       │   ├── curriculum.py   # School, Document, Section, Chunk
│   │       │   ├── ontology.py     # OntologyVersion, Pillar, Skill, Indicator
│   │       │   ├── analysis.py     # AnalysisRun, CandidateMatch, SkillScore
│   │       │   ├── compliance.py   # IntakeComplianceResult
│   │       │   ├── review.py       # Review, ReviewEdit, AuditLog
│   │       │   ├── workspace.py    # User, Workspace, WorkspaceMember
│   │       │   ├── embeddings.py   # ChunkEmbedding, SkillEmbedding
│   │       │   └── enums.py        # ~20 enums
│   │       ├── schemas/            # Pydantic v2 request/response models
│   │       ├── repositories/       # Thin data-access layer (flush, never commit)
│   │       ├── services/           # Business logic (thick orchestrator pattern)
│   │       ├── routers/            # Thin HTTP layer (8 routers)
│   │       ├── adapters/           # Embeddings + vector store adapters
│   │       └── evaluation/         # Evaluation harness (gold datasets)
│   └── web/                        # Next.js 16 frontend
│       ├── app/                    # Pages + API proxy routes
│       │   ├── layout.tsx          # Root layout (AppShell, providers)
│       │   ├── page.tsx            # Dashboard
│       │   ├── login/              # Login page (Google OAuth)
│       │   ├── results/[id]/       # Analysis results page
│       │   ├── compare/            # Side-by-side comparison
│       │   └── api/                # Proxy routes → backend
│       ├── components/             # React components
│       │   ├── AnalyzeForm.tsx     # Upload + analyze form
│       │   ├── WorkspaceGate.tsx   # Workspace onboarding gate
│       │   ├── AppShell.tsx        # Conditional nav layout
│       │   └── ...                 # PillarCards, EvidenceAccordion, etc.
│       ├── features/               # Feature-specific hooks
│       └── lib/                    # api, auth, config, schemas
├── packages/
│   ├── ontology/v1.0/              # pillars.json, skills.json, indicators.json
│   └── shared/                     # (placeholder)
└── docker/                         # (placeholder)
```

---

## Architecture

```
Router (thin)  →  Service (thick)  →  Repository (thin)  →  Database
```

- **Routers** handle HTTP concerns: parse requests, call services, map domain exceptions to HTTP status codes.
- **Services** contain all business logic. Pure services (normalization, scoring, evidence) have zero DB dependencies. The `analyze_service` orchestrator owns the transaction.
- **Repositories** are a thin wrapper over SQLAlchemy — `flush()` but never `commit()` (the orchestrator commits).

### Auth Flow

```
Browser  ──Google OAuth──▶  NextAuth (server-side)
                                  │
                                  ▼
                         Next.js proxy routes
                          (inject X-User-Email)
                                  │
                                  ▼
                        FastAPI  get_current_user()
                         ┌─ google_jwt: verify Google ID token via JWKS
                         └─ dev_header: trust X-User-Email header
```

**Auth modes** (set via `AUTH_MODE` env var):

| Mode | Use Case | How It Works |
|------|----------|--------------|
| `dev_header` (default) | Local development | Trusts `X-User-Email` header |
| `google_jwt` | Production | Verifies Google ID token via JWKS endpoint |

### Workspace Tenancy

Users belong to **workspaces**. Each workspace has an invite code. Documents and analysis runs are scoped to a workspace.

```
User → creates workspace → gets invite code → shares with team
User → joins workspace → can see docs & analyses in that workspace
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET` | `/health` | — | Liveness check |
| `GET` | `/health/db` | — | Readiness check (DB connectivity) |
| `POST` | `/api/v1/analyze` | ✅ | Run full curriculum analysis |
| `GET` | `/api/v1/results/{analysis_run_id}` | ✅ | Retrieve analysis results |
| `POST` | `/api/v1/uploads` | ✅ | Upload a curriculum document |
| `GET` | `/api/v1/documents/{id}` | ✅ | Document metadata (no text) |
| `GET` | `/api/v1/documents/{id}/preview` | ✅ | Truncated text preview |
| `GET` | `/api/v1/documents/{id}/download` | ✅ | Stream original file |
| `POST` | `/api/v1/reviews` | ✅ | Submit a human review |
| `GET` | `/api/v1/reviews/{analysis_run_id}` | ✅ | List reviews for an analysis run |
| `GET` | `/api/v1/analysis-runs` | ✅ | List analysis runs for a workspace |
| `POST` | `/api/v1/workspaces` | ✅ | Create a workspace |
| `POST` | `/api/v1/workspaces/join` | ✅ | Join via invite code |
| `GET` | `/api/v1/workspaces` | ✅ | List user's workspaces |

---

## Getting Started

### Prerequisites

- Python 3.12+ (recommend miniforge / pyenv)
- Node.js 20+
- Docker & Docker Compose

### 1. Start the database

```bash
docker compose up -d
```

This starts PostgreSQL 16 with pgvector on **port 5433** (host) → 5432 (container).

### 2. Set up the backend

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
pip install -r requirements.txt
```

### 3. Configure backend environment

Create `apps/api/.env`:

```env
DATABASE_URL=postgresql://appuser:apppass@localhost:5433/curriculum_engine
APP_ENV=local
AUTH_MODE=dev_header
EMBEDDING_PROVIDER=local
```

For production auth, set:

```env
AUTH_MODE=google_jwt
GOOGLE_CLIENT_ID=<your-google-client-id>
```

### 4. Run database migrations

```bash
cd apps/api
alembic upgrade head
```

### 5. Seed the ontology

```bash
cd apps/api
python -m app.services.seed_ontology_v1
```

Or use the convenience script from repo root:

```bash
./setup_ontology.sh
```

### 6. Start the backend

```bash
cd apps/api
uvicorn app.main:app --reload --port 8000
```

API: **http://localhost:8000** • Docs: **http://localhost:8000/docs**

### 7. Set up the frontend

```bash
cd apps/web
npm install
```

Create `apps/web/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
AUTH_SECRET=<random-32-char-string>
AUTH_GOOGLE_ID=<your-google-client-id>
AUTH_GOOGLE_SECRET=<your-google-client-secret>
```

For local dev without Google OAuth, the backend `dev_header` mode works with any email.

### 8. Start the frontend

```bash
cd apps/web
npm run dev
```

Frontend: **http://localhost:3000**

---

## Analysis Pipeline

```
Document Text / Uploaded File
         │
         ▼
┌─────────────────────────┐
│ 1. Normalize             │  → Split into sections, classify types
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐
│ 2. Intake Compliance     │  → Reject if too short / empty / no substance
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐
│ 3. Chunk                 │  → Break sections into ~1500-char segments
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐
│ 4. Semantic Matching     │  → Embed chunks, cosine-match to skill embeddings
│    (keyword fallback)    │  → If embeddings fail, fall back to keyword matching
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐
│ 5. Score                 │  → Weighted scoring per skill (0–1 scale)
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐
│ 6. Evidence              │  → Extract top-5 supporting snippets per skill
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐
│ 7. Persist & Return      │  → Save all results, return response
└─────────────────────────┘
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `connection refused` on port 5432 | This project uses port **5433**. Check `docker compose ps` and your `.env`. |
| Blank login page | Ensure `WorkspaceGate` / `AppShell` aren't blocking unauthenticated routes. Check browser console. |
| `EMBEDDING_PROVIDER` errors | Default is `local` (sentence-transformers). Set `EMBEDDING_PROVIDER=openai` + `OPENAI_API_KEY` for OpenAI. |
| `No active ontology version found` | Run the seeding script: `python -m app.services.seed_ontology_v1` |
| Google OAuth 401 | Verify `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` in `.env.local` and `GOOGLE_CLIENT_ID` in backend `.env`. Ensure redirect URI matches. |

---

## License

Private — internal use only.
