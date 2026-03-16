# Architecture & Code Quality Audit

> Date: 2025-01-XX  
> Scope: Full repository (`my-curriculum-engine`)

---

## PART A — Inventory & Structure

### A1. Repository Layout

```
my-curriculum-engine/
├── docker-compose.yml              # PostgreSQL 16 (pgvector) — port 5433:5432
├── README.md                       # Project documentation (OUTDATED)
├── IMPLEMENTATION_SUMMARY.md       # Internal notes
├── ONTOLOGY_SEEDING.md             # Seeding guide
├── setup_ontology.sh               # Convenience script
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── .env                    # Local env vars
│   │   ├── alembic.ini
│   │   ├── requirements.txt
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/           # 5 migration files (0001 → 0004)
│   │   ├── app/
│   │   │   ├── main.py             # 8 routers mounted
│   │   │   ├── core/               # config, db, auth, security, dependencies
│   │   │   ├── models/             # 8 model files + enums + mixins
│   │   │   ├── schemas/            # 8 schema files + base
│   │   │   ├── repositories/       # 11 repo files + base (dead)
│   │   │   ├── services/           # 16 service files + __main__.py
│   │   │   ├── routers/            # 8 router files
│   │   │   ├── adapters/           # embeddings + vector_store
│   │   │   └── evaluation/         # eval harness (data/, output/)
│   │   ├── storage/                # On-disk file uploads (gitignored)
│   │   └── tests/
│   └── web/                        # Next.js 16 frontend
│       ├── app/                    # Pages + API proxy routes
│       ├── components/             # 9 UI components
│       ├── features/               # analyze, results, analysisRuns hooks
│       └── lib/                    # api, auth, config, schemas, etc.
├── packages/
│   ├── ontology/v1.0/              # pillars.json, skills.json, indicators.json
│   └── shared/                     # EMPTY — placeholder
└── docker/                         # EMPTY — placeholder
```

### A2. Naming & Convention Inconsistencies

| Issue | Location | Detail |
|-------|----------|--------|
| **Repo class naming** | `document_repo.py` | `DocumentRepository` — every other repo uses `*Repo` (e.g. `CurriculumRepo`, `WorkspaceRepo`). |
| **CamelModel misnomer** | `schemas/base.py` | Named `CamelModel` but **does NOT produce camelCase** — no `alias_generator`. Emits snake_case JSON. |
| **`__init__.py` re-export gap** | `repositories/__init__.py` | Re-exports `WorkspaceRepo` but not `DocumentRepository`. |
| **`__init__.py` re-export gap** | `services/__init__.py` | Empty — no re-exports at all (fine, but inconsistent with repos). |

### A3. Dead / Unused Code

| Item | Location | Status |
|------|----------|--------|
| `BaseRepository[T]` | `repositories/base.py` | **Dead code.** Defined but never imported or subclassed by any concrete repo. Docstring says "every concrete repo inherits" — they don't. |
| `packages/shared/` | Root | Empty directory. |
| `docker/` | Root | Empty directory. |
| `__pycache__/` dirs | Various | Committed to repo — should be gitignored. |

### A4. Duplicate Logic

| Duplication | Files | Detail |
|-------------|-------|--------|
| `create_upload_batch_and_document()` | `CurriculumRepo` + `DocumentRepository` | Two different implementations of the same operation. `CurriculumRepo` version is for inline text (from `analyze_service`); `DocumentRepository` version is for file uploads (from `uploads` router). Signatures differ. Both auto-create schools. Should be consolidated. |
| School auto-creation (POC) | Both repo methods above | Identical "auto-create school if missing" pattern duplicated. |

---

## PART B — Architecture Verification Checklist

### B1. Auth on every router ❌ FAIL

| Router | `get_current_user` dep? | Workspace membership? |
|--------|:-----------------------:|:---------------------:|
| `analyze.py` | ✅ | ✅ |
| `results.py` | ✅ | ✅ |
| `uploads.py` | ✅ | ✅ |
| `documents.py` | ✅ | ✅ |
| `workspaces.py` | ✅ | ✅ |
| `analysis_runs.py` | ✅ | ✅ |
| `health.py` | — (public, correct) | — |
| **`review.py`** | **❌ MISSING** | **❌ MISSING** |

**Finding:** Both `submit_review` and `list_reviews` have zero auth. Any unauthenticated caller can create reviews or read all reviews for any analysis run.

### B2. Privacy — no extracted text leakage ✅ PASS

- Upload response returns only `document_id`, metadata, optional truncated preview.
- `AnalyzeResponse` does not include `raw_text` or `curriculum_text`.
- `ResultResponse` does not include document text.
- `DocumentMeta` returns metadata without text; preview endpoint is truncated.
- No `logger.*(f".*raw_text|extracted_text|curriculum_text")` patterns found.

### B3. Router→Service→Repo layering ✅ PASS (with notes)

- Routers are thin: parse HTTP, delegate, map exceptions.
- `analyze_service.run_analysis()` orchestrates the transaction.
- Repos flush but never commit — orchestrator commits.
- **Minor violation:** `analyze_service.py` imports `HTTPException` from FastAPI (lines 371, 378, 385) — service layer should raise domain exceptions, not HTTP exceptions.

### B4. Schema consistency ⚠️ PARTIAL

- `CamelModel` base: `from_attributes=True`, `populate_by_name=True`, `str_strip_whitespace=True`. This is correct Pydantic v2 config.
- **Issue:** `UploadResponse`, `DocumentMeta`, `DocumentPreview` in `schemas/documents.py` inherit from `BaseModel` directly, not `CamelModel`. Inconsistent with the rest of the codebase.
- **Issue:** `CamelModel` name is misleading — should be renamed or actually implement camelCase.

### B5. Migration integrity ✅ PASS

| Migration | Purpose | Notes |
|-----------|---------|-------|
| `0001` | Enable pgvector | `CREATE EXTENSION IF NOT EXISTS vector` |
| `0001a` | Base tables (27) | Full schema, correct FK relationships |
| `0002` | Embedding tables | `Vector(384)`, correct indexes |
| `0003` | `candidate_matches` add `skill_id` | Backfill + make NOT NULL, skill_indicator_id → nullable |
| `0004` | Workspace tenancy | users, workspaces, workspace_members + FKs |

All migrations are idempotent-safe and properly ordered.

### B6. Frontend proxy security ✅ PASS

- All proxy routes in `apps/web/app/api/` forward to backend with session-based auth.
- `middleware.ts` uses NextAuth to protect all routes except static assets.
- `apiFetch()` in `lib/api.ts` only targets proxy routes (never the backend directly from client).

---

## PART C — Fix Plan (Minimal Diffs)

### P0 — ✅ FIXED: Add auth to review router

**File:** `apps/api/app/routers/review.py`

The review router was the **only** router missing auth. Both endpoints were fully unauthenticated.

**Fix applied:** Added `get_current_user` dependency + `WorkspaceRepo` import to both `submit_review` and `list_reviews`.

### P1 — ✅ FIXED: Service layer importing HTTPException

**File:** `apps/api/app/services/analyze_service.py`

Lines 371–396 contained inline `from fastapi import HTTPException` — service layer should not know about HTTP.

**Fix applied:** Added `DocumentNotFoundError`, `DocumentValidationError`, `WorkspaceAccessError` domain exceptions. Replaced all four `HTTPException` raises with domain exceptions. Updated the service's outer `except` clause to re-raise them cleanly. Updated `routers/analyze.py` to handle the new exceptions with proper HTTP status codes.

### P1 — ✅ FIXED: Document schemas not inheriting CamelModel

**File:** `apps/api/app/schemas/documents.py`

`UploadResponse`, `DocumentMeta`, `DocumentPreview` inherited from bare `BaseModel`. They missed `str_strip_whitespace`, `populate_by_name`, etc.

**Fix applied:** Changed all three to inherit from `CamelModel`. Removed redundant `model_config` dicts.

### P2 — ✅ FIXED: Dead BaseRepository docstring

**File:** `apps/api/app/repositories/base.py`

`BaseRepository[T]` is defined but never used. Docstring falsely claimed "every concrete repo inherits" from it.

**Fix applied:** Updated docstring to accurately state it's unused. Added warning and TODO to delete if it remains unused.

### P2 — ✅ FIXED: CamelModel misnomer

**File:** `apps/api/app/schemas/base.py`

Named `CamelModel` but does NOT produce camelCase JSON.

**Fix applied:** Updated docstring to clarify the misleading name with a TODO note.

### P2 — ✅ FIXED: Rename DocumentRepository → DocumentRepo

**Files:** `repositories/document_repo.py`, `routers/uploads.py`, `routers/documents.py`, `repositories/__init__.py`

**Fix applied:** Renamed class to `DocumentRepo`. Updated all 5 references across routers. Added `DocumentRepo` to `repositories/__init__.py` re-exports.

### P2 — DEFERRED: Consolidate create_upload_batch_and_document

**Files:** `curriculum_repo.py` + `document_repo.py`

Two implementations exist with different signatures (one for inline text, one for file uploads). Consolidation requires careful testing — deferred to a dedicated refactoring PR.

### P2 — DEFERRED: Next.js middleware deprecation

**File:** `apps/web/middleware.ts`

Next.js 16 warns that `middleware` convention is deprecated in favor of `proxy`. Still functional but should be migrated when upgrading.

---

## Summary of Changes Made

| Priority | Issue | Status | Files Changed |
|----------|-------|--------|---------------|
| **P0** | Review router missing auth | ✅ Fixed | `routers/review.py` |
| **P1** | Service-layer HTTPException | ✅ Fixed | `services/analyze_service.py`, `routers/analyze.py` |
| **P1** | Document schemas wrong base | ✅ Fixed | `schemas/documents.py` |
| **P2** | Dead BaseRepository docstring | ✅ Fixed | `repositories/base.py` |
| **P2** | CamelModel misnomer | ✅ Fixed | `schemas/base.py` |
| **P2** | DocumentRepository → DocumentRepo | ✅ Fixed | 4 files |
| **P2** | Duplicate `create_upload_batch_and_document` | Deferred | — |
| **P2** | middleware.ts deprecation | Deferred | — |
| — | README.md rewrite | ✅ Done | `README.md` |
