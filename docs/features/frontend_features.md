# Web Frontend Features

The web client is a React, TypeScript, and Vite application. Routes are defined in `frontend/src/App.tsx`; layouts and reusable UI live in `frontend/src/components/`; API calls live in `frontend/src/api/`.

## Authentication and route access

Resident self-service routes use the resident layout and `RESIDENT` guard. Staff routes use the administrative layout with the `ADMIN` guard and narrower guards for sensitive actions. The separate `/platform/accounts` route requires the superuser flag and does not use the barangay staff layout. The current router has no hidden keyboard role-switch shortcut. Field officials use the mobile client in the current route design. These client checks complement backend permissions; they do not replace them.

## Staff capabilities

Depending on role and barangay assignment, staff can process documents and fees, advance queues, manage announcements and activities, maintain residents and verification records, triage reports, and review authorized analytics. Barangay `ADMIN` users can also manage Field Official accounts from `/settings`, including allowed profile edits and activation status; account setup is sent through an expiring email link. Field Officials have no web staff workspace and use the Flutter client. Exact visibility is defined in the route tree and backend permission classes.

## Resident capabilities

Residents can use the portal to request documents, follow queue tickets, read community bulletins, and submit assistance requests. Available pages and paths are listed in [Resident Web Portal](citizen_desktop_portal.md).

## Communications

Staff can publish announcements and generate an announcement share kit. External Facebook distribution remains manual; KapitBayan neither posts automatically nor moderates external comments.

## Document evidence and media

Protected identity, billing, and payment evidence is accessed through authenticated media endpoints. Do not expose raw storage paths or public links in UI components. Use the shared modal/accessibility patterns for focus, labels, keyboard operation, and visible focus states.

## Frontend verification

Run `npm --prefix frontend run lint`, the focused Vitest suite for changed modules, and `npm --prefix frontend run build` when the task contract asks for those checks. See the [system verification playbook](../walkthrough/system_verification_playbook.md).
