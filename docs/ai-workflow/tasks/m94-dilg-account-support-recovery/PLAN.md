# Implementation Plan: M94 DILG Account Support and Recovery

## Overview
- **Associated brief:** [TASK_BRIEF.md](TASK_BRIEF.md)
- **Branch:** `feat/dilg-account-support`
- **Base:** GitHub `main` at `46d5af8`; the isolated branch has been rebased onto the Resident Tutorial merge, retaining its changes in `frontend/src/App.tsx`.
- **Complexity:** Medium-high (privileged cross-tenant account lifecycle)

## Milestone 1: Backend support API and security boundary
1. Add a dedicated DILG account-support API/viewset and strict serializers for search, email correction, reset-link dispatch, and active-state changes.
2. Scope targets to `RESIDENT`, `FIELD_OFFICIAL`, and `ADMIN` users, including legacy users without a barangay; exclude `DILG_ADMIN` and `is_superuser=True` users. Return 404 for ineligible IDs.
3. Require a controlled reason code and explicit contact-verification attestation for email corrections and link dispatch. Validate email uniqueness case-insensitively.
4. Update only the intended field. Use transactions; revoke sessions for email correction and deactivation; reject deactivation of a barangay's last active `ADMIN`.
5. Queue the existing private password-reset task on transaction commit. Never return or log reset tokens/emails.
6. Add `USER_ACTION` audit records and shared database-backed throttle scope. Add OpenAPI schemas and route registration.
7. Add backend tests for role barriers, target eligibility, unique email, required attestations/reasons, session revocation, last-admin guard, audit redaction, and on-commit email dispatch.

**Validation:** targeted account-support tests; `DEBUG=True venv/bin/python backend/manage.py check`; `DEBUG=True venv/bin/python backend/manage.py spectacular --file /tmp/m94-openapi.yml --validate`; `DEBUG=True venv/bin/python backend/manage.py makemigrations --check --dry-run`.

## Milestone 2: DILG support console
1. Add a DILG-only route and navigation item.
2. Build an accessible account directory with bounded search, role/status display, barangay context, and loading/error/retry/empty states.
3. Add confirmation forms for email correction and reset-link resend, requiring contact-verification confirmation and a controlled reason; show delivery as requested rather than claiming delivery succeeded.
4. Add activate/deactivate controls with controlled reason and confirmation; clearly explain that deactivation revokes sessions and that the last active barangay administrator cannot be disabled.
5. Keep the UI minimal and avoid displaying sensitive resident proof/profile fields.
6. Add frontend tests for route/role visibility, API payloads, error states, confirmation requirements, and successful updates.

**Validation:** targeted Vitest suites; `npm --prefix frontend run lint`; `npm --prefix frontend run build`.

## Milestone 3: Integrated verification and status
1. Run affected backend and frontend tests plus full relevant suites.
2. Verify no migration is generated, no dependencies changed, no secrets appear in diffs, and `git diff --check` is clean.
3. Update STATUS.md with exact commands and actual outputs, file inventory, unresolved risks, and delivery state.

**Validation:** `venv/bin/pytest backend/gridy_auth`; `npm --prefix frontend run test`; `git diff --check`; status/staged review.

## Rollback
- Revert the feature commit or remove the dedicated route/view/serializers and frontend route/page. The plan adds no model/schema changes, so there is no database rollback. Emails already dispatched cannot be recalled; only a private, expiring setup/reset link is sent.
