# M90 Status: Resident Queue Notification Inbox

## Executive summary
- **State:** Ready for review; PR opened against `main`.
- **Branch:** `fix/resident-queue-notification-inbox`
- **Base:** GitHub `main` at `3caff91fe99bdbd6aa5bce679e7feec9a31a140f`.
- **Primary checkout:** left unchanged at `fix/dilg-account-support-postgres-lock`.
- **Implementation checkout:** isolated copy under `/tmp/gridy-resident-notification-inbox`.

## Milestones
| Milestone | State | Notes |
|---|---|---|
| Persist queue pages and owner-scoped API | Complete | Queue page writes an alert record; resident can read only their own latest 100 alerts. |
| Mobile Notification Center integration | Complete | Dashboard fetches and merges persisted queue alerts into the resident notification list. |
| Email log clarity, verification, and PR | Complete | Email opt-out/missing-address/accepted outcomes are logged without recipient PII; PR opened. |

## Verification log
- Focused backend tests: **8 passed** (`test_queue_notifications.py`, `test_resident_notifications_api.py`).
- Affected communications and services suites before the final API pagination adjustment: **169 passed, 2 skipped**.
- `manage.py check`: **passed**, no issues (local Firebase credentials warning only).
- `manage.py makemigrations --check --dry-run`: **passed**, no model drift.
- `git diff --check`: **passed**.
- Flutter dashboard service tests: **5 passed**.
- `flutter analyze --no-pub`: **passed**, no issues.

## Remaining risks
- The additive migration must be applied to production before the deployed mobile app calls this new endpoint.
- FCM acceptance in Render logs does not prove the OS displayed a notification. The in-app saved alert is independent of push/email settings.
- This change does not guarantee email delivery beyond the configured backend accepting the send.

## Delivery
- No production migration, backend deploy, or APK release was performed.
- Merge and deploy the backend, apply `gridy_communications.0011_residentnotification`, then build/release the mobile app to expose the saved queue alert in the resident Notification Center.
