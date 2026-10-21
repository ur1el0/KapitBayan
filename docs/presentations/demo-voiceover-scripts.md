# KapitBayan demo voice-over scripts

**Audience:** Barangay administrators, field staff, residents, and reviewers

**Run time:** About 8 minutes for all four scripts; each role can also be shown on its own

**Version:** Follows the current `main` web and mobile flows

Use demo accounts and made-up records. Keep passwords, reset links, identity documents, and real resident details off screen. The cues in brackets are actions for the presenter; read only the quoted lines aloud.

## 1. Resident — web and mobile (about 2½ minutes)

**[Open the resident web portal using an approved demo resident account. Point to the main navigation.]**

“This is the resident portal. From here, residents can request documents, join or check the live queue, read barangay announcements and activities, request assistance, and find FAQs. I’ll open the queue first. A resident can request a ticket and return here to check the serving status.”

**[Show a prepared document request and its status. Open the bulletin or FAQs briefly.]**

“Document requests stay visible with their current status, so residents can check progress without submitting the same request again. Announcements and activities are available here too.”

**[Switch to the resident mobile app. Show Dashboard, Queue, Documents, and Schedule on the bottom navigation; then point out Quick Services and Profile.]**

“The mobile app gives residents the same core services in a phone layout. Dashboard, Queue, Documents, and Schedule are on the bottom bar. Quick Services provides access to other resident services, and Profile contains account and notification settings.”

**[If demonstrating an alert, open the app’s notification center and use a prepared test alert.]**

“Saved alerts can be checked in the app. A phone banner also depends on the resident’s push preference, Android permission, network connection, and a registered device, so the in-app center is the place to check if a banner does not appear.”

**[Optional fallback: show the sign-in recovery link without sending a real reset email.]**

“If a resident forgets a password, they request a reset using the email on the account and follow the secure link in that inbox. The confirmation page protects account privacy; it does not prove that an email was delivered. If the account is still awaiting barangay verification, the resident must wait for that review before using protected services.”

## 2. Barangay Admin — web and mobile (about 2½ minutes)

**[Sign in to the demo Barangay Admin web account. Show Dashboard, then Residents.]**

“The Barangay Admin uses the web workspace for the full service workflow. The dashboard summarizes current activity. In Residents, authorized staff review resident registrations and make the verification decision. Registration alone does not approve an account.”

**[Open a prepared document request, then the live queue. Show the bell and notification center.]**

“Staff review document requests and update their status. Payment references and receipts are checked by staff; the system does not verify a transfer automatically. In the queue, staff can call the next ticket, mark service complete, or page a resident. The bell is where staff can review saved administrative alerts.”

**[Open Communications and point to a prepared announcement or activity.]**

“Communications is where the barangay manages resident-facing announcements and activities. Use a prepared item for this demo so we do not publish test content to real residents.”

**[Switch to the Admin mobile app. Show Executive Console and the available overview tiles.]**

“On mobile, the Admin sees a quick barangay overview and supported operational shortcuts. The web workspace remains the place for the complete resident, document, queue, and communications management tools.”

“Alerts are recorded in the system. Email and phone push are additional delivery attempts and may be delayed or unavailable, so staff should check the notification center and follow the barangay’s normal contact process for urgent matters.”

## 3. Field Staff — mobile (about 1½ minutes)

**[Sign in with a prepared Field Official account and show the three tabs.]**

“Field Staff sign in with their own Barangay-issued account. This mobile workspace is focused on field tasks: Queue Ticker, Verify Clearance, and Field Reports.”

**[Open Queue Ticker and show a prepared queue state. Do not advance or cancel a live ticket.]**

“Queue Ticker helps staff follow the current queue and serve residents in order. For this demo, I’m showing a prepared record and will not change a live queue.”

**[Open Verify Clearance and show where a tracking ID is entered. Do not display a real resident record.]**

“For a clearance check, staff enter the request’s tracking information and review the returned status before advising the resident.”

**[Open Field Reports and show the prepared list.]**

“Field Reports gives staff a view of reports assigned to their Barangay. These tools require a network connection to load current records. If a screen cannot load, check the connection and retry rather than assuming the action was saved.”

## 4. Barangay Operator — web (about 1½ minutes)

**[Sign in with the prepared Barangay Operator reviewer account. Open Barangay onboarding review and select a prepared application.]**

“The Barangay Operator reviews requests for a Barangay’s first Admin account. This is an onboarding and verification role, not the account that handles residents’ daily services.”

**[Show the locality and applicant details, verified-email state, and authority evidence controls. Use synthetic information only.]**

“Before approval, the reviewer checks the submitted locality and official details, confirms ownership of the official email, inspects the authority document, and independently verifies the applicant and Barangay through an official channel. The uploaded document supports the review; it does not replace independent verification.”

**[Point to the review checklist and approve/reject controls without submitting the demo application.]**

“When the checks are complete, approval activates the applicant’s existing Admin account for that Barangay. If the request cannot be verified, the reviewer rejects it with a recorded reason. The Barangay Admin then manages the Barangay’s staff accounts and service work. Operator access does not include resident service records or Barangay analytics.”

## Short closing

“That is the main path through KapitBayan: residents submit and track requests, Barangay staff review and process them, Field Staff handle their assigned mobile tasks, and the Operator verifies new Barangay onboarding. Human staff remain responsible for identity checks, eligibility, payment review, and service decisions.”

## Presenter fallback card

- **Password reset:** Use a demo email account. The page always gives a privacy-preserving confirmation; check the inbox and spam folder for delivery. Brevo delivery depends on the configured sender and service availability.
- **Missing notification banner:** Check the saved in-app notification first. Then check the recipient’s preference, Android notification permission, network, and device registration. Treat email and push as best-effort channels.
- **Pending resident account:** Show the pending state and explain that Barangay review is required. Do not make a second account to bypass it.
- **Network or provider issue:** Use a clearly labelled screenshot or recording. Do not claim an email or push was delivered unless it is visible on the recipient’s device or in the provider record.
- **Public kiosk:** Do not present kiosk access as available unless that feature has been merged and deployed in the environment being demonstrated.
