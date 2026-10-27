# KapitBayan Mobile Barangay Pilot Test Flow

Use this checklist after the mobile and FAQ changes are merged and deployed to the intended test backend. It is a pre-pilot acceptance flow, not proof that the app has passed testing.

## 1. Prepare accounts and test data

Prefer a staging backend and disposable database. If testing against production is unavoidable, use a designated test Barangay and accounts with synthetic data, and agree on cleanup with the Barangay admin first. Do not submit real residents' IDs, contact details, aid requests, fees, or other personal information.

Prepare separate accounts:

- **Resident A:** assigned to the test Barangay.
- **Resident B:** assigned to a different Barangay, for checking tenant isolation.
- **Barangay Admin:** manages that Barangay's published content in the staff web portal.
- **Field Official:** exercises only field actions supported by the mobile app.

Record the APK/app version, backend deployment commit, Redmi model and Android version, network, role, test time, and outcome. Never include passwords, tokens, cookies, or real resident details in evidence.

## 2. Run local checks before using the phone

From the repository:

```bash
cd mobile
flutter pub get
flutter analyze
flutter test
flutter devices
```

Confirm GitHub Actions is green for the exact commit being evaluated.

## 3. Check the backend

For a normal readiness check, run:

```bash
curl -sS --connect-timeout 10 --max-time 45 \
  -H 'Accept: application/json' \
  -i https://gridy.onrender.com/api/v1/health/ready/
```

Expect HTTP 200 with healthy JSON. Do not call this endpoint immediately before the cold-start test because it may wake the service.

## 4. Run the app on the Redmi

Connect the phone over USB, enable USB debugging, and accept the computer prompt. Find its current device ID:

```bash
flutter devices
```

Launch against the direct API host (replace the example device ID if needed):

```bash
flutter run -d DEVICE_ID \
  --dart-define=API_BASE_URL=https://gridy.onrender.com/api/v1
```

Replace `DEVICE_ID` with the ID shown by `flutter devices`. Do not use `localhost` for the deployed API. For a local backend over USB, first run `adb reverse tcp:8000 tcp:8000`, then use `--dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1`.

## 5. Test authentication by role

On a fresh install, sign in separately as Resident A, Barangay Admin, and Field Official. If registration is in scope, create a synthetic resident account. For each role, check the expected landing screen, sign out, sign in again, force-close/reopen, and confirm the app handles an expired session clearly. Protected actions should not become available to a different role.

When an attempt fails, record the time, role, action, API path, status code, duration, and exact user-facing message. Keep secrets and personal data out of screenshots and logs.

## 6. Verify staff-to-resident FAQs

Using the **Barangay Admin** account in the staff web portal:

1. Create a clearly marked test FAQ in the Barangay's resident audience.
2. Edit its question or answer, save, and reload to check persistence.
3. Unpublish it and confirm it no longer appears to residents.
4. Republish, then delete the test entry and confirm it disappears.
5. Confirm FAQs shown and managed by the Barangay Admin belong only to that Barangay; global legacy FAQs are not exposed through the current API.

Using **Resident A's mobile app and resident web portal**:

1. Open Help & FAQs from normal navigation.
2. Search for the test question and browse its category.
3. Expand and collapse answers, return to the page, and refresh.
4. Confirm only this Barangay's published resident FAQs appear; staff guidance, drafts, legacy global FAQs, and another Barangay's local FAQs do not.

Check common topics such as account access, document requests, queue and schedules, aid questions, notices, privacy, and safe help-seeking. Answers about eligibility, fees, required documents, processing times, office hours, or contacts must come from that Barangay's verified content.

## 7. Check usability for older adults and residents needing accessibility support

On the Redmi, increase Android font and display size and try the FAQ flow with TalkBack if available. On the web, test keyboard navigation and 200% zoom. Confirm that:

- headings and controls are understandable without relying on icons or color alone;
- text, expanded answers, and buttons remain visible without horizontal clipping;
- focus is visible and follows the page order;
- search, category selection, expand/collapse, and retry controls have clear labels;
- the guide explains larger text, how to find common services, and how to ask a trusted helper safely.

Never advise a resident to share a password, OTP, or identity document with a helper.

## 8. Test resident journeys

As Resident A, try dashboard refresh, notices, schedules, Help & FAQs, a synthetic document request and status check, queue actions if enabled, and other pilot services that the Barangay has approved. Have staff complete the supported corresponding action, then verify the resident sees the expected result.

For document payment/release checks, have the Barangay Admin save the sample O.R. using **Save O.R. number** without changing the request's status or fee. As the assigned Field Official, enter that O.R. in **Clearance & Receipt Validator** and confirm it finds the same-Barangay record. Repeat with its printed tracking ID, an unknown O.R., and a record belonging to another Barangay; unknown and cross-Barangay identifiers must not reveal records. The validator checks KapitBayan's saved identifier only; it is not proof that a transfer settled or that a paper receipt is genuine.

For hotline links, verify the displayed active number is Barangay-approved. It is safe to open the dialer and cancel; do not place an emergency call as a test.

As Resident B, confirm Barangay-specific records follow the intended visibility rules and cannot be accessed by changing an item ID. Do not probe using another real resident's records.

## 9. Exercise poor connectivity and cold start

1. Turn on airplane mode and open a page that needs the network. Confirm there is a clear error and retry action rather than an endless spinner or crash.
2. Restore connectivity and retry; confirm the page recovers without reinstalling or restarting the app.
3. Switch Wi-Fi/mobile data, background the app, return, and try the page again.
4. Let the backend idle until it may sleep. Without first pinging health, use the phone for the first request and time it.
5. After the first response, repeat navigation and note warm response times.

A failed first request, false offline message while the backend is reachable, request at the configured 35-second app timeout, crash, or repeated warm navigation above 5 seconds is a blocker or performance issue to triage before a barangay pilot.

## 10. Record results and make a go/no-go decision

For every step, mark **Pass**, **Fail**, or **Blocked** and attach a redacted screenshot/log snippet when useful. Treat cross-Barangay disclosure, unauthorized actions, lost/corrupted data, failed login/registration, repeated 5xx errors, and unhelpful connection failures as release blockers. Do not mark a path passed because its screen merely opened.

Proceed to a pilot APK only when all agreed resident and staff paths pass on the test backend, role and Barangay boundaries hold, connectivity errors recover, and the team has reviewed accessibility on a real device.

## 11. Pilot APK release gate

Before distribution, check the Android configuration. At the time this guide was written, the app ID is still `com.example.mobile` and the release build uses the debug signing key. Choose the permanent application ID and configure an owner-controlled release keystore before sharing an actual pilot APK. Keep the keystore and passwords out of Git and retain a secure backup.

After signing is configured, increment `version`/build number in `mobile/pubspec.yaml`, then build:

```bash
cd mobile
flutter build apk --release \
  --dart-define=API_BASE_URL=https://gridy.onrender.com/api/v1
```

Install the release APK on the Redmi, repeat a short clean-install and upgrade smoke test, verify its signature with `apksigner`, and record its version, source commit, backend, and SHA-256 hash. Distribute to the team first; share with barangay testers only after that release-candidate check passes.
