# Post-defense service and account controls

This guide describes the controls added after the defense feedback. It complements the feature-specific implementation and tests; it does not replace Barangay staff review or identity checks.

## Resident notifications

- The Admin dashboard highlights the unread notification count and links to the notification center. The shared Admin layout refreshes the count every five seconds and broadcasts updates to the dashboard.
- The resident web portal places the newest unread queue or document update above the page content and checks for new notices every 15 seconds while the tab is visible. Residents can open the relevant queue/documents page or dismiss the notice.
- Document status changes create a persistent in-app notice. Mobile reads the saved read state: unread notices use a gray card and a “New” label, and opening one marks it read through the resident-notifications API. Locally synthesized announcement/document summaries have no persisted read state. Mobile notifications can be refreshed by pulling to refresh. Push delivery remains dependent on device permission and Firebase configuration.

## Queue tickets

A document request can have only one active counter ticket while its ticket is `WAITING` or `SERVING`. The API/database guard is authoritative; the web portal also disables the ticket action while one is active. A new ticket is available after the prior ticket leaves those active states. This does not prevent a resident from creating a separate document request. Queue number allocation is serialized per Barangay and Manila business day, and a database uniqueness constraint is the final duplicate guard. The concurrent queue tests run only on database backends that support `SELECT FOR UPDATE`, so SQLite alone is not evidence of production concurrency behavior.

## O.R. number PDF

Every document request receives a stable KapitBayan lookup reference such as `KB-DOC-00000050`. Residents can give this reference to Barangay staff, and Field Officials can use it in the validator to find the same-Barangay record. It is an internal request reference, not an O.R. and not proof of payment.

The download is an O.R.-number slip, not the requested certificate or clearance. It is available only after the request is `RELEASED` and staff have recorded an O.R. number. It contains the O.R. label and value only, and is served as private, non-cacheable content. The Barangay Admin records the number printed on the real Barangay-issued receipt; KapitBayan must not fabricate or automatically assign an official treasury receipt number. A Barangay still issues the actual paper or digital document through its own process.

## Document requirements

The Admin document catalog offers common requirement checkboxes and a custom text area for local additions. Admins select only the items that apply to each particular document service; the preset choices do not imply that every document has the same requirements. Custom requirements already saved on an offering remain in the custom field when it is edited. Each offering saves its own list, and a request snapshots the list at submission, so a later catalog edit does not rewrite an earlier resident request.

Resident web and mobile show the published items as a checklist for preparing to visit the Barangay. Checking an item is local to the form and does not upload a file or attest that staff reviewed the physical evidence.

## Paper certificate QR verification

The Barangay issues and signs its own paper certificate. After a document request is marked `RELEASED`, a Barangay Admin may affirm that the paper was physically issued, create a separate QR label, print it, and attach it. The public scan page confirms the active issuance record using only the Barangay name, certificate type, issue date, and validity. It reveals no resident name, O.R. number, address, or request ID. A QR is not the certificate itself and does not establish the holder's identity or prove that the paper has not been altered. Admins can revoke a label; a revoked or unknown code returns the same generic invalid result. The implementation is in this branch and is not live until its migration and deployment are complete.

## Payment and fee review

Only Barangay Admin accounts can verify electronic payment references, assess or waive fees, or record an O.R. number. Field Officials may continue service-processing steps, but the API rejects financial-review fields from their document updates. The current role model has no separate Treasurer role, so the Barangay Admin is the authorized reviewer. The API permission dispatch explicitly applies this restriction to the payment-review action, and fee/O.R. fields are rejected if sent through the general document-validation action.

## Resident Barangay transfer

Residents with a verified account can ask to move their account to another active, approved Barangay. Only an Admin assigned to the destination Barangay can review it. Approval requires the Admin to affirm that identity and residence were independently checked through an official channel. A resident cannot submit a transfer request while a document request is pending, processing, or ready for pickup, or while a queue ticket is waiting or serving. Approval checks again in case new work was created after the request. The resident must finish or cancel that work first; completed historical service records remain assigned to the originating Barangay. New document and queue submissions use the same Barangay-then-account lock order as transfer approval so a request cannot slip into the old Barangay during a transfer.

Resident web and mobile document submissions send an `Idempotency-Key` UUID. Retrying the exact same request with the same key returns the original request, while reusing a key for changed details returns a conflict. While the request form remains open, clients keep the key for retries and generate a new one when the request changes. The key is not persisted across app/browser restarts. Older clients that do not send this header remain supported but do not get this retry deduplication guarantee.

The migration adds database uniqueness guards for O.R. numbers within a Barangay and queue numbers within a Barangay's Manila calendar day. It backfills tenant/day values where they can be recovered from request records, approved transfer history, and linked tickets. If historical records have no recoverable Barangay or contain duplicate identifiers, migration stops with example record IDs; reconcile them explicitly before retrying. It never silently renumbers a historic receipt or ticket.

## Minor registration

The backend rejects future birth dates, requires an under-18 applicant to link an active, verified resident guardian who is at least 18 and assigned to the same Barangay, and rejects a guardian link for adults. Minor registrations also require a stated relationship and a supporting image of up to 5 MiB. The web and mobile registration screens collect these fields; the adult account link confirms only that the linked account belongs to an eligible resident, not that the person has legal authority over the child.

Before approval, the Barangay Admin reviews the linked guardian's resident account, its current eligibility, the stated relationship, and the private supporting image in the existing resident verification dossier. The web and mobile review show the guardian's name and username plus whether the linked account is currently active, verified, adult, and registered in the same Barangay. The approval API rechecks those account conditions at approval time and refuses to verify the minor if they no longer hold or if the Admin has not submitted the explicit evidence-review attestation. On approval, it records the reviewing Admin and timestamp and adds the review to the audit trail. The attestation records that evidence was reviewed under the Barangay's procedure; it does not certify legal guardianship. The authenticated private-media API allows access only to an Admin assigned to the same Barangay; residents, Field Officials, and other Barangays cannot fetch the guardian evidence. The legacy `/media/` route also blocks `resident_guardianship/` files so it cannot bypass that authorization when filesystem media is served.

To keep the staff workload proportionate, this check is part of the existing pending-resident review: only applicants under 18 need the additional attestation, and the Admin reviews the guardian details and evidence in the same resident dossier before approving. It does not create a second approval queue or require another platform-level reviewer.

Evidence should match the claimed relationship and be checked through the Barangay's approved review process. A birth record may support a parent-child relationship; a court-appointed or other non-parent guardian may need an applicable court order or other recognized authority. These examples are not a universal legal checklist, and the system does not make a legal determination. Do not treat an uploaded ID or matching Barangay account alone as proof of guardianship. Because the file contains a minor's personal information, give a clear purpose and retention notice, restrict access, and define when it should be deleted with the Barangay privacy/legal officer. See the [Data Privacy Act](https://privacy.gov.ph/data-privacy-act/) and Supreme Court decisions discussing parental authority and the [Rule on Guardianship of Minors](https://lawphil.net/judjuris/juri2007/aug2007/gr_162421_2007.html).

## Sign-in history

Successful sign-ins record a timestamp, user agent, and an optional syntactically valid IP value. Login history is retained for 90 days; the API excludes older events, and the `cleanup_login_events` management command permanently deletes them. A scheduled GitHub Actions workflow runs that command daily against the production database after the login-event migration has been applied. The API returns an authenticated account's own history. A Barangay Admin can also see sign-ins for Field Officials assigned to that same Barangay; the Admin settings page displays this scoped history. The endpoint returns at most the latest 100 events. It does not record failed login attempts, GPS coordinates, or a verified physical location.

The forwarded IP header is only meaningful if the deployed ingress overwrites it. Configure and review that proxy behavior before treating an IP as a security signal; users may share networks, use VPNs, or appear behind hosting proxies. Apply a retention policy and restrict database access in the deployment environment.
