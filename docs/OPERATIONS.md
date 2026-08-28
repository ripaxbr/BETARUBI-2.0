# Operations

Health endpoint: `/api/health`.

Required production environment: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD`.
Optional: `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`.

Never expose environment values in logs or client responses.
