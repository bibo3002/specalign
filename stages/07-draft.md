# Stage 7 — Draft

Write `<SPEC_DIR>/SPEC-F{n}-{slug}.md` from `templates/specification-template.md`: §0–§14 including §13A–§13D
(**18 blocks**). Removals are justified in §13A. This is the only file written outside the R1 list before the write
gate; stage 11 reviews its real diff.

- Status **Draft** in §0 and in the registry. §0 carries: skill version, tier, evidence legend, `Sources` (brace
  lists and globs are fine; `tests`/`tables` labels allowed), baseline commit.
- Describe the **current, corrected** behaviour. Superseded behaviour is kept visible with its ending version
  (Rule 9 / §13C), never silently erased.
- Assign IDs once: flows `F{n}-*`, acceptance criteria `AC-*`, evidence `V-*`, decisions `D-*`, questions `Q-*`,
  flags `DF-*`.
- Every behavioural claim carries an evidence label (`gates/evidence.md`) and a citation (Rule 4).
- §13B holds the evidence from stage 6 verbatim; §13A holds DFs with dispositions and open questions; resolved
  items move to dated §13B entries.
- Specs in a patched/ripple set get their own version bump and §13C row (`gates/versioning.md`).
