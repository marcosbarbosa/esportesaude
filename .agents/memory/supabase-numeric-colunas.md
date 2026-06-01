---
name: Colunas numéricas do Supabase (IMBRA)
description: Restrições de precisão e por que não dá para ALTERAR o schema do Supabase daqui
---

A coluna `altura` em `alunos` é `numeric(4,2)` (máx 99.99) e guarda metros. Altura digitada em centímetros (ex.: 170) estoura com `numeric field overflow` (Postgres code 22003) na migração do pré-cadastro para aluno.

Normalização aplicada em `database.py` antes do insert: converter cm→m quando valor > 3, com piso 0 e teto 99.99. Peso é apenas arredondado (2 casas) — sem teto artificial, porque a coluna de peso é mais larga e nunca estourou; limitar corromperia pesos reais ≥100kg.

**Why:** O overflow só apareceu na altura (variação de digitação cm vs m), nunca no peso ao longo do histórico — indicando que peso tem coluna maior.

**How to apply:** Validar/normalizar campos numéricos no código antes de gravar. NÃO é possível `ALTER TABLE` no Supabase a partir do Replit: as credenciais em `st.secrets` são URL/anon-key (PostgREST), e `DATABASE_URL` aponta para o Postgres local do Replit (helium), não para o Supabase. Mudanças de schema precisam ser feitas no painel do Supabase pelo usuário.
