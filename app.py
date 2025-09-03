from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from pathlib import Path
from lilith.db import Project, Step, Artifact, Event, Checkpoint, init_db, session_scope
from lilith.planner import deterministic_plan
from lilith.registry import TOOL_REGISTRY, ToolError
from lilith.mirror import run_mirror
from lilith.executor import apply_tool, checkpoint_now, rollback_last

# --- IMPORTANT: point Flask at lilith/templates & lilith/static ---
BASE = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE / "lilith" / "templates"),
    static_folder=str(BASE / "lilith" / "static"),
)

WORKSPACE = BASE / "workspace"
CHECKPOINTS = BASE / "checkpoints"
WORKSPACE.mkdir(exist_ok=True)
CHECKPOINTS.mkdir(exist_ok=True)

init_db(BASE / "lilith" / "lilith.db")

@app.route("/")
def index():
    with session_scope() as s:
        projects = s.query(Project).order_by(Project.created_at.desc()).all()
    return render_template("index.html", projects=projects)

@app.post("/projects")
def create_project():
    title = request.form.get("title","").strip() or "Untitled Project"
    goal  = request.form.get("goal","").strip()
    with session_scope() as s:
        p = Project(title=title, goal=goal, status="new")
        s.add(p); s.flush()
        # plan immediately
        steps = deterministic_plan(goal, proj_id=p.id, seed=42)
        for st in steps:
            s.add(st)
        s.add(Event(project_id=p.id, kind="planned", payload_json={"goal": goal, "steps": [st.title for st in steps]}))
        # create workspace
        (WORKSPACE / str(p.id)).mkdir(parents=True, exist_ok=True)
        s.commit()
        pid = p.id
    return redirect(url_for("project_view", project_id=pid))

@app.get("/project/<int:project_id>")
def project_view(project_id):
    with session_scope() as s:
        p = s.query(Project).get(project_id)
        steps = s.query(Step).filter(Step.project_id==project_id).order_by(Step.order_idx.asc()).all()
        artifacts = s.query(Artifact).filter(Artifact.project_id==project_id).order_by(Artifact.created_at.desc()).all()
        events = s.query(Event).filter(Event.project_id==project_id).order_by(Event.ts.desc()).limit(50).all()
        cps = s.query(Checkpoint).filter(Checkpoint.project_id==project_id).order_by(Checkpoint.ts.desc()).all()
    return render_template("project.html", p=p, steps=steps, artifacts=artifacts, events=events, checkpoints=cps)

@app.post("/step/<int:step_id>/mirror")
def step_mirror(step_id):
    with session_scope() as s:
        st = s.query(Step).get(step_id)
        p = s.query(Project).get(st.project_id)
    ws = WORKSPACE / str(p.id)
    try:
        preview = run_mirror(st, ws)
        status = 200
    except ToolError as e:
        preview = {"error": str(e)}
        status = 400
    return render_template("mirror.html", step=st, preview=preview), status

@app.post("/step/<int:step_id>/apply")
def step_apply(step_id):
    with session_scope() as s:
        st = s.query(Step).get(step_id)
        p = s.query(Project).get(st.project_id)
    ws = WORKSPACE / str(p.id)
    # checkpoint
    cp_path = checkpoint_now(project_id=p.id, workspace=ws)
    with session_scope() as s:
        s.add(Event(project_id=p.id, step_id=step_id, kind="checkpoint", payload_json={"zip": str(cp_path)}))
    # apply
    try:
        result = apply_tool(st, ws)
        with session_scope() as s:
            st = s.query(Step).get(step_id)
            st.status = "done"
            s.add(Event(project_id=st.project_id, step_id=st.id, kind="applied", payload_json=result))
            # artifacts
            for a in result.get("artifacts", []):
                s.add(Artifact(project_id=st.project_id, step_id=st.id, type=a.get("type","file"),
                               uri=a.get("path"), hash=a.get("hash","")))
        return jsonify({"ok": True, "message": "Applied", "step_id": step_id})
    except ToolError as e:
        with session_scope() as s:
            st = s.query(Step).get(step_id)
            st.status = "error"
            s.add(Event(project_id=st.project_id, step_id=st.id, kind="error", payload_json={"error": str(e)}))
        return jsonify({"ok": False, "error": str(e)}), 400

@app.post("/project/<int:project_id>/rollback")
def project_rollback(project_id):
    with session_scope() as s:
        p = s.query(Project).get(project_id)
    ws = WORKSPACE / str(p.id)
    restored = rollback_last(project_id=p.id, workspace=ws)
    with session_scope() as s:
        s.add(Event(project_id=p.id, kind="rolled_back", payload_json={"restored": restored}))
        st_any = s.query(Step).filter(Step.project_id==p.id, Step.status=="error").all()
        for st in st_any:
            st.status = "pending"
    return redirect(url_for("project_view", project_id=project_id))

@app.get("/artifact/<int:artifact_id>/download")
def artifact_download(artifact_id):
    with session_scope() as s:
        a = s.query(Artifact).get(artifact_id)
        p = s.query(Project).get(a.project_id)
    ws = WORKSPACE / str(p.id)
    file_path = ws / a.uri
    if not file_path.exists():
        return "Not found", 404
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)

# === LILITH: API ENDPOINTS ===
from flask import jsonify, request
from lilith.db import session_scope, Project, Step, Event
from lilith.mirror import run_mirror
from lilith.executor import apply_tool, checkpoint_now, rollback_last

def _step_or_404(session, step_id: int):
    step = session.query(Step).get(step_id)
    if not step:
        return None, (jsonify({"ok": False, "error": "step not found"}), 404)
    return step, None

@app.post("/api/steps/<int:step_id>/mirror")
def api_mirror_step(step_id):
    with session_scope() as s:
        step, err = _step_or_404(s, step_id)
        if err: return err
        try:
            preview = run_mirror(step)
            # Log event
            e = Event(kind="mirror", message=f"Mirrored step {step_id}", project_id=step.project_id, step_id=step.id)
            s.add(e)
            return jsonify({"ok": True, "preview": preview})
        except Exception as ex:
            e = Event(kind="error", message=f"Mirror failed for step {step_id}: {ex}", project_id=step.project_id, step_id=step.id)
            s.add(e)
            return jsonify({"ok": False, "error": str(ex)}), 500

@app.post("/api/steps/<int:step_id>/apply")
def api_apply_step(step_id):
    with session_scope() as s:
        step, err = _step_or_404(s, step_id)
        if err: return err
        try:
            out = apply_tool(step)
            checkpoint_now(step.project_id, reason=f"apply step {step_id}")
            e = Event(kind="apply", message=f"Applied step {step_id}", project_id=step.project_id, step_id=step.id)
            s.add(e)
            return jsonify({"ok": True, "result": out})
        except Exception as ex:
            e = Event(kind="error", message=f"Apply failed for step {step_id}: {ex}", project_id=step.project_id, step_id=step.id)
            s.add(e)
            return jsonify({"ok": False, "error": str(ex)}), 500

@app.post("/api/projects/<int:project_id>/rollback")
def api_rollback_project(project_id):
    with session_scope() as s:
        try:
            rollback_last(project_id)
            e = Event(kind="rollback", message=f"Rollback on project {project_id}", project_id=project_id)
            s.add(e)
            return jsonify({"ok": True})
        except Exception as ex:
            e = Event(kind="error", message=f"Rollback failed on project {project_id}: {ex}", project_id=project_id)
            s.add(e)
            return jsonify({"ok": False, "error": str(ex)}), 500
# === LILITH: API ENDPOINTS (end) ===

