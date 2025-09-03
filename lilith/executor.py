from lilith.registry import TOOL_REGISTRY, ToolError
from lilith.utils import ensure_safe_args
from lilith.db import Checkpoint, session_scope
from pathlib import Path
import shutil, zipfile, time, os

def apply_tool(step, workspace: Path):
    tool = TOOL_REGISTRY.get(step.tool)
    if not tool:
        raise ToolError(f"Unknown tool: {step.tool}")
    args = step.args_json or {}
    ensure_safe_args(args)
    result = tool.apply(workspace, args)
    return result

def checkpoint_now(project_id: int, workspace: Path) -> Path:
    cp_dir = Path(__file__).resolve().parent.parent / "checkpoints" / str(project_id)
    cp_dir.mkdir(parents=True, exist_ok=True)
    ts = str(int(time.time()))
    zip_path = cp_dir / f"{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(workspace):
            for f in files:
                p = Path(root) / f
                zf.write(p, p.relative_to(workspace))
    with session_scope() as s:
        s.add(Checkpoint(project_id=project_id, zip_path=str(zip_path)))
    return zip_path

def rollback_last(project_id: int, workspace: Path):
    cp_dir = Path(__file__).resolve().parent.parent / "checkpoints" / str(project_id)
    if not cp_dir.exists():
        return False
    zips = sorted(cp_dir.glob("*.zip"), reverse=True)
    if not zips:
        return False
    latest = zips[0]
    # wipe workspace then restore
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(latest, "r") as zf:
        zf.extractall(workspace)
    return True


# --- Lilith Fix Pack: apply_tool dispatcher ---
from lilith.registry import TOOL_REGISTRY, ToolError as _LF_ToolError

def apply_tool(action: dict):
    name = action.get("name")
    args = action.get("args", {}) or {}
    if name not in TOOL_REGISTRY:
        raise _LF_ToolError(f"Unknown tool: {name}")
    fn = TOOL_REGISTRY[name]
    return fn(**args)
# --- end Fix Pack block ---
