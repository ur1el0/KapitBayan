# Architecture Decision Records

This index lists the decision records present in this repository snapshot. Read the relevant ADR before changing an architectural boundary. An ADR documents a decision and its context; it does not prove that a deployment or external integration is active today.

| ADR | Decision |
|---|---|
| [001](001-django-drf-backend-baseline.md) | Django and Django REST Framework backend baseline |
| [002](002-httponly-jwt-cookie-auth.md) | HttpOnly secure JWT cookie authentication |
| [003](003-openapi-contract-driven-development.md) | OpenAPI contract-driven development |
| [004](004-multi-tenant-isolation.md) | Strict multi-tenant data isolation |
| [005](005-session-revocation.md) | Stateful session revocation |
| [006](006-walkin-and-legacy-clearance-architecture.md) | Walk-in and legacy clearance architecture |
| [007](007-revenue-and-official-receipt-auditing.md) | Treasury revenue and Official Receipt auditing |
| [008](008-dual-portal-role-segregated-auth.md) | Role-segregated resident and staff web portals |
| [009](009-simplification-to-defended-proposal-architecture.md) | Simplified, low-dependency architecture |
| [010](010-adviser-approved-service-workflows.md) | Adviser-approved resident service workflows |
| [011](011-verified-barangay-onboarding-and-manual-payment-recipients.md) | Verified barangay onboarding and manual payment recipients |
| [012](012-legacy-rbi-import-audit-provenance.md) | Legacy RBI import audit provenance |
| [013](013-pilot-notification-and-throttle-guardrails.md) | Pilot notification and throttle guardrails |
| [014](014-safe-schema-rollout-compatibility.md) | Safe schema rollout across application revisions |
| [015](015-private-acr-image-build-path.md) | Private ACR image build and publish path |
| [016](016-shared-database-api-throttling.md) | Shared database API throttling |
| [017](017-manual-epayment-evidence-and-verification.md) | Manual e-payment evidence and verification |
| [018](018-explicit-document-fee-assessment-and-waiver-provenance.md) | Explicit fee assessment and waiver provenance |
| [019](019-public-information-ai-navigator-boundary.md) | Retired: former Public Information AI Navigator boundary |
| [020](020-dilg-account-support-boundary.md) | Superseded: historical bounded DILG account support and recovery |
| [021](021-barangay-only-product-scope-and-platform-recovery.md) | Barangay tenant scope and superuser platform recovery; onboarding reviewer scope amended by ADR 023 |
| [022](022-reviewed-new-barangay-onboarding.md) | Superseded: initial reviewed public application and operator-created first Admin flow |
| [023](023-dilg-reviewed-barangay-admin-registration.md) | DILG-reviewed Barangay Admin self-registration using official email |
| [024](024-barangay-onboarding-email-and-authority-evidence.md) | Email verification and private authority evidence for Barangay onboarding |

## Implementation notes

- ADR 008's role-separation decision remains relevant. Its proposed hidden role-switch controls are not present in the current `frontend/src/App.tsx`; see the note in that ADR before describing or implementing those controls.
- ADR 009's polling and low-dependency direction is current; queue updates use HTTP requests. Notifications remain in-process and best-effort under ADR 013. Scoped API throttles use PostgreSQL under ADR 016; general-purpose `LocMemCache` remains process-local.
- ADR 015 records a private Azure Container Registry image path, not an approval to deploy the application to Azure. Azure remains subject to its separate readiness/owner gate.
