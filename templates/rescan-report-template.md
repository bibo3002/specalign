# Rescan Report Template — SpecAlign v0.11.0

Use this template for every `SpecAlign rescan` run. Sections A–I are **mandatory**; one report
per rescan, filed in `studies/rescan-<ISO_DATE>-<slug>.md`. Prose language per binding
CONVENTIONS; user-facing strings verbatim in their runtime language; all metadata dates ISO 8601
(YYYY-MM-DD).

> **How to fill this template**
> - §A is **always** the first content. If §A fails, abort the rescan (Rule 1).
> - §B counts are pulled from the codebase, not invented; cite the path you counted from.
> - §C detects orphans (spec files without INDEX rows). One row per anomaly.
> - §D proposes new INDEX rows only (never modifies Approved rows).
> - §E uses the structured schema — no prose drift flags.
> - §F output comes from `scripts/drift_probe.py --json`, not manual `git log` walks.
> - §G refreshes the "Next recommended pilot" note when the current candidate is now Approved.
> - §H records the 5 min/survey / 20 min total budget with timestamps.

---

## §A. Binding Status

| Field | Status | Notes |
|---|---|---|
| `git status --short` | clean / dirty | If dirty tracked files → STOP, fix before proceeding. |
| `binding.md` present | yes / no | If no → STOP, follow `SpecAlign init` first. |
| Protected fields (`TEST_ACCOUNTS`, `PROJECT_PITFALLS`, `CONVENTIONS`) | unchanged / proposed | Never auto-touched. |
| Machine-derived fields | unchanged / proposed | List proposed minimal edits if any. |

**Preflight commands run:**
1. `git status --short` → expected empty.
2. `test -f docs/specs/binding.md && echo OK` → expected `OK`.
3. `python3 .opencode/skills/specalign/scripts/drift_probe.py <repo> --spec-dir <SPEC_DIR> --json > /tmp/drift.json && echo OK`
   → expected `OK`. Output saved at `/tmp/drift.json`, summarized in §F.

---

## §B. Discovery Counts

| Axis | Count | Source path(s) |
|---|---|---|
| Routes | n | `src/router/index.ts` |
| Pages (non-stub) | n | `src/pages/**/*.vue` excluding `UnderConstruction.vue` |
| Stubs (UnderConstruction) | n | matches for `UnderConstruction.vue` imports |
| API endpoint groups | n | `server/index.ts` `app.<verb>(...)` calls |
| Composables | n | `src/composables/*.ts` |
| Pinia stores | n | `src/stores/*.ts` |
| Component dirs | n | `src/components/<dir>/` |
| Spec files on disk | n | `docs/specs/SPEC-F*.md` |
| INDEX rows total | n | `docs/specs/INDEX.md` table |

---

## §C. Orphan Spec Files

Spec files present on disk without a matching INDEX row, or INDEX rows whose `SPEC-F*.md` is
missing. **One row per anomaly** — fix by adding the row or restoring the file.

| F-id | Spec file | INDEX row | Tag in `git tag` | Action |
|---|---|---|---|---|
| F{n} | `docs/specs/SPEC-F{n}-slug.md` | missing / present | missing / present | add row / restore file / set Stale |

---

## §D. New INDEX Rows Proposed

New features discovered in the codebase without a spec. Each row uses the same shape as INDEX.md,
plus a one-line rationale.

| ID | Title | Type | Rationale (file:line evidence) |
|---|---|---|---|
| F{n} | {title} | Page / Tab / Cross-cutting | `src/.../X.vue:42` — what the code does |

If no new rows: state **"§D: no new rows proposed"** explicitly (silence ≠ zero).

---

## §E. Drift Flags on Existing Rows

Structured flags only. **Type** is one of the enum below; **Evidence** must cite `file:line` or a
verifiable SQL/browser step; **Action** says what to do (SYNC, document at next SYNC, leave).

| F-id | Type | Evidence | Action |
|---|---|---|---|
| F{n} | `version-mismatch` | `tag is v0.1.0 but Tab is production-complete` | SYNC bump → 1.0.0 |
|        | `behavior-expanded`  | `NewFilePage.vue` now reuses `TabBasicData:createMode` | Document at next SYNC |
|        | `tag-missing`        | Approved row but `git tag spec/F{n}-*` returns nothing | Investigate, restore or flip Stale |
|        | `stub-501`           | `GET /api/auth/me` returns 501 | Document as known limitation |
|        | `enum-mismatch`      | `fees_status_enum` gained a value the spec doesn't list | SYNC update §4 |

**Enum (exhaustive — extend, don't rename):**
`version-mismatch` · `behavior-expanded` · `tag-missing` · `stub-501` · `enum-mismatch` ·
`lookup-richer` · `accessibility-regression` · `permission-gap` · `schema-drift`

---

## §F. Spec-Level Drift (drift_probe.py)

| Source | Output |
|---|---|
| Command | `python3 scripts/drift_probe.py <repo> --json` |
| Features scanned | n |
| `clean` | n |
| `drifted` | n (list F-ids) |
| `unverifiable` | n (list F-ids with reason) |

Detail for `drifted` and `unverifiable` rows lives in `/tmp/drift.json` (or attach inline if
short). At least one drifted row → consider scheduling a SYNC for that feature.

If `drift_probe.py` is unavailable (legacy repo), fall back to:
```bash
git log --since=<watermark> --name-only --pretty=format: -- <Approved sources>
```
and record the result here with the label `fallback-manual`.

---

## §G. Next Recommended Pilot

| Field | Value |
|---|---|
| Current recommendation | `F{n} — {title}` (from INDEX.md) |
| Current status of that row | Undocumented / Draft / Verifying / Approved |
| Action this run | keep / rotate |
| New recommendation (if rotated) | `F{n} — {title}` |
| Reasoning (one sentence) | Why this candidate beats the rest of the Undocumented pool. |

Rotation rule: if the current recommendation is now `Approved`, the next-best Undocumented row
wins, applying the pilot-selection heuristics from SKILL.md (Prefer: full CRUD + 1–3 lookups +
≤10 min verifiable; Avoid combining high transaction complexity with high UI complexity).

---

## §H. Budget & Timing

| Field | Value |
|---|---|
| Start timestamp (ISO 8601 UTC) | {ts} |
| End timestamp (ISO 8601 UTC) | {ts} |
| Wall-clock elapsed | {min} min |
| Budget cap | 5 min/feature-surveyed, 20 min total |
| Budget honored? | yes / no (justify if no) |

---

## §I. Approval

Per Stage 12.5 gate (see SKILL.md `Rescan Write Permission Gate`):

> «I approve writing/editing `<files>` for the rescan, including the finalization commit.»

Approver: {name / handle} — Timestamp: {ISO 8601 UTC} — Files touched: {list}

If zero rows were added and zero drift flips were proposed, the statement collapses to:

> «I confirm the rescan was a no-op: no INDEX changes, no drift flips.»

---

## Validation Status

- [ ] §A binding status recorded (clean tree, protected fields unchanged).
- [ ] §B counts cited from real paths (no invented numbers).
- [ ] §C orphan-spec check executed (zero is a stated result, not silence).
- [ ] §D explicit zero or populated table.
- [ ] §E flags use the structured schema; each Evidence column is a `file:line` or SQL ref.
- [ ] §F drift_probe output included; if missing, manual fallback labeled as such.
- [ ] §G pilot recommendation reviewed.
- [ ] §H budget honored; overrun justified.
- [ ] §I approval statement in the exact form above.