# ADR 023: DILG-Reviewed Barangay Admin Registration

- **Status:** Accepted
- **Date:** 2026-10-19
- **Supersedes:** The applicant credential and reviewer portions of ADR 022; preserves its locality checks, audit history, shared request throttle, and legacy setup-email fallback.

## Context

Barangays need a public route to request their first KapitBayan Admin account, while the platform must prevent an unverified applicant from activating an account or creating a tenant. The Barangay official wants to register with an official email and choose a password, rather than claim a username. Residents continue to use their username-based registration. A DILG reviewer verifies the Barangay and official, but the review role must not expose resident or service records across Barangays.

## Decision

1. A public onboarding form collects the Barangay name, municipality/city, province, official applicant name and position, official email, contact number, authority attestation, contact consent, and a password with confirmation. It has no username, role, or tenant-ID input. It does not ask for government ID numbers, resident identity documents, passwords for other systems, or one-time codes.
2. The official email is the Barangay Admin's sign-in identity. The server generates a private internal Django username; it is never requested from the applicant or returned as the Admin's login identity. Django validates the password and stores only its hash. The same email-only sign-in rule applies to Field Officials; only Residents choose usernames.
3. Submission creates an inactive, unassigned `ADMIN` user linked to a `PENDING` `BarangayApplication`. The account cannot obtain an access token before approval. Public submission cannot create or select a tenant, grant a role, or view application status/details. Shared database throttling and duplicate locality/email checks remain enabled.
4. Only an active `DILG_ADMIN` or a controlled Django superuser may list or review applications. Reviewers verify the official's identity/authority and Barangay locality through an independent official channel, then attest to that verification. Rejection requires a recorded reason. Review state changes and account activation are audited.
5. Approval runs atomically: it creates the verified Barangay tenant or matches one unambiguous legacy locality record without an Admin, then activates and assigns the same linked applicant account as the first `ADMIN`. It does not replace the applicant's account or send a password-setup email. The Admin can then sign in with the official email and password supplied during application.
6. DILG authentication is limited to application review and the account's own minimal authentication/session endpoints. DILG is excluded from platform account support, Django admin sessions, resident features, staff features, and all tenant service data. Existing tenant-level authorization remains unchanged. Django superusers may also review applications as a controlled fallback and retain their separate account-support duties.
7. Rejection retains the application and its review history while deleting only the still-inactive, unassigned applicant account. If account state no longer matches that safe pending state, the reviewer must resolve it manually. Existing accountless applications from ADR 022 remain reviewable and, when they include the historical username, continue through the previous unusable-password/setup-email flow.
8. Resident registration remains resident-only and username-based. It cannot choose an official role. Field Officials created by a Barangay Admin also use their email as their sign-in identity; the system generates and hides any required internal username. Admins cannot create peer Admins.

## Consequences

- DILG verifies and approves a legitimate request; it does not assign a pre-created account or gain global operational access.
- The applicant is responsible for safeguarding the password they set. Password reset remains available after approval through the registered official email. Field Officials use their Admin-provided email for the emailed password setup and sign-in flow.
- A submitted application and self-attestation are not proof of public-office status. DILG performs the independent verification; this form alone never establishes legitimacy.
- The review surface contains personal contact details and must remain limited to DILG reviewers and controlled platform superusers.
- The additive migration preserves existing rows and accountless historical applications. Applying it to production requires the normal release gate and is not authorized by this ADR.

## Validation and rollout

Validate password hashing and mismatch/strength errors; pending account inactivity and no tenant assignment; role-specific login; reviewer authorization and scope; atomic activation of the same applicant; reasoned rejection and safe account deletion; existing approval fallback; and unchanged tenant isolation. Apply the schema migration before deploying the code using the standard staged rollout.
