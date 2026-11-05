# Post-defense service and account controls

This guide describes the controls added after the defense feedback. It complements the feature-specific implementation and tests; it does not replace Barangay staff review or identity checks.

## Resident notifications

- The Admin dashboard highlights the unread notification count and links to the notification center. The shared Admin layout refreshes the count every five seconds and broadcasts updates to the dashboard.
- The resident web portal places the newest unread queue or document update above the page content and checks for new notices every 15 seconds while the tab is visible. Residents can open the relevant queue/documents page or dismiss the notice.
- Document status changes create a persistent in-app notice. Mobile reads the saved read state: unread notices use a gray card and a “New” label, and opening one marks it read through the resident-notifications API. Locally synthesized announcement/document summaries have no persisted read state. Mobile notifications can be refreshed by pulling to refresh. Push delivery remains dependent on device permission and Firebase configuration.

## Queue tickets

A document request can have only one active counter ticket while its ticket is `WAITING` or `SERVING`. The API/database guard is authoritative; the web portal also disables the ticket action while one is active. A new ticket is available after the prior ticket leaves those active states. This does not prevent a resident from creating a separate document request.

## O.R. number PDF

The download is an O.R.-number slip, not the requested certificate or clearance. It is available only after the request is `RELEASED` and staff have recorded an O.R. number. It contains the O.R. label and value only, and is served as private, non-cacheable content. A Barangay still issues the actual paper or digital document through its own process.

## Resident Barangay transfer

Residents with a verified account can ask to move their account to another active, approved Barangay. Only an Admin assigned to the destination Barangay can review it. Approval requires the Admin to affirm that identity and residence were independently checked through an official channel. KapitBayan does not automatically verify a move or transfer the resident's old service records into the new Barangay: existing document and queue records stay assigned to the originating Barangay.

## Minor registration

The backend rejects future birth dates, requires an under-18 applicant to link an active, verified resident guardian who is at least 18 and assigned to the same Barangay, and rejects a guardian link for adults. Minor registrations also require a stated relationship and a supporting image of up to 5 MiB. The web and mobile registration screens collect these fields; the adult account link confirms only that the linked account belongs to an eligible resident, not that the person has legal authority over the child.

Before approval, the Barangay Admin reviews the linked guardian's resident account, its current eligibility, the stated relationship, and the private supporting image in the existing resident verification dossier. The web and mobile review show the guardian's name and username plus whether the linked account is currently active, verified, adult, and registered in the same Barangay. The approval API rechecks those account conditions at approval time and refuses to verify the minor if they no longer hold or if the Admin has not submitted the explicit evidence-review attestation. On approval, it records the reviewing Admin and timestamp and adds the review to the audit trail. The attestation records that evidence was reviewed under the Barangay's procedure; it does not certify legal guardianship. The authenticated private-media API allows access only to an Admin assigned to the same Barangay; residents, Field Officials, and other Barangays cannot fetch the guardian evidence. The legacy `/media/` route also blocks `resident_guardianship/` files so it cannot bypass that authorization when filesystem media is served.

To keep the staff workload proportionate, this check is part of the existing pending-resident review: only applicants under 18 need the additional attestation, and the Admin reviews the guardian details and evidence in the same resident dossier before approving. It does not create a second approval queue or require another platform-level reviewer.

Evidence should match the claimed relationship and be checked through the Barangay's approved review process. A birth record may support a parent-child relationship; a court-appointed or other non-parent guardian may need an applicable court order or other recognized authority. These examples are not a universal legal checklist, and the system does not make a legal determination. Do not treat an uploaded ID or matching Barangay account alone as proof of guardianship. Because the file contains a minor's personal information, give a clear purpose and retention notice, restrict access, and define when it should be deleted with the Barangay privacy/legal officer. See the [Data Privacy Act](https://privacy.gov.ph/data-privacy-act/) and Supreme Court decisions discussing parental authority and the [Rule on Guardianship of Minors](https://lawphil.net/judjuris/juri2007/aug2007/gr_162421_2007.html).

## Sign-in history

Successful sign-ins record a timestamp, user agent, and an optional syntactically valid IP value. Login history is retained for 90 days; the API excludes older events, and the `cleanup_login_events` management command permanently deletes them. A scheduled GitHub Actions workflow runs that command daily against the production database after the login-event migration has been applied. The API returns an authenticated account's own history. A Barangay Admin can also see sign-ins for Field Officials assigned to that same Barangay; the Admin settings page displays this scoped history. The endpoint returns at most the latest 100 events. It does not record failed login attempts, GPS coordinates, or a verified physical location.

The forwarded IP header is only meaningful if the deployed ingress overwrites it. Configure and review that proxy behavior before treating an IP as a security signal; users may share networks, use VPNs, or appear behind hosting proxies. Apply a retention policy and restrict database access in the deployment environment.
