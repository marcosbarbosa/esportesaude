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
**Tradeoff:** para `termo != ""` o backend transfere a base inteira antes de
filtrar (mais latência). Se o volume crescer muito, avaliar coluna fonética
persistida no banco para voltar ao filtro server-side — mas hoje NÃO há acesso
ao schema do Supabase a partir do Replit.
