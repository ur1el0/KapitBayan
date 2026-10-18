# M94 Status: DILG Account Support and Recovery

## Executive summary
- **Task ID:** `m94-dilg-account-support-recovery`
- **State:** Draft PR #245 is open; implementation and non-test checks pass; regression tests remain a merge gate.
- **Branch:** `feat/dilg-account-support`
- **Worktree:** `/tmp/gridy-dilg-account-support`
- **Base:** GitHub `main` at `46d5af8` (`46d5af8e6ec05d1717d280c1f2ade434ab324cbb`). The branch was rebased onto it; `frontend/src/App.tsx` retains the merged Resident Tutorial route and adds the DILG route.
- **Primary checkout:** `/home/dokja/vsc-fedora/all/Projects/django-projects/Gridy` remained clean at `96b5e81`.
- **Hindsight:** knowledge search/list calls could not connect to the local service at `127.0.0.1:9077`; no memory claims were used.

## Scope delivered
- Added a DILG-only, throttled account directory and limited lifecycle API for `RESIDENT`, `FIELD_OFFICIAL`, and `ADMIN` accounts, including legacy unassigned accounts.
- Excluded DILG accounts and Django superusers. No create, delete, password-setting, username, role, barangay, staff-flag, or superuser-flag operations are exposed.
- Email correction and private reset-link requests require a controlled reason and contact-verification attestation. Email correction revokes refresh sessions; reset mail is queued with `transaction.on_commit` and neither token nor email is written to audit descriptions or application logs.
- Deactivation/reactivation changes only `is_active`; deactivation revokes refresh sessions. The last assigned active barangay administrator is protected from deactivation.
- Added the DILG Account Support page, DILG-only route/navigation, API types, and ADR 020/security architecture updates.
- No models, migrations, runtime dependencies, Celery/Redis services, or production configuration were added.

## Milestone tracker

| Milestone | State | Notes |
|---|---|---|
| M1 — Backend API and security boundary | Implemented; tests pending | DRF serializers/viewset, route, scoped throttle, session revocation, audit records, transaction-on-commit email dispatch, and OpenAPI annotations are present. |
| M2 — DILG support console | Implemented; tests pending | Search, role/status filters, paginated directory, error/retry/empty states, verified email actions, status confirmation, and DILG-only navigation are present. |
| M3 — Verification and handoff | Incomplete | Non-test checks passed. Backend and frontend test suites were not added or run; do not merge until regression coverage and review are completed. |

## Verification log
Commands below were run in `/tmp/gridy-dilg-account-support`. Django commands used an explicitly local SQLite database and test-only settings:

```bash
SECRET_KEY=test-dev-secret-key-123456789012345678901234567890 \
ADMIN_REGISTRATION_PASSKEY=test-passkey-secret-12345 \
DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True \
DATABASE_URL=sqlite:////tmp/gridy-dilg-account-support/db.sqlite3 \
/home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/python backend/manage.py check
```

**Result:** exit 0; `System check identified no issues (0 silenced).` The expected local warning stated Firebase credentials are unset and push notifications are disabled.

```bash
SECRET_KEY=test-dev-secret-key-123456789012345678901234567890 \
ADMIN_REGISTRATION_PASSKEY=test-passkey-secret-12345 \
DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True \
DATABASE_URL=sqlite:////tmp/gridy-dilg-account-support/db.sqlite3 \
/home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/python backend/manage.py makemigrations --check --dry-run
```

**Result:** exit 0; `No changes detected` (no schema migration required).

```bash
/home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/python -m compileall -q \
  backend/gridy_auth/serializers/account_support.py \
  backend/gridy_auth/views/account_support.py
```

**Result:** exit 0; no output.

```bash
SECRET_KEY=test-dev-secret-key-123456789012345678901234567890 \
ADMIN_REGISTRATION_PASSKEY=test-passkey-secret-12345 \
DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True \
DATABASE_URL=sqlite:////tmp/gridy-dilg-account-support/db.sqlite3 \
/home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/python \
  backend/manage.py spectacular --file /tmp/m94-openapi-final.yml --validate
```

**Result:** exit 0. The generated schema contains list, retrieve, email-correction PATCH, resend-link POST, and set-active POST operations under `/api/v1/auth/dilg/accounts/`. Repository-wide validation reports 14 warnings (6 unique) and 17 errors (5 unique), all observed in pre-existing, out-of-scope views; no account-support schema warning/error was reported. These repository-wide schema issues remain separate follow-up work.

```bash
npm --prefix frontend run lint
```

**Result:** exit 0; Oxlint reported no warnings/errors.

```bash
npm --prefix frontend run build
```

**Result before upstream rebase:** exit 0; TypeScript and Vite production build passed, 2,524 modules transformed.

After rebasing onto GitHub `main` at `46d5af8`, the same command was rerun.

**Result after rebase:** exit 0; TypeScript and Vite production build passed, 2,525 modules transformed.

```bash
git diff --check FETCH_HEAD..HEAD
```

**Result:** exit 0; clean against the rebased GitHub main base.

**Not run:** Backend or frontend tests. The task plan calls for regression suites, but they remain an explicit merge gate and their behavior is not verified by the checks above.

## Hygiene and delivery state
- Published PR head: `e715a84` (`feat/dilg): add bounded account support and recovery`.
- No production mutation or deployment was made.
- Primary checkout remained clean at `96b5e81`.
- Draft PR [#245](https://github.com/ur1el0/KapitBayan/pull/245) is open. Backend and frontend tests have not been run; keep the PR in draft.
- Final implementation files are listed by `git status`; generated OpenAPI output is under `/tmp`, not in the repository.

## Remaining blockers / risks
1. Add and run backend tests for role denial/target exclusion, strict extra-field rejection, unique-email handling, verification/reason requirements, session revocation, last-admin concurrency protection, audit redaction, and on-commit recovery dispatch.
2. Add and run frontend tests for DILG-only route/navigation, unassigned account display, search/filter/pagination, verification gating, API errors, and lifecycle confirmations.
3. Complete review, regression tests, and required CI checks before marking the PR ready or merging.
4. The external verification step is an operator attestation, not cryptographic proof; DILG procedures must define acceptable identity/contact verification channels.
5. Revoking refresh sessions does not retroactively invalidate an already-issued short-lived access token; this follows the platform's existing JWT model.

## Delivery
- PR: https://github.com/ur1el0/KapitBayan/pull/245 (open, draft, unmerged).
- Keep it blocked from merge until regression tests and review are complete.
