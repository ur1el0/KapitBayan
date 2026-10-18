# M96 status: production test login block

## State
Implementation and local verification complete on `fix/production-test-login-block`, based on `origin/main` at `4f924e9`. Pull request not yet opened.

## Progress
- [x] Confirm production API login, refresh-session, and JWT authentication paths.
- [x] Confirm local demo seed safety and synthetic identity domains.
- [x] Implement production-only account policy for login, refresh, access JWT, and Django auth sessions.
- [x] Add regression tests and environment documentation.
- [x] Run checks and record results.
- [ ] Push branch and open PR.

## Verification
All Django commands used the repository virtual environment with `DEBUG=True`, `KAPITBAYAN_TEST_USE_SQLITE=True`, and an explicit SQLite database URL under `/tmp`; no production database URL was used.

```bash
SECRET_KEY=local-test-secret-key-please-ignore ADMIN_REGISTRATION_PASSKEY=m96-local-test-passkey DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True DATABASE_URL=sqlite:////tmp/m96-production-test-login.sqlite3 /home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/python manage.py test gridy_auth -v 1
```

**Result:** exit 0; 151 tests passed, 4 skipped. Django reported no system-check issues. Output included the expected local Firebase-not-configured warning and a missing collected static-files directory warning in this isolated checkout.

```bash
SECRET_KEY=local-test-secret-key-please-ignore ADMIN_REGISTRATION_PASSKEY=m96-local-test-passkey DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True DATABASE_URL=sqlite:////tmp/m96-production-test-login.sqlite3 /home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/python manage.py check
```

**Result:** exit 0; `System check identified no issues (0 silenced).`

```bash
SECRET_KEY=local-test-secret-key-please-ignore ADMIN_REGISTRATION_PASSKEY=m96-local-test-passkey DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True DATABASE_URL=sqlite:////tmp/m96-production-test-login.sqlite3 /home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/python manage.py makemigrations --check --dry-run
```

**Result:** exit 0; `No changes detected`.

```bash
git diff --check
```

**Result:** exit 0; no whitespace errors.

## Production handoff
No production database, Render environment, or deployment has been changed. The private denylist must be configured after merge, preserving the manually created DILG and test barangay usernames. The test barangay username still needs to be confirmed before generating the exact production setting value.
