# Resetting Production Accounts

This is an irreversible operation. It retains only the unique account matching the supplied global operator email, which must have the `BARANGAY_OPERATOR` role. It deletes every other `User` row, including Barangay Admins, any other Barangay Operators, residents, field officials, Django staff, and superusers. It also deletes linked resident profiles, refresh sessions, FCM devices, issue reports, announcements, activity schedules, emergency hotlines, notifications, aid requests, document requests, queue tickets, onboarding applications, and outstanding JWT tokens for the accounts being erased. Queue tickets linked to a deleted document request are included even when their user link is already empty. Records directly linked to the retained operator remain unless they are also linked to an account being deleted. Audit log rows are retained with links for deleted accounts cleared. Any new user relation not explicitly covered by this policy blocks execution.

The command is preview-only unless `--execute` is supplied. It requires a PostgreSQL database, `DEBUG=False`, exact database host and name confirmation, a pre-reset Neon snapshot reference, a plan token copied from a preview, and the exact destructive phrase. It locks the user table and performs database changes in one transaction. The lock blocks user-table reads and writes until commit; schedule an outage and stop account-related traffic for the operation.

The command does not delete uploaded file objects from `IssueReport` and `Announcement` rows; it lists distinct external file names in the preview and refuses execution until `--accept-remaining-media` is supplied. Resident private evidence, onboarding proof, and profile pictures are queued for retryable cleanup after commit. Document payment proofs use the existing post-delete storage cleanup signal. The preview separates files scheduled for cleanup from external files that will remain.

## Preconditions

1. Use the feature worktree that contains this command, or merge the reviewed feature branch and check it out locally. The command is not present in the existing `Gridy/backend` checkout until the feature branch is brought into it.
2. Schedule a maintenance window. The command takes an exclusive lock on the user table; login, registration, and account-linked requests can block or time out while it runs.
3. In Neon, create a snapshot of the production branch immediately before the reset and verify that it is available. Record its name or identifier; the command records this reference but does not contact Neon to validate it. A Neon restore creates a branch at the selected earlier point; restoring may discard writes after that point. See [Neon snapshots](https://api-docs.neon.tech/reference/createsnapshot) and [Neon point-in-time branch restore](https://api-docs.neon.tech/reference/restoreprojectbranch).
4. For a local run, obtain the production `DATABASE_URL`, Django `SECRET_KEY`, and Cloudinary cloud name, API key, and API secret from their respective dashboards. Do not put these values in a command, commit, or chat. The local network must be allowed to connect to the Neon endpoint.

## Preview

From the feature worktree, in the directory containing `manage.py`, read the values without echo, then run the preview. Keep this terminal open for the later execution command; the values are kept only in its environment:

```bash
cd /tmp/gridy-operator-account-erasure/backend
export DEBUG=False KAPITBAYAN_ACCOUNT_RESET_RUNTIME=True
read -r -s -p 'Production Django SECRET_KEY: ' SECRET_KEY; printf '\n'; export SECRET_KEY
read -r -s -p 'Production Neon DATABASE_URL: ' DATABASE_URL; printf '\n'; export DATABASE_URL
read -r -s -p 'Production Cloudinary cloud name: ' CLOUDINARY_CLOUD_NAME; printf '\n'; export CLOUDINARY_CLOUD_NAME
read -r -s -p 'Production Cloudinary API key: ' CLOUDINARY_API_KEY; printf '\n'; export CLOUDINARY_API_KEY
read -r -s -p 'Production Cloudinary API secret: ' CLOUDINARY_API_SECRET; printf '\n'; export CLOUDINARY_API_SECRET
python manage.py reset_production_accounts --preserve-email '<GLOBAL_OPERATOR_EMAIL>'
```

This account-reset-only runtime still requires `DEBUG=False`, PostgreSQL, the production database credentials, the production Django secret, and production Cloudinary credentials. It skips unrelated mail, frontend, and Firebase startup requirements, and refuses to start for any command other than `reset_production_accounts`. If the local network cannot reach Neon, stop; do not substitute an unreviewed SQL deletion.

Expected result: `Preview only. No database rows were changed.` The output identifies the preserved email and role. Review the engine, database name, host, accounts to erase by role, superuser/staff counts among accounts to erase, direct cascade counts, linked service/auth rows to delete, retained audit rows, blocking relationships, files scheduled for cleanup, and external file objects that remain. Confirm the email is the intended global operator and the host/database identify the intended production database. Save the printed plan token. Keep the same shell open for execution so the confirmations use the reviewed database URL.

If the preview lists any relationship requiring manual review, stop. Review the external files that remain and the private files scheduled for cleanup. The command only proceeds with external files remaining if you explicitly acknowledge that by passing `--accept-remaining-media`.

## Execute

Use the exact values from the reviewed preview in the same terminal, replacing every placeholder and omitting angle brackets:

```bash
python manage.py reset_production_accounts \
  --preserve-email '<GLOBAL_OPERATOR_EMAIL>' \
  --execute \
  --confirm-preserve-email '<GLOBAL_OPERATOR_EMAIL>' \
  --confirm-database '<DATABASE_NAME>' \
  --confirm-host '<POSTGRES_HOST>' \
  --backup-reference '<NEON_SNAPSHOT_NAME_OR_ID>' \
  --expected-plan '<PLAN_TOKEN>' \
  --confirm-all-data 'DELETE ALL OTHER ACCOUNTS AND LINKED SERVICE RECORDS' \
  --accept-remaining-media
```

Omit `--accept-remaining-media` only if the preview lists no external file objects that will remain. If anything in the preview changed, rerun the preview and review its new token first. The command locks the user table, recomputes the plan under the lock, and aborts before deleting rows if its token differs from `--expected-plan` or if an unsupported relation exists.

Expected successful output includes `Erased N user accounts in one transaction.` The command also records a batch audit entry and per-account erasure entries. The named operator account and its credentials remain. All other accounts are erased; verify the retained operator can sign in before ending maintenance.

If the command exits with a storage-cleanup error after the database transaction, the account deletion may already have committed. Run the preview again before any retry; do not treat a nonzero exit alone as proof that the database rolled back. Check application/storage logs and the private-media cleanup queue.

## Verify and restore access

Run the preview again:

```bash
python manage.py reset_production_accounts --preserve-email '<GLOBAL_OPERATOR_EMAIL>'
```

Expected result: `Accounts to erase: 0`, the correct operator listed as preserved, and `Preview only. No database rows were changed.` Confirm cascade and linked service/auth delete counts are also zero. Audit log rows remain by design.

Recreate Barangay Admin and other accounts using the approved onboarding and account-provisioning procedures. Verify the retained platform operator can log in before ending maintenance.

## Recovery

If the wrong account set was removed, do not rerun the reset or create replacement production data. Restore from the recorded Neon snapshot using the reviewed recovery procedure. A restore replaces the database state with an earlier point and can discard writes made after the snapshot; coordinate the application connection and recovery window before proceeding.

The command is included here for review and future controlled use. A prior production reset was executed separately; this document does not verify the current production database state.
