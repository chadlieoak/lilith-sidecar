from pathlib import Path
import os, hashlib, difflib, json

def safe_join(root: Path, relpath: str) -> Path:
    # prevent path traversal
    p = (root / relpath).resolve()
    if not str(p).startswith(str(root.resolve())):
        raise ValueError("Path traversal blocked")
    return p

def ensure_safe_args(args: dict):
    # MVP safety: block obvious dangerous inputs
    bad = ["..", "~", "/etc/", "C:\\Windows"]
    blob = json.dumps(args)
    for b in bad:
        if b in blob:
            raise ValueError("Unsafe argument detected")

def file_hash(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def make_diff(before: str, after: str, rel: str) -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    return "".join(difflib.unified_diff(before_lines, after_lines, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
