---
name: Email BI deep-links acionáveis
description: Como os botões do e-mail BI levam o diretor direto à tela que resolve o problema.
---

# Deep-links acionáveis no Email BI

Os relatórios do Email BI (`utils/email_relatorio.py`) injetam botões que abrem a tela certa do app para RESOLVER a pendência (não só apontá-la):
- "dia sem registro" → `{base_url}/?ir=freq&d=YYYY-MM-DD` → tela Frequência na data pendente.
- "cadastro incompleto" (auditoria) e "risco de evasão" → `{base_url}/?ir=ficha&id=<aluno_id>` → ficha/prontuário do aluno.

## Fluxo de roteamento (sobrevive ao login)
**Why:** o link é clicado a partir do e-mail; o usuário normalmente ainda não está logado, então o destino precisa persistir através da tela de login.
**How to apply:** em `main.py`, logo após `inicializar_sessao()`, captura-se `?ir=` em `st.session_state._pending_deeplink` e limpa-se a query string. Dentro do bloco `if st.session_state.usuario_logado:` o destino é aplicado (set `menu_atual` + `_freq_data_alvo`, ou carrega aluno via `buscar_aluno_por_id` e abre "Portal do Aluno") e faz `st.rerun()`. O `pop()` garante consumo único — sem loop de rerun.

## base_url dos links
**Why:** o envio automático dispara quando QUALQUER pessoa loga na data agendada; se o host detectado for uma URL interna/dev, os links saem inacessíveis para os destinatários.
**How to apply:** preferir a chave de config `ebi_base_url` (campo na aba Email BI) e usar `st.context.headers["host"]` apenas como fallback. Em `gerar_html_relatorio`, a precedência é `cfg["base_url"] or base_url(param)`. Em produção (Render), configurar a URL pública explicitamente.

## Pré-seleção da data na Frequência
`views/frequencia_view.py`: o `date_input` usa `key="freq_data_aula"`; o deep-link grava `st.session_state["freq_data_aula"]` a partir de `_freq_data_alvo` ANTES de criar o widget (necessário porque, com key existente, o argumento `value` é ignorado).
