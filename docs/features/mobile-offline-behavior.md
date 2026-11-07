# Resident mobile offline behavior

## Available offline

When a server request fails because the device cannot connect, the resident app can show saved copies of:

- Announcement text that was fetched before. Remote announcement images are not downloaded.
- Barangay hotline records that were fetched before. If none are available, the app labels its built-in national emergency numbers as a fallback and does not invent a Barangay contact.
- The resident's own document requests, queue tickets, aid requests, and issue reports. Up to 100 records per list are retained. Queue snapshots show the resident's ticket but cannot show a current queue position.

These are read-only snapshots in Flutter Secure Storage. The cache is bound to the signed-in user ID and current Barangay ID, is ignored after 30 days, and is cleared on logout or when a different account/Barangay is saved. The UI labels saved data as possibly out of date. Local images and payment evidence are not cached.

## Submissions and retry

Offline submissions are not accepted as submitted, queued for later, or automatically replayed. Document, queue, aid, and issue forms remain available after a network failure. If the request times out, the app cannot know whether the server committed it, so it tells the resident to reconnect and check the corresponding request/ticket history before manually trying again. This avoids implying a successful submission and reduces accidental duplicates without silently resending a write.

The application does not yet provide a durable offline outbox, server idempotency keys for all create operations, or conflict resolution. Manual retry is the available fallback; it requires the resident to reconnect and check the saved/current history first. Offline behavior still needs device testing. Do not advertise full offline submission support.

## Web and mobile platform choice

Revision-matrix item 26 says “responsive or a PWA.” The resident web portal follows the responsive-web option; Flutter remains the installed Android client for residents and officials. A PWA would add a second install/offline layer to the existing web client and needs separate cache/auth/privacy work. It is not needed to satisfy the matrix's alternative wording. Browser compatibility results for Chrome, Edge, Firefox, and mobile Chrome are still required before closing the item.
