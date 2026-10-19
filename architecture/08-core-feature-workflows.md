# Core Service Workflows

This page summarizes current workflow boundaries. Exact transition rules live in the relevant backend services, models, serializers, and regression tests.

## New Barangay onboarding

An official submits a public application with the Barangay locality, official contact details, official email, and a password they choose. The applicant does not create a username. Submission creates an inactive, unassigned Admin account and a pending application, but no tenant or service access. An active DILG reviewer (or controlled Django superuser) independently verifies the official and locality, then approves or rejects the application with an audit record. Approval creates or matches the Barangay and activates the same applicant account; the official signs in using their email and chosen password. Historical applications without a linked applicant account retain their prior setup-email flow. Barangay Admins can provision and manage Field Officials in their own Barangay using email sign-in without choosing usernames; only Residents choose usernames. Admins cannot create or list other Admin accounts. See [ADR 023](decisions/023-dilg-reviewed-barangay-admin-registration.md).

## Document request and treasury workflow

1. A resident submits a request, or authorized staff records an in-person walk-in without creating a synthetic resident account.
2. Staff in the request's barangay review the application and record an explicit fee assessment or supported waiver. `PROCESSING` is not a payment-ready state.
3. Once the request is `READY_FOR_PICKUP`, payment may be recorded through the approved manual workflow. Electronic references and uploaded receipts are evidence for staff review, not proof of settlement.
4. Staff verifies payment against the barangay's actual account and records the Official Receipt. A positive-fee document cannot be released without the required payment verification and O.R. controls. Cash and statutory-waiver cases follow their documented paths.
5. The resident follows status and retrieves authorized documents through the API. Private evidence is served through authenticated media endpoints.

See [ADR 007](decisions/007-revenue-and-official-receipt-auditing.md), [ADR 017](decisions/017-manual-epayment-evidence-and-verification.md), and [ADR 018](decisions/018-explicit-document-fee-assessment-and-waiver-provenance.md).

## Queue workflow

Residents and walk-in visitors can receive tickets under the applicable service rules. Staff advances tickets within their barangay. Resident and public displays refresh from HTTP endpoints; the documented queue path is polling, not WebSocket delivery. Queue ticket ownership and live desk status are separate data concerns and clients handle partial failures independently.

## Communications and announcements

Authorized staff publish barangay announcements and activities. Residents can read public content, and staff can share an announcement link externally using the share kit. KapitBayan does not automatically publish Facebook posts or control comments on Facebook.

## Assistance and reports

Residents submit assistance applications and issue reports. Authorized staff review and update records within the applicable barangay scope. The platform records staff decisions; it does not autonomously determine aid eligibility or replace emergency response. For immediate danger, use official emergency channels.
