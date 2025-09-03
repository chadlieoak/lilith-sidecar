# lilith/routes_plan.py
from flask import Blueprint, current_app, request, jsonify
from lilith.plan_engine import StepSpec
from lilith.db import Project, Step, session_scope

plan_bp = Blueprint("plan_bp", __name__)

def _resolve_plan_engine_name(project) -> str:
    # priority: request arg > project.meta > app default
    name = request.args.get("planner")
    if name:
        return name
    meta = getattr(project, "meta", {}) or {}
    return meta.get("planner") or current_app.config.get("DEFAULT_PLAN_ENGINE", "deterministic")

@plan_bp.route("/projects/<int:pid>/plan", methods=["POST"])
def generate_plan(pid: int):
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    goal = (payload.get("goal") or "").strip()

    if not (title or goal):
        return jsonify({"ok": False, "error": "title or goal required"}), 400

    with session_scope() as s:
        proj = s.query(Project).get(pid)
        if not proj:
            return jsonify({"ok": False, "error": f"project {pid} not found"}), 404

        engine_name = _resolve_plan_engine_name(proj)
        engine = current_app.config["PLAN_REGISTRY"].get(engine_name)

        steps: list[StepSpec] = engine.generate(title=title, goal=goal, context={"project_id": pid})

        # Append steps (leave UI/DB schema unchanged). If you prefer, clear pending first.
        ordinal_start = len(proj.steps or [])
        created = []
        for i, spec in enumerate(steps, start=ordinal_start):
            st = Step(
                project_id=proj.id,
                ordinal=i,
                title=spec.title,
                required=bool(spec.required),
                status="pending",
            )
            s.add(st)
            created.append(st)
        s.flush()

        out = [
            {"id": st.id, "ordinal": st.ordinal, "title": st.title,
             "required": bool(st.required), "status": st.status}
            for st in proj.steps
        ]

    return jsonify({"ok": True, "steps": out, "planner": engine_name})
