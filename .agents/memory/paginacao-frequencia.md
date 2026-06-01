---
name: Paginação da tabela frequencia (Supabase)
description: O PostgREST corta em 1000 linhas e helpers de presença têm teto de páginas — cuidado ao usar para métricas históricas completas.
---

# Paginação de presenças (tabela `frequencia`)

O Supabase/PostgREST devolve no máximo 1000 linhas por request, independente do
`.limit()`. Por isso as leituras de presença paginam via `.range(offset, offset+999)`.

**Cuidado:** `bi_presencas_periodo` e `get_presentes_periodo_todos` têm teto fixo
(`MAX_PAGINAS` 30/50 → 30k/50k registros). Para métricas que precisam do histórico
**completo** ("desde o início do projeto"), NÃO reusar essas funções — elas truncam
silenciosamente quando o volume cresce. Pagine com `while True` quebrando quando o
lote vier com menos de PAGE linhas (padrão de `buscar_alunos_geral` e
`bi_media_alunos_dia`).

**Why:** uma média/contagem histórica calculada sobre dados truncados fica errada
sem nenhum aviso.

**How to apply:** ao criar métrica que varre todo o histórico de `frequencia`,
escreva paginação própria sem teto artificial (ou sinalize truncamento). O início
do projeto pode ser obtido pela 1ª `data_aula` com `status='PRESENTE'`
(`order("data_aula").limit(1)`).
