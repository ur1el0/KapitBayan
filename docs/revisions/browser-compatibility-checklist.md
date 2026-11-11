# Resident Web Browser Compatibility Record

This tracks revision-matrix browser compatibility. KapitBayan uses responsive web; the matrix wording “responsive or PWA” does not make PWA mandatory. A smoke pass on login/register is not a pass on authenticated service workflows.

## Results recorded November 12, 2026

| Browser | Version / OS | Viewport | Login / registration | Authenticated documents / queue | Layout / errors | Status |
|---|---|---:|---|---|---|---|
| Google Chrome desktop | 157.0.8103.38 / Fedora Linux 44 | 1365×900 | Both routes HTTP 200; forms rendered | Not tested; protected pages redirected to login | No horizontal overflow or page JS errors observed | Partial smoke pass |
| Google Chrome responsive viewport | 157.0.8103.38 / Fedora Linux 44 | 390×844 | Both routes HTTP 200; forms rendered | Not tested | No horizontal overflow or page JS errors observed | Partial smoke pass |
| Microsoft Edge desktop | Not installed | — | Not tested | Not tested | Browser installation attempted; failed because system dependencies require sudo authorization unavailable in this environment | Blocked |
| Firefox desktop | 159.0.1 / Fedora Linux 44 | 1365×900 | Both routes HTTP 200; forms rendered | Not tested; protected pages redirected to login | No horizontal overflow or page JS errors observed | Partial smoke pass |
| Firefox responsive viewport | 159.0.1 / Fedora Linux 44 | 390×844 | Both routes HTTP 200; forms rendered | Not tested | No horizontal overflow or page JS errors observed | Partial smoke pass |
| Chrome Android | Physical device not connected in this pass | — | Not tested | Not tested | No current phone/browser evidence | Blocked |

## Authenticated and production workflow gaps

- No authorized resident or staff test session was used. Production `/api/v1/document-requests/` and `/api/v1/tickets/` returned `401` without authentication, as expected; this does not verify the flows after login.
- The successful plan-only migration run on November 11 reported two pending production migrations: `gridy_auth.0028_residenttransferrequest_address_details_and_more` and `gridy_services.0022_official_receipt_series`. Do not submit production requests until the exact plan is reviewed and migrations are safely applied.
- No verified end-to-end checks exist in this pass for document create/status transitions, linked queue completion, payment-role denials, QR issuance/phone scan, push delivery/deep links, or offline/reconnect behavior.

## Earlier limited automated smoke

On November 9, Playwright Chromium 153.0.8010.12 and Firefox 155.0 loaded production login and registration at 1365×900 and 390×844. The pages returned 200, rendered, and had no horizontal overflow. That run was unauthenticated and did not represent Google Chrome, Microsoft Edge, physical Android Chrome, or document/queue workflow coverage.

## Completion criteria

For each target browser, record URL, date, version, operating system, viewport/device, login/registration, protected resident navigation, document and queue lifecycle, payment visibility/permissions, notification/deep link where supported, responsive layout, console/network failures, and a privacy-safe screenshot or run record. Use controlled test accounts and avoid creating real payment or service records. Mark a row complete only after its required workflows and evidence are available.
