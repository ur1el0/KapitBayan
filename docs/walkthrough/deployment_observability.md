# Local Deployment and Observability

This walkthrough covers the checked-in Docker Compose setup and health probes. It is not a production deployment guide or evidence that a hosted service is active.

## Local Compose services

The Compose file defines PostgreSQL, a one-shot migration service, the Django development server, and the Nginx-served web build. It binds PostgreSQL to localhost for local use. Copy the example environment files, use local-only credentials, and keep `.env` files untracked before starting:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
docker compose up --build
```

Compose waits for the database health check, applies migrations once, then starts the backend. Do not use the development-server Compose topology as production configuration.

When Django runs directly on the host, the Compose hostname `db` is unavailable. Start only PostgreSQL with `docker compose up -d db`, then configure `backend/.env` with a local-only `DATABASE_URL` using host `127.0.0.1`, port `5433`, database `gridy_db`, and user `gridy_user`. Keep its password aligned with `POSTGRES_PASSWORD` in the root `.env`. Never point host development at Neon or another production database.

## Health probes

- `GET /api/v1/health/live/` reports whether the Django process can serve a request; it is not a database check.
- `GET /api/v1/health/ready/` checks configured dependencies and can return HTTP 503 when they are unavailable.
- `GET /api/v1/health/` is a compatibility readiness route used by the current backend container health check.

Use the current `config.health_views` implementation for exact response fields and dependency semantics. Do not treat an HTTP health response as proof that user journeys, the configured email backend, Firebase, Cloudinary, or provider APIs work.

## Migration release gate

Compose uses a one-shot migration service and blocks backend startup if it fails. On another platform, migrations should run exactly once as a serialized pre-release step. Do not run migrations in image builds or concurrently in every application replica. Test both old and new application compatibility for schema changes according to [ADR 014](../../architecture/decisions/014-safe-schema-rollout-compatibility.md).

## Hosted environment status

Verify provider dashboards, deployed commit, secrets, domains, and live health before claiming production or preview status. The checked-in Vercel rewrite points to `gridy.onrender.com`, while the backend environment example uses `gridy-backend.onrender.com`; align and verify these values before release. Azure remains a separately gated proposal. The deployed email configuration uses Brevo SMTP; a health endpoint does not verify SMTP credentials or message delivery. For a controlled delivery check, request a password reset for a test account you own, then compare the Render application logs with Brevo's transactional email logs. See [Brevo email setup](brevo-email-setup.md) and [Deployment and CI/CD](../../architecture/11-deployment-and-ci-cd.md).

## Delivery and throttling caveats

Push/email work is in-process and best-effort; there is no persistent queue or retry. Scoped API throttle windows are stored in PostgreSQL and shared across workers, while Django's general-purpose `LocMemCache` remains process-local. Apply the throttle migration before deploying the code; PostgreSQL concurrency tests are needed because SQLite cannot verify row-lock behavior. These limits are not a volumetric DDoS defense. See [ADR 013](../../architecture/decisions/013-pilot-notification-and-throttle-guardrails.md) and [ADR 016](../../architecture/decisions/016-shared-database-api-throttling.md).

The password-reset endpoint deliberately uses a generic success response. A matching account does not prove that a message was sent; delivery depends on an unambiguous account match, throttling, background dispatch, and the email provider. Check provider logs before retrying repeatedly.
