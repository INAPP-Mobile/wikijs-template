"""Step 6: Deploy to Railway."""
from __future__ import annotations
import subprocess
from .core import ok, step_header, warn


def step_6_deploy(template_dir: str) -> bool:
    step_header("Step 6", "Deploy")

    r = subprocess.run(["railway", "up"], cwd=template_dir, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        warn(f"Deploy: {r.stderr[:200]}")
    ok("Deployed")
    return True
