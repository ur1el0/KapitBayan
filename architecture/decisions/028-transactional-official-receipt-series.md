# ADR 028: Barangay-Controlled Transactional Official Receipt Series

## Status
Accepted

## Context

The document workflow previously required staff to type an O.R. number into each request. This was error-prone, could create duplicates, and made payment confirmation and receipt assignment separate actions. The system still does not collect money or automatically verify a bank/e-wallet transfer, and the Barangay retains control of its official receipt records.

## Decision

- Each Barangay Admin configures the exact approved receipt prefix, next unused serial, and optional serial padding width in Barangay Settings. The system does not invent a prefix or initial serial.
- Authorized staff confirm cash only after the Treasurer has received it, or manually verify an electronic transfer against the Barangay's actual receiving account. A reference or uploaded image alone does not confirm payment.
- On payment confirmation, the API locks the Barangay's series row and assigns the next serial in the same database transaction as the payment status update. A failed transaction does not consume a serial. Retrying a completed confirmation returns the existing O.R. rather than assigning a second one.
- Duplicate numbers in existing requests, a missing series, or a number exceeding the supported length blocks confirmation without advancing the serial. The Admin must check the physical series and correct the next unused serial before retrying.
- Within a series, the next serial may only stay the same or move forward; it cannot be moved backward. To start a new approved series, an Admin changes the prefix and enters that series' next unused serial. The format lock resets for the new prefix, while previously assigned O.R. numbers remain attached to their requests.
- Staff screens do not accept manually typed O.R. numbers. The old assignment endpoint remains only for compatibility with requests to save an unchanged existing number; it cannot assign or clear a number.
- A positive-fee document cannot be released until payment is verified and the O.R. number has been assigned. Fee and waiver details cannot be changed while payment evidence is pending review, after payment is verified, or after an O.R. is assigned.
- The assigned number is synchronized with the Barangay's approved O.R. series. KapitBayan does not receive payment, settle transfers, or replace the Treasurer's controlled issuance and custody of the paper receipt.

## Consequences

The Barangay must configure and maintain the series against its actual receipt book before confirming any payable request. Number allocation is serialized per Barangay, and assignment is auditable. Existing historical requests and their numbers are retained; the new series does not rewrite them.

## Related decisions

- [ADR 007: Treasury Revenue and Official Receipt Auditing](007-revenue-and-official-receipt-auditing.md)
- [ADR 017: Manual E-Payment Evidence and Verification](017-manual-epayment-evidence-and-verification.md)
- [ADR 018: Explicit Fee Assessment and Waiver Provenance](018-explicit-document-fee-assessment-and-waiver-provenance.md)
- [ADR 026: Resident-Selected Document Payment Method](026-resident-selected-document-payment-method.md)
