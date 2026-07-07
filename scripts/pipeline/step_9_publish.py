"""Step 9: Create draft template."""
from __future__ import annotations
import subprocess
from .core import fail, ok, step_header


def step_9_publish(template_dir: str) -> bool:
    step_header("Step 9", "Draft")

    r = subprocess.run(["railway", "template", "create", "--project", template_dir], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        fail(f"Template creation failed: {r.stderr[:200]}")
        return False

    ok("Draft created (NOT published)")
    return True
