# Plan: M95 Barangay-Only Product Scope and Account Provisioning

## Milestone 1 — Reconcile Branch and Schema

1. Work from an isolated branch and merge latest main without touching the primary checkout or partner branch.
2. Inspect current migrations, role authorization paths, account support, onboarding, reporting, and tenant querysets.
3. Revert the unshipped `BarangayApplication.application_type` and `existing_barangay` field changes: no migration was supplied, no public official-application workflow will remain, and Barangay Admin staff provisioning already exists.
4. Preserve the existing `BarangayApplication` model/table and all legacy rows. Register them read-only in Django Admin for superusers; do not auto-reject or delete pending rows.
5. Remove `DILG_ADMIN` from active role choices and authorization. Add only the reversible role-choice migration Django requires; leave all historical migration files unchanged and never run it in production here.

Validation: DEBUG=True python backend/manage.py check; DEBUG=True python backend/manage.py makemigrations --check --dry-run; migration tests against a local/test database.

## Milestone 2 — Retire Public Application Workflow and Preserve History

1. Remove public create/list/review routes and the redundant official application UI.
2. Keep ordinary resident registration and Public Barangay Directory reads intact.
3. Rely on tenant-scoped Barangay Admin staff management for Field Official provisioning.
4. Keep historical application rows and review metadata available read-only to Django superusers; no workflow may silently reject or remove pending records.
5. Document that tenant and first-ADMIN bootstrap is performed by a deployment operator through the protected Django administration/bootstrap process.

Validation: endpoint retirement tests, read-only admin permissions, historical-row preservation, existing staff-management tenant isolation, and public directory / resident-registration regression tests.

## Milestone 3 — Retire Government-Wide Product Surfaces

1. Deny authentication and authorization to legacy DILG role values; preserve existing stored values without granting access.
2. Remove cross-tenant role bypasses from residents, documents, queue, communications, reports, and analytics.
3. Retarget bounded account recovery support to Django superusers while preserving verification, audit, throttle, session, and field restrictions.
4. Remove the role's web/mobile routes, navigation, labels, and seed accounts. Keep superuser-only operational access out of normal barangay portals.
5. Update generated schema, current product documentation, demo flow, and add a superseding ADR. Retain historical migration/ADR content.

Validation: auth/service regression suites, OpenAPI schema generation, frontend tests/lint/build, mobile tests where role behavior changes, and a repository scan distinguishing historical from active references.

## Milestone 4 — Final QA and Handoff

1. Run complete affected backend and frontend suites.
2. Run git diff --check and inspect the final diff for accidental scope expansion and secrets.
3. Record exact command output, files, migration behavior, and residual limitations in STATUS.md.

Safety: No production DB or deployment operations. Do not stage, commit, push, or open a PR until local implementation and checks are complete. The primary checkout and partner remote branch remain untouched.
