# API Endpoint Contracts

The Django URL configuration and generated drf-spectacular schema are the API contract. This page is a route-family map only; it intentionally does not copy payload fields that can drift. Inspect `/api/schema/` or Swagger UI at `/api/schema/swagger-ui/` in a running local environment for current operations, serializers, permissions, and request/response schemas.

## Route families

All application API routes are mounted below `/api/v1/` unless noted.

| Prefix or route | Owner | Purpose |
|---|---|---|
| `/auth/` | `gridy_auth` | Resident registration, login, refresh, logout, profile, resident verification/import, public Barangay directory and pending-only onboarding applications, sessions, barangay-scoped staff management, and superuser-only platform account/application review |
| `/document-requests/` | `gridy_services` | Digital and walk-in document request lifecycle, fee assessment, payment evidence, receipt and PDF operations |
| `/tickets/` | `gridy_services` | Ticket creation, resident status, staff queue operations, and live desk status |
| `/aid-requests/` | `gridy_services` | Assistance request submission and authorized review |
| `/payment-recipients/` | `gridy_services` | Barangay payment recipient configuration and retrieval under role/tenant policy |
| `/reports/` | `gridy_reports` | Resident issue submission and staff triage |
| `/announcements/`, `/activities/`, `/faqs/`, `/hotlines/`, `/devices/`, `/admin-notifications/` | `gridy_communications` | Communications, public information, device registration, and notification administration |
| `/public/barangays/<id>/queue-status/` | `gridy_services` | Public queue display data |
| `/dashboard/summary/` | `gridy_services` | Barangay- and role-scoped reporting |
| `/health/live/`, `/health/ready/` | `config` | Liveness and dependency readiness checks |

The current payment-proof view is mounted at `/api/v1/document-requests/<pk>/payment-proof/`; a compatibility alias is `/api/v1/documents/<pk>/payment-proof/`. Both paths must preserve the same authentication, ownership/tenant policy, and private response headers.

The schema browser is mounted at `/api/schema/` and `/api/schema/swagger-ui/`; those schema URLs are outside the `/api/v1/` prefix.

## Authentication and data handling

The web client uses the configured token and HttpOnly refresh-cookie contract. Native clients use the configured API base URL and do not receive server provider credentials. Private identity, billing, and payment evidence is accessed through authenticated media views, never by returning a public storage URL.

## Contract maintenance

When changing an endpoint, update its serializer/schema decorators and focused API tests. Verify role and same-barangay behavior, error semantics, and media headers. Use the generated schema and URL configuration for exact details; old examples in historical task packets are not authoritative API documentation.

See [ADR 003](decisions/003-openapi-contract-driven-development.md), [Security and RBAC](09-security-and-rbac.md), and [API Specification Guide](../docs/features/api_specification.md).
