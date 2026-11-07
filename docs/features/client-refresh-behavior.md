# Client Refresh Behavior

KapitBayan currently uses authenticated HTTP requests on a timer for live queue and notification updates. It does not use WebSockets or Server-Sent Events. The intervals below describe how often an active client attempts a refresh; they are not delivery-time guarantees. Network latency, request failures, background-tab throttling, and the backend's 35-second mobile request timeout can make an update appear later.

| Client view | Refresh interval | Notes |
| --- | ---: | --- |
| Admin document requests | 3 seconds | Refreshes while the tab is visible and on window focus/visibility return. |
| Admin residents and pending verification count | 3 seconds | Refreshes while visible and on focus/visibility return. |
| Admin live queue | 3 seconds | Polls the tickets API. |
| Resident web queue | 5 seconds | Reads queue tickets and live desk status. |
| Resident mobile queue | 5 seconds | Refreshes queue state while the queue screen is active. |
| Public “Now Serving” display | 5 seconds | Uses the public queue-status endpoint; audio announcement requires a user gesture and supported browser audio. |
| Admin unread notification count | 5 seconds | Also refreshes on in-app notification-change events and tab visibility. |
| Resident web notification center | 5 seconds | Refreshes while the notifications page is open. |
| Resident web top notification banner | 15 seconds | Checks for the latest unread queue or document notice while visible. |

The dashboard summary and activities load when the Admin dashboard opens and on user retry; they do not use the queue timer. Persistent in-app notifications are stored by the backend. Email and FCM delivery are separate best-effort provider calls and are not proven by a successful API response. See the [FCM setup guide](../walkthrough/firebase_fcm_setup.md) and [async task limits](../walkthrough/async_tasks_setup.md).

## Queue concurrency

Queue number allocation and advancing the next ticket run in database transactions and lock the Barangay row before reading or changing queue state. This serializes concurrent staff operations for the same Barangay. The implementation does not use `skip_locked=True`; instead it waits on the shared Barangay lock so another worker cannot skip the first waiting ticket. Concurrency tests are guarded by the database `has_select_for_update` feature and must be run against PostgreSQL to exercise row locking. SQLite test runs skip those database-lock tests and cannot prove production concurrency behavior.

## Manuscript wording

Describe these updates as periodic polling with a three- or five-second client interval, depending on the screen. Do not call the app push- or WebSocket-driven for queue state, and do not claim a guaranteed three-second end-to-end update.
