#!/usr/bin/env bash
# =============================================================================
# check-template-slug.sh
# Rejects Railway template slugs that contain QA / test / dev / staging
# markers. Used as a pre-publish gate by the Publisher agent in goal.md and
# as a CI step in .github/workflows/publish-lint.yml.
#
# Usage:  scripts/check-template-slug.sh <slug> [<slug> ...]
# Exit:   0 if all slugs ok; 1 if any slug rejected.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ----------------------------------------------------------------------
# Slug rules
# ----------------------------------------------------------------------
#   - Lowercase + hyphens only
#   - Must start with a letter
#   - Length 3-40 chars
#   - May NOT contain: qa, test, dev, staging, sandbox, sample, demo,
#                       scratch, tmp, debug, _qa, _test, _dev (in any case)
# ----------------------------------------------------------------------
readonly SLUG_RE='^[a-z][a-z0-9-]{2,39}$'
readonly BLACKLIST_RE='(qa|test|dev|staging|sandbox|sample|demo|scratch|tmp|debug)'

# Railway reserves these — publish would silently shadow the official one
readonly RESERVED_SLUGS=(
    "nextjs" "vite" "remix" "astro" "nuxt" "sveltekit"  # official starters
    "postgres" "mysql" "redis" "mongodb" "keydb"          # official databases
    "ghost" "discourse" "wordpress" "strapi"              # official apps
    "express" "flask" "django" "rails" "fastapi"          # official language starters
)

if [[ $# -eq 0 ]]; then
    cat <<'EOF'
Usage: check-template-slug.sh <slug> [<slug> ...]

Validates one or more Railway template slugs against the publish policy:

  ✓ Lowercase letters, digits, hyphens
  ✓ Length 3..40
  ✓ No QA / test / dev / staging / sandbox / sample / demo / scratch /
    tmp / debug markers (anywhere in the slug, in any case)
  ✓ Not one of the reserved official Railway slugs

Exit codes:
  0   all slugs passed
  1   one or more slugs rejected (stderr explains why)
EOF
    exit 2
fi

fail=0

slug_ok() {
    local s="$1"

    # Empty
    if [[ -z "${s}" ]]; then
        printf '  ✗ REJECTED (empty slug)\n' >&2; return 1
    fi

    # Format
    if ! [[ "${s}" =~ ${SLUG_RE} ]]; then
        printf '  ✗ REJECTED %q  (must match: lowercase letters, digits, hyphens; 3..40 chars; must start with a letter)\n' "${s}" >&2
        return 1
    fi

    # Blacklist (case-insensitive substring)
    local lower
    lower=$(printf '%s' "${s}" | tr '[:upper:]' '[:lower:]')
    if [[ "${lower}" =~ ${BLACKLIST_RE} ]]; then
        printf '  ✗ REJECTED %q  (slug contains QA/test/dev/staging/etc. marker)\n' "${s}" >&2
        printf '      hit: %s\n' "${BASH_REMATCH[0]}" >&2
        printf '      policy: https://github.com/INAPP-Mobile/railway-templates/blob/main/scripts/check-template-slug.sh\n' >&2
        return 1
    fi

    # Reserved
    for r in "${RESERVED_SLUGS[@]}"; do
        if [[ "${s}" == "${r}" ]]; then
            printf '  ✗ REJECTED %q  (slug is reserved by Railway official starter; choose a different name to avoid marketplace collision)\n' "${s}" >&2
            return 1
        fi
    done

    printf '  ✓ ok  %s\n' "${s}"
    return 0
}

for slug in "$@"; do
    slug_ok "${slug}" || fail=1
done

if [[ "${fail}" -ne 0 ]]; then
    printf '\nOne or more slugs were rejected. See reason above.\n' >&2
    printf 'See docs/kanboard-rename-runbook.md for context on the kanboard-qa-test bug this guard exists to prevent.\n' >&2
fi

exit "${fail}"
