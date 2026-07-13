---
name: st_keyup runtime fallback
description: O componente st_keyup pode falhar em runtime (não só ImportError) em ambientes proxy como Render; _KEYUP_RUNTIME_OK desativa globalmente na 1ª falha.
---

## Regra
`utils/busca_aluno.py` exporta `busca_aluno_widget()` que usa `st_keyup` com
fallback para `st.text_input`.

**Why:** Em produção no Render, o componente está instalado (sem ImportError)
mas falha ao tentar carregar os assets de frontend via WebSocket/proxy.
Isso gerava a mensagem "component loading trouble" e loops de rerun → 502.

**How to apply:**
- `_HAS_KEYUP` (module-level bool) — False se ImportError no import.
- `_KEYUP_RUNTIME_OK` (module-level bool, global) — começa True; na 1ª exceção
  em runtime (dentro de `_render()`), vira False e desativa para toda a sessão.
- O fallback `st.text_input` é chamado sempre que `_HAS_KEYUP=False` OU `_KEYUP_RUNTIME_OK=False`.
- NÃO precisa de reinício — o flag é de módulo e persiste enquanto o processo viver.
