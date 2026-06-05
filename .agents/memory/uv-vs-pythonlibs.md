---
name: uv vs .pythonlibs (gestor do ambiente Python)
description: Por que `uv run`/`uv sync` não reconstroem o ambiente neste repl, e o que usar no lugar.
---

# uv NÃO é o gestor do ambiente Python aqui

O projeto padroniza no diretório **gerido pelo Replit `.pythonlibs` (Python 3.11)**.
Esse diretório **não é um venv do uv** — não tem `pyvenv.cfg`.

**Regra:** não tente reconstruir o ambiente com `uv sync`/`uv run` (sync automático).
O Replit define no ambiente:
- `UV_PROJECT_ENVIRONMENT=/home/runner/workspace/.pythonlibs`
- `UV_PYTHON_PREFERENCE=only-system`
- `UV_PYTHON_DOWNLOADS=never`

**Why:** como `.pythonlibs` não é venv e downloads de Python estão desativados, o uv cai
no Python do nix-store (somente leitura) e o `sync` falha com *permission denied* ao tentar
instalar/atualizar pacotes (ex.: altair). Isto é estrutural, separado de qualquer build nativo.

**How to apply:**
- Para correr código pelo uv contra o ambiente já instalado: `uv run --no-sync ...`
  (ex.: `uv run --no-sync python -c "import pandas"`).
- Para gerir pacotes de verdade, use o package management do Replit (escreve em `.pythonlibs`),
  não o uv.
- `uv lock` / `uv lock --check` **funcionam** (resolução pura) e são úteis para validar o grafo
  de dependências sem tocar no ambiente.
- O interpretador do projeto é `.pythonlibs/bin/python3.11` (o shell tem 3.12).

## Cadeia pycairo (xhtml2pdf/svglib)
`svglib>=1.6` puxa `rlpycairo → pycairo`, cujo build nativo falha sem `cairo`/`pkg-config` no Nix.
Mantido fixo `xhtml2pdf==0.2.11` + `svglib<1.6` em `pyproject.toml` E `requirements.txt`
(senão `pip install -r requirements.txt` re-dispara o build). PDFs usam HTML/CSS + base64,
nunca SVG, então cairo é desnecessário.
