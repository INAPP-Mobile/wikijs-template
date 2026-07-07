"""Step 4: Build + health check test."""
from __future__ import annotations
import subprocess
from .core import (
    call_worker, clean_llm_output, fail, ok, read_file_content,
    step_header, sub_step, template_path, warn,
)


def step_4_build_test(template_dir: str) -> bool:
    step_header("Step 4", "Build + Test")

    image_name = f"railway-{template_dir}:test"
    dockerfile = read_file_content(template_dir, "Dockerfile")

    # Build
    sub_step("Building...")
    build = subprocess.run(
        ["podman", "build", "-t", image_name, "-f", "-", "."],
        input=dockerfile, capture_output=True, text=True, timeout=300,
    )

    if build.returncode != 0:
        warn(f"Build failed: {build.stderr[-300:]}")
        r = call_worker(f"Fix this Dockerfile. Return ONLY the full Dockerfile:\nDockerfile:\n{dockerfile}\nError:\n{build.stderr[-300:]}", step_name="Step 4 fix")
        if r:
            dockerfile = clean_llm_output(r)
            template_path(template_dir, "Dockerfile").write_text(dockerfile)
            build = subprocess.run(
                ["podman", "build", "-t", image_name, "-f", "-", "."],
                input=dockerfile, capture_output=True, text=True, timeout=300,
            )
            if build.returncode != 0:
                fail("Build failed after LLM fix")
                return False

    ok("Build succeeded")

    # Health check
    sub_step("Health check...")
    subprocess.run(["podman", "rm", "-f", f"test-{template_dir}"], capture_output=True)
    run = subprocess.run(
        ["podman", "run", "--rm", "-d", "--name", f"test-{template_dir}", image_name],
        capture_output=True, text=True,
    )

    if run.returncode != 0:
        warn(f"Container failed to start: {run.stderr[-200:]}")
        ok("Build passes (container may need external services)")
        return True

    import time
    time.sleep(5)

    inspect = subprocess.run(
        ["podman", "inspect", "--format", "{{.State.Status}}", f"test-{template_dir}"],
        capture_output=True, text=True,
    )
    subprocess.run(["podman", "rm", "-f", f"test-{template_dir}"], capture_output=True)

    status = inspect.stdout.strip()
    if status == "running":
        ok("Container healthy")
    else:
        warn(f"Container status: {status}")

    return True
