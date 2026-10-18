# Security, Privacy, and Role-Based Access

Security decisions are enforced by the Django API. Frontend route guards and mobile navigation are usability controls, not substitutes for backend authorization.

## Authentication

The API uses JWT access credentials and server-managed refresh sessions/cookies according to [ADR 002](decisions/002-httponly-jwt-cookie-auth.md) and [ADR 005](decisions/005-session-revocation.md). Logout and account lifecycle operations revoke sessions as defined by their backend contracts. Do not assume every historical token-blacklist description applies to current session handling; consult the auth code and OpenAPI schema.

## Role and tenant controls

- `RESIDENT`: access to the authenticated resident's own profile and service records.
- `ADMIN`: barangay staff operations limited to the assigned barangay.
- `FIELD_OFFICIAL`: mobile-oriented staff permissions defined per endpoint and limited to the assigned barangay.
- `DILG_ADMIN`: explicitly scoped oversight/onboarding and bounded account-recovery functions; not a general tenant bypass.

The DILG account-support endpoint may search minimal account directory fields for residents, field officials, and barangay administrators across tenants, including legacy unassigned accounts. It excludes DILG accounts and superusers, cannot change roles or barangay assignments, and supports only audited email correction/recovery-link dispatch and account activation state changes. Email corrections and recovery-link dispatch require DILG's external contact-verification attestation. See [ADR 020](decisions/020-dilg-account-support-boundary.md).

Each sensitive list, detail, create, update, deletion, and media operation must enforce its endpoint-specific role and tenant scope. Tenant ownership should come from the authenticated user and persisted record, not an unchecked client-supplied barangay ID. Object absence and authorization responses must follow the endpoint's documented information-disclosure contract.

## Private evidence

Identity documents, billing evidence, and payment proofs are private. Cloud storage uses authenticated assets where configured; local/test sensitive media is blocked from direct public `/media/` retrieval. API media views validate ownership or same-barangay staff authority, reject unauthorized roles, and use private/no-store response headers. Never return public evidence URLs or include proof contents in logs.

## Operational caveats

Scoped DRF API throttles use PostgreSQL-backed, HMAC-keyed request windows shared across workers; they do not store raw IP addresses or user IDs. The additive migration must be applied before deploying the corresponding code. These application limits reduce repeated scoped requests but do not provide volumetric DDoS protection. General-purpose Django cache remains process-local. Background notification work is in-process and best-effort. See [ADR 013](decisions/013-pilot-notification-and-throttle-guardrails.md) and [ADR 016](decisions/016-shared-database-api-throttling.md). Treat production HTTPS, secret provisioning, storage access, and provider delivery as deployment properties that require live verification, not assumptions based on this document.
