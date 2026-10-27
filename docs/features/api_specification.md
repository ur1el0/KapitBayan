# API Specification Guide

The generated drf-spectacular schema is the authoritative source for current request and response fields. A running local backend exposes the schema at `/api/schema/` and the interactive browser at `/api/schema/swagger-ui/`. Do not copy a payload from this guide into a client contract without checking the generated schema and endpoint tests for the target revision.

## API route families

Application endpoints are mounted below `/api/v1/`:

| Route family | Example operations |
|---|---|
| `/auth/` | registration, login, refresh, logout, current profile, resident verification/import, sessions, barangay onboarding |
| `/document-requests/` | request lifecycle, staff validation, fee assessment, payment submission/review, receipt and PDF operations |
| `/tickets/` | issue ticket, list ticket, live status, staff queue operations |
| `/aid-requests/` | submit and review assistance applications |
| `/payment-recipients/` | read or manage barangay payment recipients according to role |
| `/reports/` | submit and triage incident reports |
| `/announcements/`, `/activities/`, `/faqs/`, `/hotlines/` | community information and schedules |
| `/health/live/`, `/health/ready/` | process liveness and dependency readiness |

Exact URL actions and HTTP methods are defined by `backend/config/urls.py` and the Django app URL configurations. Use `/api/schema/` to inspect the current resolved schema.

New Barangay onboarding uses multipart `POST /api/v1/auth/public/barangay-applications/` with official contact details, an official email, a password, and one PDF/JPEG/PNG authority document (maximum 5 MiB). The applicant does not provide a username. Submission creates a pending application and inactive, unassigned Admin account, then requests email verification. The frontend link opens a confirmation page; a deliberate POST to `/auth/public/barangay-applications/{id}/verify-email/` confirms mailbox ownership. `/auth/public/barangay-applications/resend-verification/` accepts an application ID and email and always returns a generic response; eligible applications are limited to one resend every 10 minutes and share a request throttle. Active Barangay Operators and controlled Django superusers review requests through `GET /api/v1/auth/platform/barangay-applications/?status=PENDING`, download pending proof from the per-application `/proof/` endpoint, and call `/approve/` or `/reject/`. They may permanently erase an application in any status with a reason and exact `KB-{id}` confirmation through `/erase/`; an eligible linked Admin account is erased through the guarded account lifecycle, while the Barangay and audit/history records remain. Approval requires verified email, an attached proof document, a proof-review attestation, and independent verification of the applicant and locality; proof is queued for deletion after a review decision. Operator credentials are limited to the review API, bounded account-support API, and own session endpoints. Account support can permanently erase eligible Resident, Field Official, and Barangay Admin accounts after a controlled reason and exact username confirmation; the last active Barangay Admin is protected and statutory document and aid history is retained. Exact field contracts are in generated OpenAPI.

Barangay Admins create Field Official accounts through `POST /api/v1/auth/staff/` using the official's email and name; the request does not accept a username or password. The server generates an internal username, sends a private password setup link, and returns the email as the sign-in identity. Only Resident accounts use user-chosen usernames.

## Document O.R. save and verification

- `PATCH /api/v1/document-requests/{id}/or-number/` saves only `or_number` for an in-scope document request. It is Barangay Admin-only and accepts a trimmed string up to 50 characters. It does not change the document status, fee assessment, or payment method. A positive-fee request already marked `RELEASED` cannot have its O.R. cleared.
- `GET /api/v1/document-requests/verify/?identifier={value}` lets a Barangay Admin or Field Official look up a document by exact case-insensitive O.R. number or supported tracking identifier (`REQ-12`, a numeric request ID, or the printed `ID: #BC|CI|RC|BP|DOC-YYYY-NNNN` form). Lookup is restricted to the authenticated user's Barangay. It returns the document request when found, `404` when no matching record exists in that Barangay, and `409` when the O.R. matches multiple records.

This lookup confirms the identifier against KapitBayan's stored record. It does not verify a paper receipt with the treasury or settle an electronic transfer. The official release and payment controls remain enforced by the server-side document workflow.

## Client integration rules

- Use the repository's configured API client; keep provider credentials and integrations on the server.
- Derive tenant scope on the server from the authenticated user. Do not add a client `barangay_id` override to resident operations.
- Treat protected identity, billing, and payment-proof files as authenticated media. Do not render direct public storage URLs.
- Preserve endpoint error semantics and test unauthorized, cross-tenant, missing-record, and storage-failure cases.
- Update OpenAPI decorators, serializers, clients, and contract tests together when a route changes.

See [ADR 003](../../architecture/decisions/003-openapi-contract-driven-development.md) and the [route map](../../architecture/06-api-endpoint-contracts.md).
