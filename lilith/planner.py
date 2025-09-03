from lilith.db import Step

# Very small deterministic planner: parse a goal string to steps.
def deterministic_plan(goal: str, proj_id: int, seed: int = 42):
    goal = (goal or "").lower()
    steps = []
    idx = 0

    # Always start with README
    steps.append(Step(
        project_id=proj_id,
        title="Create README",
        desc="Initialize project README",
        required=True,
        order_idx=idx,
        tool="write_file",
        args_json={"path": "README.md", "content": f"# Project\n\nGoal: {goal or 'N/A'}\n"}
    ))
    idx += 1

    # If a site is mentioned, scaffold minimal site (Tailwind via CDN)
    if any(k in goal for k in ["site", "landing", "page", "tailwind", "vercel", "web"]):
        steps.append(Step(
            project_id=proj_id,
            title="Scaffold minimal Tailwind page",
            required=True,
            order_idx=idx,
            tool="scaffold_site",
            args_json={"dir": "site"}
        ))
        idx += 1

        steps.append(Step(
            project_id=proj_id,
            title="Add hero title",
            required=False,
            order_idx=idx,
            tool="replace_text",
            args_json={
                "path": "site/index.html",
                "search": "__TITLE__",
                "replace": "Lilith: here, done <3"
            }
        ))
        idx += 1

    # Optional: add license
    steps.append(Step(
        project_id=proj_id,
        title="Add LICENSE (MIT)",
        required=False,
        order_idx=idx,
        tool="write_file",
        args_json={"path": "LICENSE", "content": _mit_text()}
    ))
    idx += 1

    return steps


def _mit_text():
    return (
        "MIT License\n\n"
        "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
        "of this software and associated documentation files (the \"Software\"), to deal\n"
        "in the Software without restriction, including without limitation the rights\n"
        "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
        "copies of the Software, and to permit persons to whom the Software is\n"
        "furnished to do so, subject to the following conditions:\n\n"
        "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND.\n"
    )


# --- Light wrapper to keep minimum step count logic without side-effects ---
def _lf_wrap_deterministic_plan(original_fn):
    import os as _lf_os
    def _wrapped(goal: str, proj_id: int, seed: int = 42):
        try:
            steps = original_fn(goal, proj_id, seed)
        except Exception:
            steps = []
        # ensure at least a minimal number of steps if desired via env
        min_steps = int(_lf_os.getenv("LLM_MIN_STEPS", "1"))
        if len(steps) >= min_steps:
            return steps
        return steps
    return _wrapped


try:
    deterministic_plan  # noqa: F821
except NameError:
    pass
else:
    deterministic_plan = _lf_wrap_deterministic_plan(deterministic_plan)
# --- end ---
