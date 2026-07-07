#!/usr/bin/env bash
# =============================================================================
# repair-template-vars.sh — Repair published templates with 0 variables.
#
# For each template that has 0 variables:
#   1. Read .env.example from the corresponding railway-* directory
#   2. Link the project (railway link)
#   3. Set all env vars via `railway variable set`
#   4. Delete the old template
#   5. Re-generate (captures vars automatically)
#   6. Re-publish with same category/readme
#
# Usage: bash repair-template-vars.sh [--dry-run] [--template NAME]
# =============================================================================
set -euo pipefail

DRY_RUN=false
SINGLE_TEMPLATE=""
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true
[[ "${1:-}" == "--template" ]] && SINGLE_TEMPLATE="${2:-}"

BASE="/var/home/ihshim523/Work/railway"
BODIES="$BASE/pipeline-bodies"
LOGDIR="$BASE/pipeline-logs"
mkdir -p "$LOGDIR"

# Template code → (project-name, category) mapping
# project-name matches the railway-* directory name
declare -A TEMPLATES
TEMPLATES["railway-n8n"]="railway-n8n,Automation"
TEMPLATES["memos-3"]="railway-memos,Starters"
TEMPLATES["netdata-1"]="railway-netdata,Observability"
TEMPLATES["syncthing-1"]="railway-syncthing,Storage"
TEMPLATES["railway-hoppscotch"]="railway-hoppscotch,Other"
TEMPLATES["filebrowser"]="railway-filebrowser,Storage"
TEMPLATES["kanboard-2"]="railway-kanboard,Starters"
TEMPLATES["gotify"]="railway-gotify,Automation"
TEMPLATES["stirling-pdf-1"]="railway-stirling-pdf,Other"
TEMPLATES["changedetectionio-1"]="railway-changedetection.io,Observability"
TEMPLATES["pocketbase-5"]="railway-pocketbase,Starters"
TEMPLATES["plausible-2"]="railway-plausible,Analytics"
TEMPLATES["open-webui-3"]="railway-open-webui,AI/ML"

# Template codes from the API (from earlier query)
declare -A TEMPLATE_IDS
TEMPLATE_IDS["railway-n8n"]="b222f992-62aa-421d-b79d-91702a05b789"
TEMPLATE_IDS["memos-3"]="12eac690-8f8e-4093-8691-6ab6cc62ccbe"
TEMPLATE_IDS["netdata-1"]="14e24aab-8d9b-42b2-b778-1fb9079b5f6a"
TEMPLATE_IDS["syncthing-1"]="20b17cb9-da55-42dd-9cfd-f7d433bd9edb"
TEMPLATE_IDS["railway-hoppscotch"]="57127802-8196-468b-b6f4-cdfcd7e404b5"
TEMPLATE_IDS["filebrowser"]="6dd024bc-bc19-4b42-bc32-5e97fc2ede33"
TEMPLATE_IDS["kanboard-2"]="7f55a1d4-9af4-4f59-a465-d77ffa83b831"
TEMPLATE_IDS["gotify"]="bbb4fa08-e890-472a-8c0c-22b9c366d19f"
TEMPLATE_IDS["stirling-pdf-1"]="dce8dc2c-5b88-4a84-8fe5-c4f1dad58ddb"
TEMPLATE_IDS["changedetectionio-1"]="df9e11be-469e-4a00-bdc4-4d425818c051"
TEMPLATE_IDS["pocketbase-5"]="f13b9827-e4b2-473d-bb66-90e498cdba9e"
TEMPLATE_IDS["plausible-2"]="fa1c0407-24e8-4b1f-b6c9-48e20126c8bf"
TEMPLATE_IDS["open-webui-3"]="ddf337c3-1dcb-4f24-8e8a-b15a41dcea66"

echo "=== Repair Template Variables ==="
echo ""

for code in "${!TEMPLATES[@]}"; do
  if [ -n "$SINGLE_TEMPLATE" ] && [ "$code" != "$SINGLE_TEMPLATE" ]; then
    continue
  fi

  IFS=',' read -r proj_name category <<< "${TEMPLATES[$code]}"
  tid="${TEMPLATE_IDS[$code]:-UNKNOWN}"
  proj_dir="$BASE/$proj_name"
  env_file="$proj_dir/.env.example"

  echo "--- $code ($proj_name, $category) ---"
  echo "  Template ID: $tid"
  echo "  Project dir: $proj_dir"

  # Check if .env.example exists
  if [ ! -f "$env_file" ]; then
    echo "  SKIP: no .env.example found"
    echo ""
    continue
  fi

  # Count vars
  var_count=$(grep -c '^[^#].*=' "$env_file" 2>/dev/null || echo 0)
  echo "  Vars in .env.example: $var_count"

  if [ "$var_count" -eq 0 ]; then
    echo "  SKIP: no variables to set"
    echo ""
    continue
  fi

  # Parse vars from .env.example
  declare -A VARS
  while IFS= read -r line; do
    line=$(echo "$line" | xargs)  # trim
    if [[ -n "$line" && ! "$line" =~ ^# && "$line" == *=* ]]; then
      key="${line%%=*}"
      val="${line#*=}"
      key=$(echo "$key" | xargs)
      VARS["$key"]="$val"
    fi
  done < "$env_file"

  echo "  Variables to set:"
  for k in "${!VARS[@]}"; do echo "    $k=${VARS[$k]}"; done

  if $DRY_RUN; then
    echo "  [DRY RUN] Would: link project, set vars, delete old template, regenerate, republish"
    echo ""
    unset VARS
    continue
  fi

  # Step 1: Link the project
  echo "  Linking project..."
  cd "$proj_dir"
  railway link --project "$proj_name" 2>&1 || true

  # Get project/env/service IDs from the linked config
  PJ_ID=$(railway status --json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('projectId',''))" 2>/dev/null || echo "")
  ENV_ID=$(railway status --json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('environmentId',''))" 2>/dev/null || echo "")

  if [ -z "$PJ_ID" ] || [ -z "$ENV_ID" ]; then
    echo "  FAIL: could not get project/environment IDs. Set vars manually."
    echo ""
    unset VARS
    continue
  fi

  # Step 2: Set variables
  echo "  Setting variables on project $PJ_ID..."
  for key in "${!VARS[@]}"; do
    val="${VARS[$key]}"
    railway variable set "${key}=${val}" --project "$PJ_ID" --environment "$ENV_ID" --skip-deploys --json 2>&1 | grep -q "true" && echo "    OK: $key=$val" || echo "    FAIL: $key=$val"
  done

  # Step 3: Delete old template
  echo "  Deleting old template $tid..."
  railway templates delete "$tid" --yes 2>&1 || echo "    (delete failed, continuing)"

  # Step 4: Re-generate template
  echo "  Regenerating template..."
  NEW_JSON=$(railway templates create --project "$PJ_ID" --environment "$ENV_ID" --json 2>&1)
  NEW_ID=$(echo "$NEW_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
  echo "  New template ID: $NEW_ID"

  if [ -z "$NEW_ID" ]; then
    echo "  FAIL: template regeneration failed"
    echo ""
    unset VARS
    continue
  fi

  # Step 5: Re-publish
  echo "  Publishing template..."
  railway templates publish "$NEW_ID" \
    --category "$category" \
    --description "Deploy ${proj_name#railway-} on Railway" \
    --readme-file "$proj_dir/README.md" \
    --json 2>&1 | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Published: {d.get(\"code\",\"?\")}')" 2>/dev/null || echo "  (publish failed)"

  echo "  DONE"
  echo ""
  unset VARS
done

echo "=== Repair complete ==="
