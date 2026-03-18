# HLD / LLD Alignment Report

> Principal-engineer audit — generated before any new feature work.
> **Rule: no auto-commits.** You commit when ready.

---

## 1 — HLD: Module Map & Data Flow

### 1.1 Module Map

```
┌─────────────────────────────────────────────────────────────────┐
│                         apps/web (Next.js 16)                   │
│  ┌────────┐  ┌──────────┐  ┌───────────┐  ┌─────────────────┐  │
│  │ pages  │→ │components│→ │ features/ │→ │  lib/ (config,  │  │
│  │ (app/) │  │          │  │  hooks.ts  │  │  api, auth, …)  │  │
│  └────────┘  └──────────┘  └─────┬─────┘  └────────┬────────┘  │
│                                  │                  │           │
│                      ┌───────────┴──────────────────┘           │
│                      ▼                                          │
│               app/api/**/route.ts  (11 proxy routes)            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP (Authorization header)
┌──────────────────────────▼──────────────────────────────────────┐
│                        apps/api (FastAPI)                        │
│                                                                  │
│  core/           config · db · auth · security · dependencies    │
│       ↓                                                          │
│  routers/        analyze · analysis_runs · results · review      │
│                  uploads · organizations · documents · health    │
│       ↓                                                          │
│  services/       analyze_service (orchestrator, 13 steps)        │
│                  results_service · review_service                │
│                  upload_service · scoring_service                 │
│                  normalization · chunking · evidence              │
│                  intake_compliance · candidate_matching           │
│                  semantic_candidate_matching                      │
│                  text_extraction · ontology_embedding             │
│       ↓                                                          │
│  repositories/   analysis_run · curriculum · document            │
│                  scoring · candidate · results · review           │
│                  embedding · organization                         │
│       ↓                                                          │
│  models/         analysis · curriculum · ontology                 │
│                  organization · compliance · embeddings · review  │
│       ↓                                                          │
│  adapters/       embeddings (local / openai) · vector_store      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SQLAlchemy
                    ┌──────▼──────┐
                    │ PostgreSQL  │
                    │ + pgvector  │
                    └─────────────┘
```

### 1.2 Primary Data Flows

| Flow | Path |
|------|------|
| **Upload** | `POST /uploads` → `upload_service.process_upload()` → `DocumentRepo.create_upload_batch_and_document()` → disk + DB |
| **Analyze** | `POST /analyze` → `analyze_service.run_analysis()` (13 steps: resolve ontology → resolve document → create run → normalize → chunk → embed → match → score → persist) → response |
| **List runs** | `GET /analysis-runs` → `AnalysisRunRepo.list_for_organization()` → response |
| **View result** | `GET /results/{id}` → `results_service.get_result()` → `ResultsRepo` → response |
| **Review** | `POST /reviews` → `review_service.create_review()` → score overrides + audit log |
| **Compare** | Client-side: parallel `GET /results/{id}` calls → `CompareGrid` |
| **Org CRUD** | `POST/GET /organizations` → `OrganizationRepo` → response |

---

## 2 — LLD Rules Enforced

### 2.1 Singleton / One Source of Truth

| Singleton | Location | Pattern | Status |
|-----------|----------|---------|--------|
| App settings | `core/config.py` | `@lru_cache(maxsize=1)` on `get_settings()` | ✅ Correct |
| DB engine | `core/db.py` | Module-level `engine = _build_engine()` | ✅ Correct (single process) |
| Session factory | `core/db.py` | Module-level `SessionLocal` | ✅ Correct |
| Embedding provider | `core/dependencies.py` | `@lru_cache` on `get_embedding_provider()` | ✅ Correct |
| Vector store | `core/dependencies.py` | Per-request (needs DB session) | ✅ Correct |
| JWKS client | `core/security.py` | Module-level `_get_jwks_client()` with TTL | ✅ Correct |
| QueryClient (FE) | `lib/queryClient.ts` | Browser singleton / server fresh | ✅ Correct |

### 2.2 Thin Routers / Thick Services

| Router | Thin? | Violations |
|--------|-------|------------|
| `analyze.py` | ✅ | — |
| `analysis_runs.py` | ✅ | — |
| `results.py` | ⚠️ **NO** | Inline `from app.models.analysis import AnalysisRun` + direct `db.get(AnalysisRun, ...)` for org isolation check |
| `review.py` | ✅ | — |
| `uploads.py` | ⚠️ **NO** | Inline `import uuid`, direct `DocumentRepo` instantiation, `db.commit()` in router body, manual UUID parsing |
| `organizations.py` | ✅ | `db.commit()` in router is acceptable for simple CRUD |
| `documents.py` | ✅ | Helper functions are local to router (acceptable) |
| `health.py` | ✅ | — |

**Action items:**
1. **`results.py`** — Move org-isolation check into `results_service.get_result()` (pass `current_user` / `user_id` as param). The router should never import a model or call `db.get()` directly.
2. **`uploads.py`** — Extract the entire body (org check → file read → process → persist → response) into `upload_service`. Router should only call one service function and return.

### 2.3 Repository Boundary — No Direct DB in Routers

| File | Direct DB access? | Issue |
|------|-------------------|-------|
| `routers/results.py` | `db.get(AnalysisRun, ...)` | ❌ Must go through repo |
| `routers/uploads.py` | `DocumentRepo(db)` + `db.commit()` | ❌ Should be in service |
| `routers/organizations.py` | `OrganizationRepo(db)` + `db.commit()` | ⚠️ Acceptable for thin CRUD (no business logic) |

### 2.4 No Logging Raw Text

Verified: **No violations found.** All loggers use structured identifiers (UUIDs, filenames, counts), never raw curriculum text.

### 2.5 Consistent Naming: "organization" Everywhere

| Layer | Status | Notes |
|-------|--------|-------|
| DB tables | ✅ | Alembic migration `0005` renamed `workspaces` → `organizations` |
| Models | ✅ | `models/organization.py` (User, Organization, OrganizationMember) |
| Schemas | ✅ | `schemas/organizations.py` |
| Routers | ✅ | `routers/organizations.py` |
| Repositories | ✅ | `repositories/organization_repo.py` |
| Frontend | ✅ | All "organization" wording |
| **Stale files** | ✅ | `workspace.py`, `workspaces.py`, `workspace_repo.py` already deleted from disk (only stale `.pyc` in grep cache) |

### 2.6 DI (Dependency Injection)

All routers use `Depends(get_db)`, `Depends(get_current_user)`, `Depends(get_embedding_provider)` correctly. No manual session construction.

---

## 3 — Dead Code Report

### 3.1 Safe to Delete — Backend

| File / Symbol | Evidence | Risk |
|---------------|----------|------|
| **`repositories/base.py`** (entire file) | Self-documented: "Not currently used. Delete this file if it remains unused." No imports of `BaseRepository` anywhere in app code. | **None** — delete |
| **`_merge_candidates()`** in `analyze_service.py` (lines 143–170) | Comment: "kept for potential future use, but currently the pipeline is semantic-first with keyword-only fallback — no merging needed." Never called. | **None** — delete (re-add from git if needed) |
| **`if __name__ == "__main__"` block** in `analyze_service.py` (lines ~635–659) | Smoke test block. Not runnable as a module entry point in production. | **Low** — delete (tests should live in `tests/`) |

### 3.2 Safe to Delete — Frontend

| File / Symbol | Evidence | Risk |
|---------------|----------|------|
| **`components/AnalyzeForm.tsx`** (546 lines) | `app/page.tsx` was refactored to redirect to `/library`. **No file imports `AnalyzeForm` anymore** (grep confirms: zero import statements in `.tsx` source files). The `.next` build cache still references it but that's stale. | **None** — delete |
| **`components/UserNav.tsx`** | **Never imported** by any source file. `OrganizationHeader` and `TopNav` provide all user/logout UI. | **None** — delete |
| **`components/OrganizationHeader.tsx`** | **Never imported** by any page or component. `TopNav` already renders the org pill + email + logout. This is a duplicate, standalone component. | **None** — delete |

### 3.3 Refactor — Not Delete

| Item | Issue | Action |
|------|-------|--------|
| **`lib/recentAnalyses.ts`** | Comment says "replace with fetch when backend endpoint available." Backend endpoint `GET /api/v1/analysis-runs` now exists and Library page uses it. BUT `CompareSelector.tsx` and `CompareGrid.tsx` import `RecentAnalysis` type from it, and `AddCurriculumSetModal.tsx` calls `saveRecentAnalysis()`. | **Refactor later**: Compare page already uses backend data. `saveRecentAnalysis` in AddCurriculumSetModal could be removed once Library is the only entry point. Keep for now — mark with TODO. |
| **`schemas/base.py` → `CamelModel` name** | Misleading: no camelCase aliasing. Has TODO in docstring. | **Rename to `AppModel`** across all schema files. Single find-replace, zero behavior change. |
| **`repositories/document_repo.py` ↔ `curriculum_repo.py` overlap** | Both have `create_upload_batch_and_document()`. `document_repo` version is used by uploads router; `curriculum_repo` version is used by analyze_service for inline text. | **Keep both for now** — they serve different input shapes (file upload vs inline text). Add clarifying docstrings. |

### 3.4 Summary Counts

| Category | Items | Lines recovered |
|----------|-------|----------------|
| Backend dead code | 3 items (file + 2 blocks) | ~160 lines |
| Frontend dead code | 3 files | ~900 lines |
| Refactor items | 3 items | 0 lines removed (naming/docs) |

---

## 4 — Pre-Implementation Checklist

Before any new feature work, these safe deletions and fixes should land:

- [ ] Delete `apps/api/app/repositories/base.py`
- [ ] Delete `_merge_candidates()` function in `analyze_service.py` (lines 136–170)
- [ ] Delete `if __name__ == "__main__"` smoke test in `analyze_service.py` (lines ~605–659)
- [ ] Delete `apps/web/components/AnalyzeForm.tsx`
- [ ] Delete `apps/web/components/UserNav.tsx`
- [ ] Delete `apps/web/components/OrganizationHeader.tsx`
- [ ] Rename `CamelModel` → `AppModel` across all schema files
- [ ] Move org-isolation check from `routers/results.py` into `results_service`
- [ ] Move upload orchestration from `routers/uploads.py` into `upload_service`
- [ ] Verify build (backend + frontend) after each batch of changes

---

*Report complete. Ready for your go-ahead to execute the deletions and fixes.*
