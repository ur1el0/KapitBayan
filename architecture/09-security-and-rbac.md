# Security, Privacy, and Role-Based Access

Security decisions are enforced by the Django API. Frontend route guards and mobile navigation are usability controls, not substitutes for backend authorization.

## Authentication

The API uses JWT access credentials and server-managed refresh sessions/cookies according to [ADR 002](decisions/002-httponly-jwt-cookie-auth.md) and [ADR 005](decisions/005-session-revocation.md). Logout and account lifecycle operations revoke sessions as defined by their backend contracts. Do not assume every historical token-blacklist description applies to current session handling; consult the auth code and OpenAPI schema.

## Role and tenant controls

- `RESIDENT`: access to the authenticated resident's own profile and service records.
- `ADMIN`: barangay staff operations limited to the assigned barangay. Admins can provision and manage Field Officials using email sign-in, but cannot create or list peer Admin accounts. The first Admin applies using an official email and password, then a DILG reviewer approves and activates that account. Only Residents choose usernames.
- `FIELD_OFFICIAL`: mobile-oriented staff permissions defined per endpoint and limited to the assigned barangay.
- `DILG_ADMIN`: may review, approve, and reject new Barangay onboarding applications only. DILG tokens cannot access resident, service, staff, platform-account-support, or Django admin surfaces.
- Django `is_superuser`: platform account recovery and Django administration, and a controlled fallback for onboarding review; this flag does not create barangay service access.

The platform account-support endpoint is available only to an active Django superuser. It searches minimal directory fields for resident and barangay staff accounts, including legacy unassigned accounts, excludes superusers and retired role values, cannot create/delete accounts or change roles, barangay assignments, credentials, or resident evidence, and supports audited email correction/recovery-link dispatch and account activation state changes. Email corrections and recovery-link dispatch require an operator attestation that contact details were verified through an official channel. Account suspension revokes refresh sessions. See [ADR 021](decisions/021-barangay-only-product-scope-and-platform-recovery.md).

New Barangay applications are the exception for first-tenant provisioning. Applicants provide an official email and choose a password; the server creates a linked, inactive, unassigned Admin account and a pending application. Applicant contact details are visible only to active DILG reviewers and controlled Django superusers. Approval requires an independent verification attestation, blocks ambiguous locality matches and any tenant with an existing Admin, and atomically activates and assigns the same applicant account. Rejection retains the review record and removes only the still-pending applicant account. Older accountless applications retain their setup-email fallback. See [ADR 023](decisions/023-dilg-reviewed-barangay-admin-registration.md).

New first-Admin applications also require control of the official email and one private authority-supporting document. A one-time, expiring email link confirms mailbox access but does not approve the account. DILG reviewers can download the document through an authenticated, non-cacheable endpoint; the API blocks approval until the email is verified and the reviewer attests to reviewing the document and independently verifying the applicant and locality. The document is removed after a review decision through the retryable private-media cleanup queue, while review metadata remains. See [ADR 024](decisions/024-barangay-onboarding-email-and-authority-evidence.md).

Each sensitive list, detail, create, update, deletion, and media operation must enforce its endpoint-specific role and tenant scope. Tenant ownership should come from the authenticated user and persisted record, not an unchecked client-supplied barangay ID. Object absence and authorization responses must follow the endpoint's documented information-disclosure contract.

## Private evidence

Identity documents, billing evidence, and payment proofs are private. Cloud storage uses authenticated assets where configured; local/test sensitive media is blocked from direct public `/media/` retrieval. API media views validate ownership or same-barangay staff authority, reject unauthorized roles, and use private/no-store response headers. Never return public evidence URLs or include proof contents in logs.

## Operational caveats

Scoped DRF API throttles use PostgreSQL-backed, HMAC-keyed request windows shared across workers; they do not store raw IP addresses or user IDs. The additive migration must be applied before deploying the corresponding code. These application limits reduce repeated scoped requests but do not provide volumetric DDoS protection. General-purpose Django cache remains process-local. Background notification work is in-process and best-effort. See [ADR 013](decisions/013-pilot-notification-and-throttle-guardrails.md) and [ADR 016](decisions/016-shared-database-api-throttling.md). Treat production HTTPS, secret provisioning, storage access, and provider delivery as deployment properties that require live verification, not assumptions based on this document.
