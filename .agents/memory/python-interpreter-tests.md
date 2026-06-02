---
name: Interpretador Python para rodar código do projeto
description: Qual binário usar para importar database.py / rodar testes; o python padrão quebra.
---
As libs do projeto (numpy, pandas, streamlit, supabase) estão em
`.pythonlibs/lib/python3.11` e são buildadas para 3.11. O nix 3.12 entra no PATH
à frente do `.pythonlibs/bin` (via o pacote nix `lacus` em `[nix].packages` do
`.replit`, que arrasta todo o ecossistema python3.12). Importar com 3.12 falha com
"Error importing numpy: you should not try to import numpy from its source directory".

**Correção aplicada:** `.config/bashrc` (hook que o `~/.bashrc` do Replit carrega em
shells normais, i.e. `REPLIT_MODE` vazio) prependa `${REPL_HOME}/.pythonlibs/bin` ao
PATH. Em shell normal, `python -c "import pandas"` funciona (3.11). O app Streamlit
NÃO é afetado (workflow roda em modo agent/workflow e não carrega `.config/bashrc`,
e já usa o toolchain 3.11).

**Cuidados:**
- `uninstallSystemDependencies({packages:["lacus"]})` retorna success mas NÃO edita o
  `.replit` (no-op); editar `.replit`/`replit.nix` direto é bloqueado. Por isso a
  correção é via `.config/bashrc`, não pela remoção do `lacus`.
- Shells em modo agent/workflow e scripts não-interativos (`bash x.sh`) NÃO herdam
  o fix do `.config/bashrc`; nesses casos use `.pythonlibs/bin/python3.11`.

Importar `database.py` exige `.streamlit/secrets.toml` (lido por `init_connection`
via `st.secrets`) — só é encontrado quando o cwd é a raiz do projeto. Rodar de
dentro de subpastas (ex.: `tests/`) dá `StreamlitSecretNotFoundError`. Sempre rode
da raiz; o teste já faz `sys.path.insert` para achar os módulos.
