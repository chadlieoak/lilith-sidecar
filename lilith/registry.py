from pathlib import Path
from lilith.utils import safe_join, file_hash, make_diff
from dataclasses import dataclass, field

class ToolError(Exception): pass

@dataclass
class ToolManifest:
    name: str
    args_schema: dict
    side_effects: dict  # {"fs": True, "net": False, "env": False}
    requires: list = field(default_factory=list)

    def dry_run(self, workspace: Path, args: dict):
        raise NotImplementedError

    def apply(self, workspace: Path, args: dict):
        raise NotImplementedError

def _ensure_parent(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

class WriteFileTool(ToolManifest):
    def dry_run(self, workspace: Path, args: dict):
        rel = args.get("path")
        content = args.get("content","")
        target = safe_join(workspace, rel)
        before = target.read_text(encoding="utf-8") if target.exists() else ""
        diff = make_diff(before, content, rel)
        return {"preview_diff": diff, "files":[{"path": str(rel), "exists_before": target.exists()}]}

    def apply(self, workspace: Path, args: dict):
        rel = args.get("path")
        content = args.get("content","")
        target = safe_join(workspace, rel)
        _ensure_parent(target)
        target.write_text(content, encoding="utf-8")
        return {"artifacts":[{"type":"file","path": str(rel), "hash": file_hash(target)}]}

class ReplaceTextTool(ToolManifest):
    def dry_run(self, workspace: Path, args: dict):
        rel = args.get("path"); search=args.get("search",""); repl=args.get("replace","")
        target = safe_join(workspace, rel)
        if not target.exists():
            raise ToolError(f"File not found: {rel}")
        before = target.read_text(encoding="utf-8")
        after = before.replace(search, repl)
        diff = make_diff(before, after, rel)
        return {"preview_diff": diff, "files":[{"path": str(rel), "exists_before": True}]}

    def apply(self, workspace: Path, args: dict):
        rel = args.get("path"); search=args.get("search",""); repl=args.get("replace","")
        target = safe_join(workspace, rel)
        if not target.exists():
            raise ToolError(f"File not found: {rel}")
        before = target.read_text(encoding="utf-8")
        after = before.replace(search, repl)
        target.write_text(after, encoding="utf-8")
        return {"artifacts":[{"type":"file","path": str(rel), "hash": file_hash(target)}]}

class ScaffoldSiteTool(ToolManifest):
    def dry_run(self, workspace: Path, args: dict):
        rel_dir = args.get("dir","site")
        index_rel = Path(rel_dir) / "index.html"
        index_path = safe_join(workspace, index_rel)
        before = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
        after = _tailwind_index()
        diff = make_diff(before, after, str(index_rel))
        return {"preview_diff": diff, "files":[{"path": str(index_rel), "exists_before": index_path.exists()}]}

    def apply(self, workspace: Path, args: dict):
        rel_dir = args.get("dir","site")
        index_rel = Path(rel_dir) / "index.html"
        index_path = safe_join(workspace, index_rel)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(_tailwind_index(), encoding="utf-8")
        return {"artifacts":[{"type":"file","path": str(index_rel), "hash": file_hash(index_path)}]}

def _tailwind_index():
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.tailwindcss.com"></script>
    <title>__TITLE__</title>
  </head>
  <body class="min-h-screen bg-neutral-950 text-neutral-100 flex items-center justify-center">
    <main class="max-w-2xl text-center space-y-6">
      <h1 class="text-5xl font-black tracking-tight">__TITLE__</h1>
      <p class="opacity-80">Minimal Tailwind page scaffolded by Lilith.</p>
      <a class="px-4 py-2 rounded bg-white/10 hover:bg-white/20" href="#">Get started</a>
    </main>
  </body>
</html>
"""
class ShellEchoTool(ToolManifest):
    def dry_run(self, workspace: Path, args: dict):
        text = args.get("text","")
        preview = f"$ echo {text!r}\n{text}\n"
        return {"preview_log": preview}

    def apply(self, workspace: Path, args: dict):
        text = args.get("text","")
        # We only allow echo for safety in MVP
        return {"artifacts":[{"type":"log","path":"echo.log","hash":""}],"stdout": text}

TOOL_REGISTRY = {
    "write_file": WriteFileTool(name="write_file", args_schema={"path":"str","content":"str"},
                                side_effects={"fs": True,"net": False,"env": False}),
    "replace_text": ReplaceTextTool(name="replace_text", args_schema={"path":"str","search":"str","replace":"str"},
                                    side_effects={"fs": True,"net": False,"env": False}),
    "scaffold_site": ScaffoldSiteTool(name="scaffold_site", args_schema={"dir":"str"},
                                      side_effects={"fs": True,"net": False,"env": False}),
    "shell_echo": ShellEchoTool(name="shell_echo", args_schema={"text":"str"},
                                side_effects={"fs": False,"net": False,"env": False}),
}


# --- Lilith Fix Pack: basic file/process tools ---
from pathlib import Path as _LF_Path
import subprocess as _LF_subprocess, sys as _LF_sys

class ToolError(Exception): pass

def write_text(path: str, content: str):
    p = _LF_Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"wrote": str(p), "bytes": len(content)}

def append_text(path: str, content: str):
    p = _LF_Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f: f.write(content)
    return {"appended": str(p), "bytes": len(content)}

def ensure_requirements(packages: list[str]):
    p = _LF_Path("requirements.txt")
    existing = set()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                existing.add(s)
    desired = set(packages)
    merged = sorted(existing | desired)
    p.write_text("\n".join(merged) + "\n", encoding="utf-8")
    return {"requirements": merged}

def pip_install(args: list[str] = None):
    args = args or ["-r", "requirements.txt"]
    pip = _LF_Path(".venv/Scripts/pip.exe") if _LF_sys.platform.startswith("win") else _LF_Path(".venv/bin/pip")
    cmd = [str(pip), "install", *args]
    proc = _LF_subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ToolError(proc.stderr)
    return {"stdout": proc.stdout}

def run_command(cmd: list[str], cwd: str = "."):
    proc = _LF_subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return {"code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

try:
    TOOL_REGISTRY  # may already exist
except NameError:
    TOOL_REGISTRY = {}

TOOL_REGISTRY.update({
    "write_text": write_text,
    "append_text": append_text,
    "ensure_requirements": ensure_requirements,
    "pip_install": pip_install,
    "run_command": run_command,
})
# --- end Fix Pack block ---
