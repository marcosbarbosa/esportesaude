---
name: Supabase storage buckets (IMBRA)
description: Which storage buckets actually exist/work for uploads, and the anon-key constraint
---

# Buckets de Storage do Supabase (IMBRA)

A app usa a chave **anon** (`st.secrets["SUPABASE_KEY"]`, role=anon). Com chave anon:

- O bucket **`diario_midias_imbra`** EXISTE e aceita upload + URL pública. É o único bucket confiável para uploads.
- O bucket **`documentos_alunos`** NÃO existe (upload retorna `404 Bucket not found`). A chave anon **não consegue criar buckets** (`create_bucket` → `403 RLS`). Criar bucket exige acesso admin/service_role no painel do Supabase.

**Regra:** todo upload via `database.upload_midia(...)` deve mirar um bucket que exista e tenha policy de INSERT para anon. O default de `upload_midia` foi apontado para `diario_midias_imbra` justamente por isso.

**Why:** cadastros (RG/receita/atestado), triagem e fotos do diário usavam o default `documentos_alunos` (inexistente) e falhavam 100% das vezes silenciosamente (salvavam o cadastro sem o arquivo).

**How to apply:** se for criar um bucket dedicado (ex.: separar documentos sensíveis), o usuário precisa criá-lo no painel do Supabase E adicionar policy de INSERT/SELECT para anon — não dá para criar pelo código com a chave atual. Validar uploads sempre rodando contra o Supabase real (script com `PYTHONPATH=/home/runner/workspace .pythonlibs/bin/python3.11`).
