# Revision Verification Log

**Working branch:** `fix/revision-matrix-panel-comments`
**Date:** November 6, 2026
**Scope:** Targeted checks for the code changes associated with the adviser/panel revision matrix. This is engineering verification, not a user study, field trial, penetration test, or production deployment record.

## Checks run in this checkout

| Area | Command | Result |
|---|---|---|
| Web document checklist and admin dashboard | `npx vitest run src/components/accessibility/AccessibleDialogs.test.tsx src/pages/admin/Dashboard.test.tsx` from `frontend/` | **Pass:** 2 test files, 17 tests. |
| Web production build | `npm run build` from `frontend/` | **Pass:** TypeScript build and Vite production build completed. |
| Web lint | `npm run lint` from `frontend/` | **Pass:** Oxlint completed without reported issues. |
| Mobile checklist, notification routing, ticket service, queue, and document screens | `flutter test test/notification_target_test.dart test/queue_service_test.dart test/queue_screen_test.dart test/documents_screen_test.dart` from `mobile/` | **Pass on the earlier revision.** Not rerun after adding the expanded offline snapshots below. |
| Mobile static analysis | `flutter analyze --no-pub` from `mobile/` | **Pass on November 6, 2026:** no issues found after the offline snapshot changes. |
| Backend payment permissions and dashboard empty states | `SECRET_KEY=revision-test-secret-key DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True uv run --with-requirements requirements.txt --with pytest --with pytest-django --with pytest-cov python -m pytest -q gridy_services/tests/test_payment_proofs.py gridy_services/tests/test_dashboard.py` from `backend/` | **Pass:** 39 tests. Run with Python 3.14/Django 6 in an isolated `uv` environment and SQLite. Django emitted non-failing static-files warnings because this checkout has no built `staticfiles/` directory. This does not validate PostgreSQL row-lock concurrency. |
| Targeted Redmi 12C check | Installed Android `1.0.8` (version code 15) over the previous app without clearing data; the user confirmed the Tagalog tutorial text-size instruction and resident document-requirements checklist both work. | **Passed for those two checks only.** Android OS/build details were not captured. This is not full device, offline, notification-delivery, or compatibility verification. |

The CI workflow configures Python 3.12/PostgreSQL-backed backend tests and a 75% minimum backend coverage gate. The local targeted backend run used Python 3.14/SQLite, so CI remains necessary for the project's configured runtime and database. The 75% value is the configured threshold; this log does not claim a measured coverage result or a successful CI run for this revision.

## Checks still required

- The Admin common-requirement selector and paper-certificate QR workflow were added after the checks listed above. No automated tests, production migration, deployment, print, or live scan check has been run for these additions yet.
- The expanded offline snapshots for queue, aid, and issue histories have only passed static analysis so far; no unit/widget tests or airplane-mode/device checks have been run for them.
- Run backend tests under the CI Python 3.12/PostgreSQL configuration, including queue concurrency tests that depend on database row locks.
- Run the full frontend test suite and the full mobile test suite through CI, not just the focused tests above.
- Run full CI and record its URL and actual coverage result.
- Run the FCM notification path on a real Android device and record device model, Android version, build, payload, and observed deep-link destination.
- Run the authorized security assessment requested by the panel and document its scope and findings.
- Record browser/device compatibility results from actual supported browsers and devices.
- Keep new usability/evaluation results separate by web and mobile and retain the original response records.

## Interpretation

Passing unit and widget tests support the behavior of the tested code paths. They do not establish that the feature was deployed, that an external provider delivered a notification, that a human found the system usable, or that the system passed a penetration test.
