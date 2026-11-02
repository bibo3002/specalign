---
name: specalign
description: Use when documenting an existing feature of a codebase into an executable specification, when a spec may have drifted from the code, live database, or runtime behavior, when verifying spec-to-reality alignment, or when reverse-engineering undocumented features. Triggers on document feature, extract spec, sync spec, spec drift, executable specification, reverse-engineer feature, GENESIS, SYNC, align spec, توثيق ميزة، مواصفة، مزامنة المواصفة.
---

# SpecAlign (v1.0.0-dev)

SpecAlign **extracts and maintains executable, agent-readable specifications for existing features**, validated
against a **triple source of truth**: the code, the live database, and observed runtime behaviour — never code
alone. A spec is authoritative only if it is code-versioned, runtime-verified, agent-readable, drift-detectable and
self-auditing.

Modes: **GENESIS** (`modes/genesis.md`) · **SYNC** (`modes/sync.md`) · **DRIFT** (`modes/drift.md`) ·
**INIT / RESCAN** (`modes/rescan.md`). Tiers: Micro / Standard / Core.

**How to use this skill (context-safe):** this file is the router. Read the stage file for the stage you are in,
plus the gate files it names — not everything at once. Keep `.specalign/run-state.json` current so a resumed or
compacted session continues at the right stage. After a compaction, re-read this file and the current stage file.

SpecAlign is **backward-looking**: it documents what exists and audits what changed. It does not govern
spec-first development. A run that finds defects may fix them only under an explicit **remediating-run
authorization** (`gates/remediation.md`) — that is how the spec comes to describe the corrected behaviour.

## Project binding (required before any stage)

`<SPEC_DIR>/binding.md` holds project values: `PROJECT_MAP`, `SPEC_DIR`, `REGISTRY`, `DB_TOOL` / `UI_TOOL` (adapters in
`adapters/`), `TEST_ACCOUNTS`, `TEST_DATA_PREFIX` (default `__TEST_`), `TAG_PREFIX`, `BASELINE_DATE`, capability
profile, `CONVENTIONS`, `PROJECT_PITFALLS` (template: `templates/binding.template.md`). Missing or incomplete → STOP
and ask. **Never guess a binding value.**

## Binding rules

1. **Read-only until authorized.** Before the write gate you may write only (a) the draft spec inside `SPEC_DIR` and
   (b) the files listed in an approved **R1** remediation. Registry, project map, tags and pushes wait for their gates.
2. **Never guess.** Missing data becomes an open question (§13A) asked of the user.
3. **Test-data hygiene.** Only `TEST_DATA_PREFIX` rows, cleaned up by prefix; audit logs are immutable
   (`gates/ddl-protocol.md`).
4. **Cite every claim** (`file:function`, SQL, browser step). Tiers never relax this.
5. **Verbatim strings:** user-facing copy exactly as observed, in its own language.
6. **Gates close only on recorded approvals** (`gates/approval-statements.md`). Tag, push, DDL and deletion each have
   their own form; approval in one context never carries to another.
7. **Letter = spirit.** No exceptions for "obvious" shortcuts.
8. **Abort anytime** on "abort"/"switch mode": stop, summarise, write nothing further, log partial work in §13B.
9. **Zero knowledge deletion:** superseded behaviour is marked with its ending version (§13C), never erased.
10. **Mechanical checks are run, not asserted:** registry and drift results come from the tools, pasted into §14.

## Tiers (chosen at stage 1 — the user decides)

| Tier | Use for | Mandatory | May relax |
|---|---|---|---|
| **Micro** | registry metadata, typos, links, annotation-only edits | binding gate · tier decision · cited claims · §13C entry | stage count; no browser run if no behaviour claim |
| **Standard** (default) | any behavioural documentation | the full pipeline | nothing evidence-related |
| **Core** | data model, permissions/security, API contract, multi-feature surface | Standard + full cross-section pass + green-studies entry + reconstruction check (stage 10) | nothing |

Micro is forbidden when the change touches data model, permissions, security or an API contract, or adds any new
behavioural claim.

## Pipeline (one canonical order; gates marked ⚠️)

| # | Stage | File | Gate | Legacy no. |
|---|---|---|---|---|
| 0 | Preflight | `stages/00-preflight.md` | binding gate | 0 |
| 1 | Scope and tier | `stages/01-scope-tier.md` | ⚠️ T1 | 1 |
| 2 | Inventory | `stages/02-inventory.md` | ⚠️ confirm table | 2 |
| 3 | Read: code · data · UI · validation · permissions | `stages/03-read.md` | | 3, 4, 5, 6, 7 |
| 4 | Anti-pattern scan + checkpoint | `stages/04-checkpoint.md` | ⚠️ R1 dispositions | 4.5 |
| 5 | Remediation (remediating runs only) | `stages/05-remediation.md` | ⚠️ D1 per migration | — |
| 6 | Verification: tests, then runtime | `stages/06-verification.md` | | 11 |
| 7 | Draft the spec | `stages/07-draft.md` | | 8 |
| 8 | Socratic clarification | `stages/08-socratic.md` | ⚠️ questions answered | 9 |
| 9 | Cross-section → **Verifying** | `stages/09-cross-section.md` | | 10 |
| 10 | Self-check (tools + judgement) | `stages/10-self-check.md` | | 12 |
| 11 | Write gate | `stages/11-write-gate.md` | ⚠️ W1 / C1 | 12.5 |
| 12 | Finalize → **Approved** (+ map sync) | `stages/12-finalize.md` | ⚠️ G1, P1 | 13, 13.5 |
| 13 | Handoff | `stages/13-handoff.md` | | 14 |

Draft always follows verification; remediation always precedes it; the checkpoint comes after all reading.

## Status matrix

| Stages | Spec status | Registry status |
|---|---|---|
| 0–8 | Draft (file exists from stage 7) | Draft |
| 9–11 | Verifying | Verifying |
| 12–13 | Approved | Approved |

Code changes without spec updates → **Stale** (set by the discovering run). Legacy-format specs stay Approved and are
normalised at their next SYNC (`modes/sync.md`).

## Tools (`python -m specalign …`, from the skill's `tools/` dir; stdlib-only)

Exact syntax of every command, with examples: `references/cli.md`. Do not guess flags.

| Command | Purpose |
|---|---|
| `preflight <repo>` | stage 0: binding complete, tracked files clean, tag namespace, encodings; exit 0/1/2 |
| `registry check <repo>` | INDEX ↔ spec ↔ §0 Card ↔ exact tag; exit 0/1/2 |
| `drift <repo> [F-ids]` | sources changed since each release tag, split into own vs ripple; exit 0/1/2/3 |
| `inventory <repo> [F-ids]` | endpoints (and tables) in code vs what the specs say; advisory |
| `schema fingerprint\|snapshot\|check` | hash of the live database objects a spec depends on; exit 0/1/2/3 |
| `lint <repo> [F-ids]` | blocks, IDs, DF → AC → evidence chain, labels, markers; exit 0/1/2 |
| `docedit …` | table-aware, EOL/BOM-preserving edits of specs and the registry (no hand-written scripts) |
| `manifest init/stage/approve/add/show/verify` | run record + resumable state; approvals stored verbatim, UTC time |
| `finalize plan/apply/staged/tag/push <plan.json>` | dry-run-first finalization; apply, tag, push refuse without the recorded approval |
| `eval [--transcripts DIR]` | skill repository only: the 29 validation-matrix scenarios as tests + transcript graders |
| `python install.py --check` | skill copies match the source; no hand edits |

Tool output is pasted into §14, never retyped.

## Rationalization table

| Excuse | Reality |
|---|---|
| "I read the code, so the behaviour claim is safe" | Reading ≠ runtime. Unverified → `code-verified-only`. |
| "Cleanup is impossible — the DB tool is read-only" | Playbook §4 pathways; scoped SQL with X1. |
| "The checkpoint would be empty, so skip it" | Say "No anti-patterns detected". Skipping is the failure. |
| "Only the spec needs the status flip" | §0 Card AND registry flip, or the state is inconsistent. |
| "The tag shape is close enough" | The format is binding; `registry check` fails otherwise. |
| "Fix all covers it" | Only what the shown table marks Fix, inside the listed files. |
| "A scripted click worked so user clicks work" | Label `runtime-js-click` and log the anomaly. |
| "Micro means no citations" | Tiers compress breadth, never evidence. |
| "The chat summary is enough" | Review sees the real file diff. |
| "The passing check proves it" | A check passes only on evidence it can fail on; read what it checked. |
| "I'm following the spirit" | Letter = spirit. |

## Red flags — STOP

Writing outside `SPEC_DIR` or the R1 list before the write gate · a behaviour claim without a §13B entry · answering
your own question · an unprefixed active test row · tag, push, DDL or deletion without its form · deleting audit
rows · manufacturing a conflict · committing without checking the staged-file count · deleting superseded knowledge ·
retyping a check result instead of pasting it → **stop, revert if needed, resume from the gate.**

## Deliverables

Spec + registry row + README (if missing) + tag + green-studies entry (Core) + optional project-map patch + run record.
Tag `<TAG_PREFIX>F{n}-{slug}-vX.Y.Z` is the baseline. Statuses: Undocumented → Draft → Verifying → Approved → Stale.
Behavioural budget 10 min/feature. Spec structure §0–§14 incl. §13A–§13D (**18 blocks**).

## Supporting files

`stages/` · `modes/` · `gates/` (approval-statements, dispositions, remediation, ddl-protocol, versioning, evidence) ·
`templates/` · `references/verification-playbook.md` · `references/binding-example-sanad.md` · `CHANGELOG.md`
