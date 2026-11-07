# ADR 027: Verification QR for Barangay-Issued Paper Certificates

## Status

Accepted for the post-defense revision branch; production rollout is pending migration and verification.

## Context

Panel feedback requested a QR code that can be scanned to verify a Barangay certificate. KapitBayan's existing downloadable PDF is an O.R.-number slip, not a certificate. Generating a certificate PDF or placing a verification code on the O.R. slip would imply that KapitBayan issues or authenticates the paper document, which it does not.

## Decision

1. The Barangay continues to prepare, sign, and issue the paper certificate under its own process. KapitBayan creates only a separate QR label for attachment.
2. A Barangay Admin may create that label only after the request is `RELEASED` and after explicitly confirming that the paper certificate was physically issued.
3. The QR carries a random UUID URL, not a resident identifier, O.R. number, request ID, or personal data. Repeated issuance requests reuse the active token. Admins can revoke it; a status change away from `RELEASED` also revokes it.
4. The public validation response contains only validity, Barangay name, certificate type, and issuance date. Unknown, revoked, deleted, or non-released requests return the same generic invalid result. The endpoint is rate-limited.
5. Validation confirms only that KapitBayan has an active Barangay issuance record for the shown type. It does not replace a signature or seal, establish the holder's identity, or detect alteration of the physical paper. The O.R.-number slip remains a separate artifact.

## Consequences

- The physical issuing authority remains the Barangay; KapitBayan provides a lookup mechanism for a recorded issuance.
- The public page needs no resident authentication and exposes no resident identity or private request details.
- A recipient needs network access to check the code. The Barangay remains the fallback authority when lookup is unavailable or invalid.
- Removing the associated document request invalidates its token. The active record does not survive request deletion.
- Deployment requires the new migration, HTTPS frontend configuration, and a real print/scan check before the feature can be described as live.

## Related decisions

- [ADR 004: Strict Multi-Tenant Data Isolation](004-multi-tenant-isolation.md)
- [ADR 007: Treasury Revenue and O.R. Auditing](007-revenue-and-official-receipt-auditing.md)
- [ADR 009: Simplification to the Defended Proposal Architecture](009-simplification-to-defended-proposal-architecture.md)
- [ADR 017: Manual E-Payment Evidence and Verification](017-manual-epayment-evidence-and-verification.md)
