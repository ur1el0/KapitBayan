# Core Service Workflows

This page summarizes current workflow boundaries. Exact transition rules live in the relevant backend services, models, serializers, and regression tests.

## New Barangay onboarding

An official submits a public application with the Barangay locality, official contact details, official email, and a password they choose. The applicant does not create a username. Submission creates an inactive, unassigned Admin account and a pending application, but no tenant or service access. An active Barangay Operator (or controlled Django superuser) independently verifies the official and locality, then approves or rejects the application with an audit record. Approval creates or matches the Barangay and activates the same applicant account; the official signs in using their email and chosen password. Historical applications without a linked applicant account retain their prior setup-email flow. Barangay Admins can provision and manage Field Officials in their own Barangay using email sign-in without choosing usernames; only Residents choose usernames. Admins cannot create or list other Admin accounts. See [ADR 025](decisions/025-barangay-operator-onboarding-and-account-support.md).

## Document request and treasury workflow

1. A resident submits a request, or authorized staff records an in-person walk-in without creating a synthetic resident account.
2. Staff in the request's barangay review the application and record an explicit fee assessment or supported waiver. `PROCESSING` is not a payment-ready state.
3. Once the request is `READY_FOR_PICKUP`, payment may be recorded through the approved manual workflow. Electronic references and uploaded receipts are evidence for staff review, not proof of settlement.
4. Staff verifies payment against the barangay's actual account and records the Official Receipt. A positive-fee document cannot be released without the required payment verification and O.R. controls. Cash and statutory-waiver cases follow their documented paths.
5. The resident follows status and retrieves authorized documents through the API. Private evidence is served through authenticated media endpoints.

See [ADR 007](decisions/007-revenue-and-official-receipt-auditing.md), [ADR 017](decisions/017-manual-epayment-evidence-and-verification.md), and [ADR 018](decisions/018-explicit-document-fee-assessment-and-waiver-provenance.md).

Residents may optionally get a counter queue ticket from one of their document requests when they need an in-person Barangay visit. The ticket records the related request so staff can identify the visit's purpose; the ticket can be completed independently and does not approve, pay, or release the document. A document request can proceed without a queue ticket, and tickets for other services remain independent. A request can have only one waiting or serving linked ticket at a time; a later visit can get a new ticket after the earlier one is completed or cancelled.

Each Barangay Admin manages that Barangay's document-service catalog from the Admin web document-request page or the mobile Admin document-request screen. For every offered document, the Admin can save and later edit its name, requirements, published amount, and additional details, or deactivate it. Saving an active service makes its current information available in resident web and mobile request forms. Catalog entries are tenant-scoped; residents only see active offerings for their own Barangay. There are no assumed universal requirements or fees.

When a resident submits a request from a catalog entry, KapitBayan stores a snapshot of the published requirements, amount, and details with the request. Later catalog edits apply to future requests and do not change what an existing request showed when it was filed. “Other / Not listed” remains available for services that are not yet in the catalog; staff must confirm their requirements and fee. The published amount is informational; staff still assess and record the final request fee through the existing treasury workflow.

## Queue workflow

Residents and walk-in visitors can receive tickets under the applicable service rules. A resident may create a ticket from a document request to record a planned counter visit; general tickets remain available for other services. Staff can see the linked request reference in the queue list. Staff advances tickets within their barangay. Queue ticket status and document processing/payment status remain separate. Resident and public displays refresh from HTTP endpoints; the documented queue path is polling, not WebSocket delivery. Queue ticket ownership and live desk status are separate data concerns and clients handle partial failures independently.

## Communications and announcements

Authorized staff publish barangay announcements and activities. Residents can read public content, and staff can share an announcement link externally using the share kit. KapitBayan does not automatically publish Facebook posts or control comments on Facebook.

## Assistance and reports

Residents submit assistance applications and issue reports. Authorized staff review and update records within the applicable barangay scope. The platform records staff decisions; it does not autonomously determine aid eligibility or replace emergency response. For immediate danger, use official emergency channels.
