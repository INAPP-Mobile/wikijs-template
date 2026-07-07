"""
Pipeline core utilities.
"""
from __future__ import annotations
import json, os, re, shlex, subprocess, sys, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
C_RED, C_GREEN, C_YELLOW, C_BLUE, C_BOLD, C_DIM, C_CYAN, C_RESET = (
    "\033[0;31m", "\033[0;32m", "\033[0;33m", "\033[0;34m",
    "\033[1m", "\033[2m", "\033[0;36m", "\033[0m",
)
HERMES_EXE_RAW = os.environ.get("HERMES_EXE", "worker")
HERMES_ARGV = shlex.split(HERMES_EXE_RAW)
LLM_TIMEOUT = 600

def _emit(text="", log_text=""):
    print(text)

def _emit_raw(text=""):
    print(text)

def step_header(step, desc):
    print(f"\n{C_BOLD}{C_BLUE}┌─ {step} {'─' * (50 - len(step))}")
    print(f"{C_RESET}{desc}")
    print(f"{C_BOLD}{C_BLUE}└{'─' * 56}┘{C_RESET}\n")

def sub_step(msg):
    print(f"  {C_DIM}{msg}{C_RESET}")

def header(title):
    print(f"\n{C_BOLD}{C_BLUE}{'=' * 72}")
    print(f"  {title}")
    print(f"{'=' * 72}{C_RESET}")

def section_divider():
    print(f"\n{'─' * 72}\n")

def ok(msg):
    print(f"  {C_GREEN}✓ {msg}{C_RESET}")

def warn(msg):
    print(f"  {C_YELLOW}⚠ {msg}{C_RESET}")

def fail(msg):
    print(f"  {C_RED}✗ BLOCKER: {msg}{C_RESET}")

def info(msg):
    print(f"  {C_DIM}{msg}{C_RESET}")

def print_go_nogo(is_go, reasoning):
    if is_go:
        print(f"\n  {C_GREEN}GO: {reasoning}{C_RESET}")
    else:
        print(f"\n  {C_RED}NO-GO: {reasoning}{C_RESET}")

def deterministic_review(context, passed, detail=""):
    return passed, f"{context}: {'PASS' if passed else 'FAIL'}. {detail}"

def call_worker(prompt, step_name, timeout_seconds=None):
    if timeout_seconds is None:
        timeout_seconds = LLM_TIMEOUT
    r = subprocess.run(
        [*HERMES_ARGV, "-z", prompt],
        capture_output=True, text=True, timeout=timeout_seconds,
        stdin=subprocess.DEVNULL,
    )
    return r.stdout.strip()

def clean_llm_output(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return raw.strip()

def read_file_content(dir_path, filename=None):
    p = Path(dir_path) / filename if filename else Path(dir_path)
    return p.read_text() if p.is_file() else ""

template_path = lambda d, f: Path(d) / f
file_exists = lambda d, f: (Path(d) / f).is_file()

def _generate_template_vars(template_dir):
    df = read_file_content(template_dir, "Dockerfile")
    name = Path(template_dir).name.replace("-", "_").upper()
    m = re.search(r'PORT=(\d+)', df)
    port = int(m.group(1)) if m else 3000
    return {
        "PORT": {"defaultValue": str(port), "description": f"Port {name} listens on", "isOptional": False},
        f"{name}_SECRET_KEY": {"defaultValue": "${{secret(32)}}", "description": "Secret key", "isOptional": False},
    }

def _generate_template_editor_raw(template_dir):
    vp = template_path(template_dir, "template-vars.json")
    if not vp.is_file():
        return False
    try:
        data = json.loads(vp.read_text())
        raw = {k: {"value": v.get("defaultValue", ""), "description": v.get("description", "")} for k, v in data.items()}
        template_path(template_dir, "template-editor-raw.json").write_text(json.dumps(raw, indent=2) + "\n")
        return True
    except Exception:
        return False

def _get_railway_env():
    e = os.environ.copy()
    e["RAILWAY_CALLER"] = "skill:pipeline@2.0"
    e["RAILWAY_AGENT_SESSION"] = f"pipeline-{os.getpid()}"
    return e

def check_worker_available():
    try:
        r = subprocess.run(HERMES_ARGV + ["--version"], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False

def _check_railway_freshness():
    try:
        subprocess.run(["railway", "--version"], capture_output=True, text=True, timeout=10)
    except Exception:
        warn("Railway CLI not healthy")
