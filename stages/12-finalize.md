# Stage 12 — Finalization (and project-map check)

Finalization is **plan-driven**: write one `plan.json` (outside the repository, e.g. the scratchpad), dry-run it, show
the diff in the W1 message, then apply. Never an ad-hoc edit script. Line endings, BOM and UTF-8 are preserved.

```json
{ "schema": "specalign.finalize-plan/1",
  "edits": [
    {"file": "docs/specs/SPEC-F6-basic-data.md", "op": "set-card", "field": "Status", "value": "Approved"},
    {"file": "docs/specs/SPEC-F6-basic-data.md", "op": "append-row", "section": "13C", "cells": ["v1.1.0", "2026-11-02", "Modified", "…"]},
    {"file": "docs/specs/INDEX.md", "op": "patch-row", "match": {"ID": "F6"}, "set": {"Status": "Approved", "Version": "v1.1.0", "Tag": "spec/F6-basic-data-v1.1.0"}}
  ],
  "expect_files": ["docs/specs/SPEC-F6-basic-data.md", "docs/specs/INDEX.md"],
  "tags": ["spec/F6-basic-data-v1.1.0"] }
```
Ops: `set-card`, `append-row` (`section`, `cells`, optional `key`), `patch-row` (`match`, `set`, optional `section` /
`with_column`). Every op is idempotent, so a half-finished apply is simply re-run.

1. **Plan** — `python -m specalign finalize plan <repo> plan.json`: prints the exact diff, lints each changed spec as
   it *would* be written, refuses edits outside `expect_files`, refuses a tag that exists or lacks `TAG_PREFIX`.
   Content of the new rows: §0 Card (status, version, tag, baseline date and commit), §13B D-entry for the decision,
   §13C row (with *Superseded wording* where behaviour ended), §13D row quoting the reply verbatim, §14 results pasted
   from the tools. Registry rows for the feature **and** for every ripple-patched spec; refresh the pilot note.
2. **Apply** (after W1/C1 is recorded) — `finalize apply …`: writes, records each file's sha256 in the run record,
   runs `registry check` (tag checks are reported as pending until the tag exists; anything else failing stops).
3. **Studies** — `studies/green-<slug>.md` exists → append the dated matrix result (mandatory at Core).
4. **Commit** (covered by W1): `git add` the planned files, then `finalize staged …` — staged files must equal
   `expect_files`. The commit message ends with the attribution lines the environment requires.
5. **Tag** — only with G1/C1: `finalize tag …` creates every planned tag on the finalization commit, refuses a tag
   whose spec version at that commit differs, and records it. Then `registry check` must pass all nine checks.
   The tag **is** the baseline: frozen.
6. **Push** — only with P1/C1: `finalize push … --remote <r>` prints the exact command (add `--execute` to run it).
   If the sandbox lacks credentials, hand the command to the user.
7. **Rollback on failure:** `git checkout -- <file>` · `git tag -d <tag>` · back to stage 11; log in §13B.

## 12.5 Project-map sync (non-blocking)
Compare the approved spec with `PROJECT_MAP`. Stale → propose Before/After edits; declined → log "PROJECT_MAP update
declined — drift risk". Approval never depends on this step.
