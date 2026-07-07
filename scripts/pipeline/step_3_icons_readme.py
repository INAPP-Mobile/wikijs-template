"""Step 3: Icons + README generation."""
from __future__ import annotations
import os
from .core import (
    call_worker, clean_llm_output, ok, read_file_content, step_header,
    sub_step, template_path,
)


def step_3_icons_readme(template_dir: str, no_pause: bool = False) -> bool:
    step_header("Step 3", "Icons + README")

    name = os.path.basename(template_dir).replace("railway-", "").replace("_", " ").title()

    # Icon (deterministic)
    icon_path = template_path(template_dir, "template-icon.svg")
    if not icon_path.exists():
        hue = (sum(ord(c) for c in name.lower()) * 37) % 360
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800"><rect width="800" height="800" rx="120" fill="hsl({hue},70%,50%)"/><text x="400" y="550" font-family="Arial,sans-serif" font-size="400" font-weight="bold" fill="white" text-anchor="middle">{name[0]}</text></svg>\n'
        icon_path.write_text(svg)
        ok("Wrote template-icon.svg")

    # OG image (deterministic)
    og_path = template_path(template_dir, "og-image.svg")
    if not og_path.exists():
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630"><rect width="1200" height="630" fill="#1a1b1e"/><text x="600" y="315" font-family="Arial,sans-serif" font-size="72" font-weight="bold" fill="white" text-anchor="middle">{name} on Railway</text></svg>\n'
        og_path.write_text(svg)
        ok("Wrote og-image.svg")

    # README (LLM)
    readme_path = template_path(template_dir, "README.md")
    if not readme_path.exists() or readme_path.stat().st_size < 100:
        sub_step("Generating README...")
        prompt = f"Write a README.md for a Railway template called '{name}'. Include: title, deploy button (https://railway.app/new/template/{name.lower()}), features, config table, license. Return ONLY markdown."
        r = call_worker(prompt, step_name="Step 3 README")
        if r:
            readme_path.write_text(clean_llm_output(r))
            ok("Wrote README.md")

    return True
