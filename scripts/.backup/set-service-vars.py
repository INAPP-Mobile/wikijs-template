#!/usr/bin/env python3
"""
Set service variables on a Railway project.

Two transport modes:
  1. `railway variable set …` (default, subprocess) — works for non-empty values.
  2. Railway GraphQL `variableUpsert` mutation (enabled with --allow-empty) —
     needed because the Railway CLI rejects empty strings (`railway variable set KEY=` fails).

When you set env vars on the deployed project BEFORE running `railway templates create`,
the template generator captures those variables as template variables automatically.

Usage:
    python3 set-service-vars.py <project-id> <environment-id> <vars-file> [--dry-run] [--allow-empty]

    vars-file: path to .env.example or template-vars JSON file.

Flags:
    --dry-run     Print what would happen without touching Railway.
    --allow-empty Route empty-string values through GraphQL `variableUpsert` because the
                  CLI rejects them. Non-empty values still go through the CLI either way.

Requires:
    railway CLI authenticated (railway login) — used for non-empty values.
    ~/.railway/api-token present — used for empty values via --allow-empty.
"""
import json, os, subprocess, sys
import urllib.request
import urllib.error


def parse_env_file(path):
    """Parse .env.example (KEY=VALUE) or a JSON template-vars manifest.

    Supported JSON shapes:
      - dict-format:       {"KEY": {"defaultValue": "...", "description": "...", "isOptional": true}}
      - array-format:      {"variables": [{"key": "KEY", "default_value": "..."}]}
      - flat dict:         {"KEY": "plain value"}
    """
    with open(path) as f:
        content = f.read().strip()

    if content.startswith('{'):
        try:
            manifest = json.loads(content)
        except json.JSONDecodeError as e:
            print(f'Error: {path} looked like JSON but failed to parse: {e}', file=sys.stderr)
            sys.exit(1)

        # legacy array-format
        if isinstance(manifest, dict) and isinstance(manifest.get('variables'), list):
            return {
                v['key']: str(v.get('default_value', ''))
                for v in manifest['variables']
                if v.get('key')
            }

        # dict-format
        if isinstance(manifest, dict):
            out = {}
            for k, v in manifest.items():
                if isinstance(v, dict):
                    default = v.get('defaultValue')
                    out[k] = '' if default is None else str(default)
                else:
                    out[k] = '' if v is None else str(v)
            return out

    # .env format fallback
    env_vars = {}
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, val = line.split('=', 1)
            env_vars[key.strip()] = val.strip()
    return env_vars


def set_var_via_upsert(project_id, environment_id, name, value, skip_deploys=True):
    """Set one env var via Railway's GraphQL `variableUpsert` mutation.

    Returns (ok: bool, error: str). The mutation returns Boolean; we don't ask for subfields.
    """
    token_path = os.path.expanduser('~/.railway/api-token')
    if not os.path.isfile(token_path):
        return False, '~/.railway/api-token not found; --allow-empty requires the GraphQL token.'
    token = open(token_path).read().strip()
    endpoint = 'https://backboard.railway.com/graphql/v2'
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'User-Agent': 'railway-cli/5.23.1',
    }
    # Schema: mutation variableUpsert(input: VariableUpsertInput!) returns Boolean!
    mutation = '''mutation Upsert($input: VariableUpsertInput!) {
      variableUpsert(input: $input)
    }'''
    payload = {
        'query': mutation,
        'variables': {
            'input': {
                'projectId': project_id,
                'environmentId': environment_id,
                'name': name,
                'value': value,
                'skipDeploys': skip_deploys,
            }
        },
    }
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            rj = json.loads(r.read())
            if rj.get('data', {}).get('variableUpsert') is True:
                return True, ''
            errs = rj.get('errors') or []
            return False, '; '.join(e.get('message', str(e)) for e in errs) or json.dumps(rj)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        return False, f'HTTP {e.code}: {body[:300]}'
    except Exception as e:
        return False, f'request failed: {e}'


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    project_id = sys.argv[1]
    environment_id = sys.argv[2]
    vars_file = sys.argv[3]
    dry_run = '--dry-run' in sys.argv
    allow_empty = '--allow-empty' in sys.argv

    if not os.path.isfile(vars_file):
        print(f'Error: {vars_file} not found', file=sys.stderr)
        sys.exit(1)

    env_vars = parse_env_file(vars_file)
    if not env_vars:
        print('No variables to set.')
        return

    mode_hint = 'CLI' if not allow_empty else 'CLI for non-empty, GraphQL for empty'
    print(f'Setting {len(env_vars)} variables on project {project_id} ({mode_hint})')

    set_count = 0
    fail_count = 0
    for key, value in env_vars.items():
        if dry_run:
            display = key if value == '' else f'{key}={value}'
            via = 'GraphQL' if (value == '' and allow_empty) else 'CLI'
            print(f'  [DRY RUN via {via}] {display}')
            set_count += 1
            continue

        # Empty value + --allow-empty: route through GraphQL upsert (CLI rejects empty strings).
        if value == '' and allow_empty:
            ok, err = set_var_via_upsert(project_id, environment_id, key, value)
            if ok:
                print(f'  OK: {key}=  (via GraphQL upsert)')
                set_count += 1
            else:
                print(f'  FAIL: {key}=  (via GraphQL upsert) — {err}')
                fail_count += 1
            continue

        # Default path: railway CLI subprocess.
        cmd = [
            'railway', 'variable', 'set',
            f'{key}={value}',
            '--project', project_id,
            '--environment', environment_id,
            '--skip-deploys',
            '--json',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f'  OK: {key}={value}')
            set_count += 1
        else:
            print(f'  FAIL: {key}={value} — {result.stderr.strip() or result.stdout.strip()}')
            fail_count += 1

    if not dry_run:
        total = set_count + fail_count
        suffix = f' ({fail_count} failed)' if fail_count else ''
        print(f'Set {set_count}/{total} variables successfully{suffix}')
    else:
        print(f'[DRY RUN] Would set {set_count} variables')


if __name__ == '__main__':
    main()
