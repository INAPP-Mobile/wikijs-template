# Git Submodule Mistakes & Recovery

**LESSON LEARNED 2026-07-08 from Plausible CE submodule push mishap. READ THIS BEFORE any submodule push.**

## The Mistake Pattern

This project (`/var/home/ihshim523/Work/railway`) is a **collection of submodules**, each in its own subdirectory (`railway-plausible/`, `railway-n8n/`, `railway-open-webui/`, etc.). The parent repo's `master` branch contains gitlink pointers to each submodule's commit hash.

The parent repo's only configured remote is `origin-wikijs`, pointing to `INAPP-Mobile/wikijs-template.git` — a separate repository used as a collection host.

**Mistake:** Pushing a parent commit to `origin-wikijs` (the wikijs-template remote) when the change only updated a gitlink to a different submodule (e.g., `railway-plausible`). The parent commit "belongs" on a different remote (or is local-only if no correct remote is configured).

**Consequence:** `INAPP-Mobile/wikijs-template` got a parent commit whose only meaningful change was the `railway-plausible` gitlink pointer. Reverting required `git push --force-with-lease`.

## Submodule vs Parent Commit: What's Affected

| What | Where it lives | Affected by wrong push? |
|------|----------------|------------------------|
| Submodule commit hash (e.g., `867e6e4` on `railway-plausible`) | The submodule's own repo (`railway-plausible/.git`) and its actual remote (`INAPP-Mobile/railway-plausible`) | **No.** Wrong parent push doesn't touch the submodule. |
| Parent commit hash (e.g., `e3730a1`) | The parent repo (`/var/home/ihshim523/Work/railway`) and `origin-wikijs` (or any configured remote) | **Yes.** This is what the wrong push modifies. |
| Gitlink pointer in parent commit | A 40-char SHA in the parent tree object | **Yes.** This is what changes when the submodule is updated. |

**Key insight:** A wrong parent push can be reverted with `force-push-with-lease` without touching the submodule's own remote.

## Recovery: Force-Push-With-Lease to Previous Tip

```bash
# 1. Find the previous tip of the wrong remote BEFORE you do anything
git rev-parse origin-wikijs/master   # captures the SHA that was there before your push

# 2. Revert the wrong push (use --force-with-lease, NOT --force)
git push --force-with-lease origin-wikijs <PREVIOUS_TIP>:master
```

**Why `--force-with-lease` (not `--force`):**
- `--force` overwrites the remote unconditionally — **clobbers any concurrent pushes**
- `--force-with-lease` checks that the remote is still at the expected SHA — **fails safely** if someone else pushed in the meantime
- `--force-with-lease` is the safe default for solo work AND for shared branches

**Why this works:**
- The wrong parent commit only changed the gitlink pointer in the parent tree
- Force-pushing the previous tip back restores the parent tree to its prior state
- The submodule's own remote is unaffected
- Your local `master` branch keeps the new commit (which is the "intended" state, even if not yet pushed anywhere)

**The local state after `--force-with-lease`:**
- `git rev-parse master` → still the new commit (e.g., `e3730a1`)
- `git rev-parse origin-wikijs/master` → back to the previous tip (e.g., `34ee443`)
- The submodule's own remote → unchanged

## Pre-Push Checklist for Submodule Changes

Before pushing a parent commit, verify:

- [ ] `git diff <prev-commit> HEAD --stat` — does the change touch the gitlink of the submodule you intended?
- [ ] `git remote -v` — is the configured remote the correct destination for this parent commit?
- [ ] If the parent has a custom remote (not `origin`), is it pointing to a valid repo?
- [ ] If unsure, push to a new dedicated remote for the parent collection (e.g., `INAPP-Mobile/railway.git` if it exists)

## Identifying the Right Remote

```bash
git remote -v
# origin-wikijs  git@github.com:INAPP-Mobile/wikijs-template.git (fetch)
# origin-wikijs  git@github.com:INAPP-Mobile/wikijs-template.git (push)
```

If the only configured remote is for a sub-project (like wikijs-template), ask the user before pushing a parent commit that updates a different submodule.

**Quick probe for plausible parent remotes:**
```bash
for repo in railway railway-templates templates railway-collection; do
  git ls-remote --heads "git@github.com:INAPP-Mobile/${repo}.git" 2>&1 | head -1
  echo "---"
done
```

If all return "Repository not found", the user must provide the correct URL.

## Recovering When You Don't Know the Previous Tip

If you already pushed before saving the previous tip:

```bash
# 1. Get the reflog of the remote
git fetch origin-wikijs
git reflog origin-wikijs/master

# 2. The entry just before the wrong push is the previous tip
# 3. Revert with --force-with-lease
git push --force-with-lease origin-wikijs <REFLOG_ENTRY>:master
```

Or, if the remote reflog is unavailable:

```bash
# Check if the parent commit's parent is on a different branch or in another repo
git log --all --oneline | head -20

# If the wrong push was the FIRST push, the previous "tip" is the empty tree SHA:
# 4b825dc642cb6eb9a060e54bf8d69288fbee4904
# (This is `git hash-object -t tree /dev/null`)
```

## Why Not Just `git revert`?

`git revert <wrong-commit>` creates a NEW commit that undoes the wrong commit's changes. This leaves the wrong commit in the history. For submodules, the revert is harder because:
- The new commit's tree has the OLD gitlink (pointing to the previous submodule commit)
- This requires the previous submodule commit to still be reachable (usually is)
- BUT the revert's parent still contains the wrong commit's metadata

**For a single bad push to a non-shared branch, `git push --force-with-lease` is cleaner.** Use `git revert` only when the branch is shared with others.

## Related Files

- `railway-graphql-misleading-errors-and-verify-discipline.md` — companion ref for API-level error patterns
- `AGENTS.md` rule 3 — don't publish templates without consent (orthogonal, but related to "be careful with destructive operations")
- `SKILL.md` § "Pitfall: Submodule Pushes Require Remote Verification"
