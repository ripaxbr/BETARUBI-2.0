# WEBPLAY — Status

## Identidade
WEBPLAY é um projeto independente. O BETARUBI principal não faz parte desta aplicação.

## Base implementada
- UI responsiva com player, busca, voz, favoritos e navegação para TV.
- Catálogo de filmes, séries, audiolivros e TV.
- WEBPLAY Originals com séries verticais e modelo de acesso antecipado.
- PostgreSQL/Neon e Sentry preparados.
- Motor de descoberta global com limite de 50 canais por país e busca de mídia.
- Newsletter diária para assinantes com opt-in.

## Segurança de conteúdo
Descoberta não é autorização. Conteúdo de terceiros entra como inativo até existir evidência de licença, autorização oficial ou domínio público verificável para a edição utilizada.

## Operação
A publicação em produção deve ser feita somente após CI, health check, revisão de domínio e validação das variáveis de ambiente.