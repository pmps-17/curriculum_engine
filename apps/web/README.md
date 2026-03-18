# Curriculum Engine — Web Frontend

Next.js 16 (Turbopack) application providing the UI for the Curriculum
Engine analysis platform.

## Tech Stack

| Layer        | Technology                       |
| ------------ | -------------------------------- |
| Framework    | Next.js 16.1 (App Router)       |
| Auth         | NextAuth (Google OAuth + dev)    |
| Data         | TanStack Query v5                |
| Styling      | Tailwind CSS v4                  |
| Validation   | Zod                              |
| Colors       | `#4F46E5` indigo · `#10B981` green |

## Getting Started

```bash
cd apps/web
npm install
npm run dev          # → http://localhost:3000
```

Requires the FastAPI backend on port 8000
(`cd apps/api && uvicorn app.main:app --reload --port 8000`).

## Page Routes & User Flows

| Route                | Purpose                            | Auth? | Org? |
| -------------------- | ---------------------------------- | ----- | ---- |
| `/login`             | Google sign-in screen              | No    | No   |
| `/`                  | Redirects → `/library`             | Yes   | Yes  |
| `/organizations`     | Org picker — select, create, join  | Yes   | No   |
| `/library`           | Curriculum sets list + Add / Re-run| Yes   | Yes  |
| `/results/[id]`      | Analysis result detail (pillars, skills, evidence) | Yes | Yes |
| `/compare`           | Side-by-side result comparison     | Yes   | Yes  |

### User Flow

```
/login  →  (first visit)  →  /organizations  →  select org  →  /library
                                                                   │
                                    ┌──────────────────────────────┘
                                    ▼
                              Add Curriculum Set  →  /results/[id]
                                    │
                                    ▼
                              Re-run Analysis  →  /results/[id]
                                    │
                                    ▼
                              Compare (select 2+) → /compare
```

### Route Guarding (AppShell)

- **Public routes** (`/login`, `/api/auth/*`) — no shell, no nav.
- **`/organizations`** — TopNav shown, no org required.
- **All other routes** — TopNav shown, org required. If none selected,
  redirect → `/organizations`.

## API Proxy Routes

All client → backend calls go through Next.js route handlers for
auth-header injection. Each maps 1:1 to a FastAPI endpoint.

| Proxy Route                            | Method | Backend Endpoint                            |
| -------------------------------------- | ------ | ------------------------------------------- |
| `/api/organizations`                   | GET    | `GET /api/v1/organizations`                 |
| `/api/organizations`                   | POST   | `POST /api/v1/organizations`                |
| `/api/organizations/join`              | POST   | `POST /api/v1/organizations/join`           |
| `/api/organizations/[id]`              | PATCH  | `PATCH /api/v1/organizations/{id}`          |
| `/api/organizations/[id]/leave`        | POST   | `POST /api/v1/organizations/{id}/leave`     |
| `/api/analyze`                         | POST   | `POST /api/v1/analyze`                      |
| `/api/analysis-runs`                   | GET    | `GET /api/v1/analysis-runs`                 |
| `/api/results/[analysisRunId]`         | GET    | `GET /api/v1/results/{id}`                  |
| `/api/uploads`                         | POST   | `POST /api/v1/uploads`                      |
| `/api/documents/[id]`                  | GET    | `GET /api/v1/documents/{id}`                |
| `/api/documents/[id]/preview`          | GET    | `GET /api/v1/documents/{id}/preview`        |
| `/api/documents/[id]/download`         | GET    | `GET /api/v1/documents/{id}/download`       |
| `/api/backend-health`                  | GET    | `GET /health`                               |
| `/api/auth/[...nextauth]`             | *      | NextAuth (not proxied to backend)           |

## Folder Structure

```
apps/web/
├── app/                    # Next.js App Router pages + API routes
│   ├── page.tsx            # / → redirect to /library
│   ├── layout.tsx          # Root layout (Providers + AppShell)
│   ├── providers.tsx       # NextAuth + TanStack Query providers
│   ├── login/              # /login page
│   ├── organizations/      # /organizations page
│   ├── library/            # /library page
│   ├── results/[id]/       # /results/[id] page
│   ├── compare/            # /compare page
│   └── api/                # Proxy route handlers (see table above)
├── components/             # Shared UI components
│   ├── AppShell.tsx        # Layout shell — route guarding + TopNav
│   ├── TopNav.tsx          # Top navigation bar
│   ├── OrganizationCard.tsx        # Org card (click-to-select, 3-dot menu)
│   ├── CreateOrganizationModal.tsx # Create org modal
│   ├── JoinOrganizationModal.tsx   # Join org via invite code
│   ├── EditOrganizationModal.tsx   # Edit org (PATCH) modal
│   ├── ConfirmDialog.tsx           # Reusable confirm dialog
│   ├── CurriculumSetRow.tsx        # Library row item
│   ├── AddCurriculumSetModal.tsx   # Add curriculum set (upload/paste)
│   ├── PillarCards.tsx     # Pillar score cards (results page)
│   ├── SkillList.tsx       # Skill score list (results page)
│   ├── EvidenceAccordion.tsx       # Evidence snippets accordion
│   ├── CompareSelector.tsx # Select analyses for comparison
│   └── CompareGrid.tsx     # Side-by-side comparison grid
├── features/               # Feature-scoped hooks (TanStack Query)
│   ├── analysisRuns/hooks.ts   # useAnalysisRunsQuery
│   ├── analyze/hooks.ts        # useAnalyzeMutation
│   ├── analyze/uploadHooks.ts  # useUploadMutation
│   └── results/hooks.ts        # useResultsQuery + types
├── lib/                    # Shared utilities
│   ├── api.ts              # apiFetch wrapper + ApiError class
│   ├── auth.ts             # getSessionEmail, getBackendAuthHeaders
│   ├── config.ts           # API_BASE_URL, endpoints, proxyPaths
│   ├── format.ts           # pct(), scoreColor() helpers
│   ├── orgStore.ts         # Centralized org selection (localStorage)
│   ├── queryClient.ts      # TanStack QueryClient singleton
│   ├── recentAnalyses.ts   # localStorage cache for compare page
│   └── schemas.ts          # Zod schemas (AnalyzeRequest)
├── middleware.ts           # NextAuth route protection
└── public/                 # Static assets
```
