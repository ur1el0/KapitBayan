# Web Client Architecture (React)

The browser application is a React and TypeScript single-page application built with Vite. Route configuration is in `frontend/src/App.tsx`; authentication state, API clients, layouts, and page-level feature code live under `frontend/src/`.

## Route groups

| Route group | Access | Purpose |
|---|---|---|
| `/login`, `/official-login`, `/register`, password-reset routes | Public | Resident access and barangay staff sign-in |
| `/public/queue/:barangayId`, `/public/announcements/:barangayId` | Public | Read-only public displays |
| `/dashboard`, `/documents`, `/queue`, `/communications`, `/residents`, `/reports`, and related staff routes | `ADMIN`, with additional route-level restrictions where configured | Barangay staff workspace |
| `/platform/accounts` | Active Django superuser | Bounded account recovery and status support |
| `/portal/documents`, `/portal/queue`, `/portal/bulletin`, `/portal/aid` | `RESIDENT` | Resident self-service |

`/aid-requests` has an additional `ADMIN` route guard. Public barangay applications and their review routes have been retired; existing application rows are retained as read-only history for superusers. `FIELD_OFFICIAL` has no web staff workspace in the current router and uses the Flutter client; browser login for that role is rejected. These are UI route guards; the API remains the authorization boundary. The Field Official API token is not cryptographically bound to a native device.

## API and authentication

The web API client is configured in `frontend/src/api/`. Access credentials are used for authenticated requests; refresh is handled through the backend's HttpOnly cookie contract. The production build defaults to the relative `/api/v1` base when `VITE_API_BASE_URL` is unset, matching the intended reverse-proxy topology. Do not place provider secrets or private media URLs in browser code.

See [ADR 002](decisions/002-httponly-jwt-cookie-auth.md), [ADR 003](decisions/003-openapi-contract-driven-development.md), and [API contracts](06-api-endpoint-contracts.md).

## Feature boundaries

- Route components compose pages and layouts; domain components live under `frontend/src/components/`.
- API access should go through the existing API modules and client instances.
- Keep resident and staff workflows visually distinct. Do not add a role-switch shortcut unless a separately reviewed decision changes the current route contract.
- Announcement sharing generates an in-app share kit. Staff publish externally themselves; KapitBayan does not automatically post to Facebook or manage Facebook comments.
- Barangay `ADMIN` users can provision, list, edit the allowed profile fields of, and activate/deactivate Field Official accounts from `/settings`; operations are scoped to the administrator's barangay. Account setup uses an expiring email link rather than an administrator-set password.

For supported screens and workflows, see [Feature Guides](../docs/README.md#feature-guides).
