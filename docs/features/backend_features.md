# Backend Feature Guide

The Django REST API is divided into the `gridy_auth`, `gridy_services`, `gridy_reports`, `gridy_communications`, and `gridy_audit` apps. These internal names remain part of the migration and database history.

## Authentication and account lifecycle

Authentication uses access credentials and server-managed refresh sessions. Registration, verification, profile changes, and account deactivation are separate guarded workflows. Session revocation and record-retention behavior are defined by the models, tests, and [ADR 005](../../architecture/decisions/005-session-revocation.md); do not assume deleting a user deletes municipal service history.

## Roles and barangay isolation

API permissions and querysets enforce role and barangay scope. Residents access their own records; barangay staff actions are restricted to their assigned barangay. Barangay administrators can provision, list, update the permitted profile fields of, and activate/deactivate Field Officials only within their barangay. Provisioning sends an expiring password-setup link instead of setting a password in the admin UI. A separate superuser-only support API permits audited contact correction, recovery-link delivery, and account activation; it does not create/delete accounts or alter roles, barangay assignments, credentials, or resident evidence. Cross-tenant IDs supplied by clients do not grant access.

## Documents and treasury

The document workflow includes explicit fee assessment, waiver provenance, resident payment evidence, manual staff verification, O.R. recording, and release guards. `PROCESSING` is not a payment state; electronic transfers are not settled automatically. See [walk-in and revenue workflows](walkin_and_revenue_clearances.md) and the applicable ADRs.

## Queue and analytics

Queue tickets and live desk state are exposed through HTTP APIs and refreshed by clients. Staff operations and analytics are tenant/role scoped. The current client behavior is polling and fault-isolated retries, not a WebSocket stream.

## Reports, communications, and notifications

Residents can submit incident reports and staff can triage them. Communications include announcements, schedules, FAQs, hotlines, device registration, and staff notifications. Push/email work is best-effort when external credentials are configured; it is not backed by a durable task broker.

## Contract and verification

The generated OpenAPI schema and endpoint tests define exact payloads and status behavior. See the [API specification guide](api_specification.md); avoid maintaining copied payload samples here.
