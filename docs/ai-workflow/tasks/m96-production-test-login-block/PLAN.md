# M96 implementation plan: production test login block

## Milestone 1: Shared production account policy — complete
1. Add a single helper that detects exact configured usernames and the repository's reserved synthetic email domains, only when `DEBUG=False`.
2. Apply the helper to Django's model authentication backend and SimpleJWT's user authentication rule.
3. Reject blocked users during refresh and revoke their active `RefreshSession` rows.
4. Add a blank `BLOCKED_PRODUCTION_LOGIN_USERNAMES` entry and safe setup notes to `backend/.env.example`.

## Milestone 2: Regression coverage and delivery record — complete
1. Test blocked login by username and email, refresh/session revocation, existing access-token rejection, and Django session login rejection.
2. Test local debug authentication and an ordinary production user remain allowed.
3. Run the focused auth tests, Django system checks, migration dry-run check, and `git diff --check` with a local test database.
4. Record exact results and outstanding production-only configuration in `STATUS.md`.

## Safety
- No production database URL, account list, or password is read or changed by these checks.
- Production usernames must be entered into Render's private environment settings after merge, excluding the manually created DILG and test barangay accounts.
- No database migration or deployment is part of this PR.
