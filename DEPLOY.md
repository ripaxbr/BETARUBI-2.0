# Deploy

1. Conecte `ripaxbr/BETARUBI-2.0` à Vercel.
2. Configure `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD` e `SENTRY_DSN`.
3. Use `main` como Production Branch.
4. Execute `db/schema.sql` uma vez no Neon de produção.
5. Valide `/api/health` após o primeiro deploy.
