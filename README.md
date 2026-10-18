# KapitBayan

KapitBayan is a web and mobile information and service system for barangays. The repository contains a Django REST API, a React web application for staff and resident use, and a Flutter mobile application for residents and field personnel. Internal Django package names such as `gridy_auth` remain part of the migration history and are not product names.

The platform supports resident document requests, manual fee assessment and treasury verification, queue services, assistance requests, incident reporting, communications, and public information. It records out-of-band payments but does not process funds through a payment gateway. Staff make service decisions; assistance eligibility and document approval are not automated.

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

## Documentation

Start at the [documentation index](docs/README.md) for current architecture, decision records, feature guides, and walkthroughs. The [system presentation flow](docs/presentations/system-demo-flow.md) gives a short product overview; the [barangay demo and training flow](docs/presentations/barangay-demo-and-training-flow.md) walks admins, staff, field officials, and residents through actual tasks. Printable copies are available for the [system overview](docs/presentations/system-demo-flow.pdf) and [barangay training flow](docs/presentations/barangay-demo-and-training-flow.pdf). The [Brevo email setup guide](docs/walkthrough/brevo-email-setup.md) covers deployed SMTP configuration and delivery checks. The [ADR index](architecture/decisions/README.md) records the accepted architectural decisions. Use the generated OpenAPI schema for exact request/response details.

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
