# ADR 025: Barangay Operator Onboarding and Bounded Account Support

- **Status:** Accepted for implementation
- **Date:** 2026-10-19
- **Supersedes:** The reviewer identity and access boundary in [ADR 023](023-dilg-reviewed-barangay-admin-registration.md) and the superuser-only support boundary in [ADR 020](020-dilg-account-support-boundary.md)
- **Retains:** Email verification and private authority-evidence requirements in [ADR 024](024-barangay-onboarding-email-and-authority-evidence.md)

## Context

KapitBayan needs a controlled way to review a new Barangay's first Admin application and help restore access to accounts that cannot receive their setup or recovery email. The product is scoped to Barangay information and services. It has no DILG partnership or government-wide oversight mandate, and prior analytics surfaces were removed. At the same time, the existing first-Admin application and recovery flows need a named, least-privilege platform operator.

## Decision

1. The active role is `BARANGAY_OPERATOR`, displayed as **Barangay Operator**. It describes a KapitBayan platform account and does not imply employment by, endorsement from, or integration with any government agency.
2. An active Barangay Operator may review first-Admin Barangay applications. The existing official-email verification, inactive-until-approved state, private proof streaming, independent verification, audit, throttling, and tenant-provisioning safeguards remain mandatory.
3. An active Barangay Operator may use the existing bounded account-support actions for `RESIDENT`, `FIELD_OFFICIAL`, and `ADMIN` accounts across Barangays: minimal directory search, verified email correction, private setup/reset-link dispatch, and activation/deactivation. Actions remain reason-coded, audited, throttled, and session-safe. Operators cannot create or hard-delete accounts, set passwords, change usernames, roles or Barangay assignments, edit evidence, or manage superusers or other operators.
4. Operator access is limited by API authentication to onboarding review, account support, and the operator's own authentication/session endpoints. Account support may show only the minimal account directory attributes required for recovery; it does not expose resident profiles or identity evidence. Operators cannot access queue tickets, documents, aid requests, communications, treasury data, analytics, or other tenant service records. The operator role is web-only and has no mobile route.
5. No cross-Barangay analytics, dashboard, metrics, DILG branding, DILG affiliation claim, or DILG integration is part of the active system. Each Barangay's ordinary service data remains tenant-scoped under ADR 004.
6. A reversible data migration maps existing `DILG_ADMIN` role values to `BARANGAY_OPERATOR`; it preserves account IDs, passwords, email, active state, and other fields. Historical migrations and ADR records remain unchanged.
7. The guarded production migration workflow can inspect and apply only its exact reviewed migration allowlist. It uses a GitHub Actions-only filesystem storage mode for management commands, keeps production web startup strict, masks or avoids any non-production signing key, and requires an approved exact migration plan before apply.

## Consequences

- Existing review and account recovery behavior can continue under platform-owned branding without making a claim of DILG participation.
- The role is operationally cross-Barangay only for onboarding and minimal account recovery; it is not a Barangay service administrator or resident-profile reviewer.
- Existing DILG-role rows are preserved by a reversible value migration. Old DILG-specific historical migrations and decision records remain as provenance.
- Applying migrations to the hosted production database remains a separate release operation with its existing approval gate. This ADR and implementation do not authorize an apply run or deployment.

## Validation

- Verify login, session refresh, allowed onboarding/support endpoints, and denial of tenant service APIs.
- Verify support target roles, controlled fields, audit records, throttles, session revocation, and last-active-Admin guard.
- Verify migration forward and backward on an isolated local database.
- Verify `DEBUG=False` migration-only settings require GitHub Actions and use filesystem storage while ordinary production startup still requires Cloudinary, email, Firebase, PostgreSQL, and HTTPS frontend configuration.
- Confirm active routes and generated API schema contain no analytics surface and no `DILG_ADMIN` role.
