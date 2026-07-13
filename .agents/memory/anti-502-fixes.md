---
name: Anti-502 stability fixes
description: 6 causas de instabilidade no Render diagnosticadas e corrigidas; regras para código novo.
---

## Regras permanentes para código novo

**Why:** App Render free tier mata instância quando: thread bloqueada (health check timeout), OOM, ou processo sai por exceção não tratada.

### 1. NUNCA usar while True em paginação Supabase
Sempre: `for _ in range(500):` com `break` quando `len(res.data) < 1000`.
**Why:** Se Supabase retornar exatamente 1000 rows, while True nunca sai.

### 2. NUNCA usar .limit(N_grande) sem paginação
`.limit(200000)` é silenciosamente truncado em 1000 (cap do PostgREST).
Sempre paginar com `.order("id") + .range(inicio, inicio+999)`.

### 3. Gemini SEMPRE com timeout de 10s
Usar `ThreadPoolExecutor(max_workers=1)` + `.result(timeout=10)`.
**Why:** Gemini sem timeout pode bloquear thread indefinidamente → 502.

### 4. st.components.v1.html — usar import direto
`from streamlit.components.v1 import html as _html_v1` em vez de
`st.components.v1.html(...)` que gera warnings deprecados em todo render.

### 5. requests.get() SEMPRE com timeout
`requests.get(url, timeout=15)` — nunca sem timeout em produção.

### 6. Logging estruturado disponível
`from utils.logger import get_logger, cronometrar`
Chamar `configurar_logging()` uma vez em main.py (já feito).
Usar `cronometrar("nome_op")` só em funções potencialmente lentas.
