---
name: Supabase pagination rules
description: Regras obrigatórias para paginar queries no Supabase/PostgREST sem loop infinito ou corte silencioso.
---

## Regra

PAGE deve ser sempre 1000 (limite máximo do PostgREST). `.limit(N>1000)` é silenciosamente truncado em 1000.

`.range()` exige `.order()` — sem order, PostgREST pode retornar resultado vazio ou não-determinístico.

Use `for _ in range(MAX_PAG)` com MAX_PAG=500, nunca `while True`. Se RLS ou qualquer política sempre devolve exatamente 1000 linhas, `while True` entra em loop infinito e o Streamlit fica com "Running" para sempre.

**Why:** Descoberto em 2026-07 quando `listar_datas_aulas_registradas` com PAGE=5000 capturava só os primeiros 1000 registros (servia só datas antigas); depois corrigido com PAGE=1000 mas ainda exposto a loop infinito. Padrão correto confirado: PAGE=1000 + .order("id") + for range(500).

## Template correto

```python
PAGE = 1000
MAX_PAG = 500
offset = 0
pages = []
for _ in range(MAX_PAG):
    res = (
        supabase.from_("tabela")
        .select("col1, col2")
        .order("id")          # obrigatório para .range() funcionar
        .range(offset, offset + PAGE - 1)
        .execute()
    )
    if res.data:
        pages.extend(res.data)
    if not res.data or len(res.data) < PAGE:
        break
    offset += PAGE
```

Para queries filtradas por data (ex.: contar presenças num período):
- Adicione `.gte("data_aula", str(ini)).lte("data_aula", str(fim))` antes do `.order()`
- Isso reduz o resultado drasticamente e evita muitas páginas
- Pode usar `.order("data_aula")` no lugar de `.order("id")`
