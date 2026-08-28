# Architecture

Browser -> Flask/Vercel -> Neon PostgreSQL. Sentry observes application errors and performance. The worldwide crawler is a separate maintenance process and never runs automatically inside web requests.
