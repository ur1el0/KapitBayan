# ADR 020: Bounded DILG Account Support and Recovery

## Status
Accepted

## Context

The platform has tenant administrators who can manage residents and field officials in their barangay, but a DILG administrator needs a safe recovery path when the first official account was created with an invalid email or when an account requires centralized access suspension. Unrestricted cross-tenant CRUD would conflict with the least-privilege and tenant-isolation boundaries in ADRs 004, 008, and 011.

## Decision

1. DILG account support is a dedicated, authenticated, throttled operation. It may search a minimal directory of `RESIDENT`, `FIELD_OFFICIAL`, and `ADMIN` accounts across barangays, including legacy unassigned users.
2. It excludes `DILG_ADMIN` users and Django superusers. It cannot create/delete accounts or change usernames, roles, barangay assignments, staff/superuser flags, passwords, or resident identity evidence.
3. Correcting an email requires a controlled support reason and a DILG attestation that the account holder and new email were verified through an official channel. The account email is updated, refresh sessions are revoked, the action is audited, and a private one-time setup/reset link is queued after commit.
4. A recovery-link resend requires the same external-contact attestation and a controlled reason. The reset token and direct link are never returned to the API client or included in audit records/log messages.
5. Deactivation/reactivation changes only `User.is_active` and requires a controlled reason. Deactivation revokes refresh sessions. The last active administrator of an assigned barangay cannot be disabled by this support flow.
6. All lifecycle actions write `USER_ACTION` audit records with actor, target account ID, role, barangay ID (or unassigned state), action, and reason code. Email values, free text, credentials, and identity evidence are excluded.
7. No schema changes, additional services, or background worker infrastructure are introduced. Recovery email uses the existing Django password-reset token generator and in-process task helper.

## Consequences

- DILG can repair common account-access failures without direct database edits or cross-tenant profile CRUD.
- The account holder must be reached through an independently verified channel before DILG corrects an address or requests delivery of a link.
- The feature remains narrower than general CRUD: account creation and permanent erasure continue through their existing approved workflows.
- Account deactivation can interrupt access across a barangay; the last-active-administrator guard reduces accidental tenant lockout.
- Audit records show that contact verification was attested, not the underlying verification evidence. DILG remains responsible for following the approved identity-verification procedure outside the application.
