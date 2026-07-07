#!/usr/bin/env python3
"""Integration test for the deterministic Dockerfile fix patterns from scripts/pipeline/core.py.

Tests every pattern in DETERMINISTIC_FIXES:
  - Should-match: the pattern correctly transforms a broken Dockerfile
  - Should-NOT-match: pattern skips an already-fixed Dockerfile
  - Negative lookahead guards: --host/--port/--bind already present -> no-op
  - Word boundaries: "restart" != "start"
  - First-match priority: apply_deterministic_fix returns first pattern
  - Case insensitivity: CMD/cmd/Cmd treated the same
  - Multiline: only the target line changes, rest preserved
  - No false positives: clean Dockerfile triggers nothing

Output format (one per test):
  PASS|<name>
  FAIL|<name>|<reason>
  SKIP|<name>|<reason>

Exit code 0 if all tests pass, 1 otherwise.
"""

from __future__ import annotations

import re
import sys

# Import patterns from the pipeline module instead of duplicating them
sys.path.insert(0, "scripts")
from pipeline.core import DETERMINISTIC_FIXES, apply_deterministic_fix  # noqa: E402


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

PASSES = 0
FAILS = 0


def test(name: str, passed: bool, detail: str = "") -> None:
    global PASSES, FAILS
    if passed:
        print(f"PASS|{name}")
        PASSES += 1
    else:
        print(f"FAIL|{name}|{detail}")
        FAILS += 1


def check_pattern(name: str, pattern_idx: int, input_text: str, expected: str | None) -> None:
    """Test a single pattern. expected=None means NO_MATCH."""
    pattern, replacement, desc = DETERMINISTIC_FIXES[pattern_idx]
    new_content, count = re.subn(pattern, replacement, input_text, flags=re.IGNORECASE)

    if expected is None:
        if count == 0:
            test(name, True)
        else:
            test(name, False, f"unexpected match: {new_content!r}")
    else:
        if count == 0:
            test(name, False, "expected match, got no match")
        elif new_content.strip() == expected.strip():
            test(name, True)
        else:
            test(name, False, f"mismatch:\n  got: {new_content!r}\n  exp: {expected!r}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — start -> start-dev (Patterns 0-1)
# ═══════════════════════════════════════════════════════════════════════════

print("── Pattern 1: ENTRYPOINT start -> start-dev ──")

check_pattern(
    "ENTRYPOINT start -> start-dev", 0,
    'ENTRYPOINT ["kc.sh", "start"]',
    'ENTRYPOINT ["kc.sh", "start-dev"]',
)

check_pattern(
    "word boundary: start matches", 0,
    'ENTRYPOINT ["sh", "start"]',
    'ENTRYPOINT ["sh", "start-dev"]',
)

check_pattern(
    "word boundary: starting skipped", 0,
    'ENTRYPOINT ["kc.sh", "starting"]',
    None,
)

check_pattern(
    "already start-dev -> no-op", 0,
    'ENTRYPOINT ["kc.sh", "start-dev"]',
    None,
)

print("── Pattern 2: CMD start -> start-dev ──")

check_pattern(
    "CMD start -> start-dev", 1,
    'CMD ["java", "-jar", "start"]',
    'CMD ["java", "-jar", "start-dev"]',
)

check_pattern(
    "CMD already start-dev -> no-op", 1,
    'CMD ["kc.sh", "start-dev"]',
    None,
)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — serve -> dev (Patterns 2-3)
# ═══════════════════════════════════════════════════════════════════════════

print("── Pattern 3: ENTRYPOINT serve -> dev ──")

check_pattern(
    "ENTRYPOINT serve -> dev", 2,
    'ENTRYPOINT ["node", "serve"]',
    'ENTRYPOINT ["node", "dev"]',
)

check_pattern(
    "ENTRYPOINT already dev -> no-op", 2,
    'ENTRYPOINT ["node", "dev"]',
    None,
)

print("── Pattern 4: CMD serve -> dev ──")

check_pattern(
    "CMD serve -> dev", 3,
    'CMD ["npm", "run", "serve"]',
    'CMD ["npm", "run", "dev"]',
)

check_pattern(
    "CMD already dev -> no-op", 3,
    'CMD ["npm", "run", "dev"]',
    None,
)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — Python framework binds (Patterns 4-7)
# ═══════════════════════════════════════════════════════════════════════════

print("── Pattern 5: Uvicorn -- add --host 0.0.0.0 ──")

check_pattern(
    "Uvicorn: add --host", 4,
    'CMD uvicorn app.main:app',
    'CMD uvicorn --host 0.0.0.0 --port ${PORT:-8080} app.main:app',
)

check_pattern(
    "Uvicorn: --host already present -> no-op", 4,
    'CMD uvicorn app.main:app --host 0.0.0.0',
    None,
)

check_pattern(
    "Uvicorn: --port already present -> no-op", 4,
    'CMD uvicorn app.main:app --port 8000',
    None,
)

print("── Pattern 6: Flask -- add --host=0.0.0.0 ──")

check_pattern(
    "Flask: add --host", 5,
    'CMD flask run',
    'CMD flask run --host=0.0.0.0 --port=${PORT:-8080}',
)

check_pattern(
    "Flask: --host already present -> no-op", 5,
    'CMD flask run --host=0.0.0.0',
    None,
)

check_pattern(
    "Flask: --port already present -> no-op", 5,
    'CMD flask run --port 5000',
    None,
)

print("── Pattern 7: Gunicorn -- add --bind ──")

check_pattern(
    "Gunicorn: add --bind", 6,
    'CMD gunicorn app:app',
    'CMD gunicorn --bind 0.0.0.0:${PORT:-8080} app:app',
)

check_pattern(
    "Gunicorn: --bind already present -> no-op", 6,
    'CMD gunicorn app:app --bind 0.0.0.0:8000',
    None,
)

check_pattern(
    "Gunicorn: -b short flag present -> no-op", 6,
    'CMD gunicorn app:app -b 0.0.0.0:8000',
    None,
)

print("── Pattern 8: Python http.server -- add --bind ──")

check_pattern(
    "http.server: add --bind", 7,
    'CMD python -m http.server',
    'CMD python -m http.server --bind 0.0.0.0 8080',
)

check_pattern(
    "http.server: --bind already present -> no-op", 7,
    'CMD python -m http.server --bind 0.0.0.0 8080',
    None,
)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — First-match priority
# ═══════════════════════════════════════════════════════════════════════════

print("── First-Match Priority ──")

fixed_content, fix_desc = apply_deterministic_fix('ENTRYPOINT ["kc.sh", "start"]')
expected_desc = 'ENTRYPOINT: "start" -> "start-dev"'
test(
    "ENTRYPOINT start triggers Pattern 1 not Pattern 2",
    fix_desc == expected_desc,
    f"got: {fix_desc}" if fix_desc != expected_desc else "",
)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 — Case insensitivity (re.IGNORECASE)
# ═══════════════════════════════════════════════════════════════════════════

print("── Case Insensitivity ──")

check_pattern(
    "lowercase cmd uvicorn still matches", 4,
    'cmd uvicorn app.main:app',
    'cmd uvicorn --host 0.0.0.0 --port ${PORT:-8080} app.main:app',
)

check_pattern(
    "mixed case Entrypoint still matches", 0,
    'Entrypoint ["kc.sh", "start"]',
    'Entrypoint ["kc.sh", "start-dev"]',
)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 — Full Dockerfile context (multiline)
# ═══════════════════════════════════════════════════════════════════════════

print("── Multiline Dockerfile ──")

FULL_DOCKERFILE = """\
FROM keycloak/keycloak:25.0
LABEL org.opencontainers.image.title="Keycloak"
ENV KC_HOSTNAME=localhost
EXPOSE 8080
ENTRYPOINT ["/opt/keycloak/bin/kc.sh", "start"]
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8080/ || exit 1"""

EXPECTED_FULL = """\
FROM keycloak/keycloak:25.0
LABEL org.opencontainers.image.title="Keycloak"
ENV KC_HOSTNAME=localhost
EXPOSE 8080
ENTRYPOINT ["/opt/keycloak/bin/kc.sh", "start-dev"]
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8080/ || exit 1"""

pattern, replacement, _ = DETERMINISTIC_FIXES[0]
new_content, count = re.subn(pattern, replacement, FULL_DOCKERFILE, flags=re.IGNORECASE)

test(
    "Full Dockerfile: only ENTRYPOINT line changed",
    count == 1 and new_content.strip() == EXPECTED_FULL.strip(),
    f"count={count}" if count != 1 else "content mismatch",
)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 — No false positives
# ═══════════════════════════════════════════════════════════════════════════

print("── No False Positives ──")

CLEAN_DOCKERFILE = """\
FROM nginx:alpine
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]"""

fixed, desc = apply_deterministic_fix(CLEAN_DOCKERFILE)
test(
    "Clean Dockerfile -> no deterministic fix applies",
    fixed is None,
    f"false positive: {desc}" if fixed is not None else "",
)

# ═══════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════

total = PASSES + FAILS
print(f"\n=== Results: {PASSES} passed, {FAILS} failed (of {total} tests) ===")

if FAILS > 0:
    print("Some tests failed.")
    sys.exit(1)

print("All tests passed!")
sys.exit(0)
