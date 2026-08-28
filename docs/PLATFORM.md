# WEBPLAY — platform status

WEBPLAY is an independent rebuild. The original BETARUBI project is not part of this application.

## Isolation requirements
- Separate repository/workflow identity.
- Separate PostgreSQL/Neon database.
- Separate Vercel project/deployment.
- Separate production domain when one is provisioned.
- Separate secrets and API credentials.

## Current implementation
- Flask application with PostgreSQL/Neon.
- Responsive catalog/player for films, series, TV and audiobooks.
- WEBPLAY Originals and episode-access model.
- Rights-aware discovery pipeline.
- Daily discovery workflow and opt-in newsletter.
- Sentry integration without credentials committed to Git.

## Provisioning gates
The project is not considered production-ready until the dedicated Vercel project, Neon database credentials and optional Sentry DSN are configured and `/api/health` returns `ok=true`.
