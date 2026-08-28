# AGENTS.md

Monorepo with two independent apps (no shared tooling): `job_portal_backend/` (Django 5 + DRF + pgvector + Django-Q) and `job_portal_frontend/` (Next.js 16 App Router + Tailwind v4 + shadcn/ui). Docs are in Vietnamese; `README.md` (root) is the authoritative architecture doc and `run.md` has the exact PowerShell startup sequence.

## Running locally (Windows PowerShell)

1. Infra first (Postgres 16+pgvector on :5432, Redis on :6379):
   `docker compose up -d --wait` (compose ở root repo)
2. Backend venv lives at `job_portal_backend\.venv` (Windows). Always invoke via full path, never `cd` + `source`:
   - `job_portal_backend\.venv\Scripts\python job_portal_backend\manage.py runserver 0.0.0.0:8000`
   - Django-Q worker (needed for embeddings/import cleanup): `... manage.py qcluster`
   - First setup: `migrate` then `seed_demo`. Reset: `docker compose ... down -v --remove-orphans` then re-up + migrate + seed.
3. Frontend: `npm run dev --prefix job_portal_frontend -- --hostname 0.0.0.0 --port 3000`

Backend env comes from `job_portal_backend/.env` (`DJANGO_SETTINGS_MODULE=config.settings.local`); settings split as `config/settings/{base,local,test,staging,production}.py`. Frontend env from `job_portal_frontend/.env.local` (`NEXT_PUBLIC_API_URL`).

Demo accounts: `admin@gmail.com/admin123`, `employer@gmail.com/employer123`, `candidate@gmail.com/candidate123`. Swagger: `http://localhost:8000/api/docs/`, OpenAPI schema: `http://localhost:8000/api/schema/`.

## Backend

- App convention (hard rule, see README): `models → serializers → perms → selectors → services → views → urls`. Business logic lives in `services.py`, read queries in `selectors.py`, views stay thin. Read/Write serializers are split (`JobReadSerializer` / `JobWriteSerializer`).
- Use mixin-based ViewSets (`List/Retrieve/Create/Update`) not `ModelViewSet` unless the UC needs destroy. Extra API = violation of Project Charter.
- Imports are `from apps.<app>.models import ...`, never `from apps.courses...`.
- `apps/courses/` is reference code copied from an old course, NOT in `INSTALLED_APPS`, and imports nonexistent packages — never add it to `INSTALLED_APPS`.
- Tests are Django `TestCase`/`APITestCase` in `apps/<app>/tests/` — **not pytest** despite the README mentioning it (no pytest installed/config). Run with the Django test runner:
  - all: `job_portal_backend\.venv\Scripts\python job_portal_backend\manage.py test`
  - one app/class/test: `... manage.py test apps.jobs.tests.test_services.JobServiceTests.test_apply_...`
  - `manage.py` auto-clears `GEMINI_API_KEY` for the `test` command (missing mocks fail fast, never hit real Gemini).
  - Needs the Postgres docker container up. For sync Django-Q + locmem email: `--settings=config.settings.test`.
- Migrations of `candidates`/`jobs` depend on `core.0001_enable_pgvector` (the `vector` extension must exist first).
- State machine is one-way and non-reversible (Charter): `applied → shortlisted/rejected → interviewed/rejected → hired/rejected`. Jobs: `ACTIVE` → embedding, `DRAFT` → none; company must be `APPROVED` to post. `match_score` = cosine similarity of embeddings × 100; null while embedding missing, recomputed async via Django-Q.

## Frontend

- Next.js 16 is NOT the Next.js you know — read the auto-generated `job_portal_frontend/AGENTS.md` (re-added by `next dev`, don't fight it) and the bundled guides under `job_portal_frontend/node_modules/next/dist/docs/` before writing code. Notable: middleware was renamed to Proxy (`src/proxy.ts`).
- `src/app/` is routing/layout only; logic lives in `src/features/<app>/` (`api.ts`, `types.ts`, `hooks.ts`, `components/`).
- API types are generated, never hand-written: `npm run api:types --prefix job_portal_frontend` requires the backend running on :8000 and writes `src/types/generated/api-schema.ts`.
- Routing rules (see frontend README): public pages are NOT duplicated inside guarded route groups. Guards are role-based in the route-group `layout.tsx` via `RequireRole` (`(candidate)`, `(employer)`, `(admin)`); `/jobs` and `/jobs/[jobId]` stay public at top level; action-level auth (e.g. Apply button → `/login?redirect_to=...`) instead of route-level. Bearer tokens remain in `localStorage` for direct API calls and are mirrored to `jp_access`/`jp_refresh` cookies for `src/proxy.ts`; Proxy validates the access token and authoritative role through backend `/api/accounts/me/`, refreshing once through `/api/auth/token/refresh/` when needed.
- There are stale/empty dirs left in `src/app` (e.g. `src/app/auth/`, `(site)/jobs`, `(employer)/recruiter`) — ignore them; trust the `*.tsx` files that exist.
- Lint: `npm run lint --prefix job_portal_frontend` (eslint). No test runner configured for the frontend.

## Project Charter constraints (non-negotiable)

- API minimalism — only endpoints a UC requires; no "might need later" endpoints.
- AI only analyzes/ranks; never auto-hires/rejects. CV uploads must be encrypted.
- No reverse status transitions; closed jobs still allow updating existing applications, just no new ones.
- Applying requires a complete profile **including CV**; no duplicate applications.
- Out of scope: video interviews, online payments, native mobile, social network features, HRM/ERP integration.
