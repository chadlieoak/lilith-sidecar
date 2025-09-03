from lilith.registry import TOOL_REGISTRY, ToolError
from lilith.utils import ensure_safe_args
from pathlib import Path

def run_mirror(step, workspace: Path):
    tool = TOOL_REGISTRY.get(step.tool)
    if not tool:
        raise ToolError(f"Unknown tool: {step.tool}")
    args = step.args_json or {}
    ensure_safe_args(args)
    return tool.dry_run(workspace, args)
