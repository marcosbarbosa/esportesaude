---
name: Home grid snapshot
description: Painel inicial usa snapshot materializado em configuracoes_sistema para evitar 5 queries pesadas no cold start.
---

## Regra
O grid de alunos na tela "Principal" (Início) carrega dados de 5 fontes pesadas.
Em vez de executá-las no cold start (causando timeout/502 no Render), os dados
são pré-computados e persistidos como JSON em `configuracoes_sistema` com
`chave = 'snapshot_home_grid_v1'`.

**Why:** Render free tier mata e reinicia o processo frequentemente.
Sem snapshot, todo cold start dispara 5 queries simultâneas → timeout → 502.

**How to apply:**
- `computar_snapshot_home_grid()` — executa as 5 queries sem cache; chamado APENAS pelo botão.
- `salvar_snapshot_home_grid(dados)` — persiste JSON; adiciona `gerado_em`.
- `get_snapshot_home_grid()` — lê e parseia; retorna `{}` se não existir.
- `main.py` lê snapshot primeiro; se vazio, cai nas queries ao vivo (`load_*` cached).
- Botão "⚙️ Processar em Lote" na tela Início regenera o snapshot e dá rerun.
- Ao salvar snapshot, limpar `load_frequencia_ultima_presenca`, `load_atestados_vencimento`, `load_total_presencas_todos`.
- Snapshot inclui: `ultima_presenca_recs`, `total_presencas_recs`, `atestados_recs`, `ultima_pa`, `ultima_aval`, `gerado_em`.
