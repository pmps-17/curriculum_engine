# Curriculum Engine

> Automated curriculum governance engine — analyzes school curriculum documents against a skills ontology, scores alignment across pillars, and produces evidence-based findings.

---

## High-Level Architecture

```
Users ──▶ Organizations ──▶ Curriculum Sets ──▶ Documents ──▶ Analysis Reports
```

| Concept             | Description                                                       |
|---------------------|-------------------------------------------------------------------|
| **User**            | Authenticated person (Google OAuth or dev header).                |
| **Organization**    | Tenant boundary. Users create or join via invite code.            |
| **Curriculum Set**  | A logical grouping of documents (e.g. "Grade 5 Science").        |
| **Document**        | An uploaded file (PDF, Word, etc.) with extracted text.           |
| **Analysis Report** | Pillar scores, skill scores, evidence snippets, and findings.     |

### Backend Layers

```
Router (thin)  →  Service (thick)  →  Repository (thin)  →  Database
```

- **Routers** parse HTTP, call services, map exceptions to status codes.
- **Services** own business logic and transactions (`commit()`).
- **Repositories** wrap SQLAlchemy — `flush()` only, never `commit()`.

### Auth Flow

```
Browser ─── Google OAuth ───▶ NextAuth (server-side)
                                    │
                              Next.js API proxy routes
                              (inject auth headers)
                                    │
                                    ▼
                           FastAPI get_current_user()
                            ├─ google_jwt: verify ID token via JWKS
                            └─ dev_header: trust X-User-Email header
```

---

## Tech Stack

| Layer             | Technology                                      |
|-------------------|-------------------------------------------------|
| **API**           | FastAPI · Python 3.12+                          |
| **ORM**           | SQLAlchemy 2.0 (`mapped_column`)                |
| **Migrations**    | Alembic (0001 → 0007)                           |
| **Database**      | PostgreSQL 16 + pgvector                        |
| **Embeddings**    | sentence-transformers (local) or OpenAI         |
| **Frontend**      | Next.js 16 · TypeScript · Tailwind CSS          |
| **State**         | TanStack Query (server) · localStorage (org)    |
| **Auth (web)**    | NextAuth v5 (Auth.js) — Google provider         |
| **Auth (API)**    | Dual-mode: `google_jwt` / `dev_header`          |
| **Container**     | Docker Compose (PostgreSQL only)                |

---

## Project Structure

```
my-curriculum-engine/
├── docker-compose.yml              # PostgreSQL 16 + pgvector (port 5433)
├── setup_ontology.sh               # Convenience: seed ontology data
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── .env                    # Local env vars (not committed)
│   │   ├── requirements.txt
│   │   ├── alembic/                # Migrations (0001 → 0007)
│   │   └── app/
│   │       ├── main.py             # Entry point (9 routers)
│   │       ├── core/               # config, db, auth, dependencies
│   │       ├── models/             # SQLAlchemy ORM models
│   │       ├── schemas/            # Pydantic v2 request/response
│   │       ├── repositories/       # Data-access (flush, never commit)
│   │       ├── services/           # Business logic + orchestration
│   │       ├── routers/            # Thin HTTP layer
│   │       └── adapters/           # Embeddings + vector store
│   └── web/                        # Next.js 16 frontend
│       ├── app/
│       │   ├── page.tsx            # Redirects to /library
│       │   ├── login/              # Google OAuth login
│       │   ├── organizations/      # Org management page
│       │   ├── library/            # Curriculum Library (documents + sets)
│       │   ├── library/[setId]/    # Set detail + Upload & Analyze
│       │   ├── analyze/            # Upload & Analyze form
│       │   ├── results/[id]/       # Analysis results page
│       │   ├── compare/            # Side-by-side comparison
│       │   └── api/                # Proxy routes → backend
│       ├── components/             # AnalyzeForm, CurriculumSetCard, etc.
│       ├── features/               # Feature-specific hooks
│       └── lib/                    # api, auth, config, schemas, orgStore
└── packages/
    └── ontology/v1.0/              # pillars.json, skills.json, indicators.json
```

---

## Getting Started

### Prerequisites

- **Python 3.12+** (miniforge, pyenv, or system)
- **Node.js 20+**
- **Docker & Docker Compose**

### 1. Start the database

```bash
docker compose up -d
```

PostgreSQL 16 + pgvector on **host port 5433** → container port 5432.

### 2. Set up the backend

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Or with conda: `conda create -n curriculum-engine python=3.12 && conda activate curriculum-engine && pip install -r requirements.txt`

### 3. Configure backend environment

Create `apps/api/.env`:

```env
DATABASE_URL=postgresql://appuser:apppass@localhost:5433/curriculum_engine
APP_ENV=local
AUTH_MODE=dev_header
EMBEDDING_PROVIDER=local
```

### 4. Run migrations

```bash
cd apps/api
alembic upgrade head
```

### 5. Seed the ontology

```bash
cd apps/api
python -m app.services.seed_ontology_v1
```

This loads `packages/ontology/v1.0/{pillars,skills,indicators}.json` into the database and creates an active ontology version.

### 6. Start the backend

```bash
cd apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- API: **http://localhost:8000**
- Docs: **http://localhost:8000/docs**

> ⚠️ Avoid `--reload` if it picks up the wrong Python. Use the explicit path if needed:
> `/path/to/envs/curriculum-engine/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

### 7. Set up the frontend

```bash
cd apps/web
npm install
```

Create `apps/web/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
AUTH_SECRET=any-random-32-char-string-for-dev
AUTH_GOOGLE_ID=<your-google-client-id>
AUTH_GOOGLE_SECRET=<your-google-client-secret>
```

For **local dev without Google OAuth**, the backend `dev_header` mode trusts any email — Google credentials are only needed for production.

### 8. Start the frontend

```bash
cd apps/web
npm run dev
```

Frontend: **http://localhost:3000**

---

## API Endpoints

### System

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET`  | `/health` | — | Liveness probe |
| `GET`  | `/health/db` | — | Readiness probe (DB) |
| `GET`  | `/health/auth` | — | Auth mode info |

### Organizations

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET`  | `/api/v1/organizations` | ✅ | List user's organizations |
| `POST` | `/api/v1/organizations` | ✅ | Create an organization |
| `POST` | `/api/v1/organizations/join` | ✅ | Join via invite code |
| `PATCH`| `/api/v1/organizations/{id}` | ✅ | Update org name/description |
| `POST` | `/api/v1/organizations/{id}/leave` | ✅ | Leave an organization |

### Curriculum Sets

| Method   | Path | Auth | Description |
|----------|------|:----:|-------------|
| `GET`    | `/api/v1/curriculum-sets?organization_id=` | ✅ | List sets for org |
| `POST`   | `/api/v1/curriculum-sets` | ✅ | Create a set |
| `PATCH`  | `/api/v1/curriculum-sets/{id}` | ✅ | Update title/subject/etc. |
| `DELETE` | `/api/v1/curriculum-sets/{id}` | ✅ | Delete a set |

### Documents & Uploads

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST`   | `/api/v1/uploads` | ✅ | Upload file (multipart, requires `organization_id`) |
| `GET`    | `/api/v1/documents?organization_id=` | ✅ | List documents for org (library) |
| `GET`    | `/api/v1/documents/{id}` | ✅ | Document metadata |
| `PATCH`  | `/api/v1/documents/{id}` | ✅ | Update title/subject/grade_band |
| `DELETE` | `/api/v1/documents/{id}` | ✅ | Soft-delete a document |
| `GET`    | `/api/v1/documents/{id}/preview` | ✅ | Truncated text preview |
| `GET`    | `/api/v1/documents/{id}/download` | ✅ | Stream original file |

### Analysis

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/api/v1/analyze` | ✅ | Run analysis (`document_id` or `curriculum_text`, optional `curriculum_set_id`) |
| `GET`  | `/api/v1/results/{analysis_run_id}` | ✅ | Full analysis results |
| `GET`  | `/api/v1/analysis-runs` | ✅ | List runs for an organization |

### Reviews

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/api/v1/reviews` | ✅ | Submit a human review |
| `GET`  | `/api/v1/reviews/{analysis_run_id}` | ✅ | List reviews for a run |

---

## Key API Flows

### 1. Create / Join an Organization

```bash
# Create
curl -X POST http://localhost:8000/api/v1/organizations \
  -H "X-User-Email: alice@example.com" \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme School District"}'

# Join (using the invite_code from the create response)
curl -X POST http://localhost:8000/api/v1/organizations/join \
  -H "X-User-Email: bob@example.com" \
  -H "Content-Type: application/json" \
  -d '{"invite_code": "ABC123XY"}'
```

### 2. Create a Curriculum Set

```bash
curl -X POST http://localhost:8000/api/v1/curriculum-sets \
  -H "X-User-Email: alice@example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "<org-uuid>",
    "title": "Grade 5 Science",
    "subject": "Science",
    "grade_band": "3-5"
  }'
```

### 3. Upload a File to a Curriculum Set

```bash
curl -X POST http://localhost:8000/api/v1/uploads \
  -H "X-User-Email: alice@example.com" \
  -F "file=@lesson_plan.pdf" \
  -F "title=Unit 3 Lesson Plan" \
  -F "subject=Science" \
  -F "grade_band=3-5" \
  -F "organization_id=<org-uuid>" \
  -F "curriculum_set_id=<set-uuid>"
```

### 4. Analyze (by document or by text)

```bash
# By uploaded document
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "X-User-Email: alice@example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "<document-uuid>",
    "title": "Unit 3 Lesson Plan",
    "subject": "Science",
    "grade_band": "3-5",
    "organization_id": "<org-uuid>",
    "curriculum_set_id": "<set-uuid>"
  }'

# By pasted text
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "X-User-Email: alice@example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "curriculum_text": "Students will explore the water cycle...",
    "title": "Water Cycle Lesson",
    "subject": "Science",
    "grade_band": "3-5",
    "organization_id": "<org-uuid>"
  }'
```

### 5. View Results

```bash
curl http://localhost:8000/api/v1/results/<analysis_run_id> \
  -H "X-User-Email: alice@example.com"
```

Returns pillar scores, skill scores, evidence snippets, findings, and compliance status.

---

## Analysis Pipeline

```
Document Text / Uploaded File
         │
         ▼
  1. Normalize         →  Split into sections, classify types
         │
         ▼
  2. Intake Compliance →  Reject if too short / empty / no substance
         │
         ▼
  3. Chunk             →  Break sections into ~1500-char segments
         │
         ▼
  4. Semantic Match    →  Embed chunks, cosine-match to skill embeddings
     (keyword fallback)    If embeddings unavailable, fall back to keywords
         │
         ▼
  5. Score             →  Weighted scoring per skill (0–1 scale)
         │
         ▼
  6. Evidence          →  Extract top supporting snippets per skill
         │
         ▼
  7. Persist & Return  →  Save all results, return response
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **`invalid_client` (Google OAuth)** | Verify `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET` in `apps/web/.env.local`. Check `GOOGLE_CLIENT_ID` in `apps/api/.env`. Ensure the authorized redirect URI in Google Console matches `http://localhost:3000/api/auth/callback/google`. |
| **DB role / password errors** | The Docker container uses `appuser` / `apppass`. Ensure `DATABASE_URL` in `apps/api/.env` matches: `postgresql://appuser:apppass@localhost:5433/curriculum_engine`. |
| **Port 5432 conflict** | This project maps to host port **5433**, not 5432. Check `docker compose ps`. If another Postgres is on 5433, stop it or change the port in `docker-compose.yml`. |
| **Port 8000 / 3000 already in use** | `lsof -ti :8000 \| xargs kill -9` or `lsof -ti :3000 \| xargs kill -9` to free the port. |
| **`No active ontology version found`** | Ontology not seeded. Run: `cd apps/api && python -m app.services.seed_ontology_v1` |
| **pgvector extension missing** | Migration 0001 creates it. Run `alembic upgrade head`. If permission error: `docker exec -it curriculum_engine_postgres psql -U appuser -d curriculum_engine -c "CREATE EXTENSION IF NOT EXISTS vector;"` |
| **`--reload` picks up wrong Python** | Use the explicit interpreter: `/path/to/envs/curriculum-engine/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| **`EMBEDDING_PROVIDER` errors** | Default is `local` (sentence-transformers). For OpenAI set `EMBEDDING_PROVIDER=openai` and `OPENAI_API_KEY` in `.env`. |
| **Blank page / redirect loops** | Ensure an organization is selected in the UI. The app redirects to `/organizations` if none is selected. |

---

## License

Private — internal use only.
