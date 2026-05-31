---
name: Navegação interna do app IMBRA
description: Como navegar entre telas e abrir a ficha de um aluno programaticamente.
---

# Navegação no IMBRA (Streamlit)

- `st.session_state.menu_atual` é o roteador principal das telas autenticadas (ex.: "Principal", "Frequência", "Portal do Aluno", "Ficha de Matrícula", "Nova Matrícula").
- `st.query_params.get("rota")` é SÓ para rotas públicas sem login: `inscricao`, `pesquisa`, `validar`. Não reutilizar `rota` para navegação autenticada — usar um param próprio (ex.: `ir`).
- Abrir a ficha de um aluno: setar `st.session_state.aluno_prontuario = <dict do aluno>` e `menu_atual = "Portal do Aluno"` (renderiza `prontuario_ficha.renderizar_ficha`). Buscar o dict por id com `database.buscar_aluno_por_id(id)` (retorna `select("*")`).
- `st.session_state.origem_prontuario` controla o botão "voltar" da ficha: seu valor é atribuído diretamente a `menu_atual`, então DEVE ser uma rota válida do menu (ex.: "Principal", "Frequência"). Valor inválido quebra a navegação de retorno.
- Coluna da foto do aluno é `url_foto` (não `foto_url`).
