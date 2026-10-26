# Executable Specification Template — SpecAlign v0.9.0

**Blocks §0–§14 including §13A–§13D — 18 blocks total.**
File naming: `SPEC-F{n}-{slug}.md`. Prose: English-primary per binding CONVENTIONS; user-facing
strings verbatim in their runtime language; all metadata dates ISO 8601 (YYYY-MM-DD).
Start with **all** blocks. Fill each with concrete, executable detail. Remove or add a block only
with justification recorded in §13A.

> **How to fill this template**
> - Every claim cites a source: `file:function`, a SQL query, or a browser step.
> - User-facing strings are quoted **verbatim** from runtime — never paraphrased.
> - Any claim not verified at runtime is marked `code-verified-only` in §13B.
> - Binding values are referenced by key (e.g. `TAG_PREFIX`, `BASELINE_DATE`, `CONVENTIONS`).

---

## §0 Card

| Field | Value |
|---|---|
| Feature | F{n} — {title} |
| Type | tab / page / cross-cutting |
| Tier | Micro / Standard / Core (Stage 1 decision) |
| Status | Draft / Verifying / Approved / Stale |
| Version | vX.Y.Z |
| Baseline date | {ISO 8601, e.g. 2026-08-23} |
| Code baseline commit | {hash of the code the spec describes} |
| Finalization commit | {tag target; filled at Stage 13} |
| Tag | {TAG_PREFIX}F{n}-{slug}-vX.Y.Z |
| Sources | {primary files / tables} |

## §1 Purpose and Scope
What the feature does and for whom. Optionally one line: **dominant design principle**
(e.g. `Progressive Disclosure`, `Separation of Concerns`). **Explicitly out of scope** — list what
this spec does not cover, naming the feature IDs that own those parts.

## §2 Users and Permissions
Role × action matrix, then each protected action as the **isolation trio**:

| Action | Soft-check (UI) | Hard enforcement (server) | Audit trail |
|---|---|---|---|
| {action} | {hide/disable? guard?} | {endpoint check? — absence = DF} | {audit log?} |

Flag any missing server-side enforcement as a Deviation Flag in §13A.

## §3 User Interface
Direction per CONVENTIONS, then:
- **3.1 Layout & structure** — wireframe, responsiveness, core decisions.
- **3.2 Components & UI elements** — map each element to its data source, formatting,
  hidden fields; include a **display rules & calculations** list (formats, rounding, derived values).
- **3.3 Interactive patterns** — modals/forms, expandable rows, search behavior (debounce, triggers).
- **3.4 Visual differentiation & accessibility** — how states/roles/data types are distinguished;
  observed affordances (aria-labels, keyboard paths, focus management, contrast-relevant notes).
- **3.5 Visual states:**

| State | Trigger | Visual treatment |
|---|---|---|
| loading | | |
| empty | | |
| error | | |
| stale | {data-age threshold if any} | |
| offline | | |
| read-only | | |
| conflict | | |

## §4 User Flows
Numbered step-by-step (`F{n}-1`, `F{n}-2`, …) per flow, including alternative and error paths.
Cite the UI element and the API call at each step.

## §5 Data Model
Per table: columns (type/nullable/default), constraints, partial indexes, triggers, relations —
**as observed via DB_TOOL, not assumed**. Include the exact introspection queries used.
**Consumed DB machinery:** triggers fired by this feature's writes · materialized/aggregate views
it reads · DB functions it depends on (due-date calculators, notify hooks, audit setters).

## §6 API Contracts
Per endpoint: method, path, inputs, outputs, status codes, **verbatim** error messages, conflict
handling, and its **CONSUMER** (frontend caller) or ownership note if consumed elsewhere.

## §7 Frontend Logic
State modules, cache keys, invalidation rules, lifecycle mount→fetch→mutate→refetch.
**State & persistence sub-block:** fetch strategy (cache-first/network-first) · persisted keys +
TTL (e.g. localStorage/sessionStorage) · dirty-tracking semantics · save flow (manual/auto,
optimistic + rollback patterns).

## §8 Validation Rules
Pairing table:

| Field | Client rule | DB constraint | Match? |
|---|---|---|---|

Any mismatch becomes a DF in §13A. Never silently pick a side.

## §9 Data Flow
Click → validation → request → transaction → commit → cache invalidation → UI update.

## §10 Errors, Conflicts & Edge Cases

| Scenario | Type | Detection | HTTP/DB code | Message (verbatim) | Recovery | Compliance criterion |
|---|---|---|---|---|---|---|

`Type`: error / conflict / environmental edge (offline, stale, zoom/responsive) / accessibility edge.
If the feature has **no conflict path**, record `conflict: N/A — no applicable uniqueness
constraint` — never manufacture one.

## §11 Acceptance Criteria
Given/When/Then, testable, ID'd (`AC-01`…), each referencing its flow (`F{n}-*`). Cover happy +
conflict + empty paths. Conflict coverage follows the same N/A rule as §10.

| AC ID | Flow | Given/When/Then |
|---|---|---|

## §12 Dependencies
Three subsections: **Prerequisites** (features that must exist first) · **Dependents** (features
consuming this one) · **Shared components** (reused UI/store/util inventory).

## §13A Open Questions & Deviation Flags

| ID | Type | Item | Status |
|---|---|---|---|

Q statuses: `Open` / `Answered` / `Deferred`.
DF terminal states: `Open` / `Accepted-risk(owner,date)` / `Fix-scheduled(ref)` /
`Deferred(owner,date)` / `Resolved(commit)`. **Only `Open` blocks Stage 12 PASS**; Accepted-risk
and Deferred stay visible with owner+date; decision detail in §13B.

## §13B Verification Log

| ID | Date | What was verified | Method (code / DB / runtime / runtime-js-click / decision) | Result |
|---|---|---|---|---|

Include: `code-verified-only` items with reasons · budget start/end timestamps · tooling anomaly
rows · cleanups performed · rollbacks · declined map updates. For decided DFs and owner
decisions, record a **mini-decision record**: Context / Decision / Consequences (one line each)
plus the approval statement echoed at the gate.

## §13C Evolution History

| Version | Date (ISO) | Change type | Description |
|---|---|---|---|

Change types: Created / Modified / Deprecated / Superseded / Fixed / Normalized.
Zero knowledge deletion: when behavior leaves the spec narrative, mark it here with the version
that ended it — never erase silently.

## §13D Approval History

| Version | Status | Approved by | Date (ISO) | Evidence ref | Statement |
|---|---|---|---|---|---|

One row per approval event (writes, tag, push, tier). Statements quoted from the gate forms.

## §14 Self-Check (mandatory, blocking)

Process audit:

| # | Check | ✓/✗ | Comment |
|---|---|---|---|
| 1 | Rebuildable from this spec alone by another agent? | | Core tier: add reconstruction footnote (specs-only rebuild feasibility) |
| 2 | All user-facing strings verbatim from runtime? | | exceptions flagged code-verified-only |
| 3 | Client validation == DB constraints (mismatches as DF)? | | |
| 4 | All 18 blocks present, or removal justified in §13A? | | |
| 5 | REGISTRY updated (status/version/tag/coverage/pilot note)? | | |
| 6 | Tag matches `<TAG_PREFIX>F{n}-{slug}-vX.Y.Z`? | | |
| 7 | Test rows cleaned (or handed to user)? No active unprefixed rows? | | |
| 8 | UI_TOOL budget respected; start/end timestamps logged? | | |
| 9 | Every §13A item has a terminal status? Only Open blocks PASS? | | |
| 10 | §13B dated entries for every method used? | | |

Content completeness:

| # | Check | ✓/✗ |
|---|---|---|
| 11 | Purpose + design principle defined; scope boundaries explicit? | |
| 12 | Permissions as isolation trio; enforcement gaps flagged? | |
| 13 | Layout RTL-aware; display rules & calculations listed; a11y affordances noted? | |
| 14 | Flows linear and complete; AC IDs traceable to flows? | |
| 15 | DB dependencies incl. consumed triggers/views/functions? | |
| 16 | Two-layer validation paired against constraints? | |
| 17 | Edge cases cover non-error types with compliance criteria? | |
| 18 | State & persistence block filled (strategy, keys/TTL, dirty/save)? | |

**Overall: PASS / FAIL.** Any blocking ✗ → fix before presenting.

---

*Supersession note: blocks §13C/§13D were added in SpecAlign v0.9.0 (absorbing KDD evolution/
approval logging); legacy brownfield-spec v≤3.2 documents carry only §13A/§13B until normalized.*
