# ADR 021: Barangay-Only Product Scope and Platform Recovery

- **Status:** Accepted; Barangay onboarding review scope is further amended by [ADR 023](023-dilg-reviewed-barangay-admin-registration.md)
- **Date:** 2026-10-18
- **Supersedes:** The active product-scope portions of ADR 011 and ADR 020. Historical records remain unchanged.

## Context

KapitBayan's approved product and capstone scope is resident and service support for participating Barangays. A government-wide DILG workflow, oversight dashboard, or DILG user role is outside the reviewed fieldwork and stakeholder scope. Publicly allowing an official to apply for tenant creation also duplicates the existing Barangay Administrator staff-provisioning flow and risks creating unverified tenants.

The system still needs a controlled way to bootstrap its initial Barangay and first Barangay Administrator, and an operator needs a limited recovery mechanism for account contact errors or lockouts. Historical database values and prior decisions must remain available for audit continuity.

## Decision

1. The active application roles are `RESIDENT`, `ADMIN`, `FIELD_OFFICIAL`, and `DILG_ADMIN`, each limited by endpoint-specific permissions. `DILG_ADMIN` may access only new-Barangay application review and its own minimal authentication/session endpoints; it receives no account-support or tenant service access. See ADR 023.
2. Public Barangay directory reads remain available for resident registration. Reviewed public Barangay applications are defined by ADR 022 and amended by ADR 023. Public submission cannot create an active account or tenant.
3. Barangay `ADMIN` users may provision and manage Field Officials only within their own Barangay. They cannot create or list peer `ADMIN` accounts. Admin accounts are created through protected platform-operator provisioning. No application role receives cross-Barangay service-data access.
4. Django superusers are platform operators, not a product role. A separately permissioned and throttled support surface permits minimal account lookup, audited contact correction with an explicit verification attestation, recovery-link dispatch, and account activation changes. It excludes superusers and retired roles; it cannot create or delete accounts, set passwords directly, change roles or Barangay assignments, or change resident evidence. Disabling an account revokes its refresh sessions, and the last active Barangay administrator cannot be disabled by this flow.
5. Existing `BarangayApplication` rows and their review metadata are retained and may be inspected read-only by active Django superusers. They are not automatically rejected or deleted. Historical migration and ADR files are retained as records of prior decisions.

## Consequences

- Tenant onboarding is reviewed by DILG. The applicant registers using the official email and a password, with no chosen username; approval activates that same account for the verified Barangay. A controlled Django superuser remains a fallback reviewer and retains its separate account-support function. After onboarding, the Barangay Admin may manage Field Officials in that Barangay but cannot provision another Admin.
- Account recovery remains possible without adding cross-tenant service access or unrestricted account CRUD.
- A role-choice migration may remove retired values from Django's declared choices, but must not delete or rewrite existing rows. Authentication and authorization checks remain the enforcement boundary.
- Current product guides and training materials describe Barangay-only roles. Historical ADRs and migration files retain their original wording and are superseded by this decision.
- Operators must protect the Django superuser credentials, verify account holders through an established official channel before contact correction or link dispatch, and retain audit logs.

## Validation

The implementation must verify DILG review authorization, rejection of DILG access to service/account-support routes, tenant isolation for every Barangay workflow, superuser-only platform support, application-history retention, and absence of public tenant provisioning or global analytics routes. Production database changes are outside the implementation task and require a separate release gate.
