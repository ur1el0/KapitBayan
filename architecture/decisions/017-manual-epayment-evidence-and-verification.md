# ADR 017: Resident Manual E-Payment Evidence, Storage Isolation, and Verification Architecture

## Status
Accepted

## Current implementation note

The resident's payment-method choice and the available choice list are now governed by [ADR 026](026-resident-selected-document-payment-method.md). The UI details below describing the multi-provider selector are historical where they do not match that newer decision.

## Context
ADR 010 established manual GCash reference submission, and ADR 011 expanded manual electronic payment recipient configuration to support tenant-level providers (GCash, Maya, Bank Transfer) while keeping statutory cash payment at the barangay hall.

However, operational field evaluations revealed critical UX, security, and treasury compliance deficiencies in the existing manual e-payment workflow:
1. **Premature & Ambiguous Submissions**: Residents could attempt to enter payment references while document requests were still in early review or `PROCESSING` stages, prior to staff verification of document completeness or statutory fee requirements.
2. **Lack of Verifiable Payment Evidence**: Staff had only a text reference number to verify out-of-band transfers. Verifying high-volume or ambiguously formatted reference strings against physical bank or e-wallet account records without a timestamp or receipt screenshot was error-prone and time-consuming.
3. **Receipt Evidence Privacy & Leakage Risk**: Payment receipts often contain sensitive personal financial data, account numbers, resident names, and contact numbers governed by the Data Privacy Act of 2012 (RA 10173). Exposing raw media URLs or storing receipts in public object storage buckets violates privacy boundaries.
4. **Treasury Coupling & Release Bottlenecks**: Under COA regulations and ADR 007, barangay document release requires recording a serialized Official Receipt (O.R.) number when `fee_amount > 0`. In the previous workflow, O.R. recording was coupled with document release, preventing staff from persisting an issued O.R. during payment verification prior to physical handover or dispatch.
5. **Web and Mobile Client Divergence**: The resident web portal and Flutter mobile app handled payment submission states inconsistently, lacking clear in-app guidance for processing periods, cash collection desks, fee exemptions, or rejected payment retries.

## Decisions

### 1. Manual E-Payment Scope & Infrastructure Boundaries
KapitBayan retains the low-dependency, zero-gateway architecture selected in ADR 009. It does not integrate payment gateways, webhooks, bank scraping, OCR, Celery/Redis background processors, or external financial cloud services. All e-payments remain out-of-band transfers initiated by residents directly to the barangay's configured receiving account. Barangay staff manually verify receipts against their actual receiving account.

### 2. Strict Lifecycle Gate
Payment reference and proof submission is unlocked **strictly** when the document request transitions to `READY_FOR_PICKUP`. While in `PENDING` or `PROCESSING`, payment submission is blocked server-side, and clients display a clear informational banner explaining that fees are only payable once document preparation is complete and the request is approved for release.

### 3. Schema & Evidence Metadata
Extended `DocumentRequest` with:
- `payment_proof_image`: `ImageField(upload_to=..., null=True, blank=True)` storing an authenticated screenshot of the transaction receipt.
- `payment_transacted_at`: `DateTimeField(null=True, blank=True)` recording the timestamp when the out-of-band transfer was completed.

Enforced through reversible migration `0015_document_payment_proof_and_transacted_at.py`.

### 4. Dual Private Storage Isolation & Streaming Gateway
Payment receipt images are strictly treated as private, access-controlled financial artifacts:
- **Production (Cloudinary)**: Added `payment_proofs` to `ResidentAwareCloudinaryStorage.PRIVATE_DIRECTORIES`. Assets are uploaded as authenticated private resources with randomized UUID identifiers. Overridden `.url()` prevents returning public or signed Cloudinary URLs directly to clients.
- **Development & Testing (Local Storage)**: Files reside below `MEDIA_ROOT/payment_proofs/`. Registered `payment_proofs` within `ProtectedMediaView.SENSITIVE_DIRECTORIES`, and configured routing precedence so direct `/media/payment_proofs/...` requests return `404 Not Found`.
- **Authenticated Streaming Gateways**: Proof images are streamed exclusively through authorized backend endpoints:
  - Canonical: `GET /api/v1/document-requests/<pk>/payment-proof/`
  - Tested Alias: `GET /api/v1/documents/<pk>/payment-proof/`
  Both endpoints stream bytes with detected MIME types (`image/jpeg`, `image/png`, `image/webp`) and strict HTTP security headers:
  `Cache-Control: private, no-store, max-age=0` and `X-Content-Type-Options: nosniff`.

### 5. Access Control & Authorization (RBAC)
Access to payment proof images and payment verification endpoints is restricted to:
- The resident owner who submitted the document request (`request.user == document_request.user`).
- Barangay officials (`ADMIN` or `FIELD_OFFICIAL`) belonging to the exact same barangay tenant (`request.user.barangay_id == document_request.barangay_id`).
- All other authenticated actors (Barangay Operators, officials from other barangays, unassigned staff, and third-party residents) or non-existent proofs receive **HTTP 404 Not Found** to prevent tenant existence probing. Unauthenticated requests receive **HTTP 401 Unauthorized**.

### 6. Decoupled O.R. Persistence & Server-Side Release Gate
- Authorized staff (`ADMIN` or `FIELD_OFFICIAL`) can persist and update the Official Receipt (`or_number`) independently during payment review or while the request is `READY_FOR_PICKUP`, without triggering immediate document release.
- When transitioning to `RELEASED`, the server-side model and serializer validation strictly enforce:
  `if fee_amount > 0 and not or_number: raise ValidationError("An Official Receipt (O.R.) number is required before releasing a document with a fee.")`
- The release gate does not require an O.R. when `fee_amount == 0.00`. Statutory exemptions are determined by the document type in the fee policy; an ordinary request's initial zero fee is pending assessment, not proof of exemption.

### 7. Transaction-Safe Storage Cleanup
Storage lifecycle is managed through atomic database transactions and post-delete signals:
- File replacements, method conversions to CASH, or fee exemptions schedule file deletion strictly after database transaction commit via `transaction.on_commit(safe_delete_storage_file)`.
- If database operations fail or rollback occurs, uncommitted files are cleaned up immediately without removing existing valid proof assets.
- Deletion of a `DocumentRequest` schedules proof file deletion via `post_delete` signal on transaction commit.

### 8. Audit Logging, Privacy (RA 10173), and Rollback Retention
- `AuditLog` records the actor, action type, free-form description identifying the document request, IP address, and timestamp for submission and review events. The transaction reference and transfer timestamp remain on `DocumentRequest`; they are not separate structured `AuditLog` fields. Raw image bytes, account passwords, PINs, OTPs, and private banking credentials are never logged.
- A database migration rollback drops the proof path and transaction timestamp columns but leaves existing files in private storage. This preserves access restrictions, yet loses the request-to-file association and can leave orphaned files. Operators must inventory and securely retain the database metadata before any production rollback to support COA audit retrieval.

### 9. Web and Mobile Parity
Both the React web portal and Flutter mobile application provide identical user experience across all payment states:
- `PROCESSING`: Explanatory notice that payment opens upon approval.
- `CASH`: Clear instructions to visit the Barangay Treasurer desk.
- `NOT_REQUIRED` / Fee-Exempt: A statutory exemption badge with the relevant citation appears only for exempt document types. Ordinary requests at their initial zero fee remain pending staff assessment; a zero fee after approval is shown as no payment required without a statutory claim.
- `UNPAID` / `REJECTED`: Multi-provider selector, reference input, Manila datetime picker, screenshot picker/dropzone with client-side image preview and remove button, and staff rejection note display.
- `PENDING_VERIFICATION`: Transfer snapshot summary with authenticated in-modal/dialog proof preview.
- Staff Desk: Electronic transfer card, full zoom inspection modal, decoupled O.R. save button, release gate verification, and mandatory rejection feedback.

## Consequences

### Positive
- **Auditable Financial Verification**: Barangay treasurers and desk officials can inspect verified visual receipts alongside transaction references and timestamps, eliminating guesswork.
- **Data Privacy & RA 10173 Compliance**: Private storage isolation and authenticated streaming ensure sensitive financial receipts are never exposed to public URLs or unauthorized users.
- **Treasury Workflow Flexibility**: Decoupling O.R. entry from final release enables staff to record receipts as payments arrive while maintaining the strict release gate before document handover.
- **Cross-Platform Consistency**: Web and mobile residents experience identical flows and status explanations.

### Trade-offs & Operational Considerations
- **Storage Consumption**: Uploading screenshot proofs increases storage usage; mitigated by a 5 MB file size ceiling and image re-validation.
- **Manual Staff Inspection**: Does not automate bank statement reconciliation; staff must still verify transfers against their barangay's physical accounts.
- **Image Decoding Overhead**: Validating uploaded receipts using Pillow on the server and resizing thumbnails on clients introduces minor CPU overhead, which is well within capacity for municipal workloads.

## Related ADRs
- [ADR 007: Treasury Revenue Auditing and Official Receipt (O.R.) Compliance](007-revenue-and-official-receipt-auditing.md)
- [ADR 009: Simplification to Defended Proposal Architecture](009-simplification-to-defended-proposal-architecture.md)
- [ADR 010: Adviser-Approved Service Workflows](010-adviser-approved-service-workflows.md)
- [ADR 011: Verified Barangay Onboarding and Tenant Payment Recipients](011-verified-barangay-onboarding-and-manual-payment-recipients.md)
