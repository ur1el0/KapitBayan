# Core Service Workflows

This page summarizes current workflow boundaries. Exact transition rules live in the relevant backend services, models, serializers, and regression tests.

## New Barangay onboarding

An official submits a public application with the Barangay locality and proposed Admin details. The request remains pending and creates no account or tenant. An active Django superuser independently verifies the official and locality, then approves or rejects the application with an audit record. Approval provisions the Barangay and its Admin with no usable password, then requests a private Set Password email. Barangay Admins can provision and manage Field Officials in their own Barangay; they cannot create or list other Admin accounts. See [ADR 022](decisions/022-reviewed-new-barangay-onboarding.md).

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
