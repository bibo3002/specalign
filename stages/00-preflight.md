# Stage 0 — Preflight

**Binding gate.** Read `<SPEC_DIR>/binding.md` first. Missing or incomplete → STOP, say what is missing, offer to
create it (`modes/rescan.md` → *init*). Never guess a binding value.

## Checks

1. **Skill integrity** — if installed with `install.py`, `python install.py --check` reports no hand-edited file.
2. **Repository state** — no unstaged modifications to *tracked* files under `SPEC_DIR`, `PROJECT_MAP` or the
   feature's code paths. Unrelated untracked entries are noted in §13B and ignored. Dirty tracked files → STOP.
3. **Baseline registry** — `python -m specalign registry check <repo>` (exit 0). A failing baseline is reported
   before work starts; it is not silently inherited.
4. **Tools** — `DB_TOOL` answers a trivial query; `UI_TOOL` launches (skip for features with no DB / no UI and say
   so in §13B). Record the capability profile from the binding (`ui.trusted_clicks`, `ui.print_blocks`, …).
5. **Mode + feature** — confirm explicitly; never infer from a path-like input. See `modes/genesis.md`,
   `modes/sync.md`.
6. **Run record** — create `.specalign/run-state.json` (stage, mode, feature, tier, approvals so far) and keep it
   current; a resumed or compacted session reads it first.
7. **Budget** — behavioural verification is capped at **10 minutes per feature**: cumulative UI_TOOL wall-clock from
   the first browser call to the end of cleanup. Record start/end timestamps in §13B.

## Edge cases

- **E1** SYNC but the spec file is missing → ask: switch to GENESIS or abort?
- **E2** Spec exists but its §0 Card names another feature → warn, ask.
- **E3** Feature changed since the spec → `python -m specalign drift <repo> <F-id>`; list the commits; ask.
- **E4** Duplicate registry rows → ask which is canonical.
- **E5** Feature flags / conditional logic → grep flag and env branches; state the result at the checkpoint.

Staging hygiene: when committing later, verify the staged-file count; **path-case mismatches silently stage
nothing** (playbook §6).

Failure codes: `BINDING_MISSING` · `BINDING_INCOMPLETE` · `DIRTY_TRACKED_FILES` · `MODE_AMBIGUOUS` ·
`REGISTRY_BASELINE_FAILING`.
