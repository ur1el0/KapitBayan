# ADR 018: Explicit Document Fee Assessment and Waiver Provenance

## Status
Accepted

## Current implementation note

O.R. numbers are assigned from the Barangay's configured series when staff confirms payment; see [ADR 028](028-transactional-official-receipt-series.md). The fee assessment and verified-payment release gates in this ADR remain active.

## Context
Under ADR 007, ADR 010, and ADR 017, KapitBayan established municipal revenue accounting and manual payment verification for barangay clearance and certification requests. Residents may pay out-of-band via GCash, Maya, or bank transfer once a request is marked `READY_FOR_PICKUP`, and staff must record an Official Receipt (O.R.) number before release whenever `fee_amount > 0`.

However, an audit of the document request lifecycle revealed a significant treasury governance loophole:
1. **Ambiguous Default Zero-Fee State**: Ordinary document requests (such as Barangay Clearance and Business Permit) were initialized with `fee_amount = Decimal('0.00')` and `payment_status = NOT_REQUIRED`. This default made unassessed requests visually and programmatically indistinguishable from deliberate zero-fee waivers or statutory exemptions.
2. **Lack of Assessment Provenance**: Although staff could update the fee amount during review, the backend did not persist who assessed the fee, when the assessment occurred, or the justification for granting a zero-fee waiver.
3. **Premature Release Vulnerability**: An ordinary document request could proceed through `PROCESSING` to `READY_FOR_PICKUP` and ultimate release with `fee_amount = 0.00` without any staff member ever explicitly reviewing or assessing the statutory fee. This presented substantial financial leakage risks and violated COA municipal auditability standards.

## Decisions

### 1. Four-State Explicit Fee Assessment Lifecycle
`DocumentRequest` models an explicit `fee_assessment_status` field (`CharField` with choices):
- **`AWAITING_ASSESSMENT`**: Default state for ordinary document requests upon resident creation. The request cannot transition to `READY_FOR_PICKUP` or `RELEASED` until staff perform an explicit assessment.
- **`ASSESSED`**: Staff explicitly set a positive fee (`fee_amount > 0`). Automatically transitions `payment_status` to `UNPAID` (if previously `NOT_REQUIRED`) and records staff attribution.
- **`WAIVED`**: Staff deliberately grant a zero-fee waiver (`fee_amount == 0.00`). Requires a non-empty written justification (`fee_waiver_reason`). Sets `payment_status` to `NOT_REQUIRED` and records staff attribution.
- **`STATUTORY_EXEMPT`**: Automatic statutory exemption reserved exclusively for canonical statutory document types (`Certificate of Indigency`, `First Time Job Seeker Certificate` under RA 11261). Enforced server-side; fee is strictly `₱0.00` and `payment_status` is `NOT_REQUIRED`.

### 2. Server-Side Lifecycle Gate
Transitioning an ordinary document request to `READY_FOR_PICKUP` or `RELEASED` strictly requires an explicit assessment decision:
- If `fee_assessment_status == AWAITING_ASSESSMENT` and the document type is not statutory exempt, the backend raises `ValidationError({"fee_assessment_status": "Document fee must be assessed or explicitly waived before marking ready for pickup."})`.
- The client cannot bypass this gate; status validation is enforced inside the atomic `validate` action in `gridy_services/views/documents.py`.

### 3. Treasury Release Gate & Official Receipt (O.R.) Rules
- **Positive Fee (`fee_amount > 0`)**: Document release strictly requires an `or_number` and verified payment.
- **Zero Fee (`WAIVED` or `STATUTORY_EXEMPT`)**: Document release does not require an `or_number`, allowing legitimate indigent and statutory beneficiaries to receive documents without phantom receipt numbers.

### 4. RBAC & Multi-Tenant Scoping
- Only barangay staff (`ADMIN` or `FIELD_OFFICIAL`) belonging to the exact same barangay tenant (`request.user.barangay_id == document_request.barangay_id`) may assess or waive fees.
- Residents, cross-tenant officials, unassigned staff, and unauthenticated actors cannot mutate assessment state. Unauthenticated requests receive HTTP 401; unauthorized requests receive HTTP 404 to prevent tenant probing.
- Assessment provenance fields (`fee_assessment_status`, `fee_assessed_by`, `fee_assessed_at`, `fee_waiver_reason`) are exposed as strictly read-only fields in `DocumentRequestSerializer`.

### 5. Transaction Safety & Concurrency
The `validate` review action executes within `transaction.atomic()` and locks the target `DocumentRequest` using `select_for_update()`, preventing race conditions during concurrent staff reviews or status updates.

### 6. Audit Logging
Every fee assessment or waiver event logs an `AuditLog` entry recording the responsible staff user, action type (`UPDATE`), client IP address, and a human-readable description containing the assessed fee amount or waiver justification.

### 7. Truthful Historical Migration & Reversibility
Migration `0016_document_fee_assessment_provenance.py` adds the schema columns and executes a data migration that preserves audit truth without fabricating staff attribution:
- Canonical statutory documents are set to `STATUTORY_EXEMPT` with `fee_assessed_at = created_at`.
- Historical released requests with `fee_amount > 0` are set to `ASSESSED` with `fee_assessed_at = updated_at` and `fee_assessed_by = None`.
- Historical released requests with `fee_amount == 0` are set to `WAIVED` with `fee_waiver_reason = "Legacy clearance released prior to explicit fee assessment tracking."` and `fee_assessed_by = None`.
- Active/rejected requests with `fee_amount > 0` are set to `ASSESSED`; those with `fee_amount == 0` are set to `AWAITING_ASSESSMENT`.
- The migration is fully reversible; rollback drops the provenance columns without deleting document records.

### 8. Web and Mobile Client Parity
- **Web (`ReviewDocumentModal.tsx`, `DocumentRequests.tsx`, `DocumentRequestRow.tsx`)**:
  - Displays clear assessment provenance badges (`Statutory Exemption`, `Staff Waiver (₱0.00)`, `Staff Assessed (₱XX.XX)`, or `Awaiting Assessment`).
  - Staff modal provides explicit positive fee entry or fee waiver checkbox with mandatory justification textarea.
  - Action button disables "Mark Ready for Pickup" if fee is unassessed.
  - Resident portals display explanatory guidance during `PROCESSING` regarding pending fee assessment.
- **Mobile (`DocumentRequestModel`, `DocumentPaymentSection`)**:
  - Displays pending assessment guidance banner during `PROCESSING`.
  - On `READY_FOR_PICKUP`, renders staff waiver card with reason or statutory exemption badge.
  - Electronic payment form is rendered only when an assessed positive fee is payable.

## Consequences

### Positive
- **Guaranteed Treasury Auditability**: Eliminates accidental zero-fee document releases and ensures all fee waivers have documented justifications.
- **Clear Staff Attribution**: Pinpoints which official assessed or waived fees and when the decision occurred.
- **Truthful Historical Records**: Distinguishes statutory entitlements from discretionary waivers and unassessed legacy records.
- **Consistent UX Across Platforms**: Both web and mobile applications clearly communicate assessment status to residents and officials.

### Trade-offs & Operational Considerations
- **Staff Workflow Requirement**: Staff must perform an extra step to assess or waive fees before marking documents ready for pickup.
- **Reversibility Consideration**: Rolling back migration `0016` drops provenance columns; database backups should be preserved prior to schema rollback.

## Related ADRs
- [ADR 004: Multi-Tenant Architecture & Data Isolation](004-multi-tenant-isolation.md)
- [ADR 007: Treasury Revenue Auditing and Official Receipt (O.R.) Compliance](007-revenue-and-official-receipt-auditing.md)
- [ADR 009: Simplification to Defended Proposal Architecture](009-simplification-to-defended-proposal-architecture.md)
- [ADR 010: Adviser-Approved Service Workflows](010-adviser-approved-service-workflows.md)
- [ADR 011: Verified Barangay Onboarding and Tenant Payment Recipients](011-verified-barangay-onboarding-and-manual-payment-recipients.md)
- [ADR 017: Resident Manual E-Payment Evidence, Storage Isolation, and Verification Architecture](017-manual-epayment-evidence-and-verification.md)
