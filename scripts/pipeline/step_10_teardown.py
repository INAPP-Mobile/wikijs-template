"""Step 10: Cleanup."""
from __future__ import annotations
import shutil
from .core import step_header


def step_10_teardown(template_dir: str, cleanup: bool) -> bool:
    step_header("Step 10", "Done")
    if cleanup:
        shutil.rmtree(template_dir, ignore_errors=True)
    return True
