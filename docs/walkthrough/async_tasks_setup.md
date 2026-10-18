# In-Process Background Work

KapitBayan does not use Celery or Redis for the background operations described by [ADR 009](../../architecture/decisions/009-simplification-to-defended-proposal-architecture.md). Selected email and Firebase Cloud Messaging work is dispatched using daemon threads in the Django process.

## Operational behavior

- Returning an API success response means the application accepted the operation; it does not prove that the email provider or FCM delivered it.
- A process restart or termination can interrupt an in-flight task.
- The current thread wrapper does not provide a persistent queue, retry schedule, delivery record, or cross-process coordination.
- Exceptions are handled/logged by the task implementation; raw private resident data must not be included in task logs.

These operations are best-effort. Do not describe them as durable jobs or promise delivery guarantees. If product or LGU requirements need durable retries, propose a separate reviewed outbox/worker design and update ADR 009 before introducing a queue or broker. ADR 013 records the pilot limits and the remaining owner decisions.

## Local verification

Use mocked provider calls in tests. Do not send real email or push messages during ordinary test runs. Configure SMTP or email API credentials and Firebase credentials only in local ignored environment files or an approved deployment secret store; never commit service-account JSON or provider keys.
