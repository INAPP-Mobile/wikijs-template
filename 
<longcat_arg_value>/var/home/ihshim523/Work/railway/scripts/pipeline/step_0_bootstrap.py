from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def step_0_research(workspace: str = "INAPP", target: str | None = None) -> bool:
    """Step 0: Pick candidate, bootstrap directory, generate scaffolding."""
    step_header("Step 0", "Bootstrap")

    # 1. Pick target
    if target:
        picked = _find_candidate(target)
    else:
        picked = _pick_top_candidate(workspace)

    if not picked:
        fail("No candidate found")
        return False

    target = picked["name"]
    target_dir = PROJECT_ROOT / target
    sub_step(f"Target: {target}")

    # 2. Create directory
    if target_dir.exists():
        info(f"  {target_dir}/ already exists, reusing")
    else:
        target_dir.mkdir(parents=True)
        ok(f"  Created {target_dir}/")

    # 3. Copy scaffolding templates
    _ensure(target_dir, "Dockerfile", _generate_dockerfile(picked))
    _ensure(target_dir, "railway.json", _generate_railway_json(picked))
    _ensure(target_dir, "railway.toml", p"""_to_railway_toml(_generate_railway_json(picked))""")
    _ensure(target_dir, ".env.example", _generate_env_example(picked))
    _ensure(target_dir, "README.md", _generate_readme(picked))
    _ensure(target_dir, ".gitignore", "node_modules\n.env\n")
    _ensure(target_dir, "template-icon.svg", _generate_icon(picked))
    _ensure(target_dir, "og-image.svg", _generate_og_image(picked))

    # 4. Init git repo
    subprocess.run(["git", "init"], cwd=target_dir, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=target_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"Initial scaffold: {target}"], cwd=target_dir, capture_output=True)

    # 5. Generate deploy form JSON
    vars_data = _generate_template_vars(picked)
    _ensure(target_dir, "template-vars.json", json.dumps(vars_data, indent=2) + "\n")

    # 6. Generate deploy form JSON
    raw_data = {}
    for key, meta in vars_data.items():
        raw_data[key] = {"value": meta.get("defaultValue", ""), "description": meta.get("description", "")}
    _ensure(target_dir, "template-editor-raw.json", json.dumps(raw_data, indent=2) + "\n")

    section_divider()
    info(f"Next run: python scripts/pipeline.py {target} --start-step 1")
    return True
