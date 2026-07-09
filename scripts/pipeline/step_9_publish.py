"""Step 9: Create draft template."""
from __future__ import annotations
import json, subprocess
from pathlib import Path
from .core import fail, ok, step_header, warn


def step_9_publish(template_dir: str) -> bool:
    step_header("Step 9", "Draft")

    # Get project ID from .railway/project.json
    project_json = Path(template_dir) / ".railway" / "project.json"
    if not project_json.is_file():
        fail("No .railway/project.json found. Run step 6 first.")
        return False

    try:
        data = json.loads(project_json.read_text())
        project_id = data.get("projectId") or data.get("id")
    except Exception:
        fail("Cannot parse .railway/project.json")
        return False

    if not project_id:
        fail("No project ID found")
        return False

    # Create template with explicit project ID
    r = subprocess.run(
        ["railway", "templates", "create", "--project", project_id, "--json"],
        capture_output=True, text=True, timeout=60,
    )

    if r.returncode != 0:
        fail(f"Template creation failed: {r.stderr[:300]}")
        return False

    ok("Draft created (NOT published)")
    return True
