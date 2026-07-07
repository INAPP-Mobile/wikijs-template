"""Step 5: Commit + push."""
from __future__ import annotations
import subprocess
from .core import ok, step_header, warn


def step_5_commit_push(template_dir: str, confirm: bool = False) -> bool:
    step_header("Step 5", "Commit + Push")

    subprocess.run(["git", "add", "-A"], cwd=template_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"Update: {template_dir}"], cwd=template_dir, capture_output=True)

    if confirm:
        ans = input("Push? [y/N]: ")
        if ans.lower() != "y":
            warn("Push skipped")
            return True

    subprocess.run(["git", "push"], cwd=template_dir, capture_output=True)
    ok("Committed")
    return True
