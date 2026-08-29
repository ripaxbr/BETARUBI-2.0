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

## Identidade e infraestrutura
O produto é **WEBPLAY**. O código, banco, domínio e deployment permanecem independentes do projeto BETARUBI principal.

As credenciais existentes do ambiente BETARUBI podem ser reutilizadas quando o usuário autorizar e quando forem compatíveis com o WEBPLAY, sem copiar valores para o repositório. Sempre que houver risco de compartilhamento indevido de dados, prefira banco/schema e recursos próprios do WEBPLAY.

## Segurança
Credenciais nunca devem ser commitadas. Configure `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD`, `SENTRY_DSN`, chaves de API e SMTP somente no ambiente de execução.
