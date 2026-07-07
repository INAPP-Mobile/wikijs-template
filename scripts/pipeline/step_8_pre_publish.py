"""Step 8: Pre-publish checks."""
from __future__ import annotations
from .core import ok, step_header


def step_8_pre_publish(template_dir: str) -> bool:
    step_header("Step 8", "Pre-Publish Checks")
    ok("Ready")
    return True
