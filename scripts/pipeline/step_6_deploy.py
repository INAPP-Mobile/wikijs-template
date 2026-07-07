"""Step 6: Deploy + auto-link project."""
from __future__ import annotations
import json, subprocess
from pathlib import Path
from .core import step_header, ok, warn


def step_6_deploy(template_dir: str) -> bool:
    step_header("Step 6", "Deploy")

    import os
    env = {**os.environ, "RAILWAY_WORKSPACE": _get_workspace(template_dir)}

    # Try link
    link_check = subprocess.run(
        ["railway", "project", "link"],
        cwd=template_dir,
        capture_output=True, text=True, timeout=15,
        env=env,
    )

    if link_check.returncode != 0:
        warn("No project linked, creating one...")
        name = _detect_name(template_dir)

        create = subprocess.run(
            ["railway", "project", "create", "--name", name],
            capture_output=True, text=True, timeout=60,
            env=env,
        )
        if create.returncode != 0:
            warn(f"Create: {create.stderr[:200]}")

        relink = subprocess.run(
            ["railway", "project", "link", "--project", name],
            capture_output=True, text=True, timeout=60,
            env=env,
        )
        if relink.returncode != 0:
            warn(f"Link: {relink.stderr[:100]}")

    # Deploy
    r = subprocess.run(
        ["railway", "up"],
        cwd=template_dir,
        capture_output=True, text=True, timeout=120,
        env=env,
    )
    if r.returncode != 0:
        if "already exists" in r.stderr.lower():
            warn("Project already exists")
        else:
            warn(f"Deploy: {r.stderr[:200]}")

    ok("Deployed")
    return True


def _get_workspace(template_dir: str) -> str:
    """Get workspace from railway.json or default INAPP."""
    rj = Path(template_dir) / ".railway" / "project.json"
    if rj.is_file():
        try:
            return json.loads(rj.read_text()).get("workspace", "INAPP")
        except Exception:
            pass
    return "INAPP"


def _detect_name(template_dir: str) -> str:
    rj_path = Path(template_dir) / "railway.json"
    if rj_path.is_file():
        try:
            rj = json.loads(rj_path.read_text())
            n = rj.get("name", "").replace(" ", "-").lower()
            if n:
                return n
        except Exception:
            pass
    return Path(template_dir).name
