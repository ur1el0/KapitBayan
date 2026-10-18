# System Verification Playbook

Use this checklist in a local or disposable test environment. Do not use real resident data, production credentials, or a production database. Record the exact code revision and commands in the active task's status record.

## Resident flow

1. Register or use an authorized synthetic resident account; verify registration requires the configured evidence and consent fields.
2. Submit a document request and confirm its tenant, status, and assessment provenance.
3. Verify payment controls stay unavailable before `READY_FOR_PICKUP`.
4. For a payable request, test the CASH path and a manual transfer submission using a test recipient. Confirm submitted proof remains private and is not treated as automatically verified.
5. Verify authenticated residents can read only their own request, queue, profile, and media records.
6. Check bulletins, activities, assistance, and reporting using the current route tree and generated API schema.

## Staff and tenant flow

1. Use synthetic accounts with known barangay assignments and role scope.
2. Verify an authorized staff member can review only the intended barangay's records.
3. Test cross-tenant object IDs, unassigned staff, residents, and legacy/unknown role accounts against endpoint-specific authorization rules.
4. Record an explicit fee assessment or waiver, manually verify electronic payment against a test transaction, record the O.R., and verify the server-side release gate.
5. Verify walk-in records keep barangay and treasury history without requiring a synthetic login account.

## Communications

1. Verify announcement sharing creates a shareable link/kit only; KapitBayan does not automatically publish to Facebook or control external comments.
2. Treat email and push sends as best-effort and verify them only with synthetic accounts and a test provider setup.

## Checks by layer

Run only the checks relevant to the change and its task contract:

```bash
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
./venv/bin/pytest backend
npm --prefix frontend run lint
npm --prefix frontend run test -- --run
npm --prefix frontend run build
cd mobile && flutter analyze && flutter test
```

Some commands require local credentials, databases, or SDKs. Record unavailable checks as unverified; do not substitute remembered results. For cloud behavior, verify the active revision, hostnames, secrets, routing, and provider logs separately. See [Deployment and Observability](deployment_observability.md).
