# Brevo email setup and delivery checks

KapitBayan sends account and notification email through Django's configured email backend. The deployed Render service is configured to use Brevo's SMTP relay on port 2525 with TLS. Local development continues to use the SMTP values in `backend/.env.example`; an HTTPS Resend backend is also available as an alternative.

## Render environment values

Set these values in the Render service's private environment settings. Do not put credentials in Git, the mobile app, screenshots, or support messages.

| Variable | Brevo value |
| --- | --- |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `smtp-relay.brevo.com` |
| `EMAIL_PORT` | `2525` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | The SMTP login shown by Brevo |
| `EMAIL_HOST_PASSWORD` | The Brevo SMTP key |
| `DEFAULT_FROM_EMAIL` | A sender address verified in Brevo |

The SMTP key is different from a Brevo API key and from the password used to sign in to Brevo. Save the environment changes and redeploy the service. Keep port 2525 for this relay configuration; do not substitute the common SMTP submission port 587 without checking the host's outbound network rules. If SMTP cannot connect in the hosted environment, the configured code also supports `config.email_backends.ResendEmailBackend` over HTTPS; see [Deployment and CI/CD](../../architecture/11-deployment-and-ci-cd.md).

## Verify one message

1. Confirm the sender is verified in Brevo and matches `DEFAULT_FROM_EMAIL`.
2. Use a test account and an inbox you control to request a password reset, or trigger a notification for a test resident who has email notifications enabled.
3. Check the Render application logs for dispatch or connection errors.
4. Open Brevo's transactional email logs and look for the recipient and send time. Check the mailbox's Spam folder as well.

KapitBayan uses background work inside the API process. A generic password-reset success response means the request was accepted by the endpoint; it does not confirm that an email was handed to Brevo or delivered. A healthy API probe also does not test SMTP.

## Troubleshooting

| What you see | What to check |
| --- | --- |
| Reset page says to check the inbox, but Brevo has no event | Confirm the account email matches exactly one user record, check for HTTP 429 throttling, then inspect Render logs for a dispatch failure. The response text is intentionally generic. |
| Render logs show an SMTP connection or authentication error | Recheck the relay host, port 2525, TLS setting, SMTP login, and SMTP key in Render. Do not print or paste the secret while troubleshooting. |
| Brevo logs show rejected, blocked, or bounced mail | Read the provider event reason, verify the sender, recipient address, and account-level delivery status in Brevo. |
| Brevo reports delivery, but the recipient cannot find the message | Check Spam, Promotions, filters, and mailbox rules; verify the recipient address. |
| A password-reset request returns HTTP 429 | Wait for the configured throttle window, then retry once. Repeated requests can prolong the wait and make the logs harder to inspect. |
| The account email is wrong or account recovery still fails | Ask an authorized platform operator to verify the account holder through an official channel and use the superuser-only Platform Account Support recovery flow. Do not send passwords or reset links through public or unverified channels. |

The endpoint deliberately returns the same success text for an unknown email and for an address that does not resolve to exactly one account record. This prevents account discovery but means that the page alone cannot diagnose delivery. The current notification and email dispatch helpers are best-effort and do not use a durable retry queue.

## Email preferences and push notifications

The resident's email notification preference controls optional service-update emails. Password-reset email is a separate account-recovery message. Mobile push is a separate Firebase Cloud Messaging channel and requires the resident to opt in, grant Android notification permission, and register a device token. Web profile settings do not register an FCM device. For the end-to-end demonstration and notification fallbacks, see the [system demo flow](../presentations/system-demo-flow.md).
