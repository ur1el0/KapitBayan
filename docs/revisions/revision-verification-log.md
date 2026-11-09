# Revision Verification Log

**Code baseline:** main merge commit `75cc376d20c76d8b6c250edffaaef061684a15b7` (PR #317)
**Updated:** November 9, 2026
**Scope:** Targeted checks for the code changes associated with the adviser/panel revision matrix. This is engineering verification, not a user study, field trial, penetration test, or production deployment record.

## Historical checks through November 6

| Area | Command | Result |
|---|---|---|
| Web document checklist and admin dashboard | `npx vitest run src/components/accessibility/AccessibleDialogs.test.tsx src/pages/admin/Dashboard.test.tsx` from `frontend/` | **Pass:** 2 test files, 17 tests. |
| Web production build | `npm run build` from `frontend/` | **Pass:** TypeScript build and Vite production build completed. |
| Web lint | `npm run lint` from `frontend/` | **Pass:** Oxlint completed without reported issues. |
| Mobile checklist, notification routing, ticket service, queue, and document screens | `flutter test test/notification_target_test.dart test/queue_service_test.dart test/queue_screen_test.dart test/documents_screen_test.dart` from `mobile/` | **Pass on the earlier revision.** Not rerun after adding the expanded offline snapshots below. |
| Mobile static analysis | `flutter analyze --no-pub` from `mobile/` | **Pass on November 6, 2026:** no issues found after the offline snapshot changes. |
| Backend payment permissions and dashboard empty states | `SECRET_KEY=revision-test-secret-key DEBUG=True KAPITBAYAN_TEST_USE_SQLITE=True uv run --with-requirements requirements.txt --with pytest --with pytest-django --with pytest-cov python -m pytest -q gridy_services/tests/test_payment_proofs.py gridy_services/tests/test_dashboard.py` from `backend/` | **Pass:** 39 tests. Run with Python 3.14/Django 6 in an isolated `uv` environment and SQLite. Django emitted non-failing static-files warnings because this checkout has no built `staticfiles/` directory. This does not validate PostgreSQL row-lock concurrency. |
| Targeted Redmi 12C check | Installed Android `1.0.8` (version code 15) over the previous app without clearing data; the user confirmed the Tagalog tutorial text-size instruction and resident document-requirements checklist both work. | **Passed for those two checks only.** Android OS/build details were not captured. This is not full device, offline, notification-delivery, or compatibility verification. |

These entries describe the November 6 checkout only. They are not the latest verification state.

## Post-merge checks on November 9

| Area | Evidence | Result and limits |
|---|---|---|
| PR and full CI | [PR #317](https://github.com/ur1el0/KapitBayan/pull/317), [merge CI run 42553599566](https://github.com/ur1el0/KapitBayan/actions/runs/42553599566), commit `75cc376d20c76d8b6c250edffaaef061684a15b7` | **Pass:** all listed CI jobs succeeded. Backend: 430 passed, 4 skipped, 41 subtests passed; coverage **91%** (configured gate 75%). PostgreSQL row-lock tests passed for concurrent queue advances and ticket allocation. This verifies those tested cases, not every concurrency or production scenario. |
| Mobile registration evidence patch | [PR #318](https://github.com/ur1el0/KapitBayan/pull/318), branch `codex/mobile-registration-evidence-compression` | **Local verification pass; CI pending:** Flutter analysis and `register_screen_test.dart` plus `auth_service_test.dart` passed (10 tests). Registration photos are resized to 1600×1600 at quality 85 and rejected if still larger than 5 MiB. Not merged or tested on a physical phone. |
| Deployed site and API health | `https://kapitbayan-ph.vercel.app/`, `/api/v1/health/ready/`, and `https://gridy.onrender.com/api/v1/health/ready/` | **Read-only smoke pass at 03:19 UTC:** frontend and proxied API returned HTTP 200; readiness reported database and cache healthy. This does not prove the migration is applied or validate authenticated workflows. The alternate `gridy-backend.onrender.com` host returned 404. |
| TLS/security headers | HTTPS response headers from the deployed frontend/API | HSTS, `X-Frame-Options: DENY`, and `X-Content-Type-Options: nosniff` were observed. No Content-Security-Policy header was present in the checked frontend response. This was a limited header check, not a security assessment. |
| Browser smoke | Playwright Chromium 153.0.8010.12 and Firefox 155.0; login and resident-registration routes; 1365×900 and 390×844 viewports | **Limited pass:** pages returned HTTP 200, rendered their login/registration forms, and document width matched viewport width. No credentials or submissions were used. This does not count as Google Chrome, Edge, real Chrome Android, or authenticated queue/document workflow coverage. |
| Production migration | [Apply run 42553805198](https://github.com/ur1el0/KapitBayan/actions/runs/42553805198), [plan-only run 42553944389](https://github.com/ur1el0/KapitBayan/actions/runs/42553944389) | **Blocked safely:** migration `gridy_services.0021_documentrequest_submission_fingerprint_and_more` remains pending because Barangay 5 has duplicate receipt `123` on requests 33, 37, and 41. The migration reported that it changed no ticket or receipt numbers. Reconcile against official receipts before retrying. |
| Redmi 12C | ADB serial `t4skeyozvwylxocm`; `getprop`, `dumpsys package`, and app launch | **Partial device check:** identified model `22120RN86G`, Android 14/API 34, build `UP1A.231005.007`, security patch `2025-12-01`; installed `com.example.mobile` is version `1.0.9` (version code 17, target SDK 36, min SDK 24). The main activity launched. USB disconnected before screenshot capture or interactive checks; FCM delivery/deep-link, offline snapshots, and registration evidence compression remain unverified. The installed build predates PR #318. GitHub's latest release remains `v1.0.8`; version `1.0.9` is an installed review build, not a published release. |
| Questionnaire archive inventory | `/home/dokja/Downloads/drive-download-20261106T140835Z-1-001.zip` | 26 JPEGs: 16 first-page images and 10 continuation-page images. Opaque filenames do not pair continuation pages to respondents. The earlier age list has 12 entries. The archive does not establish 30 complete resident responses or a reconciled role/age count. Names and handwritten responses were not copied into this log. |
| Automated security alerts | GitHub repository alert endpoints | Dependabot alerts are disabled; GitHub code scanning reports no analysis. This is unavailable evidence, not a clean security result. No authorized penetration test was run. |

## Open evidence and actions

- Reconcile the three duplicate O.R. records against Barangay source receipts; then rerun the production migration plan-only and apply only after it is clean.
- Keep the Redmi connected while unlocked; test the current APK's screens, FCM receipt/deep-link, offline snapshots, and registration image compression. Device/build and installed version have now been recorded, but the USB connection dropped before interactive checks.
- Complete the browser matrix on actual Chrome, Edge, Firefox, and Chrome Android. Test authenticated document and queue workflows with controlled test accounts.
- Arrange a scoped, authorized security assessment. Do not present source review, CI, HTTPS, or response headers as a penetration-test result.
- Reconcile original study responses and age/role counts. If the 30-resident requirement applies, collect an approved additional sample; do not fabricate or relabel responses. Separate platform evaluations/SUS results require new data.
- Complete manuscript revisions, final page count, appendix split, and official matrix signatures after the evidence is reconciled.

## Interpretation

Passing unit and widget tests support the behavior of the tested code paths. They do not establish that the feature was deployed, that an external provider delivered a notification, that a human found the system usable, or that the system passed a penetration test.
