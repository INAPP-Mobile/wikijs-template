"""
Railway Template Publish Pipeline
=================================
Usage:
  python scripts/pipeline.py <app-name> [--workspace INAPP] [--no-pause]
  python scripts/pipeline.py <app-name> --start-step 4

Name argument:
  Any name: 'keycloak', 'my-app', 'my_app'. No railway- prefix required.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from .core import (
    PROJECT_ROOT, _check_railway_freshness, check_worker_available,
    header, info, ok, fail, C_BOLD, C_BLUE, C_CYAN, C_RED, C_YELLOW, C_RESET, _emit,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Railway Template Publish Pipeline",
        epilog="""
Examples:
  python scripts/pipeline.py keycloak
  python scripts/pipeline.py memos --workspace INAPP --cleanup
  python scripts/pipeline.py gotify --no-pause
        """,
    )
    parser.add_argument("template_dir", help="Directory name (e.g. keycloak)")
    parser.add_argument("--workspace", "-w", default="INAPP", help="Railway workspace")
    parser.add_argument("--no-pause", action="store_true")
    parser.add_argument("--confirm-push", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--start-step", type=int, default=0)
    parser.add_argument("--llm-timeout", type=int, default=600)
    args = parser.parse_args()

    from . import core as core_mod
    core_mod.LLM_TIMEOUT = args.llm_timeout

    template_dir = args.template_dir
    for prefix in ("railway-", "railway_"):
        if template_dir.startswith(prefix):
            stripped = template_dir[len(prefix):]
            info(f"Stripped '{prefix}' -> '{stripped}'")
            template_dir = stripped
            break

    workspace = args.workspace

    if not (PROJECT_ROOT / template_dir).is_dir():
        _emit(f"{C_YELLOW}Directory '{template_dir}' missing, step 0 will bootstrap{C_RESET}")

    if not check_worker_available():
        fail("worker not available")
        sys.exit(1)

    _check_railway_freshness()

    header("Railway Template Publish Pipeline")
    _emit(f"  Template: {C_BOLD}{template_dir}{C_RESET}")
    _emit(f"  Workspace: {workspace}")
    _emit(f"  Start step: {args.start_step}")

    def load_step(step_num: int):
        if step_num == 0:
            from .step_0_research import step_0_research
            return step_0_research(template_dir, workspace)
        elif step_num == 1:
            from .step_1_dockerfile import step_1_dockerfile
            return step_1_dockerfile(template_dir, args.no_pause)
        elif step_num == 2:
            from .step_2_env_example import step_2_env_example
            return step_2_env_example(template_dir)
        elif step_num == 3:
            from .step_3_icons_readme import step_3_icons_readme
            return step_3_icons_readme(template_dir, args.no_pause)
        elif step_num == 4:
            from .step_4_build_test import step_4_build_test
            return step_4_build_test(template_dir)
        elif step_num == 5:
            from .step_5_commit_push import step_5_commit_push
            return step_5_commit_push(template_dir, args.confirm_push)
        elif step_num == 6:
            from .step_6_deploy import step_6_deploy
            return step_6_deploy(template_dir)
        elif step_num == 7:
            from .step_7_vars_template import step_7_vars_and_template
            return step_7_vars_and_template(template_dir)
        elif step_num == 8:
            from .step_8_pre_publish import step_8_pre_publish
            return step_8_pre_publish(template_dir)
        elif step_num == 9:
            from .step_9_publish import step_9_publish
            return step_9_publish(template_dir)
        elif step_num == 10:
            from .step_10_teardown import step_10_teardown
            return step_10_teardown(template_dir, args.cleanup)
        return False

    for i in range(args.start_step, 11):
        success = load_step(i)
        if not success:
            fail(f"Step {i} NO-GO. Fix and rerun: --start-step {i}")
            break
    else:
        ok("PIPELINE COMPLETE")


if __name__ == "__main__":
    main()
