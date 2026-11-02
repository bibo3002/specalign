# SpecAlign Changelog

Single version-history home for the SpecAlign skill.

## [1.0.0-dev] — unreleased (branch `v1-production`)
Production-hardening release. Not yet 1.0.0: the release criteria are in the plan (all evals green, three dry-run
adoptions, linter clean on the reference corpus).

### Changed — process (breaking: stage numbers)
- `SKILL.md` is now a ≤150-line router; detail lives in `stages/`, `modes/`, `gates/` and is read per stage. This
  fixes the 25 KB monolith that compaction truncated.
- **One canonical stage order, 0–13, no duplicates.** Remediation is an explicit stage (5), the checkpoint comes after
  all reading (4), verification precedes the draft (6 → 7).

  | New | Stage | Legacy |
  |---|---|---|
  | 0–2 | preflight · scope/tier · inventory | 0 · 1 · 2 |
  | 3 | read (code, data, UI, validation, permissions) | 3–7 |
  | 4 | anti-pattern scan + checkpoint | 4.5 |
  | 5 | remediation (new) | — |
  | 6 | verification | 11 |
  | 7–10 | draft · Socratic · cross-section · self-check | 8 · 9 · 10 · 12 |
  | 11 | write gate | 12.5 |
  | 12 | finalize (+ map sync) | 13 · 13.5 |
  | 13 | handoff | 14 |
- Rule 1 and the lifecycle fence reconciled with practice: an explicit **remediating run** (R1) may change the files it
  lists; live DDL needs its own confirmation (D1). `gates/remediation.md`, `gates/ddl-protocol.md`.
- Approval statements v2 (fixed the truncated tag/push form; added R1, D1, X1, V1, G1, P1, C1, N1; replies are recorded
  verbatim). `gates/approval-statements.md`.
- Disposition vocabulary (Fix / Accept / Defer / Reject) and the rule for shorthand such as "fix all".
- Versioning policy with a decision tree and **ripple patches**; SYNC procedure with drift classes, legacy
  normalization and superseded-wording convention. `gates/versioning.md`, `modes/sync.md`.
- Controlled evidence vocabulary and the DF → AC → evidence chain. `gates/evidence.md`.
- Data-safety rules in the skill itself: audit logs immutable, scoped cleanup, no bypass of a refusing tool.

### Changed — tooling (`tools/specalign`, stdlib only; `scripts/*.py` kept as wrappers)
- `registry check` replaces `rescan_check.py`. Fixes: the tag check accepted *any* tag with the F-prefix; check 6 was
  hard-coded to pass; INDEX status/version/tag were never compared with the spec's §0 Card; the tag prefix ignored the
  binding; files were read without UTF-8. Now: the exact tag of the INDEX version must exist and its commit must contain
  that spec version; INDEX ↔ §0 Card must agree; exit codes 0/1/2; `--json` (`specalign.registry/1`).
- `drift` replaces `drift_probe.py`. Fixes: brace groups, globs and annotations in `Sources` voided the whole feature;
  the time-window range hid same-second commits; renames were missed. Now: token-level parsing, exact `<tag>..HEAD`
  range, dead-source report, `--exit-zero`/`--strict`.
- `install.py`: installs/syncs the global and project copies, LF-normalised, with `INSTALL-MANIFEST.json`; `--check`
  detects hand edits, missing and out-of-date files; refuses to overwrite hand edits without `--force`.
- Tests: 69 stdlib `unittest` cases incl. fixture repos (Arabic, CRLF), installer round trip, and a conformance test
  that keeps the skill's own documents consistent (size budget, no dangling references, no unshipped commands).
- CI for the skill repo (`.github/workflows/ci.yml`) and a copy-in workflow for adopters (`templates/adopter-ci.yml`).

### Changed — templates
- Specification template v1.0: skill version, evidence legend, ID conventions, dispositions, superseded-wording and
  ripple-patch conventions, machine-check block in §14. New `binding.template.md`. Rescan report and handoff README
  refreshed. Playbook validation matrix extended with traps 18–29 (not yet exercised: "not exercised", never assumed).

### Not yet shipped (planned)
`lint`, `docedit`, `finalize`, `manifest` (run record / resumable state), `inventory`, DB/UI/test adapters beyond
documentation, executable evals. The documents say so wherever a step is still manual.

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
