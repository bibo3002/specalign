# Stage 5 — Remediation (only in a remediating run)

Rules: `gates/remediation.md`. Live DDL: `gates/ddl-protocol.md`.

1. Work through the DFs marked **Fix**, one at a time: change → test → next. Stay inside the R1 file list.
2. For each DDL migration: show **D1** (pre-check + result, rollback, verification query) and wait; then apply in one
   transaction and verify.
3. After the last Fix: run the full test suite and the typecheck/build. Record the commands and counts. Red → stop.
4. Update each DF in the working notes to its terminal status and name the test that pins it.
5. Anything that needs a file outside the list, a contract change or a design decision → stop and amend R1 / ask.

Nothing here tags, pushes, deploys, or deletes data (G1 / P1 / X1 stay closed).
