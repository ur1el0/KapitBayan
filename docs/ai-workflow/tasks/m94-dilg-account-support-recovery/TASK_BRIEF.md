# M94: DILG Account Support and Recovery

## Metadata
- **Task ID:** m94-dilg-account-support-recovery
- **Task Type:** Feature
- **Target components:** Django REST Framework API and React DILG administration
- **Lead / writer:** Codex
- **Reviewer:** Pending
- **Base:** GitHub `main` at `46d5af8` (Resident Tutorial merge). The branch is rebased on this commit and preserves its web tutorial route.

## Objective
Give DILG administrators a narrowly scoped, audited way to find resident, field-official, and barangay-admin accounts (including legacy unassigned accounts), correct an account email after independently verifying the new contact, issue a private password setup/reset link, and deactivate or reactivate an account when support requires it.

## Non-goals
- This is not unrestricted CRUD. It does not create accounts, delete accounts, change usernames, roles, barangay assignments, staff/superuser flags, or passwords.
- It does not let DILG alter another DILG account or any Django superuser.
- It does not expose passwords, reset tokens, identity evidence, resident profile evidence, or refresh-token details.
- It does not change the barangay-admin resident/field-official workflows or public password-reset behavior.
- No production data changes, deployment, new infrastructure, or dependency additions.

## Current behavior and evidence
- DILG navigation currently exposes onboarding applications and analytics only; `frontend/src/App.tsx` has no account-support route.
- The approved-barangay onboarding flow creates the first barangay `ADMIN` with an unusable password and emails password setup instructions to the submitted address. There is no DILG correction/resend screen for an address that was mistyped or cannot receive email.
- Residents and field officials have tenant-admin lifecycle paths, but they do not provide DILG with cross-barangay recovery support.
- The existing password-reset flow creates a one-time Django token link and dispatches email through the repository's daemon-thread `@async_task` helper.
- `RefreshSession` rows are stored and already revoked by account lifecycle workflows.

## Required rules
- **RBAC / ADR 008 and ADR 011:** Only authenticated `DILG_ADMIN` may call the support endpoints. DILG must independently verify a corrected email/contact through an external official channel; the API must require the verification attestation and a reason.
- **Tenant/data integrity / ADR 004:** The support queryset may span barangays only because the actor is DILG. Every result is limited to roles `RESIDENT`, `FIELD_OFFICIAL`, or `ADMIN`; legacy accounts without a barangay may be shown as unassigned. Exclude DILG accounts and all superusers. No operation can change role or barangay.
- **Session security / ADR 005:** Email correction revokes existing refresh sessions. Deactivation revokes all active refresh sessions; reactivation does not restore them.
- **Auditability:** Email correction, link dispatch, deactivation, and reactivation each create a `USER_ACTION` audit record with actor, target account ID, target role/barangay ID, action, and a controlled reason code. Never record free-form user text, the corrected email, or reset link/token in the audit description or application logs.
- **No hard deletion:** Existing application, resident, document, treasury, and audit history remains intact.
- **Abuse controls:** Use the shared database-backed scoped throttle; enforce bounded search and reason lengths.

## Acceptance criteria
1. **AC-1:** DILG can search a paginated, minimal account directory across barangays, including legacy unassigned accounts. Search supports account email/username and account display name; results include role, active state, and barangay identity (or an explicit unassigned state) but no passwords, tokens, or evidence fields.
2. **AC-2:** Non-DILG users receive 403 for every support endpoint. DILG cannot retrieve or mutate DILG-admin or superuser accounts; unknown/ineligible IDs return 404.
3. **AC-3:** Email correction requires a valid, unique email, a controlled reason code, and `contact_verified=true`. It updates only `User.email`, revokes all target refresh sessions, audits without storing email/token/free text, and dispatches a secure setup/reset email only after the database transaction commits.
4. **AC-4:** DILG can request a setup/reset link to the target's current email after the same verification attestation and controlled reason. The API response never includes a reset token or direct link; delivery uses the existing reset-email task.
5. **AC-5:** Deactivate/reactivate requires a controlled reason code, changes only `is_active`, writes a `USER_ACTION` audit record, and revokes active refresh sessions on deactivation. The last active barangay `ADMIN` cannot be deactivated through this surface.
6. **AC-6:** No action can set or change a target's password, role, barangay, username, `is_staff`, or `is_superuser`; request extra fields are rejected.
7. **AC-7:** The React DILG account-support page provides search, loading/error/retry/empty states, email correction and recovery-link actions, and reason/verification confirmation for lifecycle actions. It is routed and navigable only for DILG; backend authorization remains authoritative.
8. **AC-8:** Frontend/API contract and OpenAPI schema describe the endpoints and payloads.
9. **AC-9:** No database schema/migration, new runtime dependency, Celery/Redis service, production change, or deployment is introduced. Delivery occurs through the feature branch and PR after review.

## Risks and mitigations
- **Wrong-contact takeover:** Require external verification attestation, reason, DILG-only authorization, email uniqueness validation, audit, and session revocation.
- **Tenant/privilege escalation:** Exclude DILG/superuser targets and make role/barangay fields non-writable; test unauthorized and cross-role boundaries.
- **Email enumeration:** The endpoint is authenticated and DILG-only; no public reset response changes. Do not return tokens or email-delivery internals.
- **Tenant lockout:** Prevent disabling the last active barangay administrator.
- **Audit PII leakage:** Store only target ID, role, barangay ID, action, and a controlled reason code; never include email value, free text, password, token, or profile evidence.
- **Email delivery failure:** Preserve the account change, return a generic accepted response, and rely on existing secure reset flow for a later resend; task logs must not reveal email or token.
