## Render Backend

Create a Native Python web service with root directory `job_portal_backend`.

| Render field | Value |
| --- | --- |
| Build Command | `sh deploy/render/build.sh` |
| Pre-Deploy Command | `python manage.py migrate --noinput` |
| Start Command | `sh deploy/render/start.sh` |
| Health Check Path | `/api/health/` |
| Settings | `DJANGO_SETTINGS_MODULE=config.settings.production` |

Use Render's internal PostgreSQL connection URL as `DATABASE_URL`. Ensure the database supports pgvector; the existing migration executes `CREATE EXTENSION IF NOT EXISTS vector`. If the Render database role cannot create extensions, enable `vector` from the provider dashboard before the pre-deploy migration.

Do not run migrations from Gunicorn startup or from every worker. A failed database probe returns HTTP `503`, so Render does not mark an instance healthy while its database is unavailable.

### Required Backend Variables

Use `job_portal_backend/.env.production.example` as the source-of-truth checklist. Required groups are:

| Group | Variables |
| --- | --- |
| Django/routes | `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `BACKEND_PUBLIC_URL` |
| Database | `DATABASE_URL`, or all five `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` |
| Redis | `REDIS_URL` using `rediss://` |
| QStash | `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`; `QSTASH_DEV=false` |
| R2 | `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, and either `R2_ENDPOINT_URL` or `R2_ACCOUNT_ID` |
| Gemini | `GEMINI_API_KEY`, `GEMINI_PARSER_MODEL`, `GEMINI_EMBEDDING_MODEL` |
| Google | `GOOGLE_CLIENT_ID` |
| SMTP | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, plus TLS/SSL flags |

Set `ALLOWED_HOSTS` to hostnames without schemes or paths. CORS and CSRF entries must be full HTTPS origins. Keep R2 buckets private; application responses use short-lived signed URLs.

Begin with `ENABLE_HTTPS_REDIRECT=false` and `ENABLE_HSTS=false`. After Render HTTPS and custom domains are confirmed, enable the redirect, verify it, then enable HSTS. HSTS is intentionally gated because an incorrect value can lock browsers into a broken HTTPS configuration.

## Vercel Frontend

Create a Vercel project with root directory `job_portal_frontend`. Use the repository's standard Next.js build command.

Set these variables for Production and the corresponding Preview values when previews should call a separate backend:

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Public Render API origin, for browser requests |
| `API_URL` | Public Render API origin, for server-side requests |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | The same Google OAuth client ID allowed by the backend |

`NEXT_PUBLIC_*` values are embedded at build time. Redeploy the frontend after changing them. Add every deployed Vercel/custom origin to Django CORS and CSRF configuration.

## One-Time Render Demo Seed

For a disposable demo database, add these Render variables before one backend deploy:

```text
RUN_RENDER_SEED=true
SEED_ADMIN_EMAIL=admin.demo@jobportal.local
SEED_ADMIN_PASSWORD=<strong unique password>
SEED_EMPLOYER_EMAIL=employer.demo@jobportal.local
SEED_EMPLOYER_PASSWORD=<strong unique password>
SEED_CANDIDATE_PASSWORD=<shared strong demo-candidate password>
```

The build runs `seed_render_demo` after migrations and creates or updates the skill taxonomy, 50 active jobs under one approved company, 10 complete candidate profiles, one employer, and one admin. It does not enqueue embeddings during the build and does not print passwords.

After the first successful deploy, immediately remove `RUN_RENDER_SEED` or set it to `false`. The command is idempotent and will not duplicate its records, but leaving the flag enabled resets demo passwords and rewrites the seeded records on every deploy. Do not use these demo accounts for real production data.

## QStash Production

The callback is `POST <BACKEND_PUBLIC_URL>/api/internal/tasks/`. It verifies `Upstash-Signature` before dispatch. Invalid permanent payloads return QStash's non-retry status `489`; task exceptions return `500` for retry.

After each production deployment, run `python manage.py setup_qstash_schedules` once from a Render shell or one-off job. Fixed schedule IDs prevent duplicates. Do not use QStash Dev credentials in production.

Task publication occurs after database commit. Resume and JD parser tasks atomically claim records and cap Gemini attempts. Successful or consumed imports ignore duplicate delivery.

## Verification

Run before release:

```text
python manage.py check --settings=config.settings.test
python manage.py makemigrations --check --dry-run --settings=config.settings.test
python manage.py test --settings=config.settings.test
python manage.py check --deploy --settings=config.settings.production
npm run lint
npm run typecheck
npm run build
```

The production check needs placeholder syntactically valid environment variables even when run locally. It does not need to connect to cloud services.

Verify after deployment:

1. `GET /api/health/` returns `200`, `status=ok`, and `database=ok`.
2. Upload a small test CV/JD and confirm QStash logs one successful callback and a completed parse.
3. Upload/download a disposable private file and confirm the signed R2 URL expires.
4. Run `python manage.py send_test_email --to verified-recipient@example.com`; the command never prints SMTP credentials.
5. Complete Google sign-in using every intended Vercel domain.
