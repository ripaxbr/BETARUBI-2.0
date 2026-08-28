# Deploy WEBPLAY

WEBPLAY é independente do BETARUBI principal. Não compartilhe banco, secrets, domínio ou deployment.

1. Conecte o repositório do WEBPLAY ao provedor de hospedagem.
2. Configure `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD` e `SENTRY_DSN`.
3. Para descoberta diária, configure `YOUTUBE_API_KEY`.
4. Para newsletter, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` e `SMTP_FROM`.
5. Use `main` como Production Branch.
6. Execute `db/schema.sql`/inicialização da aplicação no banco novo do WEBPLAY.
7. Valide `/api/health` e `/api/status` após o primeiro deploy.
8. Agende `motor_ia_global.py` diariamente somente após configurar as credenciais.

O motor de descoberta grava novas mídias como inativas até que a autorização/licença da fonte seja verificada. Isso evita publicar automaticamente material de terceiros sem comprovação de direitos.