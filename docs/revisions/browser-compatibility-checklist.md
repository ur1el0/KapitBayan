# Resident Web Browser Compatibility Record

This checklist tracks revision-matrix item 26. The matrix accepts a responsive resident web portal **or** a PWA, then asks for checks on Chrome, Edge, Firefox, and mobile Chrome. KapitBayan uses the responsive-web option; this record must contain actual manual results before the item is marked complete.

## Test record

| Browser | Version / OS | Viewport or device | Login and registration | Documents and queue | Layout / navigation | Result and evidence |
|---|---|---|---|---|---|---|
| Chrome desktop | Not recorded | Not recorded | Not tested | Not tested | Not tested | Pending manual verification |
| Microsoft Edge desktop | Not recorded | Not recorded | Not tested | Not tested | Not tested | Pending manual verification |
| Firefox desktop | Not recorded | Not recorded | Not tested | Not tested | Not tested | Pending manual verification |
| Chrome Android | Not recorded | Not recorded | Not tested | Not tested | Not tested | Pending manual verification |

## Minimum checks

1. Record the tested production or preview URL, date, browser version, operating system, and viewport/device.
2. Check resident registration and login, then open dashboard, document request, queue, announcements, and profile views.
3. Check horizontal overflow, readable text, form controls, navigation, dialogs, and keyboard focus where relevant.
4. Record failed cases with a screenshot and console/network details. Do not mark an unexecuted check as passed.

The current React web client has responsive CSS but no web app manifest or service worker. Flutter remains the separate Android app for residents and officials; this checklist does not claim PWA installation or offline web behavior.
