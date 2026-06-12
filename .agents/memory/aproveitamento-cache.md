---
name: Aproveitamento duplicata — cache do Portal do Aluno
description: Após merge via _tela_aproveitamento_duplicata, o Portal do Aluno mostrava dados velhos porque as caches do CRM não eram limpas.
---

## Regra
Após qualquer operação que altere um registro em `alunos` via `atualizar_perfil_aluno_dict`, é preciso limpar TAMBÉM as caches locais do prontuário_dashboard.

## Por quê
`atualizar_perfil_aluno_dict` chama `_inv_alunos()` que limpa `buscar_aluno_por_id`, `buscar_alunos_geral` etc.
Mas `prontuario_dashboard.py` tem caches próprias (`carregar_dados_crm_avaliacoes_senior` e `obter_todos_alunos_cache`) com TTL=300s que NÃO estão em `_inv_alunos()`.
Quando o usuário vai ao Portal do Aluno e clica no aluno, o `a.to_dict()` vem do DataFrame velho → `st.session_state.aluno_prontuario` carrega dados antigos → ficha exibe dados pré-merge.

## Como aplicar
```python
try:
    from views.prontuario_dashboard import (
        carregar_dados_crm_avaliacoes_senior,
        obter_todos_alunos_cache,
    )
    carregar_dados_crm_avaliacoes_senior.clear()
    obter_todos_alunos_cache.clear()
except Exception:
    pass
st.session_state["_force_reload_crm"] = True
```
Chamar esse bloco logo após `atualizar_perfil_aluno_dict` retornar `ok=True` em qualquer operação de merge/aproveitamento.
