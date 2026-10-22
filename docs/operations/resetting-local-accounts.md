# Resetting Local User Accounts

`reset_local_accounts` removes all Django user accounts on a local development database while using the application's account-erasure lifecycle. It deletes resident profiles and private identity evidence, revokes sessions, writes erasure audit records, and retains document requests, aid requests, and audit history according to the application's retention rules. Other rows with cascading account foreign keys, such as issue reports, announcements, activity schedules, hotlines, and notifications, are deleted with the accounts. Barangay rows are not reset.

Uploaded files attached to cascaded issue reports and announcements are not removed by this command. Account profile pictures and resident private evidence use the existing lifecycle cleanup behavior.

The command includes Django superusers and Barangay Operators. Recreate a superuser after the reset. The command refuses to execute when `DEBUG` is false, the database host is not local, or the database engine is unsupported. It previews counts without changing data by default.

## Docker Compose PostgreSQL

Run these from the Gridy repository root. Start the local stack and create a private backup:

```bash
docker compose up -d
```

```bash
umask 077
docker compose exec -T db pg_dump -U gridy_user gridy_db > /tmp/gridy-before-account-reset.sql
```

Preview the database name and account counts:

```bash
docker compose exec backend python manage.py reset_local_accounts
```

Review the output. For the Compose database shown as `gridy_db`, execute the reset with the exact name:

```bash
docker compose exec backend python manage.py reset_local_accounts --execute --confirm-database gridy_db
```

Create a new Django superuser:

```bash
docker compose exec backend python manage.py createsuperuser
```

## Host-run Django

For SQLite, back up the database file before continuing:

```bash
cp backend/db.sqlite3 /tmp/gridy-before-account-reset.sqlite3
```

From the repository root, preview first:

```bash
cd backend
python manage.py reset_local_accounts
```

Use the exact database name printed by the preview in the execution command. For a PostgreSQL database named `gridy_db`:

```bash
python manage.py reset_local_accounts --execute --confirm-database gridy_db
python manage.py createsuperuser
```

For SQLite, the preview may show a full path; use that exact value for `--confirm-database`.

## Safety notes

- Do not run this against production or a shared database.
- `manage.py flush` is not appropriate when only accounts should be reset; it clears every application table.
- Keep the backup private. It contains the database contents before erasure.
- The command does not recreate Barangay Operators or Barangay Admins. Create new accounts through the normal onboarding and provisioning workflows.
