"""Step 7: Variables + template creation."""
from __future__ import annotations
import json, subprocess
from .core import (
    _generate_template_vars, _generate_template_editor_raw, ok, step_header,
    sub_step, template_path, warn,
)


def step_7_vars_and_template(template_dir: str) -> bool:
    step_header("Step 7", "Variables + Template")

    # Generate template-vars.json
    sub_step("Generating vars...")
    vars_data = _generate_template_vars(template_dir)
    template_path(template_dir, "template-vars.json").write_text(json.dumps(vars_data, indent=2) + "\n")

    # Generate template-editor-raw.json
    _generate_template_editor_raw(template_dir)
    ok("Vars generated")

    return True
