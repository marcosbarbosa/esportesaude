"""
cleanup.py — Smart Python bytecode cache checker.

Only removes .pyc files / __pycache__ dirs when stale or orphaned bytecode
is actually detected. Clean environments skip the scan with no overhead.

On removal, persists a structured log entry to configuracoes_sistema so admins
can audit cache-corruption history from the Backup & Diagnostics screen.
"""
import os
import sys
import struct
import time


def _pyc_is_stale(pyc_path: str, py_path: str) -> bool:
    """Return True if the .pyc is stale or untrustworthy.

    PEP-552 introduced two .pyc validation modes:
      flags & 1 == 0  →  timestamp-based (classic)
      flags & 1 == 1  →  hash-based
        flags & 2 == 0  →  checked (hash verified at import)
        flags & 2 == 2  →  unchecked (hash stored but NEVER verified by CPython)

    Unchecked hash-based pycs (flags == 3) are dangerous: CPython loads them
    blindly even when the source has changed.  We always treat them as stale
    so they are deleted and CPython falls back to the .py source.
    """
    try:
        # PEP-3147 .pyc layout: magic(4) + flags(4) + ...
        with open(pyc_path, "rb") as f:
            header = f.read(16)
        if len(header) < 16:
            return True  # truncated / corrupt

        flags = struct.unpack_from("<I", header, 4)[0]

        if flags & 1:
            # Hash-based pyc.
            if flags & 2:
                # Unchecked hash (flags == 3): CPython never validates → always stale.
                return True
            # Checked hash-based: verify SHA-256 of source matches stored hash.
            import hashlib
            stored_hash = header[8:16]  # 8 bytes of hash
            with open(py_path, "rb") as f:
                src_hash = hashlib.sha256(f.read()).digest()[:8]
            return src_hash != stored_hash
        else:
            # Timestamp-based (classic): compare source mtime with stored timestamp.
            py_mtime = os.path.getmtime(py_path)
            cached_ts = struct.unpack_from("<I", header, 8)[0]
            return int(py_mtime) > cached_ts

    except (OSError, struct.error):
        return True  # unreadable → treat as stale


def _find_issues(root: str):
    """Yield (kind, path) tuples for orphaned or stale bytecode found under root."""
    skip_dirs = {".git", ".local", "node_modules", ".venv", "venv"}
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Prune directories we never want to inspect
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]

        if os.path.basename(dirpath) == "__pycache__":
            parent = os.path.dirname(dirpath)
            for fname in filenames:
                if not fname.endswith(".pyc"):
                    continue
                pyc_path = os.path.join(dirpath, fname)
                # Derive the source name: strip .cpython-3XX or similar tag
                base = fname.split(".")[0]  # e.g. "module" from "module.cpython-311.pyc"
                py_path = os.path.join(parent, base + ".py")
                if not os.path.exists(py_path):
                    yield ("orphan", pyc_path)
                elif _pyc_is_stale(pyc_path, py_path):
                    yield ("stale", pyc_path)


# ==============================================================================
# 📦 LOG DE LIMPEZA → configuracoes_sistema
# ==============================================================================

_CHAVE_LOG = "cleanup_cache_log"
_MAX_ENTRADAS = 50  # mantém os últimos 50 eventos


def _ler_secrets_toml(root: str) -> dict:
    """Lê .streamlit/secrets.toml sem dependência do Streamlit."""
    try:
        import tomllib
        secrets_path = os.path.join(root, ".streamlit", "secrets.toml")
        with open(secrets_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _registrar_log_supabase(root: str, n_orfaos: int, n_obsoletos: int, elapsed: float):
    """Persiste um evento de limpeza em configuracoes_sistema via Supabase REST."""
    try:
        import json
        import datetime

        secrets = _ler_secrets_toml(root)
        url = secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
        key = secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY", "")

        if not url or not key:
            print("[cleanup] Aviso: credenciais Supabase não encontradas — log não registrado.", file=sys.stderr)
            return

        from supabase import create_client
        sb = create_client(url, key)

        # Lê log existente
        res = (
            sb.table("configuracoes_sistema")
            .select("valor")
            .eq("chave", _CHAVE_LOG)
            .execute()
        )
        try:
            entradas = json.loads(res.data[0]["valor"]) if res.data else []
            if not isinstance(entradas, list):
                entradas = []
        except Exception:
            entradas = []

        # Adiciona nova entrada
        nova = {
            "data": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "orfaos": n_orfaos,
            "obsoletos": n_obsoletos,
            "total": n_orfaos + n_obsoletos,
            "duracao_s": round(elapsed, 2),
        }
        entradas.append(nova)

        # Mantém apenas as últimas N entradas
        if len(entradas) > _MAX_ENTRADAS:
            entradas = entradas[-_MAX_ENTRADAS:]

        payload = json.dumps(entradas, ensure_ascii=False)

        sb.table("configuracoes_sistema").upsert(
            {"chave": _CHAVE_LOG, "valor": payload},
            on_conflict="chave",
        ).execute()

        print(f"[cleanup] Evento de limpeza registrado no banco ({nova['total']} arquivo(s)).")

    except Exception as exc:
        # Nunca deve travar o startup por falha no log
        print(f"[cleanup] Aviso: não foi possível registrar log: {exc}", file=sys.stderr)


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    t0 = time.monotonic()

    issues = list(_find_issues(root))

    if not issues:
        elapsed = time.monotonic() - t0
        print(f"[cleanup] Bytecode cache OK ({elapsed:.2f}s) — nothing to remove.")
        return

    print(f"[cleanup] Found {len(issues)} stale/orphaned .pyc file(s) — cleaning...")
    removed_files = 0
    removed_dirs = set()
    n_orfaos = 0
    n_obsoletos = 0

    for kind, pyc_path in issues:
        cache_dir = os.path.dirname(pyc_path)
        try:
            os.remove(pyc_path)
            removed_files += 1
            removed_dirs.add(cache_dir)
            if kind == "orphan":
                n_orfaos += 1
            else:
                n_obsoletos += 1
        except OSError as exc:
            print(f"[cleanup] Warning: could not remove {pyc_path}: {exc}", file=sys.stderr)

    # Remove empty __pycache__ directories left behind
    for cache_dir in removed_dirs:
        try:
            if os.path.isdir(cache_dir) and not os.listdir(cache_dir):
                os.rmdir(cache_dir)
        except OSError:
            pass

    elapsed = time.monotonic() - t0
    print(f"[cleanup] Removed {removed_files} file(s) in {elapsed:.2f}s.")

    # Registra o evento no banco para auditoria
    _registrar_log_supabase(root, n_orfaos, n_obsoletos, elapsed)


if __name__ == "__main__":
    main()
