# Implementation Plan: M90 Resident Queue Notification Inbox

## Overview
- **Brief:** [TASK_BRIEF.md](TASK_BRIEF.md)
- **Branch:** `fix/resident-notification-inbox`
- **Base:** GitHub `main` at `3caff91fe99bdbd6aa5bce679e7feec9a31a140f`
- **Complexity:** Medium

## Milestone 1: Persist queue pages and expose owner-scoped API
1. Add a resident notification model and reversible migration with a user/read/time index.
2. Add a read-only owner-scoped list API and a serializer that exposes no writable recipient/content fields.
3. Create the notification in the queue paging request before dispatching the existing asynchronous email/push task.
4. Add tests for create-on-page, owner isolation, and invalid page requests.

**Validation:** targeted queue/communications tests; Django check; migration check.

## Milestone 2: Show queue pages in the mobile Notification Center
1. Fetch the resident notification endpoint as part of dashboard loading.
2. Map persisted queue events into the current notification UI model and merge/sort them with existing synthesized items.
3. Add the queue alert icon/label and tests for decoding and display data.

**Validation:** targeted Flutter tests and `flutter analyze`.

## Milestone 3: Clarify email delivery logs and prepare PR
1. Log whether email was skipped due to preferences/address or accepted by the configured backend, without PII.
2. Run the affected regression suites and `git diff --check`.
3. Record actual results in STATUS.md and open a PR against `main`.

**Validation:** backend targeted tests; Flutter targeted tests/analyze; migration check; diff check.

## Rollback
Revert the PR and its additive migration if needed. The migration only creates the resident notification table and index; it does not alter or delete existing records. Do not run a production migration or deploy without explicit production authorization.
