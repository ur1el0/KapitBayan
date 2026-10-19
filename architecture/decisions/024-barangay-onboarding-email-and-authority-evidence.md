# ADR 024: Email Verification and Private Authority Evidence for Barangay Onboarding

> The reviewer identity in this decision is superseded by [ADR 025](025-barangay-operator-onboarding-and-account-support.md). The email-verification, proof-security, and approval safeguards below remain active.

- **Status:** Accepted
- **Date:** 2026-10-19
- **Extends:** [ADR 023](023-dilg-reviewed-barangay-admin-registration.md)

## Context

ADR 023 requires DILG to independently verify the Barangay and proposed first Admin. The public form's attestation and typed contact details do not establish control of the submitted email or give reviewers a document to assess. The onboarding flow needs evidence and email confirmation without collecting resident identity records or turning the public form into an approval mechanism.

## Decision

1. New applications include one authority-supporting document in PDF, JPEG, or PNG format, limited to 5 MiB. The API checks the content signature, assigns an opaque storage name, and stores the file under private media controls. The form tells applicants to use an appointment, designation, authorization, or Barangay endorsement and not to upload a government ID or resident record.
2. Submission sends an expiring email verification link using the configured Django email backend. The token is tied to the pending applicant, application email, and latest send time; it is not stored. The token is carried in a URL fragment and posted only after the applicant selects Verify Email. A GET does not verify an account, protecting against email link scanners. Resend responses are generic, shared-database throttled, and limited to one send per application every ten minutes.
3. Email verification proves control of the mailbox only. It does not approve an application, establish public-office authority, activate the account, or create/select a Barangay tenant.
4. New linked applicant accounts may be approved only if the official email is verified, proof is still attached, the reviewer attests to reviewing the proof, and the reviewer independently verifies the applicant and locality through an official channel. Backend checks enforce these conditions in addition to the DILG/superuser permission boundary. Existing accountless historical applications keep the ADR 023 setup-link fallback.
5. A reviewer-only API streams a pending proof download with attachment disposition, `private, no-store`, `nosniff`, and no direct storage URL. Public media serving blocks the onboarding evidence directory. Only active DILG reviewers and controlled Django superusers can access it.
6. Evidence is retained only while a request is pending. Approval or rejection clears its database reference and creates an encrypted, retryable cleanup record in the same transaction; storage deletion runs after commit. The application, reviewer, verification timestamp, decision, and review attestation remain for audit. Cleanup uses the existing Django database process and adds no external queue.
7. Existing pending linked applications created before this change have no verified email or proof. They cannot be approved under the new checks; the reviewer should reject them with a reason explaining that the official must submit a new application with the required verification and document.

## Consequences

- DILG still performs the legitimacy decision. Email verification and uploaded proof are supporting controls, not automatic approval.
- Brevo or the configured email backend must accept the verification message. The public response confirms application receipt, not successful delivery; delivery remains best-effort under ADR 009.
- The private proof endpoint is limited to reviewers and its response is not cacheable. The proof is deleted after the decision; the review attestation remains.
- Schema changes are additive and preserve existing applications. The migration must pass the normal release migration gate before deployment; no production migration is authorized by this ADR.

## Validation

Validate allowed and rejected file signatures/sizes, opaque private storage names, single-use and expired tokens, GET non-mutation, resend limits and generic responses, reviewer-only downloads and security headers, server-side approval gates, durable cleanup after approval/rejection, preservation of historical accountless approval, and unchanged resident registration and tenant permissions.
