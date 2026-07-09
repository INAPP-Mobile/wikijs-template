# Template Publishing Class-Level Gotchas & Pitfalls

From real Plausible CE template work plus sibling templates. These patterns recur across every template publish cycle.

## Gotcha 1: Empty Required Var Crashes App on First Boot

**Pattern:** Application requires a public URL (or any non-empty string) at boot time. Template ships it as `""` → app crashes.

**Real cases:**
- `BASE_URL` — Plausible CE v3.2.1 requires non-empty; crashes with `"BASE_URL configuration option required"`
- `VITE_BASE_URL`, `BASE_URL` in many frontend apps — same pattern

**Rule:** Any var that the app requires at runtime must have a non-empty `defaultValue` that points to something real (Railway public domain, the companion service domain, or at worst a documented placeholder).

**Fix:** Change `defaultValue: ""` to `defaultValue: "https://placeholder.yourdomain.com"`. Document explicitly that the user MUST change it post-deploy.

---

## Gotcha 2: Manually Overriding Plugin-Managed Vars Breaks Deploys

**Pattern:** Adding PostgreSQL's `PGDATA`, `POSTGRES_PASSWORD`, `DATABASE_URL` to the deploy form because they were visible on the original project.

**Why:** Railway plugins auto-manage these. Manually overriding them creates path mismatches (PGDATA), stale credentials (DATABASE_URL), or skips injection rules the plugin relies on.

**Rule:** 
- Plugin-managed vars live in the service that defines the plugin
- Do NOT add them to `template-vars.json` or `template-editor-raw.json`
- Only reference them via `${{Service.VAR}}`

**Real case:** Plausible CE template had `PGDATA: /var/lib/postgresql/data/pgdata` bolted on. Every fresh deploy then crashed with `PGDATA variable does not start with expected volume mount path`. Removing the manual var let Postgres start correctly.

---

## Gotcha 3: Two-File Sync Manually Maintained

**Pattern:** `template-editor-raw.json` drifts away from `template-vars.json` because they have slightly different schemas and are updated by hand.

**Schema difference:**
- `template-vars.json` keys: `defaultValue`, `description`, `isOptional`
- `template-editor-raw.json` keys: `value`, `description`

**Rule:** Whenever one of these files is updated, regenerate the other. Use the deterministic pipeline step or a quick Python sync script:

```python
import json
vars_data = json.load(open('template-vars.json'))
raw = {k: {"value": v["defaultValue"], "description": v["description"]}
       for k, v in vars_data.items()}
json.dump(raw, open('template-editor-raw.json','w'), indent=2)
```

For the ClickHouse companion service (which is its own template), sync the same way.

---

## Gotcha 4: Verifying Changes Actually Hit Disk

**Pattern:** Repetitive `write_file`/`patch`/`python3 open('w')` calls that write `&&` into a string but the terminal `cat` shows no `&&`. Extremely confusing because the bytes look like they were stripped but they were not — terminal rendering collapses them.

**Rule:** Changes ARE on disk. Verify with `python3 -c "print(repr(open('Dockerfile').read()))"` to see raw bytes. Do NOT trust `cat` for content containing `&&`. Do NOT repeat failed-looking writes.

---

## Gotcha 5: Deploy Verification Must Include Fresh Project

**Pattern:** Template deploys only against the original development project. Production template test requires deploying from the marketplace URL into a brand-new project.

**Rule:** After every template publish, immediately deploy the fresh project from the marketplace URL and check all services come Online.

Steps:
1. Open `https://railway.com/deploy/<slug>` (or private workspace deploy for drafts)
2. Click "Deploy"
3. Wait for build + deploy
4. Run `railway link --project <new-project-id>` then `railway status`
5. All three services must be **Online**, not "Crashed", not "Completed"
6. Check each consumer service's DATABASE_URL is non-empty:
   ```bash
   railway variables --service plausible-ce --output json | python3 -c "import sys,json; d=json.load(sys.stdin); print('DATABASE_URL non-empty' if d.get('DATABASE_URL') else 'EMPTY DATABASE_URL')"
   ```

---

## Gotcha 6: Template Publishing Uses Default --yes Pattern

**Pattern:** `railway service delete` flags behave differently than expected — `--yes` works but `echo "yes" | railway` does not because the prompt is not stdin-based.

**Rule:** Always use `--yes` flag on `railway service delete`. Never pipe for confirmation.
