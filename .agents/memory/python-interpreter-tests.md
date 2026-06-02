---
name: Interpretador Python para rodar código do projeto
description: Qual binário usar para importar database.py / rodar testes; o python padrão quebra.
---
O `python`/`python3` padrão no PATH é o nix 3.12, mas as libs do projeto (numpy,
pandas, streamlit, supabase) estão em `.pythonlibs/lib/python3.11` e são buildadas
para 3.11. Importar com 3.12 falha com "Error importing numpy: you should not try
to import numpy from its source directory".

**Como aplicar:** rode scripts/testes com `.pythonlibs/bin/python3.11`, não `python`.
Ex.: `.pythonlibs/bin/python3.11 tests/test_busca_paridade.py`.

Importar `database.py` exige `.streamlit/secrets.toml` (lido por `init_connection`
via `st.secrets`) — só é encontrado quando o cwd é a raiz do projeto. Rodar de
dentro de subpastas (ex.: `tests/`) dá `StreamlitSecretNotFoundError`. Sempre rode
da raiz; o teste já faz `sys.path.insert` para achar os módulos.
