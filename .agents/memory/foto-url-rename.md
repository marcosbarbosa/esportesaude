---
name: foto_url rename coverage
description: Rastreamento da renomeação url_foto→foto_url na tabela alunos e todos os arquivos Python afetados.
---

# Regra
A coluna na tabela `alunos` foi renomeada de `url_foto` para `foto_url`. Todo acesso ao banco (leitura e escrita) deve usar `foto_url`.

**Why:** A coluna antiga foi dropada do Supabase; usar `url_foto` como chave retorna None silenciosamente em leituras e falha em escritas.

**How to apply:** Ao adicionar novo código que lê/escreve foto do aluno, sempre usar `foto_url`. `url_foto` pode aparecer como nome de variável local (ok), mas nunca como chave de dict enviado ao Supabase nem em `.get("url_foto")` sem fallback.

# Arquivos corrigidos (chaves de DB)
- modulos_frequencia/tab_emergencia.py — `row.get("foto_url")`
- modulos_frequencia/tab_niver.py — 4 ocorrências (word export, HTML card, display inline)
- views/relatorio_identificacao_view.py — `df["foto_url"]`, `row.get("foto_url")`
- views/ficha_aluno_view.py — `row.get("foto_url")`
- views/prontuario_view.py — leitura (u_v, url_atual_foto) e escrita ({"foto_url": nova_url})
- views/prontuario_ficha.py — leitura (u_v), escrita ({"foto_url": nova_url}), session_state
- views/inscricao_publica_view.py — payload de insert `"foto_url": url_foto`
- views/merge_alunos_view.py — campo_db `"foto_url"` e tuple de mapeamento
- views/triagem_view.py — tuple de mapeamento `("foto_url", "foto_url", ...)`

# Exceções seguras
- `views/bi_individual_view.py:169` — `aluno.get("url_foto") or aluno.get("foto_url")`: fallback duplo, funciona.
- Variáveis locais nomeadas `url_foto` em tab_tablet.py, ficha_aluno_view.py, inscricao_publica_view.py: nomes de variável Python, não chaves de BD.
