# Authorized Security Assessment — Scope Draft

**Status:** Prepared for review; no assessor has been contacted or authorized and no assessment is scheduled or completed.

## Goal

Have an independent assessor evaluate the deployed KapitBayan web, API, and mobile service boundaries with written authorization, a defined time window, and agreed safety limits. The output should distinguish verified vulnerabilities from observations and include severity, evidence, remediation, and retest status.

## Proposed in-scope areas

- Authentication, password reset, token refresh, logout, and account recovery.
- Role and Barangay isolation for Barangay Admin, Field Official, Resident, and platform operator accounts.
- Document request lifecycle, queue ticket creation/advancement, and duplicate/race handling.
- Payment evidence, fee/waiver controls, O.R. assignment, and certificate-verification QR lookup.
- Registration/profile image upload and private-media access controls.
- Notification payloads and record-specific deep links.
- TLS configuration, security headers, API input validation, rate limits, and dependency exposure.

## Preconditions and safety limits

1. Name the assessor and obtain written authorization from the project owner and deployment owner before testing.
2. Agree on exact hosts, accounts, dates, request rates, test data, contact/escalation path, and stop conditions.
3. Use staging or dedicated test accounts and synthetic records. Do not access real residents' records, enumerate private files, alter or delete production data, or send messages to residents.
4. Do not perform denial-of-service, destructive tests, credential stuffing, social engineering, or tests against third-party providers without separate authorization.
5. Define whether mobile package testing and any production testing are allowed. Record exclusions explicitly.
6. Ensure a backup and operational contact are available for any permitted production test.

## Requested deliverables

- Scope, date/time window, assessor, tested release/commit, and test environment.
- Findings with reproducible but privacy-safe evidence, severity rationale, affected role/endpoint, and impact.
- Clear distinction between confirmed findings, informational observations, and untested areas.
- Remediation recommendations, retest results, and residual risks.

## Current engineering evidence (not a substitute)

The backend dependency review branch updates nine pinned packages. `pip-audit` reports no known vulnerabilities for that dependency set and the backend regression suite passes. These are automated dependency and functional checks only; they are not an independent security assessment or penetration test.

## Scheduling information still required

- Authorized assessor/provider and contact.
- Written authorization/signatory and approved host list.
- Preferred date/window and whether testing may touch production.
- Test-account provisioning owner and emergency stop contact.
