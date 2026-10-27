# Walk-in Clearances and Treasury Revenue Auditing

This guide documents the hybrid document workflow for registered residents and in-person applicants. Exact field names and transitions are owned by `DocumentRequest`, its serializers/views, migrations, and tests.

## Walk-in records

Authorized barangay staff can record a walk-in request without creating a synthetic user account. The request stores its barangay and walk-in details so the record remains tenant-scoped and auditable. Do not make the user relationship required for walk-in records or assign them fake credentials.

## Fee assessment

Fee amount and fee provenance are separate. Staff must make an explicit positive assessment or record an allowed waiver; statutory exemptions retain their own provenance. A zero amount is not sufficient evidence of why a fee is not due. See [ADR 018](../../architecture/decisions/018-explicit-document-fee-assessment-and-waiver-provenance.md).

## Payment and release

- Residents pay only after the request reaches `READY_FOR_PICKUP`.
- CASH remains an in-person treasury flow. Electronic payment methods are out-of-band transfers to configured barangay recipients.
- Resident references, transfer timestamps, and private receipt screenshots are submitted evidence; staff verify them manually against the barangay's actual account.
- O.R. recording is retained as a treasury action. A request with a positive fee cannot be released without its required O.R.; the release gate is server-side.
- Statutory fee-exempt requests display the appropriate not-required state and do not require an O.R. for a fee of zero.

### Saving and checking an O.R. number

Barangay Admins save the Official Receipt number from the document review screen using the dedicated **Save O.R. number** action. This updates the receipt field independently from status, payment method, and fee assessment, so an O.R.-only edit does not repeat unrelated workflow actions. Residents cannot edit this field.

Field Officials can use the mobile **Clearance & Receipt Validator** to enter either the printed document tracking ID or the exact O.R. number recorded by the Barangay. The API searches only records in the Field Official's assigned Barangay, checks an exact case-insensitive O.R. match first, and otherwise resolves supported tracking-ID formats. A missing record returns not found; an O.R. shared by multiple records returns an ambiguity error for staff follow-up.

The mobile validator shows the API's error message when a lookup fails, instead of labeling every failure a network error. An unknown or out-of-Barangay identifier displays a not-found message; an ambiguous O.R. displays the server's review instruction. Session, access, and service errors remain separate from those record results. If the service reports an error, record its status and the matching backend log before treating a receipt as verified.

The validator confirms that the entered identifier matches a record in KapitBayan. It does not independently authenticate a paper receipt or confirm that money settled with a bank or e-wallet. Treasury staff still verify payment evidence against the Barangay's actual account.

There are no payment gateways, webhooks, bank scraping, or automated settlement processes. See [ADR 007](../../architecture/decisions/007-revenue-and-official-receipt-auditing.md) and [ADR 017](../../architecture/decisions/017-manual-epayment-evidence-and-verification.md).

## Evidence storage and access

Payment proofs and resident identity evidence are private. Requests for proof images use authenticated, role- and tenant-scoped API media views. Superseded or deleted evidence is cleaned after database changes commit and may remain queued for retry if storage deletion fails. Do not expose a public CDN URL or treat a submitted screenshot as verified payment.

## Reporting and reconciliation

Financial dashboard totals must follow the current backend aggregation rules and distinguish assessed, waived, exempt, cash, pending electronic proof, verified, and released records as implemented. Do not treat an unverified payment reference or an unassessed zero amount as collected revenue.
