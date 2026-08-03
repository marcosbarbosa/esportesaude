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
    """Return True if the .pyc timestamp is older than the .py source file."""
    try:
        py_mtime = os.path.getmtime(py_path)
        # PEP-3147 .pyc layout: magic(4) + flags(4) + timestamp(4) + size(4)
        with open(pyc_path, "rb") as f:
            header = f.read(16)
        if len(header) < 16:
            return True  # truncated / corrupt
        # bytes 8-11 hold the source timestamp (little-endian uint32)
        cached_ts = struct.unpack_from("<I", header, 8)[0]
        # Compare with 1-second granularity (same as CPython's own check)
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
