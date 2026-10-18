# Database and Data Boundaries

PostgreSQL is the production relational database configured by `DATABASE_URL`. SQLite is used by selected local and test workflows. Django models and committed migrations are the authoritative schema; this page describes relationships and invariants rather than duplicating every column.

## Domain relationships

- `Barangay` is the tenant root for barangay-scoped users, documents, queues, communications, and operational data.
- `User` carries an active product role and, for barangay roles and residents, an assigned barangay. Existing rows with retired role strings may remain for audit continuity but are denied authentication and authorization.
- `Resident` is a profile associated with a user. Verification and evidence fields are handled through guarded workflows.
- `DocumentRequest` records online and walk-in transactions. Walk-in requests may have no user account; the barangay relationship preserves their tenant and treasury history. User erasure uses the reviewed `SET_NULL` relationship so municipal records can remain.
- `QueueTicket`, `AidRequest`, `IssueReport`, `Announcement`, `ActivitySchedule`, and hotline/FAQ records serve their respective feature domains.
- `AuditLog` records selected administrative actions. Its text descriptions and correlation identifiers are not database-enforced immutable or unique audit chains.
- `PrivateMediaCleanup` supports retryable cleanup of encrypted private-media references after the related database change commits.

## Schema change rules

- Tenant-owned records must preserve an explicit tenant relationship and be queried through the authenticated tenant boundary.
- Use explicit fee-assessment and waiver provenance for document fees; `fee_amount = 0` alone is not proof of a statutory exemption.
- Preserve transaction history and the Official Receipt release gate defined in [ADR 007](decisions/007-revenue-and-official-receipt-auditing.md), [ADR 017](decisions/017-manual-epayment-evidence-and-verification.md), and [ADR 018](decisions/018-explicit-document-fee-assessment-and-waiver-provenance.md).
- Keep Django app labels and historical table/migration identities stable. Renaming internal `gridy_*` identifiers requires a separate, reviewed migration plan.
- Follow expand/backfill/switch/contract for changes that must work across application versions. See [ADR 014](decisions/014-safe-schema-rollout-compatibility.md).

For exact current fields, constraints, indexes, and deletion behavior, inspect the models and migrations in `backend/`; do not use old copied SQL tables in feature prose as the schema contract.
