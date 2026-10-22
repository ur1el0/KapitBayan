# Security, Privacy, and Role-Based Access

Security decisions are enforced by the Django API. Frontend route guards and mobile navigation are usability controls, not substitutes for backend authorization.

## Authentication

The API uses JWT access credentials and server-managed refresh sessions/cookies according to [ADR 002](decisions/002-httponly-jwt-cookie-auth.md) and [ADR 005](decisions/005-session-revocation.md). Logout and account lifecycle operations revoke sessions as defined by their backend contracts. Do not assume every historical token-blacklist description applies to current session handling; consult the auth code and OpenAPI schema.

Passwords are case-sensitive. They must be at least eight characters and must not be a commonly used password or too similar to the user's account attributes. Uppercase letters, symbols, and digit classes are optional; the server does not impose character-composition requirements.

## Role and tenant controls

- `RESIDENT`: access to the authenticated resident's own profile and service records.
- `ADMIN`: barangay staff operations limited to the assigned barangay. Admins can provision and manage Field Officials using email sign-in, but cannot create or list peer Admin accounts. The first Admin applies using an official email and password, then a Barangay Operator approves and activates that account. Only Residents choose usernames.
- `FIELD_OFFICIAL`: mobile-oriented staff permissions defined per endpoint and limited to the assigned barangay.
- `BARANGAY_OPERATOR`: may review, approve, and reject new Barangay onboarding applications; permanently erase an application and its eligible linked Admin account with a reason and exact application-reference confirmation; and perform bounded, audited account support for `RESIDENT`, `FIELD_OFFICIAL`, and `ADMIN` accounts. The account directory exposes only minimal account identifiers/contact, name, role, active state, and Barangay fields; it does not expose full resident profiles or identity evidence. Operators cannot create accounts, alter passwords/roles/Barangay assignments, manage superusers or other operators, access analytics, or view tenant service records. The last active Barangay Admin is protected. Operators are web-only and have no mobile route.
- Django `is_superuser`: platform account recovery and Django administration, and a controlled fallback for onboarding review; this flag does not create barangay service access.

The bounded account-support endpoint is available to active Barangay Operators and active Django superusers. It searches minimal directory fields for resident and barangay staff accounts, including legacy unassigned accounts, excludes superusers and retired role values, cannot create accounts or change roles, Barangay assignments, credentials, or resident evidence, and supports audited email correction/recovery-link dispatch, account activation state changes, and guarded permanent erasure. Email corrections and recovery-link dispatch require an operator attestation that contact details were verified through an official channel. Account suspension revokes refresh sessions. See [ADR 025](decisions/025-barangay-operator-onboarding-and-account-support.md).

New Barangay applications are the exception for first-tenant provisioning. Applicants provide an official email and choose a password; the server creates a linked, inactive, unassigned Admin account and a pending application. Applicant contact details are visible only to active Barangay Operators and controlled Django superusers. Approval requires an independent verification attestation, blocks ambiguous locality matches and any tenant with an existing Admin, and atomically activates and assigns the same applicant account. Rejection retains the review record and removes only the still-pending applicant account. An operator may later erase an application in any status with a reason and exact application-reference confirmation; any eligible linked Admin account is erased through the guarded account lifecycle, while the Barangay and audit/history records remain. Older accountless applications retain their setup-email fallback. See [ADR 025](decisions/025-barangay-operator-onboarding-and-account-support.md).

New first-Admin applications also require control of the official email and one private authority-supporting document. A one-time, expiring email link confirms mailbox access but does not approve the account. Barangay Operators can download the document through an authenticated, non-cacheable endpoint; the API blocks approval until the email is verified and the reviewer attests to reviewing the document and independently verifying the applicant and locality. The document is removed after a review decision through the retryable private-media cleanup queue, while review metadata remains. See [ADR 024](decisions/024-barangay-onboarding-email-and-authority-evidence.md) and [ADR 025](decisions/025-barangay-operator-onboarding-and-account-support.md).

Each sensitive list, detail, create, update, deletion, and media operation must enforce its endpoint-specific role and tenant scope. Tenant ownership should come from the authenticated user and persisted record, not an unchecked client-supplied barangay ID. Object absence and authorization responses must follow the endpoint's documented information-disclosure contract.

## Private evidence

Identity documents, billing evidence, and payment proofs are private. Cloud storage uses authenticated assets where configured; local/test sensitive media is blocked from direct public `/media/` retrieval. API media views validate ownership or same-barangay staff authority, reject unauthorized roles, and use private/no-store response headers. Never return public evidence URLs or include proof contents in logs.

## Operational caveats

Scoped DRF API throttles use PostgreSQL-backed, HMAC-keyed request windows shared across workers; they do not store raw IP addresses or user IDs. The additive migration must be applied before deploying the corresponding code. These application limits reduce repeated scoped requests but do not provide volumetric DDoS protection. General-purpose Django cache remains process-local. Background notification work is in-process and best-effort. See [ADR 013](decisions/013-pilot-notification-and-throttle-guardrails.md) and [ADR 016](decisions/016-shared-database-api-throttling.md). Treat production HTTPS, secret provisioning, storage access, and provider delivery as deployment properties that require live verification, not assumptions based on this document.
