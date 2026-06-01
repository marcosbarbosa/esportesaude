---
name: Cache invalidation de alunos (IMBRA)
description: Onde invalidar caches após mutações em alunos; armadilha dos caches locais da Busca Global
---

Qualquer função que altere a tabela `alunos` (insert/update/delete/turma/status) deve chamar `_inv_alunos()` em `database.py` antes de retornar. `_inv_alunos()` limpa um conjunto fixo de funções `@st.cache_data` (incluindo `get_alunos_por_turma`, `buscar_alunos_geral`, etc.).

**Why:** O botão "Transferir" (frequencia_view) atualizava o banco mas não invalidava o cache, então o grid da turma atual continuava mostrando a lista antiga e o aluno "não aparecia" na turma destino. O "Ativar+Transferir" parecia funcionar porque a outra ação (`alterar_status_aluno`) já chamava `_inv_alunos()`.

**Armadilha:** `views/frequencia_view.py` tem caches LOCAIS próprios (`obter_todos_alunos_cache`, `obter_todos_alunos_com_inativos_cache`) que alimentam a Busca Global e **NÃO** são limpos por `_inv_alunos()` (que vive em database.py). Após transferir/reativar, é preciso limpar esses caches locais também — usar `_limpar_cache_busca_global()` em frequencia_view.

**How to apply:** Ao criar nova mutação de aluno em database.py, adicione `_inv_alunos()`. Se a ação roda na tela de frequência e afeta a Busca Global, limpe também os caches locais dessa view. Regra geral: cache `@st.cache_data` não é invalidado por `st.rerun()` — só por `.clear()` explícito ou TTL.
