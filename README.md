# Lilith Sidecar — MVP

[![Dev Bootstrap & Sanity](https://github.com/chadlieoak/lilith-sidecar/actions/workflows/dev.yml/badge.svg)](https://github.com/chadlieoak/lilith-sidecar/actions/workflows/dev.yml)

A minimal, runnable prototype of the **core Lilith loop**:

- **Memory + Provenance**: SQLite with Projects, Steps, Artifacts, Events, Checkpoints.
- **Deterministic Planner**: seeded plan from a goal/spec.
- **Mirror (dry-run)**: shows diffs/files touched before applying.
- **Sandboxed Executor + Rollback**: path jail per project, checkpoints as zips, one-click rollback.
- **HTMX UI**: chat-ish surface with chips (Mirror · Apply · Skip · Rollback).

## Quickstart

```bash
cd lilith_sidecar_mvp
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export FLASK_APP=app.py
flask run  # visit http://127.0.0.1:5000
```

## Notes

- Workspace is under `workspace/<project_id>` (auto-created).
- Checkpoints saved under `checkpoints/<project_id>/<timestamp>.zip`.
- Tools included:
  - `scaffold_site`: creates a minimal Tailwind landing page (CDN) and README.
  - `write_file`: write content to a path (safe path-joined, mirrorable).
  - `replace_text`: search/replace within a file (mirrorable).
  - `shell_echo`: demonstration of a "command tool" that only allows `echo` (no arbitrary shell).
- Deterministic planner emits required+optional steps from the goal string.

This is intentionally compact—so you can see it working end-to-end today and extend it.
