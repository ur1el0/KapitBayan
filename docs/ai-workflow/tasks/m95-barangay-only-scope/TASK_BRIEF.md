# M95: Barangay-Only Product Scope and Account Provisioning

## Goal

Align the active application with the capstone's barangay-only scope. Remove the active DILG-facing role, routes, cross-tenant services, and user-facing claims. Keep tenant operations limited to each barangay. Retain a minimal, audited cross-tenant account recovery path for Django superusers, as previously requested, without exposing it as a government-stakeholder workflow.

## Non-goals

- Do not rewrite historical migrations or erase historical audit records/ADRs.
- Do not modify production data, run production migrations, or deploy.
- Do not add new roles, external services, task queues, or cross-tenant business workflows.
- Do not remove existing resident, Barangay Admin, or Field Official services.
- Do not accept public new-tenant creation. Initial tenant and first-admin provisioning remains a controlled deployment-operator operation.

## Rules

- Tenant isolation: Barangay Admin API queries and writes are limited to request.user.barangay_id; cross-tenant IDs return 404.
- Platform support: Only authenticated Django superusers may use the existing account-recovery support API. They cannot change roles, barangay assignment, superuser status, or passwords; email/recovery changes remain audited and session-safe.
- Official accounts: The existing Barangay Admin staff-management flow is the only application-level path for provisioning Field Officials. Retire public official applications rather than adding a duplicate approval workflow.
- Tenant bootstrap: No public endpoint may create a Barangay or initial Admin account. The operator process must be documented and use the existing protected Django administration/bootstrap path.
- Historical data: Preserve old applications, user rows, and audit records. Never silently delete or auto-reject legacy pending applications. Preserve historical migration and ADR files; supersede active guidance with a new decision record.
- Safety: All migration checks and tests run against local/test databases only.

## Acceptance Criteria

1. Active authentication and API authorization no longer grant privileges to legacy DILG_ADMIN role values.
2. Cross-barangay service access is removed from ordinary application APIs; Barangay Admin access remains tenant-scoped.
3. Account recovery/support is accessible only to Django superusers, retains field restrictions, audit logging, verification checks, throttling, and session revocation.
4. Public official and barangay application routes are retired; new public requests cannot create tenants, initial ADMIN accounts, or standalone official-review workflows.
5. Legacy `BarangayApplication` rows, review history, and applicants remain preserved and inspectable read-only by Django superusers. Pending rows are not auto-rejected or deleted.
6. The unshipped `application_type` / `existing_barangay` model changes from the partner branch are reverted because no migration exists and the duplicate official request flow is retired. Existing historical migrations remain untouched.
7. Active web navigation, route copy, seed commands, generated API schema, and current architecture/runbook documentation contain no government-wide oversight role or workflow. Historical migrations/ADRs remain for audit history and are explicitly superseded.
8. Regression tests cover legacy-role login denial, superuser-only support, tenant-isolated staff management and service access, retired application endpoints, and preservation/read-only visibility of legacy applications.
9. Django checks, migration checks, affected backend/frontend tests, frontend lint/build, and diff hygiene are run and recorded accurately.

## Current Evidence

- The partner branch adds application_type and existing_barangay to BarangayApplication without a migration.
- Its official account request/review path still depends on IsDILGAdmin and approves ADMIN accounts globally.
- The branch rejects public BARANGAY applications and hides historical pending rows from its reviewer list.
- The partner branch is 6 commits behind latest main and has no PR.
- Latest `main` already contains Barangay Admin Field Official provisioning; a second public official-application flow is unnecessary and would preserve the out-of-scope government approval dependency.
- The correction retires active application endpoints while keeping historical application data available to Django superusers as read-only records.
