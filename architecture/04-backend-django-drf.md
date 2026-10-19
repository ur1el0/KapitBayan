# Backend Architecture (Django REST Framework)

The API is a Django project in `backend/config/` with feature apps under `backend/gridy_*/`. The `gridy_*` package names are intentionally retained because Django app labels, migration dependencies, and database objects depend on them.

## Application areas

- `gridy_auth`: users, residents, barangays, registration, verification, sessions, and onboarding.
- `gridy_services`: document requests, manual payment workflows, queues, assistance, and service analytics.
- `gridy_communications`: announcements, schedules, FAQs, hotlines, and notifications.
- `gridy_reports`: resident-submitted issue reports and staff triage.
- `gridy_audit`: durable records for selected administrative actions.

The exact models, serializers, permissions, and URL configuration in each app are the implementation source of truth. Exact public request and response schemas are generated through drf-spectacular; see [API contracts](06-api-endpoint-contracts.md).

## Tenant and authorization boundary

Authenticated user identity and the user's assigned `barangay_id` determine tenant scope. Views and querysets must enforce both role and barangay rules. A web/mobile route or hidden UI control does not grant server access. Barangay Operator credentials are restricted to onboarding review, bounded account support, and their own session endpoints; they cannot access analytics or barangay service records. Account support is separately permissioned, audited, and throttled. Django superusers retain a separate recovery path and do not receive barangay service access through that role alone.

## Storage boundary

The default storage backend is configured from environment. In the private Cloudinary configuration, identity, billing, and payment-proof assets use authenticated storage and are streamed through permission-checked API views. In local development, protected media routes deny direct access to sensitive media directories. Never document or expose public URLs for protected evidence. Issue-report media has a separate policy; check the relevant model and storage configuration before describing its visibility.

## Background work, throttling, and dependencies

This implementation does not add Celery or Redis. Selected notification and email work uses in-process daemon threads, which are best-effort: a process exit can interrupt work and there is no persistent retry queue. Scoped API throttles use the PostgreSQL `APIRateLimitWindow` table with per-bucket row locking and HMAC-derived keys, so counters are shared across workers without storing raw client identifiers. The additive migration must be applied before deploying this code; PostgreSQL tests are required to verify concurrency because SQLite does not provide the needed row-lock behavior. These controls are not a volumetric DDoS defense. See [ADR 009](decisions/009-simplification-to-defended-proposal-architecture.md), [ADR 013](decisions/013-pilot-notification-and-throttle-guardrails.md), and [ADR 016](decisions/016-shared-database-api-throttling.md).
