---
name: specalign
description: Use when documenting an existing feature of a codebase into an executable specification, when a spec may have drifted from the code, live database, or runtime behavior, when verifying spec-to-reality alignment, or when reverse-engineering undocumented features. Triggers on document feature, extract spec, sync spec, spec drift, executable specification, reverse-engineer feature, GENESIS, SYNC, align spec, توثيق ميزة، مواصفة، مزامنة المواصفة.
---

# SpecAlign (v0.11.0)

## Overview

SpecAlign **extracts and maintains executable, agent-readable specifications for existing features**.
It guarantees accuracy by validating against a **triple source of truth**: the code, the live
database, and observed runtime behavior — never code alone. Two modes:

- **GENESIS** — reverse-engineer an undocumented feature into a brand-new spec.
- **SYNC** — compare existing documentation against current reality, close every gap, resolve drift.

A spec is authoritative only if it is **code-versioned, runtime-verified, agent-readable,
drift-detectable, and self-auditing** (evolution + approval history inside the document).

**Lineage.** Supersedes `brownfield-spec` v3.2 (retired), natively absorbing: all thirteen F4-pilot
refinements (R1–R13), knowledge-governance mechanisms adapted from KDD 1.1 (dynamic tiers,
cross-section analysis, evolution/approval history, traceability IDs, decision records, explicit
approval statements, named failure states), and authoring gaps closed against the Unified Structure
for Executive Specification Documents (DB functions/views/triggers, state & persistence, edge-type
taxonomy, isolation trio, shared components, content completeness checks).

### Lifecycle Fence (read before borrowing ideas)

SpecAlign is **backward-looking**: it documents what EXISTS and audits what CHANGED.
Forward change governance (spec-first development, plans, implementation approval dashboards)
belongs to a different methodology. If such a methodology produces approved specs, SpecAlign's
SYNC is the auditor that later verifies them against reality. Do not import forward-development
artifacts (plans, implementation checklists) into this workflow.

## When to Use

- Feature exists but has no spec (**GENESIS**).
- Code changed; the spec may be stale (**SYNC**).
- Before a major refactor, to pin current behavior.
- When a rebuild/migration needs an authoritative behavior record.
- Registry metadata maintenance (tiered micro-sync).

**Not for:** greenfield design documents, pure API-reference generation, one-off notes,
or governing new feature implementation.

## Project Binding (required before any stage)

Project-specific values live in `<SPEC_DIR>/binding.md`:

| Key | Meaning |
|---|---|
| PROJECT_MAP | Project map file (AGENTS.md, CLAUDE.md, …) |
| SPEC_DIR / REGISTRY | Spec dir and registry file (INDEX.md) |
| DB_TOOL / UI_TOOL | DB introspection / browser automation tools |
| TEST_ACCOUNTS | Named accounts for behavioral tests only |
| TEST_DATA_PREFIX | Marker for experimental rows (default `__TEST_`) |
| TAG_PREFIX | Git tag prefix (e.g. `spec/`) |
| BASELINE_DATE | Project baseline date (ISO 8601) |
| GOVERNING_SKILL | Path to this skill (informational) |
| CONVENTIONS | Prose language, date format (ISO 8601 in metadata), string-copy rules |
| PROJECT_PITFALLS | Known environment traps |

⚠️ **Binding gate:** read `binding.md` first. Missing/incomplete → STOP, ask the user, offer to
create it. **Never guess bindings.** Example: `references/binding-example-sanad.md`.

## Binding Rules

1. **Read-only until authorized.** Stages 0–12 write nothing **outside `<SPEC_DIR>`**; the sole
   pre-12.5 exemption is the draft spec file created/updated by Stage 8. Every other write
   (code, DB rows, REGISTRY, PROJECT_MAP) happens only inside Stage 12.5's granted scope.
2. **Never guess.** Missing data becomes an Open Question (§13A) asked of the user.
3. **Test-data hygiene.** Behavioral tests create only prefixable rows (`TEST_DATA_PREFIX`);
   tables without prefixable fields follow playbook §4-2b (UI create→remove same session +
   soft-delete verification). Never leave active unprefixed test rows.
4. **Cite every claim.** Source = `file:function`, SQL query, or browser step. **Tiers never
   relax this rule** — they only compress documentation breadth.
5. **Verbatim strings.** User-facing copy quoted exactly as observed at runtime, in its own language.
6. **Permission gates.** Tag and push require explicit approval. Tag format is binding:
   `<TAG_PREFIX>F{n}-{slug}-vX.Y.Z`. Gates close on the **exact approval statements** defined below.
7. **Letter = spirit.** Violating the letter of these rules IS violating the spirit. No exceptions.
8. **Abort anytime.** On "abort"/"switch mode": stop, summarize, write nothing, log partial work in §13B.
9. **Zero knowledge deletion.** Superseded/deprecated behavior is marked with its ending version
   (§13C) — never silently erased from the spec narrative.

## Dynamic Tiers (selected at Stage 1 — user decides)

Tiers scale **documentation depth**, never evidence quality:

| Track | Use for | Mandatory | May relax |
|---|---|---|---|
| **Micro** | Registry metadata fixes, typos/formatting, broken links, annotation-only edits | Binding gate · tier decision recorded · touched claims still cited · §13C entry | Stage count (run 0→1→patch→12→13); no behavioral run if zero behavior claims |
| **Standard** (default) | Any behavioral documentation | Full stage pipeline | Nothing evidence-related |
| **Core** | Data-model, permissions/security, API-contract, or multi-feature surface | Standard + mandatory Cross-Section pass (Stage 10 full pairwise) + green-studies dated entry + §14 reconstruction footnote | Nothing |

**Forbidden at every tier:** skipping discussion · executing without a tier decision · relaxing
Rule 4 citations · using Micro to rush a behavioral change · inventing evidence.

Micro-Track is **forbidden** if the change touches: data model, permissions, security, API
contracts, or makes any new behavioral claim.

## Workflow

### Stage 0 — Preflight & Edge Cases
Verify binding, DB_TOOL connectivity, UI_TOOL launch.
Repository state: **no unstaged modifications to TRACKED files** under SPEC_DIR, PROJECT_MAP, or
the feature's code paths (unrelated untracked entries noted in §13B and ignored; dirty tracked
files → STOP). ⚠️ On commit, verify staged-file count matches expectation — **path-case mismatches
(e.g. `skills/` vs `Skills/`) silently stage nothing** (playbook §6).
Confirm mode + feature explicitly (never infer from a path-like input). Edge cases:
- **E1** SYNC but spec file missing → ask: switch to GENESIS or abort?
- **E2** Spec exists but §0 Card names a different feature → warn, ask.
- **E3** Feature changed since spec → compare §0 baseline commit vs `git log` of feature files; list diverging commits; ask.
- **E4** Duplicate REGISTRY rows → ask which is canonical.
- **E5** Feature flags / conditional logic → grep flag/env branches; result stated explicitly at the Stage 4.5 checkpoint.

Set the behavioral budget: **10 min/feature** = cumulative UI_TOOL wall-clock, first browser call
→ cleanup end; record start/end timestamps in §13B.

Failure codes: `BINDING_MISSING` · `BINDING_INCOMPLETE` · `DIRTY_TRACKED_FILES` · `MODE_AMBIGUOUS`.

### Bootstrap (from zero) — `SpecAlign init`
For a fresh adopting repo with no `binding.md` / `INDEX.md` yet. Agent-executed, no script:
1. Presence scan: `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` → propose `PROJECT_MAP`.
2. Read MCP configs (`opencode.json` `.mcp.json`) → propose `DB_TOOL`/`UI_TOOL` mappings.
3. Git facts: first-commit date → `BASELINE_DATE`; tag-prefix collision check → `TAG_PREFIX`.
4. Manifest cues: framework → router conventions (agent reads contextually, **not via parser**).
5. Draft `binding.md` with machine-derivable fields filled; **protected fields left as placeholders**:
   `TEST_ACCOUNTS` · `PROJECT_PITFALLS` · `CONVENTIONS` (agent drafts a guess for CONVENTIONS from
   observed language, marks it **proposed** for explicit confirmation).
6. Discover candidate features (routes / tab components / endpoint groups) → propose INDEX rows
   with status `Undocumented` (matches your AGENTS.md "new feature → INDEX row" rule).
7. ⚠️ **Gate**: show the full draft + proposed rows, ask for corrections, then write.

### Maintenance — `SpecAlign rescan`
Same scan as `init`, but **diff against existing files**. Proposals:
- Machine-derived fields: minimal-edit proposals to `binding.md`.
- **Protected fields never touched**: `TEST_ACCOUNTS` · `PROJECT_PITFALLS` · `CONVENTIONS`.
- INDEX: additions as `Undocumented` for newly-discovered features; flag vanished routes. Approved
  row content never modified.

⚠️ **Gate**: show proposed diffs, confirm, then write.

#### Rescan Preflight (mandatory, before any scan)
1. `git status --short` is empty (untracked entries noted in §B, ignored; dirty tracked files → STOP).
2. `binding.md` exists and parses (DB_TOOL/UI_TOOL strings non-empty).
3. `python3 .opencode/skills/specalign/scripts/drift_probe.py <repo> --json` runs without error;
   output saved to `/tmp/drift.json` for §F. If the probe is missing, label fallback as
   `fallback-manual` in §F — never silently reimplement the probe.

A preflight failure aborts the rescan (Rule 1: read-only until authorized).

#### Rescan Output Schema (mandatory)
Every rescan produces one report using `templates/rescan-report-template.md` with sections A–I
(see template for full schema). Summary:

| Section | Purpose | Failure mode if missing |
|---|---|---|
| §A Binding Status | Preflight result + protected-field check | Drift propagates silently |
| §B Discovery Counts | Route / page / API / composable / store / spec counts | Invented numbers |
| §C Orphan Spec Files | Spec file ↔ INDEX row ↔ git tag cross-check | Silent spec loss |
| §D New INDEX Rows | Proposed additions (only); never modifies Approved | Discovery leaks |
| §E Drift Flags | Structured table (Type / Evidence / Action) | Unparseable backlog |
| §F Spec-Level Drift | `drift_probe.py` output (or labeled fallback) | False negative drift |
| §G Next Pilot | Rotation when current recommendation becomes Approved | Stale pilot note |
| §H Budget | Start/end timestamps; cap 5 min/survey, 20 min total | Budget drift |
| §I Approval | Stage 12.5 statement form (or "no-op confirmed") | Untracked writes |

#### CI Integration
A GitHub Actions workflow at `.github/workflows/specalign-rescan.yml` runs
`scripts/rescan_check.py` on every push/PR touching `docs/specs/INDEX.md`,
`docs/specs/SPEC-*.md`, or the check script itself. The check validates:
1. Every `Approved` row has a spec file and a git tag.
2. Every spec file has an INDEX row.
3. No `Undocumented` row has a spec file on disk.
4. No duplicate F-ids in INDEX.
5. Spec file §0 Card Feature ID matches filename (legacy specs: warning only).

CI failure blocks merge until registry consistency is restored. This implements the
"≥5 Approved specs → CI on REGISTRY consistency" rule from Quick Reference.

#### Rescan Write Permission Gate
Even though rescan only edits `INDEX.md` (and never code/DB), present the **exact** `git diff`
output **before** any write tool call. Then ask:

> «I approve writing/editing `docs/specs/INDEX.md` for the rescan, including the finalization
> commit.»

If the rescan proposes zero new rows and zero drift flips, the diff is still shown but approval
collapses to:

> «I confirm the rescan was a no-op: no INDEX changes, no drift flips.»

A bare "yes" to a prompt that displayed the statement satisfies the gate (per Rule 6).

#### Rescan Anti-Patterns (E10)
- **Modifying an `Approved` row's version or tag** (even "to fix a typo") → wrong; fix the spec, not the row.
- **Treating rescan as a covert SYNC for one feature** → wrong; SYNC has its own gates.
- **Skipping the diff-before-write because "it's just metadata"** → wrong; Rule 1 is read-only until authorized.
- **Recording drift flags without Evidence column** → wrong; Rule 4 (cite every claim) applies.
- **Silently reimplementing `drift_probe.py` logic** instead of calling the probe → wrong; E6 mandates reuse.
- **Omitting §C orphan-spec check because "zero is implied"** → wrong; zero must be stated explicitly.
- **Letting the budget drift** without recording §H timestamps → wrong; E7 enforces 5 min/survey cap.

### Stage 1 — Scope & Tier → status **Draft**
In/out of scope, explicitly (recorded in §1). Propose a tier with reasoning;
⚠️ **Gate:** explicit user tier decision before composition (statement form below). Record in §13B.

### Stage 2 — Meta-Discovery Inventory
Build the variable table, then cross-check against reality:

| Variable | Source |
|---|---|
| FEATURE_NAME | spec §0 (SYNC) / user + PROJECT_MAP (GENESIS) |
| ROUTE_PATH(S) | router files |
| FRONTEND_FILES | grep on frontend tree |
| API_ENDPOINTS **(+ CONSUMER)** | server grep; CONSUMER = frontend caller per endpoint |
| DB_TABLES / CONSTRAINTS | code grep + DB_TOOL |
| STATE_MODULES | stores / composables / hooks |
| TYPE_SCHEMAS | validation schema files |

SYNC: extract from the spec first, then cross-check the codebase — the table reflects what the
code actually has, not what the spec claims. Mismatches → §13A. Also cross-check PROJECT_MAP.
⚠️ **Gate:** present the table; wait for user confirmation.

### Stage 3 — Code Reading
Read every inventoried file: actual behavior, error codes, verbatim messages, transactions.

### Stage 4 — Data Model (DB_TOOL)
Tables, columns, types, defaults, constraints, partial indexes, triggers, enums — playbook §1
queries, as observed. **Additionally enumerate what the feature CONSUMES:** relevant triggers,
materialized/aggregate views, and DB functions (e.g. due-date calculators, notify hooks).

### Stage 4.5 — Anti-Pattern Scan + Checkpoint
Base checklist (**extensible**, cite rationale): 1. endpoint error handling missing · 2. missing
UNIQUE where logic implies · 3. soft-delete column unfiltered · 4. audit columns missing vs
siblings · 5. N+1 / missing transaction · 6. hardcoded values vs config · 7. client schema ≠ DB
constraint.
⚠️ **Checkpoint:** numbered Deviation Flags (DF-1…); wait for user. Zero findings → say "No
anti-patterns detected". State the **E5 result explicitly** ("flags found: …" / "none found").

### Stage 5 — UI & Flows (code)
Layout, visual states (loading/empty/error/**stale**/offline/read-only/conflict), flows with
alternative paths, accessibility affordances as observed (aria, keyboard, focus). UI-heavy
feature + binding `UI_REVIEW_SKILL` set → load it here.

### Stage 6 — Validation Pairing
Client schema ↔ DB constraint per field. Any mismatch is a DF; never silently pick a side.

### Stage 7 — Permissions
Document each action as the **isolation trio**: soft-check (UI) / hard-enforcement (server) /
audit-trail (logging). Enforcement absent where siblings have it → DF.

### Stage 8 — Draft
Write the draft spec file `<SPEC_DIR>/SPEC-F{n}-{slug}.md` from
`templates/specification-template.md` — §0–§14 including §13A–§13D (**18 blocks**); removals
justified in §13A. Sole pre-12.5 write exemption (Rule 1): Stage 12.5 reviews the real diff.
Draft carries status **Draft**. Assign flow IDs (`F{n}-*`) and acceptance-criteria IDs (`AC-*`).

### Stage 9 — Socratic Clarification Gate
Compile gaps into Q-1, Q-2, … in §13A.
Predicate: open this gate **before** Stage 8 composition whenever {version, tag slug, scope
boundary, verification channel} is undecided; reopen mid-run only for §0/§1-changing discoveries.
⚠️ **Gate:** STOP until every question is answered or explicitly deferred.

### Stage 10 — Internal Consistency + Cross-Section → **Verifying**
Cross-check flows ↔ API ↔ data model ↔ validation. Then the **Cross-Section pass** (mandatory
at Core; recommended at Standard) over section pairs: flows↔API · roles↔UI · validation↔DB ·
errors↔edge-cases · **terminology consistency across sections** (one concept = one meaning —
catches e.g. a label backed by two different data fields). Every inventoried endpoint shows an
in-scope CONSUMER or §6 records the owning feature.

### Stage 11 — Behavioral Verification (UI_TOOL)
Playbook §2: TEST_ACCOUNTS only; prefixed test rows (or §4-2b for non-prefixable tables);
verbatim capture; **silent click failure protocol** (assert effect ≤2s → retry once → JS `.click()`
fallback → evidence labeled `runtime-js-click` + anomaly row); transient-capture recipe;
optional negative-claim probes; budget timestamps. No conflict path → `conflict: N/A` in §13B —
never manufacture one. Unverifiable-in-budget → `code-verified-only` with reason. Dated entries for everything.

### Stage 12 — Self-Check & Presentation
Run §14 Self-Check (process audit + content completeness). Blocking ✗ → fix before presenting.
Present the real draft diff + results. Binding `DOCS_REVIEW_SKILL` set → load here.

### Stage 11.5 — Drift Check — `SpecAlign drift`
Proactive drift detection — makes the 4th authoritative-spec pillar ("drift-detectable") mechanical.
- Run `scripts/drift_probe.py <repo_root> [drift [F-ids...]] [--json]` (stdlib-only).
- Per-feature: parses §0 Card `Sources`, computes watermark (newest of: finalization tag commit
  date · INDEX `last_verified` date, exclusive by +1s), then `git log` over each source path since
  the watermark. Report: `drifted` / `clean` / `unverifiable` per feature.
- **Unverifiable** is reported when a Sources token is not a recognizable file path (e.g., table
  names, parenthesized annotations). Fix at next SYNC by editing the §0 Card `Sources` line —
  see "Limitations" below.
- ⚠️ **Gate**: probe lists drifted features + offending commits; you confirm per-row → edit
  REGISTRY to set matched rows → `Stale`. No other writes.
- **Limitations (stated, not hidden)**: DB-only changes invisible unless inside a listed source
  file; Sources quality depends on spec discipline; watermark trusts git history. Future CI
  consumers: the probe's `--json` output is the stable contract.

### Stage 12 — Self-Check & Presentation
Run §14 Self-Check (process audit + content completeness). Blocking ✗ → fix before presenting.
Present the real draft diff + results. Binding `DOCS_REVIEW_SKILL` set → load here.

### Stage 12.5 — Write Permission Gate
⚠️ Summarize every file to be written/edited; ask explicit approval **using the statement form**
(below). Approval covers the writes AND the finalization COMMIT (local, reversible).
Tag creation and push remain separately gated (Rule 6).

### Stage 13 — Finalization
1. §0 Card: Status → Approved; hashes, tag, date.
2. REGISTRY: status/tag/last-verified/coverage marks; **refresh the "Next recommended pilot" note**.
3. Tag `<TAG_PREFIX>F{n}-{slug}-vX.Y.Z` at the finalization commit. *(The tag IS the baseline —
   frozen, immutable, restorable.)*
4. `studies/green-<slug>.md` exists → append dated matrix results (Core tier: mandatory).
5. Commit (covered by 12.5); request push confirmation (sandbox lacks push auth → hand the command).
6. **Rollback on failure:** `git checkout -- <file>` · `git tag -d <tag>` · re-enter 12.5; log in §13B.

### Stage 13.5 — Project Map Sync Check (**non-blocking**)
Compare approved spec vs PROJECT_MAP. Stale → propose Before/After edits; decline → log
"PROJECT_MAP update declined — drift risk". Approval never depends on this stage.

### Stage 14 — Handoff
Ensure `<SPEC_DIR>/README.md` exists. Deliver: sections changed, DFs, open questions,
REGISTRY/README/map status, tag, push command.

## Approval Statements (gates close on these exact forms)

- **Tier (Stage 1):** «I classify this run as `<Micro|Standard|Core>` per the agent's recommendation; discussion, citation discipline, and final approval remain mandatory.»
- **Writes (12.5):** «I approve writing/editing `<files>` for `<FEATURE>` v`<X.Y.Z>`, including the finalization commit.»
- **Tag/push (Rule 6):** «I approve creating tag `<TAG_PREFIX>F{n}-{slug}-vX.Y.Z»`» / push variant.
A bare "yes" to a prompt that displayed its statement satisfies the gate; the statement must have been shown first.

## Status Matrix

| Stages | Spec status | Registry status |
|---|---|---|
| 0–9 | Draft (draft file on disk from Stage 8) | Draft |
| 10–12 | Verifying | Verifying |
| 12.5 | Verifying (draft written; final flip at 13) | Verifying |
| 13–14 | Approved | Approved |

Code changes without spec updates → **Stale** (set by the discovering SYNC).
Legacy-format specs remain Approved; normalization to this template happens at their next natural SYNC.

## Versioning

patch (+0.0.1) wording · minor (+0.1.0) non-breaking behavior · major (+1.0.0) contract/data-model/
breaking — major requires owner approval. Every spec update ships in the same commit/PR as the
triggering code change. Version bump only at approval; every version gets a §13C Evolution entry.

## Pilot Selection (next feature)

Prefer: full CRUD + 1–3 lookups + loading/empty/error states + ≤10 min verifiable.
Avoid combining high transaction complexity with high UI complexity in one pilot.

## Rationalization Table

| Excuse | Reality |
|---|---|
| "I read the code, so the behavior claim is safe" | Reading ≠ runtime. Unverified → `code-verified-only`. |
| "Cleanup is impossible — DB tool is read-only" | Playbook §4 pathways; UI soft-delete counts; hand SQL if needed. |
| "Checkpoint would be empty, so skip it" | Empty checkpoints are stated explicitly. Skipping IS the failure. |
| "Only the spec file needs the status flip" | §0 Card AND REGISTRY flip, or state is inconsistent. |
| "Tag shape is close enough" | `f4/1.0` ≠ `spec/F4-files-list-v1.0.0`. Format is binding. |
| "The commit needs its own approval too" | 12.5 covers the commit; only tag/push are separately gated. |
| "A JS click succeeded so user clicks work" | It proves the handler, not the pointer path. Label `runtime-js-click`; log anomaly. |
| "Micro-tier means I can skip citations" | Tiers compress breadth, never evidence. Rule 4 is inviolable. |
| "The chat summary is enough for review" | Review sees the REAL file diff (that's why Stage 8 writes it). |
| "No endpoint consumer, so no doc needed" | Record ownership in §6 or reopen scope — silent drops forbidden. |
| "I'm following the spirit" | Letter = spirit (Rule 7). |

## Red Flags — STOP

Writing outside `<SPEC_DIR>` before 12.5 · behavior claim without §13B entry · answering your own
question · unprefixed active test row · tag/push without approval · manufacturing a conflict ·
committing without checking staged-file count · deleting superseded knowledge instead of marking it
→ **stop, revert if needed, resume from the gate.**

## Quick Reference

Modes `GENESIS`/`SYNC` · Tiers `Micro`/`Standard`/`Core` · Deliverables: spec + REGISTRY row +
README (if missing) + tag + green-studies entry (Core) + optional map patch ·
Tag `<TAG_PREFIX>F{n}-{slug}-vX.Y.Z` (= baseline) · Statuses Undocumented→Draft→Verifying→Approved→Stale ·
Budget 10 min/feature with timestamps · Spec structure §0–§14 incl. §13A–§13D (**18 blocks**) ·
At ≥5 Approved specs, consider CI on REGISTRY consistency.

## Common Mistakes

1. Inferring mode from input shape → confirm at Stage 0.
2. Inventory from spec alone → cross-check code (Stage 2).
3. §13A accumulating answered items → resolutions become dated §13B entries.
4. Approving without flipping REGISTRY/README (Stage 13 checklist).
5. Burning budget on one widget → type instead of clicking; fall back `code-verified-only`.
6. Lowercase-vs-capitalized path in `git add` staging nothing → always verify staged count.
7. Treating a JS-dispatched click as proof of natural-user interaction.
8. Rewriting behavior sections on SYNC without a §13C Deprecated/Superseded marker.

## Supporting Files

`templates/specification-template.md` · `templates/handoff-readme-template.md` ·
`references/verification-playbook.md` · `references/binding-example-sanad.md`

## Validation Status (TDD per writing-skills)

- **RED (documented):** Sanad F3 pilot failures (missed flips, malformed tag, print-dialog wedge,
  read-only cleanup, §13 rewrite) + F4 GENESIS additions (approval-target mismatch, endpoint
  without CONSUMER, ad-hoc DF states, undefined budget, silent trusted-click swallow, transient
  toast loss, non-prefixable table, path-case staging miss). All encoded above.
- **GREEN plan:** pressure scenarios pending first SpecAlign pilot — priority probes:
  (a) Micro-tier cannot suppress citations; (b) Cross-Section pass catches a terminology DF;
  (c) CONSUMER column forces ownership note; (d) staged-count check fires on case mismatch.
- **Rescan GREEN (v0.11.0):** all 10 enhancements (E1–E10) have RED baseline (manual rescan run
  2026-08-27) and GREEN validation (template + SKILL.md + CI script + workflow passing checks).
- Status: **v0.11.0 rescan-hardened — flips to 1.0.0 after one successful GREEN pilot.**

## Changelog

Single home: `CHANGELOG.md` in this folder. Current: **v0.11.0 — 2026-08-27**.
