# ADR 022: Reviewed New Barangay Onboarding

- **Status:** Superseded by [ADR 023](023-dilg-reviewed-barangay-admin-registration.md)
- **Date:** 2026-10-19
- **Supersedes:** ADR 021 decision 2 and its consequence that public Barangay applications are retired; restores only the pending-application and verified-provisioning workflow first recorded in ADR 011.

> This record documents the initial operator-provisioned flow. ADR 023 is the active policy for applicant credentials and DILG review.

## Context

A Barangay that is new to KapitBayan has no way to request an Admin account. Public self-provisioning would let an unverified person create a tenant or assign themselves an Admin role. Admin account creation must remain operator-controlled, while a new Barangay needs a clear route to apply. After approval, its Admin can manage Field Officials but cannot create or list another Admin account.

## Decision

1. The official sign-in page links to a public new-Barangay application form. It collects the Barangay name and locality, the proposed first Admin's name, position, contact details, requested username, an authority attestation, and consent to use those contact details for review.
2. Public submission creates only a pending `BarangayApplication`. It cannot create or select a tenant, create an account, choose a role, set a password, or see the state or details of another application. Submissions use a shared database throttle.
3. Only an active Django superuser can list application details or approve/reject. Before approval, the operator must verify the Barangay and official through an independent official channel. Rejection records a reason. Review actions are one-time from the pending state and are audited.
4. Approval runs in one database transaction. It creates the tenant for the verified Barangay locality or reuses one matching legacy record with incomplete locality fields. Multiple possible matches, an existing Admin, a conflicting username/email, or a database uniqueness conflict stop approval for manual review. Client-supplied role or tenant identifiers are never accepted.
5. Approval creates the Barangay's first `ADMIN` assigned to the resulting tenant with an unusable password, records the reviewing operator and verification attestation, and requests a one-time `/set-password` email after the transaction commits. If a setup email is not received, the platform operator can use the bounded account-support recovery path after independently verifying the official's contact details.
6. Barangay Admins may provision and manage Field Officials only within their own Barangay. They cannot create or list peer Admins. No DILG product role or cross-Barangay service access is introduced.

## Consequences

- New Barangays have a public entry point, but account and tenant creation remain reviewed operator actions.
- The application is not proof of official identity or legal Barangay status; the operator remains responsible for out-of-band verification.
- The applicant's contact details are private and appear only in the superuser review surface and retained application record.
- Existing legacy application rows remain preserved. Pending historical records without a proposed username may need the applicant to resubmit through the current form.
- Email delivery is best-effort and depends on the configured provider. Approval creates an account even if email delivery later fails; operators can use account support to resend a verified setup link.

## Validation and rollout

- API authorization, tenant matching, state transitions, account provisioning, audit records, and email dispatch are implemented in the backend.
- A schema migration is required before the updated API is deployed. Production migration/deployment must follow the normal release gate; this ADR does not authorize production changes.
