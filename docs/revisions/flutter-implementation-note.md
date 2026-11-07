# Flutter Mobile Implementation Note

This note summarizes the checked-in Flutter implementation for the manuscript’s mobile-application section. It describes source code, not results of a device or usability study.

## Structure and navigation

The app separates reusable responsibilities under `mobile/lib/`:

- `core/`: API configuration/client, navigation keys, localization, and theme.
- `models/`: typed representations of residents, documents, queue tickets, activities, and notifications.
- `services/`: REST requests, session handling, secure storage, image selection, hotline dialing, and push registration.
- `screens/`: role-specific pages and resident service pages.
- `widgets/`: reusable forms, cards, summaries, and dialogs.

After authentication, the app selects a portal based on the authenticated role: residents enter the resident dashboard, Field Officials enter the field-operations screen, and Barangay Admins enter the admin dashboard. Screen-to-screen navigation uses Flutter `Navigator` routes; resident tabs replace the current page to keep the primary dashboard/queue/documents/schedule flow direct.

Most screens use Flutter `StatefulWidget` and `setState` for local presentation state. Data access and request logic live in service classes. The project does not use Bloc, Riverpod, or Provider as its main state-management framework.

## API communication

`ApiClient` sends authenticated JSON or multipart requests to the Django REST API under `/api/v1/`. It attaches the access JWT to authenticated requests, handles the refresh-cookie exchange, maps HTTP/network errors, and shares one HTTP implementation across feature services. Screens call services such as `DocumentService`, `QueueService`, `DashboardService`, and `HotlineService` rather than constructing API requests in button callbacks.

Queue and resident notification data refresh through HTTP polling. The queue view attempts refreshes every five seconds while active; this is periodic polling, not a WebSocket or a delivery-time guarantee. See [client refresh behavior](../features/client-refresh-behavior.md).

## Token storage

`StorageService` stores the access token and refresh cookie using `flutter_secure_storage`. It also stores the authenticated user snapshot there so it can render the cached profile at startup. SharedPreferences is used for non-secret preferences such as the selected language and optional saved username. Token refresh writes rotated credentials back through the secure-storage service.

## Image capture and validation

Resident identity registration offers camera and gallery selection. Payment-proof capture offers camera and gallery, resizes the image to at most 2048 × 2048 at quality 85, checks a client-side 5 MiB limit, and the backend independently validates the actual image bytes, supported JPEG/PNG/WEBP format, and 5 MiB limit. Registration currently does not apply the same explicit client-side compression flow; this is a remaining improvement.

## Push notification routing

Firebase Messaging registers a device token after the resident enables push and grants OS permission. The listener handles foreground banners, notification taps, and launch-from-notification events. In this branch, queue notifications carrying `ticket_id` open the matching ticket context, and document notifications carrying `request_id` or `document_request_id` open the matching request detail. The app still depends on successful FCM provider delivery and a valid registered device token; unit/widget tests do not prove end-to-end delivery to a real handset.

## Connectivity and limitations

The app shows retryable states for failed reads and caches the signed-in profile. It also stores encrypted, read-only snapshots of previously fetched announcements, hotlines, and the resident's document, queue, aid, and issue requests. Snapshots are scoped to the signed-in account and Barangay, limited to 100 records per list, expire after 30 days, and are labelled as potentially stale. Announcement and evidence images are not cached, and a cached queue ticket does not include a current queue position. Failed submissions are not queued or replayed; the resident reconnects, checks the relevant request history, and manually retries if needed because a timeout cannot establish whether a write reached the server. Real-device offline verification remains outstanding.

The Android app’s minimum SDK is pinned to API 24 (Android 7.0). iOS is not built in this project. On November 6, 2026, Android `1.0.8` (version code 15) was installed on a Redmi 12C without clearing app data. On November 7, the user confirmed two targeted behaviors on that phone: the Tagalog tutorial includes the text-size instruction, and the resident document-requirements checklist works. The Android OS/build was not captured, and these checks do not establish broad device compatibility, offline behavior, or end-to-end notification delivery.
