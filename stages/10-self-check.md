# Stage 10 — Self-check and presentation

Run the §14 self-check (process audit + content completeness). A blocking ✗ is fixed before presenting.

## Machine checks first (paste their output into §14, do not retype a verdict)
- `python -m specalign registry check <repo>` — INDEX, spec §0, tags.
- `python -m specalign drift <repo> <F-id>` — against the *previous* tag it lists exactly this run's commits and
  uncommitted-to-tag changes; every listed source must be reflected in the draft (after finalization it must be clean).
- `python -m specalign lint <repo> <F-id>` — blocks, IDs, DF → AC → evidence links, label vocabulary, leftover
  markers, §14 verdict, §13C. Every error is a ✗ to fix before presenting; warnings are listed in §14 with a reason.

## Judgement checks
- **Rebuildable from the spec alone?** At Core tier answer five questions derived from the ACs using *only* the spec;
  any question the spec cannot answer is a gap to fix (record the questions and answers in §14).
- Verbatim strings match the source/runtime capture; counts (endpoints, tables, tests) match the inventory.
- No leftover `PENDING`, `TODO`, or Open DF on a spec about to be Approved.

Present the real diff of the draft and the results. Binding `DOCS_REVIEW_SKILL` set → load it here.
