---
name: Mensagens de aniversário (CRM)
description: Regra de qual texto e quando enviar parabéns de aniversário.
---

Toda mensagem de parabéns (WhatsApp, e-mail, Z-API, grid) deve usar o texto
cadastrado no painel admin "Mensagens" (tabela `crm_templates`), escolhido pelo
status do aniversário — nunca um texto genérico de config nem hardcoded.

- Status por delta de dias: `0` → "hoje" (gatilho `niver_hoje`, "Dia Exato");
  `< 0` → "passou" (`niver_passou`, "Atrasado"); `> 0` → None (futuro).
- **Futuro não recebe mensagem.** "Aviso Prévio" (`niver_futuro`) foi descontinuado;
  ele fica oculto do painel e nenhum fluxo deve gerar link/envio para futuros.

**Why:** o pedido foi alinhar o que os módulos enviam exatamente com o que o admin
edita; antes divergia porque usavam `mensagem_padrao`/textos fixos. Forçar "hoje"
para futuros (ex.: `status or "hoje"`) reintroduz o "Aviso Prévio" indevidamente.

**How to apply:** centralizar via helpers em `utils/niver_automatico.py`
(`status_niver_por_delta`, `montar_mensagem_niver`). Ao construir datas de
aniversário, tratar 29/02 em ano não bissexto (ValueError → usar 28/02).
