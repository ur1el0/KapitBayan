# KapitBayan system demo flow

**Audience:** Barangay stakeholders, advisers, and pilot testers

**Suggested duration:** 18–22 minutes
**Companion:** [Printable PDF](system-demo-flow.pdf)

For hands-on barangay training, see the [barangay demo and user-training flow](barangay-demo-and-training-flow.md) ([PDF](barangay-demo-and-training-flow.pdf)).

This guide gives a role-by-role route through the web and mobile system, then shows how to explain account recovery and notification fallbacks. It describes the current implementation and its limits; it is not a claim that every external provider will deliver every message.

## Before the demo

- Confirm the site, API, and mobile APK point to the intended environment and recent release.
- Prepare separate barangay-admin, resident, and field-official demo accounts. Use synthetic residents and service records. Keep any superuser recovery demonstration in a separate operator-only session.
- Keep the resident app signed in on the phone. Pre-grant notification permission only if you plan to demonstrate a real push alert.
- Verify a controlled test email address and the Brevo sender before demonstrating password recovery.
- Open a second browser profile for role switching. Keep passwords, reset links, resident identity documents, and provider secrets off screen.
- Have screenshots or a short recording available as a clearly labelled backup if the network or provider is unavailable.

## Walkthrough at a glance

| Time | Role and area | Show |
| --- | --- | --- |
| 1 min | Opening | Purpose, roles, and the path through the system |
| 2 min | Barangay administrator | Tenant-scoped account support and initial service overview |
| 5 min | Barangay administrator | Resident verification, documents and payments, queue, communications, and notifications |
| 4 min | Resident web | Registration status, self-service requests, bulletin, help, and profile settings |
| 4 min | Resident mobile | Queue, documents, schedules, help, and notification center |
| 2 min | Field official | Queue ticker, clearance validation, and incident reports |
| 2–4 min | Fallbacks and close | Password reset, email checks, push behavior, and offline boundaries |

## 1. Open with the system path

Say: “KapitBayan connects resident self-service with barangay processing. The React web app and Flutter mobile app use the Django API. PostgreSQL stores service records; Cloudinary stores configured media; Brevo sends transactional email; Firebase Cloud Messaging can send mobile push alerts.”

Show the path:

**Barangay processing → resident web/mobile → notification and recovery fallbacks**

State that eligibility, document approval, payment verification, and service decisions remain with authorized staff. Electronic payment references are evidence for manual review; the system does not process payments through a gateway. The mobile app requires a network connection for server-backed workflows and is not fully offline.

## 2. Operator account recovery (optional; outside the barangay user workflow)

KapitBayan does not expose a government-wide oversight dashboard or public Barangay onboarding workflow. Initial tenant and first-administrator setup is performed by an authorized deployment operator. If account recovery must be demonstrated, a Django superuser may use the isolated **Platform Account Support** page to find an eligible account, attest that contact was independently verified, and request a private recovery link. The tool cannot change account roles or Barangay assignments, create/delete accounts, or reveal passwords.

Do not alter a real deployed account or send a recovery email during the demo unless the account owner has asked for it.

## 3. Barangay administrator

Use an account assigned to one demo barangay.

1. **Dashboard and residents:** Show barangay-scoped counts, resident records, and verification review. Registering a resident does not mean the account is verified; an authorized barangay administrator must complete the review before the resident can use protected services.
2. **Documents and treasury controls:** Open a resident request, review it, record an explicit fee or supported waiver, and show the status change. Explain that staff manually verify payment evidence and record the Official Receipt before release where required.
3. **Queue:** Add or select a ticket, advance the queue, show the serving ticket and waiting list, and open the public queue display. Use **Page resident** on a serving ticket to demonstrate a saved in-app alert and the optional email/push attempts.
4. **Communications:** Create or edit an announcement and activity schedule; maintain the hotline directory and FAQs. Show the resident view after publishing. External sharing creates a share link; KapitBayan does not publish a Facebook post automatically.
5. **Other service work:** Open an assistance request or incident report and show that staff record the outcome. The system does not automatically decide aid eligibility or replace an emergency response service.
6. **Notifications:** Show the staff notification center and its read/clear controls. Explain that these are staff alerts, separate from a resident's notification inbox.

## 4. Resident web portal

1. Show the resident registration flow and the verification state. If the account is pending, explain that login remains restricted until an authorized administrator approves it.
2. Submit a document request and show its status. If the request reaches a payment-ready state, explain that payment options and fee details depend on the staff assessment and barangay configuration.
3. Open **Queue** and show the resident ticket and live desk status. Show **Community Bulletin** for announcements and activities, and **Aid** for assistance requests.
4. Open **Help / FAQs** and the **Tutorial**. Both remain available after registration so residents can return when they need guidance, including older users who may need a slower step-by-step walkthrough.
5. Open **Profile** to review account details and the email notification preference. The web portal does not register a phone for Firebase push notifications; push preference and device permission are managed in the mobile app.

## 5. Resident mobile app

1. Sign in as the resident and show the dashboard and current service summaries.
2. Open **Queue** to request a ticket or follow an active ticket. Open **Documents** to review or request a document, and **Schedule** to view community activities and appointments.
3. Show **Announcements**, **Aid**, **Issue Reports**, and **Hotlines** where available in the current build. When a hotline's dial button cannot open the phone app, show the number and dial it manually from the device.
4. Open **Profile → Notification Preferences**. Explain that push alerts require both the in-app preference and the Android permission. Show the resident notification center, which can display a saved queue paging alert even if an operating-system push banner did not appear.
5. Open the FAQ and Tutorial from Help. Use the installed candidate APK when demonstrating notification behavior; an older release may not include current mobile changes.

## 6. Field official mobile workflow

Sign in with the field-official account and show the available tabs:

- **Queue ticker:** View queue status and use the permitted field queue actions.
- **Clearance validator:** Enter a tracking ID and inspect the returned clearance status.
- **Field reports:** Review barangay incident reports and record the supported field update.

Explain that field staff have limited permissions scoped by their barangay. Do not use the platform-operator or barangay-admin account to represent a field role.

## 7. Password reset and email fallback

1. Use **Forgot password** with a test email associated with exactly one account record.
2. Explain that the page intentionally gives a generic success response to avoid revealing whether an email is registered. That response does not confirm that Brevo received or delivered a message.
3. Check the recipient's Inbox and Spam folder. If the message does not arrive, inspect Render application logs and Brevo **Transactional → Email logs**.
4. If the address is wrong or recovery still fails, an authorized platform operator can verify the account holder and request a private setup/reset link through Platform Account Support. The resident must never share the link or password.

The current endpoint may suppress dispatch when the submitted address matches zero or multiple user records. Use a unique test address for the live demonstration. Password-reset requests can also be rate limited; if the API returns HTTP 429, wait before retrying. The notification email preference does not turn password-reset messages on or off.

Brevo is configured as the current Render email provider using its SMTP relay, port 2525, TLS, an SMTP login/key, and a verified sender. Do not display or read any secret during the demo. See the [Brevo setup guide](../walkthrough/brevo-email-setup.md).

## 8. Notification behavior and fallback

When a staff member pages a resident with a currently serving ticket:

1. The backend saves a resident-owned queue alert. The resident can find it in the mobile app's notification center.
2. The backend separately attempts email and FCM push delivery according to the resident's preferences and registered device. These sends run as best-effort background work; a successful web response or an FCM acceptance log does not prove that a handset displayed a banner.
3. In the foreground, the mobile app displays the push message in an in-app banner. In the background, Android notification display also depends on device permission and OS state.

If no push banner appears, open the app's notification center and refresh. Check that push is enabled in Profile, Android permission is allowed, the app has a registered token, and the server and APK use the same Firebase project. An `UnregisteredError` means Firebase invalidated a device token; sign in and enable push again to register a fresh token. A `SenderIdMismatchError` requires the operator to compare the Firebase project used by the server credential with the project used by the APK. If the persistent in-app alert is also missing, check API access and whether the production database has the resident-notification migration.

Residents on the web can use the email preference and in-app queue view, but the web profile does not configure FCM push. Do not describe push or email as guaranteed delivery. If the API or phone network is unavailable, use the barangay desk, public queue display, or official hotline as appropriate; confirm the request status before submitting a second time.

## 9. Close with a clear scope statement

Say: “KapitBayan makes resident service requests, barangay processing, and queue visibility available through a connected web and mobile workflow. Staff retain service decisions, payments are manually verified, and email and push delivery depend on provider and device settings. The demo uses test data and does not replace official barangay channels.”
