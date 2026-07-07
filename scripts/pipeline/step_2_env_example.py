"""Step 2: .env.example generation (deterministic)."""
from __future__ import annotations
from .core import fail, ok, read_file_content, step_header, sub_step, template_path


def step_2_env_example(template_dir: str) -> bool:
    step_header("Step 2", ".env.example")

    dockerfile = read_file_content(template_dir, "Dockerfile")
    if not dockerfile:
        fail("Dockerfile not found")
        return False

    lines = ["# Environment variables"]
    for line in dockerfile.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) >= 2 and parts[0] == "ENV":
            kv = " ".join(parts[1:]).split("=", 1)
            if len(kv) == 2:
                v = kv[1].strip().strip('"').strip("'")
                lines.append(f"# {kv[0]} - from Dockerfile")
                lines.append(f'{kv[0]}="{v}"')

    if len(lines) == 1:
        lines.append('PORT="3000"')

    template_path(template_dir, ".env.example").write_text("\n".join(lines) + "\n")
    ok(f"Wrote .env.example ({len(lines)} lines)")
    return True
