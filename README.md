# WEBPLAY

Plataforma independente de streaming mundial, reconstruída do zero a partir da especificação do antigo BETARUBI 2.0.

## Escopo
- Filmes, séries, TV e audiolivros
- Player e busca mundial
- Favoritos e voz
- Navegação responsiva e Smart TV
- Originals: minisséries verticais inspiradas em obras em domínio público
- Modelo de acesso antecipado/premium
- Catálogo de obras com verificação jurídica por jurisdição/edição
- Motor de descoberta global e cadastro de canais
- Newsletter de atualizações para usuários inscritos
- PostgreSQL/Neon, Sentry e Vercel

## Identidade
O produto é **WEBPLAY**. Não depende do projeto BETARUBI principal e não deve compartilhar banco, domínio, secrets ou deployments com ele.

## Segurança
Credenciais nunca devem ser commitadas. Configure `DATABASE_URL`, `SECRET_KEY` e, quando aplicável, `SENTRY_DSN`, chaves de API e SMTP somente no ambiente de execução.