"""Step 1: Dockerfile validation + small LLM fixes."""
from __future__ import annotations
import re
from .core import (
    call_worker, clean_llm_output, deterministic_review, fail, ok,
    print_go_nogo, read_file_content, section_divider, step_header,
    sub_step, template_path, warn,
)


def step_1_dockerfile(template_dir: str, no_pause: bool = False) -> bool:
    step_header("Step 1", "Dockerfile Validation")

    content = read_file_content(template_dir, "Dockerfile")
    if not content:
        fail("Dockerfile not found")
        return False

    final = content

    # Phase 0: :latest tag
    if ":latest" in final and "scratch:latest" not in final:
        sub_step("Phase 0/5: Pin version...")
        r = call_worker(f"Replace :latest tag with a pinned version (e.g. alpine:3.20). Return ONLY full Dockerfile:\n{final}", step_name="Step 0a")
        if r:
            final = clean_llm_output(r)

    # Phase 1: USER directive
    if "USER " not in final or "USER root" in final:
        sub_step("Phase 1/5: USER...")
        r = call_worker(f"Add non-root USER (node or 1000) to this Dockerfile. Return ONLY the full Dockerfile:\n{final}", step_name="Step 1a")
        if r:
            final = clean_llm_output(r)

    # Phase 2: EXPOSE
    if "EXPOSE " not in final:
        sub_step("Phase 2/4: EXPOSE...")
        r = call_worker(
            f"Add EXPOSE 8080 to this Dockerfile. Return ONLY the full Dockerfile:\n{final}",
            step_name="Step 1b"
        )
        if r:
            final = clean_llm_output(r)

    # Phase 3: HEALTHCHECK
    if "HEALTHCHECK" not in final:
        sub_step("Phase 3/4: HEALTHCHECK...")
        r = call_worker(
            f"Add HEALTHCHECK directive. Return ONLY the full Dockerfile:\n{final}",
            step_name="Step 1c"
        )
        if r:
            final = clean_llm_output(r)

    # Phase 4: Verify
    sub_step("Phase 4/4: Verify...")
    blockers = []
    if ":latest" in final and "scratch:latest" not in final:
        blockers.append(":latest tag")
    if "USER " not in final:
        blockers.append("USER missing")
    if "HEALTHCHECK" not in final:
        blockers.append("HEALTHCHECK missing")
    if "EXPOSE " not in final:
        blockers.append("EXPOSE missing")

    if blockers:
        fail(f"Still broken: {blockers}")
        return False

    template_path(template_dir, "Dockerfile").write_text(final)
    ok("Dockerfile passes")
    return True
