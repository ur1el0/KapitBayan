# M90: Resident Queue Notification Inbox

## Metadata
- **Task ID:** `m90-resident-queue-notification-inbox`
- **Task type:** Bug fix / focused feature
- **Components:** Django REST API and Flutter resident app
- **Branch:** `fix/resident-notification-inbox`
- **Base:** GitHub `main` at `3caff91fe99bdbd6aa5bce679e7feec9a31a140f`

## Goal
Persist queue paging alerts for the resident and show them in the mobile app's existing Notification Center so a resident can still see the page after the brief push banner is missed.

## Non-goals
- Change Firebase project credentials, Android notification permission policy, or email provider configuration.
- Add notification delivery guarantees or a new background-job service.
- Build a general-purpose notification center for every event or add a web-resident UI.
- Modify production data, run a production migration, deploy, or publish an APK.

## Current behavior and evidence
- Render logs show FCM accepted messages for project `device-streaming-aca41bd3`; they do not prove Android displayed a banner or identify which registered device received it.
- `backend/gridy_services/views/queue.py` schedules push/email delivery after a serving ticket is paged, but creates no resident-owned notification record.
- `mobile/lib/services/dashboard_service.dart` synthesizes the existing resident notification list only from announcements and document request status. Queue paging is therefore absent from the in-app list.
- `backend/gridy_communications/services.py` skips email without a log when the resident has disabled email alerts or has no email address. The task also does not log an accepted email send.

## Acceptance criteria
1. Paging a resident's currently serving queue ticket creates a persistent notification associated only with that resident, with ticket context and instructions to proceed to the counter.
2. The authenticated resident API can list only that user's notifications; notification writes cannot be used to create arbitrary messages or access another user's records.
3. The mobile dashboard includes recent queue paging records in its existing notification list, sorted newest first, and displays their queue context.
4. Notification delivery logs distinguish opted-out/missing-address email from accepted email delivery without logging addresses or tokens.
5. Backend API tests cover persistence, owner isolation, and that failed paging validations do not create notifications. Mobile tests cover mapping and inclusion of queue alerts.
6. A reversible migration is included. It is not applied to production as part of this PR.

## Rules and risks
- Preserve barangay authorization on queue paging and owner-scope notification reads.
- Follow ADR 009: continue using the existing `@async_task` helper; do not add Celery or Redis.
- Production backend migration must be applied before the updated mobile build relies on this endpoint.
