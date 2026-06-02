---
name: Busca fonética server-side (ativação)
description: Como ativar/depurar o caminho server-side de busca de alunos por nome_fonetica
---

# Ativação da busca server-side por `nome_fonetica`

`buscar_alunos_geral` só usa o filtro server-side quando `_coluna_fonetica_pronta()`
retorna True — ou seja, a coluna `alunos.nome_fonetica` existe **e** está 100%
preenchida (nenhum aluno ativo com valor nulo). Senão, cai no fallback (baixa a
base inteira e filtra em Python). Resultados são idênticos nos dois caminhos.

**Como ativar:** a coluna exige DDL no Supabase (não há acesso ao schema a partir
do Replit). Rodar no SQL Editor do Supabase:
`ALTER TABLE alunos ADD COLUMN nome_fonetica text;` + extensão `pg_trgm` + índice
GIN trigram. Depois, retro-preencher via botão admin (aba "🗑️ Admin" da tela de
Frequência → expander "🔎 Busca rápida"), que chama `backfill_nome_fonetica()`.

**Why:** sem a coluna persistida, a busca não escala (download da base inteira a
cada termo). O backfill é idempotente e cobre inativos também.
