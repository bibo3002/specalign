# SpecAlign Changelog

Single version-history home for the SpecAlign skill.

## [0.11.0] — 2026-08-27
### Added — Rescan Hardening (E1–E10)
- `templates/rescan-report-template.md` — 9-section structured rescan output (A–I) with
  binding preflight, discovery counts, orphan-spec cross-check, structured drift flags,
  drift_probe integration, pilot rotation, budget tracking, and Stage 12.5 approval gate.
- `scripts/rescan_check.py` — stdlib-only CI validator for INDEX.md ↔ SPEC-F*.md consistency:
  6 checks (Approved has spec+tag, spec has row, Undocumented has no spec, no duplicate F-ids,
  §0 Card F-id matches filename).
- `.github/workflows/specalign-rescan.yml` — GitHub Actions CI running rescan_check on every
  push/PR touching specs or the script; blocks merge on inconsistency.
- SKILL.md: Rescan Preflight, Output Schema, CI Integration, Write Permission Gate, Anti-Patterns
  (7 red flags specific to rescan maintenance).
- Pilot rotation rule (§G): auto-suggest next candidate when current recommendation becomes Approved.
- Budget enforcement (§H): 5 min/feature-surveyed, 20 min total, with timestamps.

### Fixed
- Rescan no longer silently skips preflight; drift_probe invocation is mandatory (E2, E6).
- Drift flags use structured schema (Type/Evidence/Action enum) instead of prose (E5).
- Spec file §0 Card Feature ID validation is warning-level for legacy brownfield-spec files (F2, F3).

## [0.10.0] — 2026-08-25
### Added
- `scripts/drift_probe.py` — stdlib-only drift probe (`SpecAlign drift` command) with:
  - Watermark from finalization tag + INDEX last_verified (exclusive by +1s)
  - §0 Card `Sources` parsing for file-path discovery
  - Propose → confirm → write gate for Stale flips
  - 7 unit tests covering clean/drifted/unverifiable/multi-tag/last_verified edge cases
- `SpecAlign drift` command added to skill invocation (readme/commands/spec.md)
- Drift Check (Stage 11.5) and Bootstrap/Maintenance procedures (init/rescan) in SKILL.md
- Protected-field merge policy for init/rescan (TEST_ACCOUNTS/PITFALLS/CONVENTIONS never auto-touched)
- `scripts/drift_probe.py` stdlib-only; `--json` output ready for future CI consumption

## [0.9.0] — 2026-08-25
### Created — supersedes brownfield-spec v3.2 (retired in the same commit)
Native design, absorbing three sources:

**From the F4 GENESIS pilot critique (R1–R13):**
- R1 draft-file write exemption (12.5 reviews a real diff, not a chat summary)
- R2 Socratic gate predicate (opens before composition; reopens only for §0/§1 changes)
- R3 CONSUMER column + endpoint ownership rule (Stage 2/10)
- R4 DF terminal states; only Open blocks PASS
- R5 budget = cumulative UI_TOOL wall-clock with §13B timestamps
- R6 silent-click protocol (`runtime-js-click` label + anomaly row)
- R7 transient-capture recipe (single evaluate)
- R8 cleanup pathway for non-prefixable tables
- R9 status-matrix wording ("Verifying (draft written)")
- R10 split Code-baseline / Finalization commit fields
- R11 E5 explicit checkpoint output
- R12 Stage 13 registry pilot-note refresh + green-studies append
- R13 optional negative-claim runtime probe

**Adapted from KDD 1.1.0 (with the lifecycle fence):**
- Dynamic tiers Micro/Standard/Core — compress documentation depth, never evidence (Rule 4 inviolable)
- Cross-Section Analysis as a named Stage 10 pass incl. terminology consistency
- Evolution History (§13C) + zero-knowledge-deletion rule (Deprecated/Superseded markers)
- Approval History (§13D) + exact gate approval statements
- Traceability-lite: flow IDs `F{n}-*` and AC IDs in §4/§11
- Mini decision records (Context/Decision/Consequences) for decided DFs
- Named failure states (BINDING_MISSING, DIRTY_TRACKED_FILES, …)
- Baseline ≡ git tag equivalence; reconstruction footnote at Core tier

**Absorbed from the Unified Structure for Executive Specification Documents:**
- §5 consumed triggers/views/functions sweep
- §7 state & persistence sub-block (fetch strategy, storage keys/TTL, dirty/save semantics)
- §10 edge-type taxonomy + a11y/stale states
- §2 isolation trio format (soft-check / hard-enforcement / audit-trail)
- §12 split into Prerequisites / Dependents / Shared components
- §1 dominant-design-principle line; §3.4 accessibility affordances
- §14 merged content-completeness checklist (items 11–18)

**Conventions baked in:** English-primary prose · ISO 8601 metadata dates · verbatim non-English strings.

Validation stance: field-tested draft; GREEN pressure scenarios pending first pilot
(see SKILL.md Validation Status).
