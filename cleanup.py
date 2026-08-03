"""
cleanup.py — Smart Python bytecode cache checker.

Only removes .pyc files / __pycache__ dirs when stale or orphaned bytecode
is actually detected. Clean environments skip the scan with no overhead.
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

    for kind, pyc_path in issues:
        cache_dir = os.path.dirname(pyc_path)
        try:
            os.remove(pyc_path)
            removed_files += 1
            removed_dirs.add(cache_dir)
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


if __name__ == "__main__":
    main()
