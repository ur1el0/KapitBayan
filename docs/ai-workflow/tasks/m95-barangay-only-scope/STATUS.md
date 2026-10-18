# M95 Status: Barangay-Only Product Scope and Account Provisioning

## State

- Status: Implementation and local verification complete; pushed to origin on `fix/barangay-only-scope-no-dilg`
- Worktree: /tmp/gridy-onboarding-fix-full
- Branch: fix/barangay-only-scope-no-dilg
- Base: Partner branch 04a9e591 merged with latest fetched main
- Primary checkout: Preserved; existing unstaged login changes not touched
- Partner branch: Preserved; no updates pushed
- Production: No access or changes

## Plan

- [x] M1 — Reconcile branch and schema
- [x] M2 — Retire public application workflow and preserve history
- [x] M3 — Retire government-wide product surfaces
- [x] M4 — Final QA and handoff

## Verification Log

- `SECRET_KEY=test-dev-secret-key-123456789012345678901234567890 ADMIN_REGISTRATION_PASSKEY=test-passkey-secret-12345 DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True /home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/pytest backend/gridy_auth backend/gridy_services backend/gridy_communications backend/gridy_reports -q` — **354 passed, 6 skipped**, 279 warnings, exit 0. The output included a warning for the absent local `backend/staticfiles/` directory; no test failed.
- `npm --prefix frontend run lint` — passed, exit 0.
- `npm --prefix frontend run test -- --pool=threads` — **46 test files, 222 tests passed**, exit 0.
- `npm --prefix frontend run build` — `tsc -b` and Vite production build passed; 2,523 modules transformed, exit 0.
- GitHub Actions run `39139701710` on verification commit `d8c227e` reported **frontend-tests failed: 221/222 passed**. The sole failure was `PublicAnnouncements.test.tsx > focuses and scrolls to the announcement named by the share link`: the test asserted focus immediately after the article appeared, before React's passive effect applied focus. Added `waitFor` around the focus assertion. Reverification on the updated worktree: the focused file passed **6/6**, the full frontend suite passed **46 files / 222 tests**, lint passed, and the production build passed. A new remote run is pending the follow-up push.
- `cd mobile && PUB_CACHE=/home/dokja/.pub-cache /home/dokja/development/flutter/bin/flutter pub get --offline` — dependencies resolved from cache; no dependency files changed.
- `cd mobile && PUB_CACHE=/home/dokja/.pub-cache /home/dokja/development/flutter/bin/flutter analyze` — **No issues found**, exit 0.
- `cd mobile && PUB_CACHE=/home/dokja/.pub-cache /home/dokja/development/flutter/bin/flutter test` — **157 tests passed**, exit 0. Tests emitted expected messages that Firebase push-notification listeners are unavailable in the local test environment.
- `SECRET_KEY=test-dev-secret-key-123456789012345678901234567890 ADMIN_REGISTRATION_PASSKEY=test-passkey-secret-12345 DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True /home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/python backend/manage.py check` — **System check identified no issues (0 silenced)**, exit 0. Firebase credentials are not configured locally, so push notifications are disabled for this check.
- `SECRET_KEY=test-dev-secret-key-123456789012345678901234567890 ADMIN_REGISTRATION_PASSKEY=test-passkey-secret-12345 DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True /home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/python backend/manage.py makemigrations --check --dry-run` — **No changes detected**, exit 0. Migration `0018_alter_user_role.py` is the only new migration and updates the role choices; it contains no data migration or row rewrite.
- `SECRET_KEY=test-dev-secret-key-123456789012345678901234567890 ADMIN_REGISTRATION_PASSKEY=test-passkey-secret-12345 DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True /home/dokja/vsc-fedora/all/Projects/django-projects/Gridy/venv/bin/python backend/manage.py spectacular --file /tmp/gridy-m95-schema.yml` — exit 0; fresh schema matches tracked `backend/schema.yml`, includes `/api/v1/auth/public/barangays/` and `/api/v1/auth/platform/accounts/` routes, and contains no DILG route or role enum. drf-spectacular reports **131 warnings (40 unique) and 13 errors (4 unique)** for serializer/authenticator inference and enum naming; these diagnostics were not baseline-compared and remain a documentation-quality risk.
- Active application source scan across backend, frontend, and mobile — no active DILG roles, screens, routes, or labels found. Legacy references remain only in historical migrations/ADRs and regression tests that confirm those identities cannot authenticate or authorize.
- `git diff --check` — clean, exit 0. `git diff --cached --name-only` — empty; no files staged.
- Primary checkout safety check: `/home/dokja/vsc-fedora/all/Projects/django-projects/Gridy` still shows only the same three pre-existing unstaged Login files (`frontend/src/App.tsx`, `frontend/src/pages/auth/Login.test.tsx`, `frontend/src/pages/auth/Login.tsx`); this task did not edit them. No production database or deployment operation occurred.

## Delivery

- Implementation commit: `299cc64` (`feat: restore barangay-only scope and platform recovery`).
- Push: `git push -u origin fix/barangay-only-scope-no-dilg` succeeded; branch tracks `origin/fix/barangay-only-scope-no-dilg`.
- No pull request was opened.

## Decisions / Risks

- Existing DILG_ADMIN database values and historical migration/ADR references must remain available for audit continuity, but the role must not authenticate or authorize active product access.
- Public tenant creation is retired; initial Barangays and first ADMIN accounts remain an operator bootstrap responsibility.
- Legacy pending application rows must remain preserved and inspectable. No automated rejection or deletion will occur.
- Plan correction before code changes: the partner's `application_type` / `existing_barangay` fields have no migration and are not needed once the public official-application flow is retired. Revert those unshipped fields; do not invent a workflow duplicating existing Field Official CRUD.
- `BarangayApplication` storage remains as historical evidence. Superusers may inspect records read-only; active product users cannot create, review, or mutate applications.
- Existing tenant creation and first-ADMIN setup require a protected deployment-operator bootstrap procedure; they are not public applicant actions.
- Current architecture, API, feature, presentation, and recovery documentation is being updated to describe the Barangay-only product boundary; historical ADRs and migrations remain as records and are superseded by ADR 021.
- Final QA also corrected the superuser login redirect ordering, handled nullable user state in `ProtectedRoute`, and aligned the resident registration assertions with the revised Barangay-only copy.
- Hindsight search/list/capture calls were attempted before implementation, but the local service returned `ECONNREFUSED 127.0.0.1:9077`; decisions are grounded in repository docs and code instead.
- The `DILG_ADMIN` label remains in immutable historical migration and ADR text and in negative regression fixtures. Existing stored legacy role values are deliberately not rewritten or deleted; login, refresh, token authentication, application routes, and tenant service authorization reject them.
- The OpenAPI generator's 13 non-fatal serializer inference errors and 131 warnings are recorded above. The generated schema matches the current API, but generator diagnostics need a separately scoped cleanup if a warning-free schema is required.
- Commit `299cc64` contains the verified implementation and is published on its feature branch. No PR has been created.
