# M96: Block production test account logins

## Goal
Prevent known demo/test accounts from authenticating against the production API while keeping local development fixtures usable. Provide an environment-configured username denylist so production-only accounts can be blocked without publishing their identities or modifying production records.

## Non-goals
- Do not modify the production database, accounts, Render settings, or deploy the application.
- Do not block accounts by role, broad username patterns, or shared credentials.
- Do not commit local test-account inventories or passwords.
- Do not add database migrations or runtime dependencies.

## Evidence
- Production mobile login uses `CustomTokenObtainPairSerializer` in `backend/gridy_auth/serializers/auth.py`.
- Refresh sessions are validated in `backend/gridy_auth/views/token.py`.
- API access JWTs use SimpleJWT's `JWTAuthentication` configured in `backend/config/settings.py`.
- Local demo seeding is guarded by `require_local_demo_database`; its synthetic addresses use `.example.invalid` and legacy seed identities use `gridy.local`.

## Constraints
- Keep the intentionally created production DILG and test barangay accounts usable.
- Treat account identifiers as private configuration; do not add them to source or documentation.
- In production, deny blocked users at login, refresh, existing access-token authentication, and Django session authentication.
- Keep demo accounts available when `DEBUG=True`.

## Acceptance criteria
1. Production config can deny exact usernames from `BLOCKED_PRODUCTION_LOGIN_USERNAMES`, matched case-insensitively.
2. Seed identities using reserved synthetic domains `.example.invalid` and `gridy.local` are denied in production by default.
3. Denied users cannot obtain a new JWT, refresh an existing session, use a previously issued access JWT, or start a Django auth session.
4. A configured denial revokes the user's active refresh-session records upon a refresh attempt.
5. Normal users and all local (`DEBUG=True`) users continue to authenticate.
6. No production data/config is changed and no migration is generated.
7. Add regression tests and provide the production configuration instructions privately after merge; actual production rollout remains a separate, explicit step.
