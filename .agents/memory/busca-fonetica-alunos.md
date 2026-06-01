---
name: Busca fonética unificada de alunos
description: Padrão único para toda busca livre de nome de aluno no IMBRA e por que buscar_alunos_geral filtra em Python.
---

# Busca fonética de alunos

Toda busca livre por nome (e turma) de aluno deve usar `normalizar_fonetica`
(`utils/texto.py`), não `remover_acentos` nem `str.lower()`. O helper de
referência é `filtrar_alunos_df` (`utils/busca_aluno.py`).

**Why:** acentuação e variações de grafia (ph/f, th/ct/t, y/i, ll/l, nn/n)
faziam buscas idênticas retornarem resultados diferentes entre telas. Unificar
em `normalizar_fonetica` torna o comportamento previsível em todas as telas.

**How to apply:** ao adicionar/alterar qualquer campo de busca de aluno, aplique
`df[col].fillna("").apply(normalizar_fonetica).str.contains(normalizar_fonetica(termo), na=False)`.
Preserve o gatilho mínimo de caracteres específico de cada tela (alguns usam 2, outros 3).

## buscar_alunos_geral (database.py) filtra em Python
`buscar_alunos_geral(termo)` NÃO usa mais `.ilike` server-side. Carrega a base
paginada (mantendo `neq status Inativo`) e filtra com `normalizar_fonetica` em
Python. **Why:** `.ilike` é sensível à grafia/acentos e quebrava a unificação.

O download paginado mora em `_carregar_base_alunos(incluir_inativos)`, cacheado
APENAS por `incluir_inativos`. `buscar_alunos_geral` chama esse loader e só faz o
filtro fonético em Python por cima. **Why:** o `@st.cache_data` chaveia por
`termo`, então antes cada termo distinto re-baixava a base inteira do Supabase;
separando download (1x por TTL) do filtro (barato em memória), termos diferentes
reusam o mesmo download. **How to apply:** `_inv_alunos()` precisa limpar TAMBÉM
`_carregar_base_alunos` (já incluído) — senão mutações em alunos servem base
velha. Resultados são idênticos: o filtro não mudou, só o de onde vêm os dados.

**Server-side ainda bloqueado:** uma coluna fonética persistida (filtro no banco)
seria o passo escalável seguinte, mas exige DDL e hoje NÃO há acesso ao schema do
Supabase a partir do Replit. Um pré-filtro `.ilike` no servidor NÃO serve: perde
resultados foneticamente diferentes (ex.: "Phelipe" vs "Felipe").
