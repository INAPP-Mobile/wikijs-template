"""Step 0: Static checks + duplicate detection."""
from __future__ import annotations
import json, re, subprocess
from .core import (
    fail, ok, print_go_nogo, read_file_content, section_divider,
    step_header, sub_step, warn,
)


def step_0_research(template_dir: str, workspace: str) -> bool:
    step_header("Step 0", "Static Checks + Dedup")

    content = read_file_content(template_dir, "Dockerfile")
    if not content:
        fail("Dockerfile not found")
        return False

    blockers = _detect_blockers(content)
    for b in blockers:
        warn(b)

    name = _detect_name(content, template_dir)
    published = _fetch_published(workspace)

    if _is_duplicate(name, published):
        fail(f"'{name}' duplicates published: {_find_matches(name, published)}")
        return False

    ok(f"Candidate: {name}")
    return not blockers


def _detect_blockers(content: str) -> list[str]:
    out = []
    if ":latest" in content.lower():
        out.append(":latest")
    if "USER " not in content and "USER\t" not in content:
        out.append("No USER")
    if "HEALTHCHECK" not in content:
        out.append("No HEALTHCHECK")
    return out


def _detect_name(content: str, fallback: str) -> str:
    m = re.search(r'FROM\s+(\S+)', content)
    if m:
        return m.group(1).split("/")[-1].split(":")[0].lower()
    return fallback.split("/")[-1].replace("railway-", "").lower()


def _fetch_published(workspace: str) -> list:
    try:
        r = subprocess.run(
            ["railway", "templates", "list", "--workspace", workspace, "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return []
        parsed = json.loads(r.stdout) if r.stdout.strip() else []
        items = parsed if isinstance(parsed, list) else parsed.get("items", parsed.get("data", []))
        return list(items.values()) if isinstance(items, dict) else items
    except Exception:
        return []


def _is_duplicate(name: str, published: list) -> bool:
    normalized = re.sub(r'[\s_\-]+', '-', name.lower().strip())
    for t in published:
        for key in ("name", "slug", "code"):
            val = re.sub(r'[\s_\-]+', '-', t.get(key, "").lower().strip())
            if val and (normalized in val or val in normalized):
                return True
    return False


def _find_matches(name: str, published: list) -> list:
    matches = []
    normalized = re.sub(r'[\s_\-]+', '-', name.lower().strip())
    for t in published:
        for key in ("name", "slug", "code"):
            val = re.sub(r'[\s_\-]+', '-', t.get(key, "").lower().strip())
            if val and (normalized in val or val in normalized):
                matches.append(f"{key}={t.get(key)}")
    return matches
