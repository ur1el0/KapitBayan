# Mobile Client Architecture (Flutter)

The mobile application is implemented in Flutter and Dart under `mobile/lib/`. Its current organization separates screens, reusable widgets, models, services, core networking/configuration, and theme code. It does not use the BLoC package or a `blocs/` layer; describe state management from the actual feature implementation rather than assuming BLoC.

## Main code areas

```text
mobile/lib/
├── core/       # API configuration, network client, feature flags, theme
├── models/     # API and UI data models
├── screens/    # Role-specific and resident-facing screens
├── services/   # API and device service coordination
└── widgets/    # Reusable presentation components
```

Authentication and role checks select the appropriate experience for residents, barangay administrators, and field officials. Client-side role branching improves navigation; backend permissions and tenant scoping remain authoritative.

Field Officials use the Flutter client for their supported staff workflow and sign in with their official email. Barangay administrators provision and manage these accounts in the web settings page without assigning usernames. Residents retain username-based registration and sign-in. The API token is not cryptographically bound to a mobile device, so “mobile-only” describes the supported product workflow and browser-role restriction, not device attestation.

## Network and privacy boundaries

The mobile app calls the Django API using the configured `API_BASE_URL` build value. Do not embed Firebase service-account or other server credentials in the app. Private identity, billing, and payment evidence is accessed through authenticated backend media endpoints; do not construct public storage URLs for it.

## Notifications and asynchronous behavior

Firebase Messaging is used where the project is configured for push delivery. Screen refresh and queue status also use API requests; do not describe this as WebSocket delivery unless an implemented and tested socket contract is added. The backend's in-process background work is best-effort and does not provide a durable queue. See [ADR 009](decisions/009-simplification-to-defended-proposal-architecture.md) and [Deployment](11-deployment-and-ci-cd.md).

## Verification

Run Flutter commands from `mobile/`. The authoritative commands and environment setup are linked from the [documentation index](../docs/README.md#developer-walkthroughs); test totals change over time and are intentionally not frozen in this architecture page.
