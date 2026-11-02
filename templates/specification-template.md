# Executable Specification Template — SpecAlign v1.0

**Blocks §0–§14 including §13A–§13D — 18 blocks total.**
File naming: `SPEC-F{n}-{slug}.md`. Prose language per binding `CONVENTIONS`; user-facing strings verbatim in their
runtime language; all metadata dates ISO 8601 (YYYY-MM-DD).
Start with **all** blocks. Fill each with concrete, executable detail. Remove or add a block only with
justification recorded in §13A.

> **How to fill this template**
> - Every claim cites a source: `file:function`, a SQL query, or a browser step.
> - User-facing strings are quoted **verbatim** from runtime — never paraphrased.
> - Every behavioural claim carries an evidence label from the legend (`gates/evidence.md`); a claim not exercised is
>   `code-verified-only` with a reason in §13B.
> - IDs are assigned once and never reused: `F{n}-*` flows · `AC-*` criteria · `V-*` evidence · `D-*` decisions ·
>   `Q-*` questions · `DF-*` flags.
> - Binding values are referenced by key (`TAG_PREFIX`, `BASELINE_DATE`, `CONVENTIONS`).
> - The machine reads the §0 Card (`Feature`, `Status`, `Version`, `Tag`, `Sources`): keep the `| Field | Value |` table.

> **Evidence legend** (copy under the title of the spec; add the artefact names): `code` · `db` · `static` · `unit` ·
> `contract` · `runtime` · `runtime-js-click` · `runtime-synthetic` · `historical-log` · `code-verified-only`.

---

## §0 Card

| Field | Value |
|---|---|
| Feature | F{n} — {title} |
| Type | tab / page / cross-cutting |
| Tier | Micro / Standard / Core (stage 1 decision, T1 in §13D) |
| Status | Draft / Verifying / Approved / Stale |
| Version | vX.Y.Z |
| Skill version | SpecAlign {X.Y.Z} used for this run |
| Baseline date | {ISO 8601} |
| Code baseline commit | {hash of the code the spec describes} |
| Finalization commit | {tag target; filled at stage 12} |
| Tag | {TAG_PREFIX}F{n}-{slug}-vX.Y.Z (earlier: {previous tags}) |
| Sources | {primary files; `a/{b,c}.vue`, `dir/*`, `tests …`, `tables …` allowed} |
| Schema fingerprint | {hash of the introspection result, or `n/a`} |
| Run record | {path of the run manifest, or `n/a`} |

## §1 Purpose and Scope
What the feature does and for whom. Optionally one line: **dominant design principle**. **Explicitly out of scope** —
list what this spec does not cover, naming the feature IDs that own those parts.

## §2 Users and Permissions
Role × action matrix, then each protected action as the **isolation trio**:

| Action | Soft-check (UI) | Hard enforcement (server) | Audit trail |
|---|---|---|---|
| {action} | {hide/disable? guard?} | {endpoint check? — absence = DF} | {audit log?} |

Flag any missing server-side enforcement as a Deviation Flag in §13A.

## §3 User Interface
Direction per CONVENTIONS, then:
- **3.1 Layout & structure** — wireframe, responsiveness, core decisions.
- **3.2 Components & UI elements** — map each element to its data source, formatting, hidden fields; include a
  **display rules & calculations** list (formats, rounding, derived values).
- **3.3 Interactive patterns** — modals/forms, expandable rows, search behaviour (debounce, triggers).
- **3.4 Visual differentiation & accessibility** — how states/roles/data types are distinguished; observed
  affordances (accessible names, keyboard paths, focus management).
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

(No UI → `N/A — reason` here and in §13B.)

## §4 User Flows
Numbered step-by-step (`F{n}-1`, `F{n}-2`, …) per flow, including alternative and error paths. Cite the UI element and
the API call at each step.

## §5 Data Model
Per table: columns (type/nullable/default), constraints, partial indexes, triggers, relations — **as observed via
DB_TOOL, not assumed**. Include the exact introspection queries used.
**Consumed DB machinery:** triggers fired by this feature's writes · materialized/aggregate views it reads · DB
functions it depends on. (No database → `N/A — reason`.)

## §6 API Contracts
Per endpoint: method, path, inputs, outputs, status codes, **verbatim** error messages, conflict handling, and its
**CONSUMER** (caller) or an ownership note if consumed elsewhere.

## §7 Frontend Logic
State modules, cache keys, invalidation rules, lifecycle mount→fetch→mutate→refetch.
**State & persistence sub-block:** fetch strategy · persisted keys + TTL · dirty-tracking semantics · save flow
(manual/auto, optimistic + rollback patterns).

## §8 Validation Rules

| Field | Client rule | DB constraint | Match? |
|---|---|---|---|

Any mismatch becomes a DF in §13A. Never silently pick a side.

## §9 Data Flow
Click → validation → request → transaction → commit → cache invalidation → UI update.

## §10 Errors, Conflicts & Edge Cases

| Scenario | Type | Detection | HTTP/DB code | Message (verbatim) | Recovery | Compliance criterion |
|---|---|---|---|---|---|---|

`Type`: error / conflict / environmental edge (offline, stale, zoom/responsive) / accessibility edge.
No conflict path → `conflict: N/A — {reason}`; never manufacture one.

## §11 Acceptance Criteria
Given/When/Then, testable, each referencing its flow and its evidence entry; every `Resolved` DF has at least one AC.

| AC ID | Flow | Given/When/Then | Evidence (V-id · label) | Resolves |
|---|---|---|---|---|

## §12 Dependencies
**Prerequisites** · **Dependents** · **Shared components** (reused UI/store/util inventory). A shared component changed
by this run lists the other specs it patches (ripple).

## §13A Open Questions & Deviation Flags

| ID | Type | Item | Severity | Disposition → status | AC / evidence |
|---|---|---|---|---|---|

Q status: `Open` / `Answered` / `Deferred`. DF disposition → terminal status (`gates/dispositions.md`):
Fix → `Resolved(commit)` · Accept → `Accepted(owner, reason, reopen-trigger)` · Defer → `Deferred(trigger/date,
tracker)` · Reject → `Rejected(evidence)`. **Only `Open` blocks self-check PASS.**

## §13B Verification Log

| ID | Date | What was verified | Label | Result |
|---|---|---|---|---|

Label ∈ the evidence legend (`code` · `db` · `static` · `unit` · `contract` · `runtime` · `runtime-js-click` ·
`runtime-synthetic` · `historical-log` · `code-verified-only`; for decisions `decision`).
Include: `code-verified-only` items with reasons · test command + counts · budget start/end timestamps · tooling
anomaly rows · cleanup statements with row counts · rollbacks · declined map updates · the run type (documentation-only
or remediating) and the R1 file list. Decisions get a **mini decision record** (`D-n`): Context / Decision /
Consequences, plus the gate id and the user's reply **verbatim**.

## §13C Evolution History

| Version | Date (ISO) | Change type | Description |
|---|---|---|---|

Change types: Created / Modified / Deprecated / Superseded / Fixed / Normalized / Patched (ripple).
Zero knowledge deletion: when behaviour leaves the spec narrative, write **"Superseded wording: …"** in the row with the
old statement and the version that ended it. A ripple patch names the spec and version that caused it.

## §13D Approval History

| Version | Gate | Approved by | Date (ISO) | Evidence ref | Statement / reply |
|---|---|---|---|---|---|

One row per approval event: T1, R1, D1 (per migration), X1, W1, V1, G1, P1 (or C1 for the combined form). Quote the
user's reply verbatim; list every tag and every patched spec named by the approval.

## §14 Self-Check (mandatory, blocking)

Machine checks (paste their output, do not retype a verdict):

```
python -m specalign registry check <repo>     →  {paste: n/n checks passed}
python -m specalign drift <repo> {F-id}       →  {paste: clean / listed commits explained}
```

Process audit:

| # | Check | ✓/✗ | Comment |
|---|---|---|---|
| 1 | Rebuildable from this spec alone? Core: five questions from the ACs answered from the spec only (list them) | | |
| 2 | All user-facing strings verbatim from runtime? | | exceptions flagged `code-verified-only` |
| 3 | Client validation == DB constraints (mismatches as DF)? | | |
| 4 | All 18 blocks present, or removal justified in §13A? | | |
| 5 | Registry updated (status/version/tag/coverage/pilot note) and ripple specs patched? | | |
| 6 | Tag matches `<TAG_PREFIX>F{n}-{slug}-vX.Y.Z`, one per patched spec? | | |
| 7 | Test rows cleaned with proof (count query)? No active unprefixed rows? Audit rows untouched? | | |
| 8 | UI_TOOL budget respected; start/end timestamps logged? | | |
| 9 | Every §13A item has a terminal status; none `Open`? | | |
| 10 | §13B dated entries for every label used; DF → AC → V chain complete? | | |

Content completeness:

| # | Check | ✓/✗ |
|---|---|---|
| 11 | Purpose + design principle defined; scope boundaries explicit? | |
| 12 | Permissions as isolation trio; enforcement gaps flagged? | |
| 13 | Layout direction-aware; display rules & calculations listed; accessibility affordances noted? | |
| 14 | Flows linear and complete; AC IDs traceable to flows? | |
| 15 | DB dependencies incl. consumed triggers/views/functions? | |
| 16 | Two-layer validation paired against constraints? | |
| 17 | Edge cases cover non-error types with compliance criteria? | |
| 18 | State & persistence block filled (strategy, keys/TTL, dirty/save)? | |

**Overall: PASS / FAIL.** Any blocking ✗ → fix before presenting.

---

*Template history: §13C/§13D added in SpecAlign v0.9.0; v1.0 adds skill version, evidence legend, ID conventions,
dispositions, superseded-wording and ripple-patch conventions, machine-check block in §14.*
