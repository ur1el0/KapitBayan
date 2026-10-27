# ADR 026: Resident-Selected Document Payment Method

## Status
Accepted

## Context

The document review screens previously let Barangay staff set the payment method on a resident's request. That assigns the resident's choice to staff and can display a method that the Barangay has not configured. Payment recipients are already managed per Barangay, and the system does not process electronic payments.

## Decision

- Staff assess document fees and manage the Barangay's active e-payment recipients.
- Once a positive-fee request is `READY_FOR_PICKUP`, its resident chooses how to pay.
- Cash at the Barangay Hall is always available and appears first. E-payment choices are derived only from active recipient records configured for that resident's Barangay. With no active recipients, cash is the only choice.
- The API persists a resident-owned choice of cash or one active recipient. E-payment references can be submitted only for the recipient saved as the resident's choice.
- The resident may change an unpaid or rejected choice. A rejected choice change clears the prior evidence. A choice cannot change while evidence is pending verification or after payment has been verified.
- Barangay staff continue to verify transfers manually and record the O.R. before release. No payment gateway or automated settlement is introduced.

## Consequences

Residents control how they pay, while each Barangay controls which electronic accounts it accepts. The server enforces request ownership, request state, and Barangay scope. Cash remains usable without configuring any e-payment recipient. Web and mobile clients must expose the same choices and lifecycle.

## Related decisions

- [ADR 007: Treasury Revenue Auditing and Official Receipt (O.R.) Compliance](007-revenue-and-official-receipt-auditing.md)
- [ADR 017: Resident Manual E-Payment Evidence and Verification](017-manual-epayment-evidence-and-verification.md)
