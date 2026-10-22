# KapitBayan Web Frontend

The web client is a React, TypeScript, and Vite application for barangay staff and residents.

## Local development

Start the local Django API using the [root README host development setup](../README.md#run-clients-without-docker). The Vite development server uses `http://localhost:8000/api/v1` by default. To override the API URL or feature flags, copy the example environment file and edit the values:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

`VITE_API_BASE_URL` controls the development API base URL. Production builds use the same-origin `/api/v1` route configured by the deployment, regardless of that development setting. Never place secrets in `VITE_*` variables; Vite embeds them in client-side assets.

## Admin list freshness

Admin Documents and Residents views refresh automatically. The [Web Frontend Features guide](../docs/features/frontend_features.md#admin-list-refresh) lists the covered data, cadence, and focus behavior.

## Checks

```bash
npm run lint
npm test
npm run build
```

## Related project docs

- [Root README and application quickstart](../README.md)
- [System overview](../architecture/01-system-overview.md)
- [Security and RBAC](../architecture/09-security-and-rbac.md)
- [Testing and QA matrix](../architecture/10-testing-and-qa-iso25010.md)
