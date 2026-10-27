# KapitBayan

KapitBayan is a web and mobile information and service system for barangays. The repository contains a Django REST API, a React web application for staff and resident use, and a Flutter mobile application for residents and field personnel. Internal Django package names such as `gridy_auth` remain part of the migration history and are not product names.

The platform supports resident document requests, manual fee assessment and treasury verification, queue services, assistance requests, incident reporting, communications, and public information. A new Barangay's first Admin applies with an official email and password; DILG independently verifies the locality and official before approval activates that same account. DILG review is limited to onboarding and does not expose resident or service records. Only Residents choose usernames. Barangay Admins and Field Officials sign in with email; Admins manage Field Official accounts for their own Barangay and cannot create peer Admin accounts. It records out-of-band payments but does not process funds through a payment gateway. Staff make service decisions; assistance eligibility and document approval are not automated.

## Download the Android app

[**Download the latest Android APK directly**](https://github.com/ur1el0/KapitBayan/releases/latest/download/KapitBayan-Android-v1.0.5.apk) (v1.0.5). This link downloads the APK file directly instead of opening the GitHub Releases page. Android may ask you to confirm installation from your browser or file manager. Install only APKs published by this repository.

## Architecture and API

- Backend: Django and Django REST Framework in `backend/`.
- Web: React, TypeScript, and Vite in `frontend/`.
- Mobile: Flutter in `mobile/`.
- Backend authentication and API docs: SimpleJWT and `drf-spectacular`.
- Database: PostgreSQL in hosted and Docker environments. The production database is Neon; tests may use SQLite where configured.
- Media storage: Cloudinary stores uploaded evidence and documents; private evidence is served through authenticated backend views.
- Push notifications: Firebase Cloud Messaging (FCM), using Firebase Messaging in the mobile app and Firebase Admin in Django.
- Email: the deployed Render service uses the Brevo SMTP relay on port 2525 with TLS. The built-in Resend HTTPS backend remains an alternative if SMTP is unavailable; local development defaults to Django SMTP.
- Error monitoring: Sentry SDK support, enabled when `SENTRY_DSN` is configured.
- Production hosting: Vercel hosts the web app and rewrites `/api/v1` to the Django API on Render. The API connects to Neon through `DATABASE_URL`.
- Local services: Docker Compose runs the development database and application services; Nginx serves the local web build and proxies API requests.
- Background delivery: email and push dispatch currently uses in-process daemon threads. There is no Celery or Redis task queue, so delivery is best effort.
- Exact endpoint contracts: generated OpenAPI at `/api/schema/` and Swagger UI at `/api/schema/swagger-ui/` when the API is running.
- Database schema and migrations: Django models and migration files. Do not infer schema from historical documentation.

The web client is configured for a same-origin API proxy, while mobile clients call the configured API URL. Private identity and payment evidence is served through authenticated backend views; never construct public evidence URLs. Provider selection describes the current deployment configuration; check provider dashboards for live service health and environment values.

Admin web Documents and Residents lists refresh automatically while their pages are open. See the [web frontend guide](docs/features/frontend_features.md#admin-list-refresh) for the covered lists, cadence, and focus behavior.

## Documentation

Start at the [documentation index](docs/README.md) for current architecture, decision records, feature guides, and walkthroughs. The [system presentation flow](docs/presentations/system-demo-flow.md) gives a short product overview; the [barangay demo and training flow](docs/presentations/barangay-demo-and-training-flow.md) walks admins, staff, field officials, and residents through actual tasks. The [barangay training flow PDF](docs/presentations/barangay-demo-and-training-flow.pdf) is available to print. The system overview PDF is an older export; use its current [Markdown source](docs/presentations/system-demo-flow.md) for the updated Barangay onboarding steps. The [Brevo email setup guide](docs/walkthrough/brevo-email-setup.md) covers deployed SMTP configuration and delivery checks. The [ADR index](architecture/decisions/README.md) records the accepted architectural decisions. Use the generated OpenAPI schema for exact request/response details.

## Local development with Docker Compose

Requirements: Docker Compose and Git.

1. Copy the example files. Set a local-only PostgreSQL password and a Compose database URL in the root `.env` (host `db`, port `5432`, database `gridy_db`, user `gridy_user`):

   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   ```

2. Set a local Django secret in `backend/.env`. Keep both environment files untracked; do not put production credentials in a local file or container image.
3. Start the local stack:

   ```bash
   docker compose up --build
   ```

Compose starts PostgreSQL, runs migrations in a one-shot service, then starts Django's development server and the Nginx-served web build. It is for local development and demos, not production. Ports and service names are defined in `docker-compose.yml`.

## Run clients without Docker

### Backend

This runs Django directly on the computer. If using PostgreSQL, the database can stay in the local Compose container. From the repository root, create the ignored environment files if needed:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

Set a local `SECRET_KEY` in `backend/.env` and set its `DATABASE_URL` to use host `127.0.0.1`, port `5433`, database `gridy_db`, and user `gridy_user`. Set the same local database password in the root `.env` as `POSTGRES_PASSWORD`, then start only the local database with `docker compose up -d db`. Keep these credentials separate from Neon or any other production database.

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py check
python backend/manage.py runserver 0.0.0.0:8000
```

Run migrations only against the configured local URL. Do not run seed or demo commands against deployed databases.

### Web

```bash
cd frontend
npm ci
npm run dev
```

### Mobile

```bash
cd mobile
flutter pub get
flutter devices
```

For an Android emulator, run `flutter run -d emulator-5554` (replace the example ID with the one shown by `flutter devices`); debug builds default to the host API at `10.0.2.2:8000`. For a physical Android phone over USB, keep the local API running, forward its port, and launch with the forwarded URL:

```bash
adb devices
adb reverse tcp:8000 tcp:8000
cd mobile
flutter run -d DEVICE_ID --dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Replace `DEVICE_ID` with the ID shown by `flutter devices`. For Wi-Fi testing, use the laptop LAN IP in the API URL (for example, `http://192.168.1.25:8000/api/v1`), bind Django to `0.0.0.0:8000`, add the LAN IP to `ALLOWED_HOSTS`, and allow port `8000` through the local firewall. Do not embed provider credentials in a client build. See [mobile setup](mobile/README.md) and the [mobile barangay pilot test flow](docs/testing/mobile-barangay-pilot-flow.md).

## Verification commands

Run relevant suites for changed code and follow the task packet's required validation:

```bash
./venv/bin/pytest backend
npm --prefix frontend run lint
npm --prefix frontend run test -- --run
npm --prefix frontend run build
cd mobile && flutter analyze && flutter test
```

These are example commands, not a report that the current checkout has passed them. Record actual output and any unavailable checks in the active task status.

## What the system does

KapitBayan connects residents with their Barangay's services through a web portal and Android app. The Django API is the source of truth: clients submit requests to it, the API checks the account's role and Barangay scope, and PostgreSQL stores the resulting records and statuses.

### User roles

- **Residents** register for their Barangay, view public information, request available documents, follow request and queue statuses, submit assistance requests and issue reports, and review announcements, schedules, FAQs, and hotlines.
- **Barangay Admins** review resident accounts and service requests, configure document offerings, manage queue operations and walk-ins, process assistance requests and reports, publish announcements and schedules, maintain public information, and manage Field Official accounts for their Barangay.
- **Field Officials** use their assigned accounts for the field workflows and records permitted to their role and Barangay.
- **Barangay Operators** review first-Admin applications and provide bounded account support. They do not use the operator role to browse resident service records. Platform recovery remains a separate, controlled Django superuser function.

### How document requests and queues work together

An Admin maintains the Barangay's document catalog, including each service's requirements, published amount, and instructions. Residents see the active catalog for their Barangay and submit a request with the details shown at that time. KapitBayan saves a snapshot of those details with the request, so later catalog edits do not rewrite an existing application. Staff still review the request and assess or waive fees through the documented process.

A resident can optionally create a counter queue ticket from a document request when they need an in-person visit. The ticket records the visit and its purpose; it does not approve, pay for, or release the document. Document processing and queue position are separate workflows, and either can exist without the other. Residents may also receive a general queue ticket for another service.

### Payments, notifications, and public sharing

- KapitBayan records manual cash or electronic-payment evidence for staff review. It does not connect to a payment gateway or automatically confirm settlement. Staff verify transfers and record the Official Receipt before release when required.
- Queue, document, report, and announcement updates can trigger push notifications where FCM is configured and the resident has enabled them. Provider acceptance is not proof that a device displayed the notification; delivery is best effort.
- The Admin notification bell is a database-backed in-app alert and is separate from mobile operating-system push notifications.
- Web and mobile queue views refresh from API endpoints using periodic HTTP polling. This is near-real-time refresh, not a WebSocket stream or a strict latency guarantee; refresh intervals vary by screen.
- The announcement share tool can create a public notice link and a QR code for that link. The QR is for sharing public announcement content; it is not an identity, payment, queue, or document verification credential.
- Email is sent through the configured provider. The current production setup uses Brevo SMTP; delivery should be checked in the application and provider logs, since a generic success message alone does not prove inbox delivery.

### Security and service boundaries

The Django API enforces role checks and Barangay tenant scope for protected operations. A user cannot gain another Barangay's access by changing a client-side identifier. Private identity, onboarding, and payment evidence is served through permission-checked backend paths in the configured private-media deployment. Upload rules differ by endpoint; file validation does not prove an image or document is genuine, and the reviewed implementation does not perform duplicate-image matching.

Human staff make the service decisions. The platform does not automatically determine aid eligibility, verify legal authenticity of submitted documents, settle bank transfers, publish posts to external social media, or provide emergency response. For immediate danger, residents must contact official emergency services or Barangay hotlines.

### Where to learn more

- [Architecture overview](architecture/01-system-overview.md) and [core service workflows](architecture/08-core-feature-workflows.md)
- [Security and role-based access](architecture/09-security-and-rbac.md)
- [Feature guides and developer walkthroughs](docs/README.md)
- [System demo flow](docs/presentations/system-demo-flow.md) and [Barangay demo and training flow](docs/presentations/barangay-demo-and-training-flow.md)
- [Brevo SMTP setup and troubleshooting](docs/walkthrough/brevo-email-setup.md)

For the direct APK link, update the asset filename in this README when publishing a later release with a differently named APK asset.
