# SpecAlign — evaluations and improvements log

Purpose: record, run after run, how SpecAlign behaves in real use, what was adjusted, and what should change. When enough runs are logged, this file is the input for **SpecAlign 1.1.0**. Baseline under evaluation: **1.0.0** (source commit `b5afdf3`).

This file lives in the skill repository only. It is not part of the install payload (`PAYLOAD` in `tools/specalign/installer.py` is an explicit list), so it never reaches an installed copy and does not affect `install.py --check`.

## How to use this file

1. After every use of the skill, append one **run entry** (section 2) and its **findings** (section 3). Never rewrite earlier entries; change only a finding's *Status* and *Recurrence*.
2. Keep **observations** (facts, with evidence) separate from **proposals** (opinion). An observation must cite a command, tool output, message, file or commit that someone can check.
3. Link each run to its run record (`<project>/docs/specs/runs/<run-id>.json`) and its commits.
4. Promote a finding to the 1.1.0 backlog (section 5) when it **recurs in at least two runs**, or when it is a plain defect (wrong output, crash, contradiction). A single-run friction item stays *Open* until it recurs.
5. Do not edit the skill between runs except to fix outright defects; log each such fix as a finding with Status *Fixed (commit)* so later runs compare like with like.
6. The author of an entry is the agent that ran the skill. The owner records a verdict in the *Owner verdict* column (agree / disagree / priority). Until then the verdict is *pending*.

**Finding id:** `SA-nnn`, assigned once, never reused. **Category:** tooling · process · template · gate · verification · docs · environment. **Severity:** low · medium · high. **Status:** Open · Backlog (1.1.0) · Rejected · Fixed (commit) · Shipped (1.1.0).

## 1. Run index

| Run | Date | Project / feature | Mode (asked → used) | Tier | Run type | Skill version | Result |
|---|---|---|---|---|---|---|---|
| R-01 | 2026-11-03 | Sanad / F19 Appointments | SYNC → GENESIS | Core | remediating | 1.0.0 | Approved v1.0.0, 3 tags pushed |

## 2. Run entries

### R-01 — Sanad F19 Appointments (2026-11-03)

- **Run record:** `docs/specs/runs/2026-11-03-F19-genesis.json` (Sanad repository).
- **Commits:** `ccb9ea0` (finalization), `418fb41` (tags recorded in the run record), `9893c9e` (run record closed at the handoff stage). Tags: `spec/F19-appointments-v1.0.0`, `spec/F2-parties-v1.3.1`, `spec/F10-date-picker-v1.0.1`.
- **Outcome:** spec of 415 lines; 11 deviation flags (2 fixed, 5 accepted, 4 deferred); 4 questions, all answered; registry 9/9; drift clean for F19, F2, F10; `npm test` 403 passed / 0 failed / 0 skipped; typecheck clean.
- **Cost:** gates closed: T1, R1, X1 (test-row cleanup), X1 (deletion of two legacy files), C1; plus the mode question, the inventory confirmation and the Socratic answers. About 10 user round-trips. Files in the finalization commit: 10 (spec, run record, INDEX, two ripple specs, green-studies file, one code file, project map, two deletions). Browser time: 10:07:19Z to 10:09:50Z, about 2.5 of the 10 minutes allowed.
- **Where the run was hard:** the headless browser ignored real clicks and typing on the date picker and Select widgets, so the add form was never driven end to end; test rows were created with same-origin `fetch` under the real browser session and labelled `runtime-synthetic`.

## 3. Findings

Format: **SA-nnn** · category · severity · status · recurrence (runs) · owner verdict.

### From R-01

**SA-001 · tooling · medium · Open · R-01 · verdict pending**
*Observation:* `manifest init … --mode GENESIS` without `--tier` / `--run-type` left `tier: null`, `run_type: "documentation-only"` and `skill_version: ""` in the run record. They stayed that way after T1 and R1 were recorded, although R1 makes the run remediating (`manifest show` printed "tier not set, documentation-only"). The record was corrected by hand-editing the JSON.
*Proposal:* derive tier from the recorded T1, run type from R1, and skill version from `VERSION`; or make `approve T1` / `approve R1` update those fields.

**SA-002 · tooling · medium · Open · R-01 · verdict pending**
*Observation:* `manifest add cleanup --json …` failed with `json.decoder.JSONDecodeError: Invalid \escape` when the payload carried a SQL `LIKE '\_\_TEST\_%'` pattern, both inline (Git Bash) and via `--json-file` with `\\_` escapes. It succeeded only after removing every backslash from the payload.
*Proposal:* reproduce on Windows (Git Bash and PowerShell), make the loader accept valid JSON escapes in both paths, and document the quoting rule in `references/cli.md`.

**SA-003 · tooling · low · Open · R-01 · verdict pending**
*Observation:* `manifest stage` refuses to jump (`error: cannot jump from stage 0 to 2`). The earlier stages had in fact been done in the same working session, so recording them was ceremony (`stage 1`, then `stage 2`).
*Proposal:* allow a forward jump with an automatic note, or let `manifest approve T1` advance the stage.

**SA-004 · tooling · medium · Open · R-01 · verdict pending**
*Observation:* `finalize plan` lists `expect_files` for the spec and registry edits only (4 files). A remediating run legitimately commits more (the R1 code file, project map, studies file, run record, deletions: 10 files). `finalize staged` requires equality with `expect_files`, so the plan had to be edited by hand before it would pass.
*Proposal:* build the expected set from the plan edits plus the run record's `files` (scope remediation) plus an optional `extra_files` list; treat staged deletions explicitly.

**SA-005 · tooling · medium · Open · R-01 · verdict pending**
*Observation:* the tools modify the run record after the finalization commit (recording tags, then the stage 13 transition). This forced two follow-up commits (`418fb41`, `9893c9e`) on top of the finalization commit. The same happened in the earlier Sanad F4 run (`e79e8f7`).
*Proposal:* write tags and the final stage to the git-ignored `.specalign/` state and fold them into the committed record only once; or document the expected follow-up commit in stage 12 and cover it in the W1/C1 file list.

**SA-006 · process · low · Open · R-01 · verdict pending**
*Observation:* stage 9 says "Spec and registry status move to Verifying", while binding rule 1 says the registry is read-only until the write gate (and the status matrix says registry Verifying for stages 9–11). The run followed stage 9 and edited `INDEX.md` before W1/C1.
*Proposal:* state one rule. Recommended: the registry flip to Verifying is an allowed pre-gate write, listed in rule 1.

**SA-007 · process · medium · Open · R-01 · verdict pending**
*Observation:* deviation flags found after the stage-4 checkpoint (DF-9 and DF-10 while extracting knowledge from legacy documents, DF-11 in the cross-section pass) have no defined protocol. The run added them with proposed dispositions and obtained the owner's confirmation through a reply to a later, different message.
*Proposal:* define a "late DF" rule: Accept / Defer / Reject need a recorded owner acknowledgement (a D-entry quoting the reply); a Fix returns to an R1 amendment.

**SA-008 · verification · high · Open · R-01 · verdict pending**
*Observation:* what the driver can and cannot do was discovered mid-run. The binding already declared `ui.trusted_clicks: false`, but real clicks on «إضافة موعد» and typed or clicked input on the date picker and Select widgets silently did nothing, costing several attempts. The 10-minute budget (2.5 minutes used) was not the constraint; driver capability was. As a result the spec is Approved with the whole add-form path and several UI states (`V-11`) only `code-verified-only`.
*Proposal:* add a stage-0 or stage-3 **driver capability probe** (click, type, open an overlay, select an option) that records what works in the run record, and a sanctioned, named fallback for the rest (same-origin `fetch` under the real session = `runtime-synthetic`). Measure the budget on productive time, or drop it in favour of a step count.

**SA-009 · gate · high · Open · R-01 · verdict pending**
*Observation:* a remediation of about 30 lines in one file produced three specs, three tags, ten staged paths and roughly ten approval round-trips. The two ripple patches (F2, F10) only reword one Deferred row each, yet each cost a PATCH bump, a tag, §13C and §13D rows and an INDEX update. The same approval text was recorded in four places (run record, F19 §13D, F2 §13D, F10 §13D).
*Proposal:* a lighter path for annotation-only ripples (no tag or no version bump, one pointer row); record the approval once and reference its id elsewhere; offer C1 earlier in the run for small remediations.

**SA-010 · tooling · low · Open · R-01 · verdict pending**
*Observation:* `lint` read a Deferred cell as a Resolved flag because the cell contained the word "Resolved" ("F19's share Resolved in SPEC-F19…"), and warned `L05-df-ac: DF-9 is Resolved but cites no AC`. Status appears to be matched by substring. Rewording fixed it. Legacy specs F2 and F10 still emit 30 warnings between them (pre-existing).
*Proposal:* parse the status by its leading keyword (`Resolved(`, `Accepted(`, `Deferred(`, `Rejected(`).

**SA-011 · process · medium · Open · R-01 · verdict pending**
*Observation:* the §14 self-check, including the five-question "rebuildable from the spec alone" test and the PASS verdict, was authored by the same agent that wrote the spec. `lint` checks structure and links, not truth. The author knows the answers.
*Proposal:* an optional independent pass: a second agent (or the owner) answers the five questions from the spec only, without repository access; record who answered.

**SA-012 · environment · medium · Open · R-01 · verdict pending**
*Observation:* `TEST_DATABASE_URL`, with credentials, was exported in the shell and pointed at the live shared database, so `npm test` ran the contract suites against live data. The skill's hygiene rules (prefix, cleanup, X1) limit the damage but the preflight did not mention that the binding's `TEST_COMMAND` would write to the live database.
*Proposal:* preflight note: list environment variables that make `TEST_COMMAND` use a database, and state which database. (Credential values must never be copied into a spec, run record or this file.)

**SA-013 · template · medium · Open · R-01 · verdict pending**
*Observation:* the template has no place for a decision record. Carrying decisions (D-01…D-15, AD-01…AD-08) and nine rejected proposals from legacy documents into §13B needed a custom table and an `RP-` prefix that the ID conventions do not list. `lint` accepted it. `genesis.md` says legacy documents are inputs and their fate is a question, but gives no guidance on preserving their rationale when the owner asks for deletion (Rule 9, zero knowledge deletion, versus an explicit instruction).
*Proposal:* add a decision-record sub-block and `RP-` (rejected proposal) to the template and ID conventions; add a short procedure to `genesis.md` for folding then deleting legacy documents (extract, record, gate the deletion with X1, fix references).

**SA-014 · tooling · low · Open · R-01 · verdict pending**
*Observation:* `drift` for a Draft feature with no tag printed "No features found." (first, before the registry row existed as Verifying) and later "? unverifiable — no tag and no last-verified date to compare against". The first message reads like a tool failure.
*Proposal:* say "F19 has no release tag yet (first run)" and name what to do.

**SA-015 · docs · low · Open · R-01 · verdict pending**
*Observation:* the evidence label for a scripted `.click()` (`runtime-js-click`) is well defined, but the same run also needed a label for rows created by `fetch` under the browser session. `runtime-synthetic` ("injected conditions") covers it only loosely.
*Proposal:* clarify in `gates/evidence.md` that requests sent from the page context outside the UI are `runtime-synthetic`, and say what they do and do not prove (server contract and rendering, not the form).

## 4. What worked well (do not lose these in 1.1.0)

- **E1 stop:** `SYNC` with no spec on disk was caught at preflight; the mode was confirmed with the owner, never inferred.
- **Gate discipline:** T1, R1, X1 and C1 filled statements, replies recorded verbatim (file arguments kept Arabic text safe), no tag, push or deletion without its own form. X1 stopped a deletion the owner had already asked for until the exact command was shown.
- **Three sources of truth** found real defects that reading code alone would not: the dashboard view using the Berlin `CURRENT_DATE` and counting cancelled appointments, an absent rate limit, unused composable mutations, redundant indexes, and the unaddressed accessibility flags of two other specs.
- **Re-verification of legacy claims:** the dashboard-view claim from the old document was re-read from `pg_get_viewdef` before it was written down, and turned out to be partly different.
- **Mechanical checks:** `registry check` (9/9), `drift` (own versus ripple, clean after tagging), `inventory` (6 of 6 endpoints), the `finalize plan` dry-run diff, the `finalize staged` count check, tag creation refused without G1/C1, `schema fingerprint`.
- **Honest evidence labels:** `runtime-js-click`, `runtime-synthetic` and `code-verified-only`, with an anomaly note, let the spec say what was not driven.
- **Ripple rule:** the fixes were tied to the other specs that named F19 as owner, so those were patched in the same run instead of left stale.
- **Cleanup proof:** a scoped DELETE with an expected row count and a `SELECT count(*)` afterwards, audit rows kept.

## 5. Backlog for 1.1.0 (promote from section 3 when recurring or defective)

| Candidate | From | Why it is (or is not yet) promoted |
|---|---|---|
| Driver capability probe + named fallback | SA-008 | Proposed for promotion after a second run confirms the same driver limits |
| Lighter path for annotation-only ripple patches | SA-009 | Recurrence needed; the F4 run also repeated approval text |
| `finalize` expected-file set from the run record | SA-004 | Recurrence needed |
| Run-record updates folded into one commit | SA-005 | Already seen in F4 (`e79e8f7`) and F19: **recurring, promote** |
| `manifest init` / approve defaults tier, run type, skill version | SA-001 | Defect-like; promote if it recurs |
| JSON escape handling in `manifest add` | SA-002 | Defect-like; reproduce first |
| Lint status parsing by leading keyword | SA-010 | Defect-like; promote if it recurs |
| Late-DF protocol | SA-007 | Recurrence needed |
| Decision-record block and legacy-fold procedure | SA-013 | Recurrence needed |

## 6. Fixes and adjustments applied to the skill

None yet. The skill was used unmodified at 1.0.0 in R-01.

## 7. File history

| Date | Change |
|---|---|
| 2026-11-03 | Created and seeded with the findings of run R-01 (Sanad F19). Not committed. |
