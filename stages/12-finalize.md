# Stage 12 — Finalization (and project-map check)

Until `specalign finalize` ships, these steps are done by hand with a scripted, re-runnable edit (never an ad-hoc
heredoc; Arabic or quoted text in shell strings breaks). Preserve each file's line endings and read/write UTF-8.

1. **Spec §0:** Status → Approved; version; tag; baseline date; baseline commit; approval references. §13D row with the
   approval statement id and the user's reply; §13B D-entry for the decision; §14 results from the machine checks.
2. **Registry:** status, version, tag, last-verified, coverage marks; refresh the "next recommended pilot" note.
   Ripple-patched specs get their own rows.
3. **Studies:** `studies/green-<slug>.md` exists → append the dated matrix result (mandatory at Core).
4. **Verify before committing:** `python -m specalign registry check <repo>` *except* the tag checks (the tag does not
   exist yet); staged-file count equals the plan from stage 11.
5. **Commit** (covered by W1). Message ends with the attribution lines the environment requires.
6. **Tag** `<TAG_PREFIX>F{n}-{slug}-vX.Y.Z` on the finalization commit — only with G1 — for the feature and every
   patched spec. Then re-run `registry check`: all nine checks must pass. The tag **is** the baseline: frozen.
7. **Push** only with P1; if the sandbox lacks credentials, hand the user the exact command.
8. **Rollback on failure:** `git checkout -- <file>` · `git tag -d <tag>` · back to stage 11; log in §13B.

## 12.5 Project-map sync (non-blocking)
Compare the approved spec with `PROJECT_MAP`. Stale → propose Before/After edits; declined → log "PROJECT_MAP update
declined — drift risk". Approval never depends on this step.
