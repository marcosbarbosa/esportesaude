---
name: Config singleton pattern (configuracoes_sistema)
description: Generic key/value settings helper for simple admin-configurable values, distinct from the log-entry pattern and the JSON-file identity config.
---

`configuracoes_sistema` (chave/valor table) is used for two different purposes — do not conflate them:

1. **Log entries** — one row per event, key includes a timestamp/id (e.g. `atestado_log_<ts>_<aluno_id>`), value is a JSON blob. Used for audit trails.
2. **Singleton settings** — one fixed key holding a single current value (e.g. `config_dias_validade_anamnese`). Use `get_config_valor(chave, default)` / `set_config_valor(chave, valor)` in `database.py` for this — read via `.eq("chave", chave).limit(1)`, write via `.upsert(..., on_conflict="chave")`.

**Why:** before this helper existed, every settings-like feature reimplemented the upsert pattern ad hoc, and it was easy to confuse it with the log-entry pattern (which intentionally creates many rows) or with `utils/identidade.py`'s separate JSON-file config (used only for logos/org identity, not DB-backed).

**How to apply:** for any new admin-configurable single value that must persist in the DB, reuse `get_config_valor`/`set_config_valor` instead of writing a new upsert. Admin UI controls for such settings live in `modulos_frequencia/tab_admin.py` (restricted to `ADMIN_MASTER`).
