# System Overview

KapitBayan is a web and mobile system for barangay services. Residents use it to request documents, follow queues, read public information, and submit eligible service requests. Authorized personnel process those requests within their barangay. The system supports digital and in-person service; it does not replace barangay decisions or treasury controls.

## Runtime shape

```text
React web client ─┐
                  ├── Django REST API ── PostgreSQL
Flutter app ──────┘          ├────────── private media storage
                             ├────────── Firebase Cloud Messaging (when configured)
                             └────────── Email provider (HTTPS; SMTP locally)
```

The web client uses the API through the configured same-origin proxy in the intended production topology. The Flutter app connects to the configured API URL. Hosting details and checks that remain unverified are recorded in [Deployment](11-deployment-and-ci-cd.md); this diagram describes components, not a claim that every external integration is live.

## Roles and tenancy

- `RESIDENT` accounts belong to one barangay and can access their own resident services.
- `ADMIN` and `FIELD_OFFICIAL` accounts are assigned to a barangay and receive staff permissions defined by each endpoint.
- A new Barangay's first `ADMIN` applicant registers with an official email and a password, with no chosen username. A DILG reviewer independently verifies the applicant and locality; approval activates the same account and assigns it to the Barangay. DILG review does not expose service records. Barangay Admins and Field Officials sign in with email; only Residents choose usernames. The Admin manages Field Officials in the assigned Barangay and cannot provision or list peer Admins. See [ADR 023](decisions/023-dilg-reviewed-barangay-admin-registration.md).
- `DILG_ADMIN` is limited to Barangay application review and its own account sessions. Django superusers retain platform account recovery and can serve as fallback onboarding reviewers; neither role receives normal Barangay service access through that role alone.

Tenant scope is derived and enforced by the backend. A client-supplied barangay identifier does not grant access to another tenant's records. See [Security and RBAC](09-security-and-rbac.md) and [ADR 004](decisions/004-multi-tenant-isolation.md).

## Core capabilities

- Resident registration, identity evidence review, account sessions, and profile lifecycle.
- Document requests, explicit fee assessment, statutory waivers, manual payment evidence review, and official-receipt controls.
- Digital and in-person queue workflows.
- Announcements, activities, FAQs, emergency hotlines, and notifications.
- Assistance requests, incident reports, resident directories, and scoped analytics.

## Architecture records

Accepted decisions and their current status are listed in [the ADR index](decisions/README.md). Internal Django app and database identifiers such as `gridy_auth` are implementation names and remain unchanged unless a separate, migration-safe project is approved.
