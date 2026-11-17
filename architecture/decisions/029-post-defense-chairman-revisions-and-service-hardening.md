# ADR 029: Post-Defense Chairman Revisions & Service Integrity Hardening

## Context

During the capstone oral defense and panel feedback review, the panel chairman identified operational and integrity risks across several user-facing and administrative services:
1. **Public Kiosk Equipment Borrowing Abuse Risk:** The public kiosk allowed borrowing requests without verifying who the borrower is or why they need it. Anyone visiting the physical kiosk could submit borrowing requests with unverified names.
2. **Backdated Activity Scheduling:** Staff could inadvertently or intentionally schedule community activities or announcements with elapsed dates or hours (e.g. creating an event for 1 hour earlier or a past date).
3. **Resident Mobile Issue Reporting Friction:** Residents reporting physical incidents (potholes, fallen trees, hazards) had to exit the app, take a picture using their native camera app, return to the app, and attach it from gallery. For emergencies or urgent situations, this caused unnecessary delay.
4. **Resident Mobile Issue Tracking Usability:** Residents lacked pagination and filtering for their submitted reports, making it hard to track active reports or find previous submissions when their report history grew.
5. **Administrative Report Customization (PDF/CSV/UI):** The administrative dashboard only supported standard monthly accomplishment reports. The Barangay requested custom date range filters (start date to end date) and selective metric toggles (e.g. only documents issued, or only newly registered residents) that synchronize identically across the on-screen dashboard preview, downloadable PDF, and CSV export.

## Decision

We enacted architectural and service enhancements across backend, frontend, and mobile clients:

### 1. Kiosk Borrowing Verification & Staff Authorization
- **Ephemeral Resident Sign-In vs. Supervised Walk-In:** Kiosk equipment borrowing now enforces an identity boundary:
  - **Resident Path:** Requires resident credentials (username/password) verified against tenant scope in an ephemeral transaction (`_authenticate_kiosk_resident`). No persistent session or cookie is left stored on the shared public kiosk device.
  - **Supervised Walk-In Path:** Requires the Barangay Staff Desk Passcode (`Barangay.kiosk_staff_pin_hash`).
- **Required Borrower Identity & Borrowing Rules:**
  - Mandatory fields: `walkin_contact` (7 to 15 digits), `walkin_purok` (non-empty), `borrower_id_type` (government/student/company ID), and `purpose` (minimum 10 characters).
  - Validation: `borrow_date` must be greater than or equal to current local Manila date (`timezone.localdate()`). Past borrowing dates are strictly rejected on create.
  - Admin Management: Barangay Admins configure and rotate the kiosk staff authorization PIN in Barangay Settings (`/settings`).

### 2. Activity Schedule Non-Past Enforcement
- Both backend `ActivityScheduleSerializer.validate_event_datetime` and frontend `ScheduleActivityModal` enforce `event_datetime >= timezone.now()`.
- Prevents creation of past-dated activities across same-day hours (e.g., 1 hour prior) and historical dates.

### 3. Mobile Issue Reporting Camera Access
- Integrated `ImageSource.camera` ("Take Photo") alongside `ImageSource.gallery` ("Choose Gallery") in `ReportIssueScreen`.
- Kept photo evidence optional so emergency reports can still be filed immediately without camera blockers.

### 4. Issue Reports Newest-First Ordering, Pagination & Query Filters
- Backend `IssueReportPagination` (`page_size=5`, customizable via `page_size` query param) with ordering by `-created_at`, `-id`.
- Added query filters: `status`, `category`, `urgency`, and `search`.
- Mobile `MyIssuesScreen` provides interactive status chips, category selector, search query input, and pagination controls (Previous/Next) with full date and time timestamps (`MM/dd/yyyy h:mm a`), backed by local offline snapshot pagination in `IssueService`.

### 5. Synchronized Multi-Format Accomplishment Reporting
- Unified report query params in `AccomplishmentReportService`:
  - `start_date` and `end_date` (ISO `YYYY-MM-DD`) supporting custom date spans, with fallback to `year` and `month`.
  - `metrics`: Comma-separated list of active metrics (`new_registered_residents`, `rbi_transfers`, `documents_issued`, `incidents`, `aid_requests`, `equipment_borrowing`, `communications`).
- Synchronized across:
  - `/api/v1/dashboard/accomplishment-report/` (JSON preview)
  - `/api/v1/dashboard/accomplishment-report/pdf/` (WeasyPrint PDF export)
  - `/api/v1/dashboard/accomplishment-report/csv/` (CSV tabular export)

## Consequences

- Prevents anonymous vandalism and untraceable equipment borrowing at physical barangay kiosks.
- Guarantees calendar activity data integrity without retroactive schedule pollution.
- Lowers friction for mobile incident reporting during emergency situations.
- Ensures administrative accomplishment reports can be customized for specific auditing windows or single-service audits (e.g. COA document fee audits or disaster incident summaries).
