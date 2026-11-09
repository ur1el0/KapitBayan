# Production API recovery: document requests and queue

**Observed:** November 9, 2026, during an authenticated Redmi 12C review. Document-request reads and queue live-status/ticket reads returned HTTP 500. Do not create replacement requests or tickets while these reads fail; a timed-out write may have reached the server.

## Current migration lead

Production migration `gridy_services.0021_documentrequest_submission_fingerprint_and_more` is pending. Its preflight found Barangay 5 receipt number `123` on request IDs 33, 37, and 41 and aborted before changing receipt or ticket numbers. The application models now use fields introduced by that migration. This makes an application/database schema mismatch a likely explanation for the 500s, but it is not confirmed until the Render traceback or live schema is checked.

## Safe recovery sequence

1. In Render logs, inspect the traceback for the authenticated document-request and queue endpoints at the time of a failed request. Record the exception and the deployed commit; do not copy access tokens or resident data into an issue or log.
2. Using the exact backend commit deployed to production and the production database connection stored in the hosting environment, check `showmigrations gridy_services` and inspect whether the migration’s columns and constraints are present. Keep credentials out of shell history, chat, and repository files. Do not enable production `DEBUG` to obtain a traceback.
3. Reconcile request IDs 33, 37, and 41 with the Barangay’s official receipt records. Do not guess an O.R. number, change a valid receipt merely to satisfy a constraint, or edit production rows directly without an authorized audit trail. Resolve any other unscoped requests or duplicate daily ticket numbers the migration reports.
4. Run the migration command’s plan against the same deployed code and database to confirm the expected migration is pending. **A plan does not run the data checks.** The migration’s duplicate and tenant-scope checks run during application and must be observed in a controlled migration run.
5. Apply only after authoritative data reconciliation and a clean preflight. Do not use `--fake` or hand-add columns: that can mark an incomplete schema as migrated and leave the API inconsistent. Preserve the failed migration output and confirm it changed no official numbers.
6. After the migration and backend deploy, verify authenticated document-request and queue reads first. Only then test a controlled request/ticket flow and confirm the returned ticket and document IDs in both screens. Stop if any request still returns 500 or a write has an uncertain result.

## Current status

This is an incident/recovery checklist, not evidence that production has been repaired. The phone’s request and queue screens remain unverified against a healthy API. The next required evidence is the Render traceback and authoritative confirmation of the duplicate receipt values.
