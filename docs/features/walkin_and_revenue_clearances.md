# Walk-in Clearances and Treasury Revenue Auditing

This guide documents the hybrid document workflow for registered residents and in-person applicants. Exact field names and transitions are owned by `DocumentRequest`, its serializers/views, migrations, and tests.

## Walk-in records

Authorized barangay staff can record a walk-in request without creating a synthetic user account. The request stores its barangay and walk-in details so the record remains tenant-scoped and auditable. Do not make the user relationship required for walk-in records or assign them fake credentials.

## Fee assessment

Fee amount and fee provenance are separate. Staff must make an explicit positive assessment or record an allowed waiver; statutory exemptions retain their own provenance. A zero amount is not sufficient evidence of why a fee is not due. See [ADR 018](../../architecture/decisions/018-explicit-document-fee-assessment-and-waiver-provenance.md).

## Payment and release

- Residents pay only after the request reaches `READY_FOR_PICKUP`.
- Staff assess the fee and configure the Barangay's active electronic-payment recipients; the resident chooses the payment method for their request.
- Cash at the Barangay Hall is always available and is shown first. E-payment choices come only from active recipients configured for that resident's Barangay. If none are configured, cash is the only choice.
- The resident's choice is saved on the request. For an electronic transfer, the resident follows the selected recipient's instructions and submits the reference, transaction time, and receipt evidence. The API rejects a reference for an e-payment recipient that was not selected for that request.
- CASH remains an in-person treasury flow. Electronic payment methods are out-of-band transfers to configured barangay recipients.
- Resident references, transfer timestamps, and private receipt screenshots are submitted evidence; staff verify them manually against the barangay's actual account.
- A rejected electronic payment may be resubmitted using the same or another currently active Barangay recipient, or changed to cash. Changing a rejected choice clears the rejected reference and proof so stale evidence is not reused.
- The Barangay Admin configures the exact approved O.R. prefix, next unused serial, and optional zero-padding width in Barangay Settings. The configuration must match the Barangay-controlled receipt book; the system does not invent a series.
- When authorized staff confirms received cash or verifies an electronic transfer, the server assigns the next O.R. serial inside the same database transaction. A retry returns the already assigned number; missing configuration, an existing duplicate, or an out-of-range number blocks confirmation without consuming the serial. A request with a positive fee cannot be released until payment is verified and its O.R. is assigned; the release gate is server-side.
- KapitBayan generates a separate `KB-DOC-00000050` style request reference for staff lookup. It is not a receipt and must never be used as one. The Barangay Treasurer still issues and controls the matching paper O.R.
- Statutory fee-exempt requests display the appropriate not-required state and do not require an O.R. for a fee of zero.

The staff review screens do not select the resident's payment method. They assess the fee, manage the Barangay's offered e-payment accounts and O.R. series in payment settings, review uploaded evidence, and confirm payment. Cash is confirmed only after the Treasurer physically receives it. Resident payment-choice updates are restricted to the request owner and validated against the active recipients in the request's Barangay.

### Configuring and checking an O.R. number

Barangay Admins configure the series in **Barangay Settings → Official Receipt (O.R.) series**. Within a series, the next serial may only stay the same or move forward. To start a new approved series, change the prefix and enter that series' next unused serial; the old O.R. numbers remain attached to their requests. The legacy per-request O.R. endpoint accepts only an unchanged number and cannot be used to assign or clear one.

Field Officials can use the mobile **Clearance & Receipt Validator** to enter a KapitBayan request reference, the printed document tracking ID, or the exact O.R. number recorded by the Barangay. The API searches only records in the Field Official's assigned Barangay and normalizes leading/trailing whitespace and case for O.R. lookup. A missing record returns not found; an O.R. shared by multiple records returns an ambiguity error for staff follow-up. New O.R. assignments are serialized on the configured Barangay series row and also checked against historical records before the number is saved.

The mobile validator shows the API's error message when a lookup fails, instead of labeling every failure a network error. An unknown or out-of-Barangay identifier displays a not-found message; an ambiguous O.R. displays the server's review instruction. Session, access, and service errors remain separate from those record results. If the service reports an error, record its status and the matching backend log before treating a receipt as verified.

The validator confirms that the entered identifier matches a record in KapitBayan. It does not independently authenticate a paper receipt or confirm that money settled with a bank or e-wallet. Treasury staff still verify payment evidence against the Barangay's actual account.

There are no payment gateways, webhooks, bank scraping, or automated settlement processes. See [ADR 007](../../architecture/decisions/007-revenue-and-official-receipt-auditing.md) and [ADR 017](../../architecture/decisions/017-manual-epayment-evidence-and-verification.md).

## Evidence storage and access

Payment proofs and resident identity evidence are private. Requests for proof images use authenticated, role- and tenant-scoped API media views. Superseded or deleted evidence is cleaned after database changes commit and may remain queued for retry if storage deletion fails. Do not expose a public CDN URL or treat a submitted screenshot as verified payment.

## Reporting and reconciliation

Financial dashboard totals must follow the current backend aggregation rules and distinguish assessed, waived, exempt, cash, pending electronic proof, verified, and released records as implemented. Do not treat an unverified payment reference or an unassessed zero amount as collected revenue.
