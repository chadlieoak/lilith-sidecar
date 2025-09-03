# lilith/routes_mirror.py
from flask import Blueprint, request, jsonify
from lilith.mirror import run_mirror
from lilith.executor import apply_tool, checkpoint_now
from lilith.db import Event, session_scope, Step

mirror_bp = Blueprint("mirror_bp", __name__)

@mirror_bp.route("/steps/<int:sid>/mirror", methods=["POST"])
def mirror_step(sid: int):
    body = request.get_json(silent=True) or {}
    dry = bool(body.get("dry_run", True))

    with session_scope() as s:
        st = s.query(Step).get(sid)
        if not st:
            return jsonify({"ok": False, "error": f"step {sid} not found"}), 404

        if dry:
            diff = run_mirror(step_id=sid, apply=False)
            Event.log(kind="mirror_preview", step_id=sid, meta={"len": len(diff or "")})
            return jsonify({"ok": True, "diff": diff, "applied": False})

        # Apply path: checkpoint -> apply -> event + mark step
        checkpoint_now(reason=f"apply step {sid}")
        result = run_mirror(step_id=sid, apply=True)
        try:
            apply_tool(step_id=sid)  # keep if your pipeline expects it
        except Exception:
            # If apply_tool is already done by run_mirror, you can ignore or log
            pass

        st.status = "applied"
        Event.log(kind="mirror_apply", step_id=sid, meta={"result": bool(result)})
        return jsonify({"ok": True, "diff": result, "applied": True})
