# Documentation Index

Use this page to find current system guidance. Source code, migrations, generated OpenAPI, accepted ADRs, and the active task packet are the authorities for implementation details. Historical pages and test output are not evidence of current runtime behavior unless checked against the current revision.

## System architecture

- [Architecture overview](../architecture/01-system-overview.md)
- [Web client](../architecture/02-frontend-web-react.md)
- [Mobile client](../architecture/03-frontend-mobile-flutter.md)
- [Backend](../architecture/04-backend-django-drf.md)
- [Data boundaries](../architecture/05-database-schema-postgresql.md)
- [API route map](../architecture/06-api-endpoint-contracts.md)
- [External integrations](../architecture/07-cloud-services-integration.md)
- [Service workflows](../architecture/08-core-feature-workflows.md)
- [Security and RBAC](../architecture/09-security-and-rbac.md)
- [Testing and QA](../architecture/10-testing-and-qa-iso25010.md)
- [Deployment and CI/CD](../architecture/11-deployment-and-ci-cd.md)
- [Project history](../architecture/12-agile-sprint-backlog.md)
- [Architecture Decision Record index](../architecture/decisions/README.md)

## Feature guides

- [Adviser-approved service workflows](features/adviser-approved-workflows.md)
- [API specification guide](features/api_specification.md) — route families and how to inspect the generated schema
- [Backend features](features/backend_features.md)
- [Bulk RBI census import](features/bulk_rbi_census_import.md)
- [Resident web portal](features/citizen_desktop_portal.md)
- [Web frontend features](features/frontend_features.md) — includes the Admin Documents and Residents auto-refresh behavior.
- [Walk-in clearances and treasury auditing](features/walkin_and_revenue_clearances.md)

## Developer walkthroughs

- [Developer onboarding](walkthrough/developer_onboarding.md)
- [Cloudinary and protected media](walkthrough/cloudinary_setup.md)
- [Firebase Cloud Messaging](walkthrough/firebase_fcm_setup.md)
- [In-process background work](walkthrough/async_tasks_setup.md)
- [Deployment and observability](walkthrough/deployment_observability.md)
- [Brevo SMTP email setup and troubleshooting](walkthrough/brevo-email-setup.md)
- [Nginx and web container](walkthrough/nginx_web_server_setup.md)
- [System verification](walkthrough/system_verification_playbook.md)
- [Mobile barangay pilot test flow](testing/mobile-barangay-pilot-flow.md)

## Demonstration guides

- [KapitBayan system demo flow](presentations/system-demo-flow.md) ([older PDF export](presentations/system-demo-flow.pdf))
- [Barangay demo and user-training flow](presentations/barangay-demo-and-training-flow.md) ([PDF](presentations/barangay-demo-and-training-flow.pdf))

## Domain and architecture guidance

This repository uses barangay, resident, field official, walk-in request, fee assessment, waiver, and Official Receipt as domain terms. Historical migrations and ADRs retain the terminology used when they were written; it does not imply an active government-wide product role. Before changing a workflow, inspect its models, serializers, permissions, tests, and current ADRs. Preserve tenant scoping and distinguish staff review from automated decisions. Do not describe public information as private evidence or treat a payment reference as proof of settlement.

ADRs are stored under `architecture/decisions/`. Read the relevant accepted decision before changing a domain boundary. If implementation and an ADR disagree, record the discrepancy and propose a reviewed decision update; do not silently rewrite the architecture in code or docs.

## Issue tracking and task history

GitHub Issues are the repository issue tracker. Use `gh issue view`, `gh issue list`, and other `gh` commands from a configured GitHub checkout; inspect repository remotes first when working in a local snapshot. Pull requests are reviewed delivery artifacts, not a substitute for an issue or task contract.

Scoped implementation packets, when present in a working environment, use `docs/ai-workflow/tasks/<task-id>/TASK_BRIEF.md`, `PLAN.md`, and `STATUS.md`. These files may be local workflow artifacts and are not necessarily included in the public repository. Treat a task's `STATUS.md` as a record of commands actually run, not as a guarantee about a later revision.

## Agent guidance and local tooling

Project-specific guidance under the root `.agents/` directory is tracked. Downloaded third-party skill packages under `.agents/skills/` and generated `.agents/ecc-install-state.json` are local developer tooling, are intentionally ignored by Git, and are not application dependencies.

## Setup and live status

Use the root [README](../README.md) for safe local setup commands. Deployment pages describe intended/configured topology; verify the hosting provider, active branch, secrets, and live health before claiming a service is deployed or available.
