---
name: Catálogo clínico em produção
description: Estado confirmado externamente e regra de evolução segura do schema clínico.
---

A estrutura inicial do catálogo clínico já foi aplicada no Supabase e deve ser tratada como schema histórico. Não fazer rollback destrutivo nem reescrever a migration inicial; evoluções devem usar migrations complementares e idempotentes.

**Why:** A aplicação inicial criou as sete tabelas clínicas e elas foram confirmadas com RLS habilitado e nenhuma policy cadastrada. Isso mantém acesso direto bloqueado por padrão. Campos clínicos legados continuam sendo a fonte operacional do sistema atual e não podem ser apagados, sobrescritos ou classificados automaticamente.

**How to apply:** Antes de executar qualquer complemento, conferir o schema e as policies reais. Manter RLS sem policy pública, `anon` ou `authenticated` permissiva e não alterar `problemas_saude`, `restricoes_fisicas` ou `tags_saude`. Novas telas só devem consumir o schema após uma estratégia backend compatível com o perfil SuperAdmin; service role só pode existir em segredo de servidor.

Enquanto SQL/RPC/trigger não estiverem autorizados, mutações administrativas de catálogo devem reservar o histórico antes de escrever, reconciliar pendências ativamente e manter casos ambíguos visíveis.

**Why:** Requisições PostgREST separadas não tornam a mudança de catálogo e a auditoria atômicas. A reserva prévia impede alterações sem rastro, e a reconciliação preserva transparência na janela entre a mutação e a finalização do histórico.

**How to apply:** Não adicionar novos caminhos de mutação que contornem a reserva e a reconciliação. Quando mudanças de schema forem permitidas, preferir uma RPC ou trigger transacional e preservar compatibilidade com pendências já registradas.