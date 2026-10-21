# Public Barangay kiosk operations

The public kiosk provides a shared, account-free path for residents who need to make a walk-in service request at the Barangay hall. Open the web app at `/kiosk` on a Barangay-managed device.

## Resident flow

1. Select the approved Barangay serving the resident.
2. Choose **Queue**, **Documents**, or **Report an Issue**.
3. Enter only the fields needed for that service:
   - Queue: name and service type.
   - Document: name, optional purok/zone, document type, and purpose.
   - Issue report: category, title, description, location, and optional name.
4. Read and acknowledge the privacy notice, then submit. The kiosk shows a reference number and clears personal form entries.
5. A resident who needs an account can scan the QR code and continue registration on their own phone. The kiosk does not handle passwords or identity-document uploads.

The screen returns to a clean form after two minutes without activity. Residents should not leave the device while their information is visible. The kiosk does not display existing queue, document, report, resident, or account records.

## Barangay staff flow

- Queue tickets appear in the Barangay queue as regular waiting walk-ins.
- Document requests appear as pending walk-ins. Staff review the request and assess any applicable fee through the normal document workflow.
- Issue reports appear in the assigned Barangay's report list as pending, with minor urgency. Staff triage them through the normal report workflow.
- The Barangay Admin notification center receives an in-app alert for each new kiosk submission.

Each submission is stored with its Barangay, the kiosk privacy-notice version (`kiosk-v1`), and the acknowledgement timestamp. The API returns a ticket or request reference only. Public requests cannot set status, priority, urgency, or fee decisions and cannot retrieve or modify a submission.

## Language and accessibility

Residents can switch between English and Filipino using the language selector. The selection is saved on that browser/device. Current Filipino copy is a draft; have a fluent Filipino speaker and local Barangay staff review the wording before public use. Offer staff assistance without asking residents to disclose passwords, reset links, or identity documents aloud.

## Device and network setup

- Use a Barangay-owned or Barangay-managed device in a supervised area. Keep it in browser kiosk mode and prevent access to other websites, browser settings, saved passwords, downloads, and developer tools.
- Use a dedicated browser profile without a staff account signed in. The kiosk screen itself does not send browser credentials with public intake requests.
- Keep the device updated, use a trusted network, and physically secure it. Provide a staff member who can help users and check for abandoned sessions.
- The API applies a PostgreSQL-backed limit of 20 intake requests per hour per client IP. This is an application abuse control, not DDoS protection. People sharing a network may share the same limit; adjust only after observing pilot usage.
- Do not use the public kiosk for account approval, payment verification, emergency dispatch, or handling identity documents. Continue those steps through the established Barangay process.

The privacy notice is stored as consent evidence, but it does not set a Barangay retention schedule or replace the Barangay's approved privacy notice and operating policy. Confirm the notice, lawful purpose, retention, and access process with the responsible data-protection officer before public deployment.
