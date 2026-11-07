# Paper certificate QR verification

KapitBayan does not create the Barangay's certificate. The Barangay prepares, signs, and issues the paper certificate; KapitBayan can create a separate QR label for that paper.

## Issuance flow

1. A Barangay Admin moves a document request to **Released** after the Barangay's normal review, payment, and release procedure.
2. In the released request, the Admin confirms that the paper certificate was physically issued and chooses **Create verification QR**.
3. KapitBayan creates a random UUID token scoped to that request and returns a public verification URL. Repeated issue requests reuse the active token; an Admin can revoke it, and a later issue creates a new token.
4. The Admin prints the QR label and attaches it to the Barangay-issued paper certificate.
5. A recipient scans the code and sees whether an active issuance record exists, the issuing Barangay, the certificate type, and the issuance date.

The public response contains no resident name, account identifier, address, purpose, request number, O.R. number, payment information, uploaded evidence, or document image. The QR confirms that the Barangay recorded an issuance for the shown certificate type; it does not establish the holder's identity, replace a signature or seal, or prove that a printed paper was not altered. The actual paper certificate remains the authoritative document.

## API and access boundaries

- Admin-only request action: `GET`, `POST`, or `DELETE /api/v1/document-requests/{id}/certificate-verification/`. The request is tenant-scoped. `POST` requires the Admin to affirm that the paper certificate was issued and the request must already be `RELEASED`. `DELETE` revokes the active token.
- Public scan lookup: `GET /api/v1/public/certificate-verifications/{uuid}/`. It returns a generic invalid result for unknown, revoked, or no-longer-released requests, and is application-rate-limited to 60 requests per minute per client bucket.
- The QR points to the configured HTTPS frontend route `/verify-certificate/{uuid}`. The public page calls only the minimal lookup endpoint.
- Token values are random UUIDs and act as unguessable public capabilities. Do not put resident information or an O.R. number in the URL or QR payload. Revoke a code if a label is lost or its issuance record should no longer validate.
- The verification model is removed if its associated document request is deleted; the QR then returns the generic invalid result.

## User-facing instructions

Tell residents to keep the signed paper certificate and use the QR to check that the Barangay has a matching active record. If a scan says invalid or cannot connect, ask the issuing Barangay to check the paper directly; a phone needs an internet connection to perform this lookup.

## Delivery status

The workflow is implemented on `fix/revision-matrix-panel-comments`. It still needs a database migration in the target environment, a production deployment, a real scan/print check, and a scoped review of the public response before it should be described as live.
