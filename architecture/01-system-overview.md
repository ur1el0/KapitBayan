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
- A new Barangay's first `ADMIN` account is provisioned by an active Django superuser after reviewing and verifying its public onboarding application. The Admin manages Field Officials in the assigned Barangay and cannot provision or list other Admin accounts. See [ADR 022](decisions/022-reviewed-new-barangay-onboarding.md).
- Django superusers are platform operators, not a resident or barangay staff role. Their bounded account-recovery surface is isolated from normal barangay portals; legacy role values cannot authenticate.

Tenant scope is derived and enforced by the backend. A client-supplied barangay identifier does not grant access to another tenant's records. See [Security and RBAC](09-security-and-rbac.md) and [ADR 004](decisions/004-multi-tenant-isolation.md).

## Core capabilities

- Resident registration, identity evidence review, account sessions, and profile lifecycle.
- Document requests, explicit fee assessment, statutory waivers, manual payment evidence review, and official-receipt controls.
- Digital and in-person queue workflows.
- Announcements, activities, FAQs, emergency hotlines, and notifications.
- Assistance requests, incident reports, resident directories, and scoped analytics.

## Architecture records

Accepted decisions and their current status are listed in [the ADR index](decisions/README.md). Internal Django app and database identifiers such as `gridy_auth` are implementation names and remain unchanged unless a separate, migration-safe project is approved.
