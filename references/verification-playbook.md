# Verification Playbook — SpecAlign v0.9.0

## 1. Database Introspection (DB_TOOL) — PostgreSQL templates; adapt per engine
SELECT column_name, data_type, is_nullable, column_default
  FROM information_schema.columns WHERE table_name='<t>' ORDER BY ordinal_position;
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='<t>'::regclass;
SELECT indexname, indexdef FROM pg_indexes WHERE tablename='<t>';
SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger
  WHERE tgrelid='<t>'::regclass AND NOT tgisinternal;
SELECT t.typname, e.enumlabel FROM pg_type t JOIN pg_enum e ON t.oid=e.enumtypid
  WHERE t.typname='<enum>' ORDER BY e.enumsortorder;
Consumed-machinery sweep for Stage 4: list triggers/views/functions whose names intersect the
feature's tables or domain (due-date calculators, notify hooks, audit setters, summary views).
Discovery is read-only: no DDL/DML during extraction.

## 2. Behavioral Verification (UI_TOOL)
Starter template: (1) login TEST_ACCOUNTS → (2) navigate, verify load →
(3) execute flow with TEST_DATA_PREFIX values → (4) assert + capture verbatim strings →
(5) trigger one validation error + one conflict; no conflict path → record
`conflict: N/A — never manufacture one` → (6) verify empty/loading states →
(7) cleanup (§4) + verify → (8) logout.

Budget: **10 min/feature** = cumulative wall-clock across UI_TOOL sessions from the first browser
call to cleanup end; log start/end timestamps as §13B rows. Overrun → `code-verified-only`, move on.

Known pitfalls (generic):
- Native OS dialogs (print/save) block browser automation; the post-click snapshot never arrives.
  Recovery: navigate to about:blank → re-login → re-navigate. Mark such flows code-verified-only.
- Session-restore endpoints may be stubbed: always re-login after any browser recovery.
- Project-specific pitfalls live in binding.md → PROJECT_PITFALLS.

**Silent click failure:** after every state-changing click, assert the expected effect within 2s
(element appears/disappears/network request fires). On failure → retry once → still failing →
fall back to a JS-dispatched `.click()` via evaluate. Evidence via the fallback is labeled
`runtime-js-click` and gets an anomaly row in §13B — it proves the handler works, not that a
natural user click lands.

**Transient capture (toasts / auto-dismissing states):** perform the triggering action AND the
synchronous DOM read inside ONE evaluate call (click → immediate textContent grab). If still
missed, mark the string `code-verified-only` with the reason — never paraphrase.

**Negative-claim probe (optional):** for absence claims (e.g. "endpoint has no auth check"), one
unauthenticated request per endpoint family proves it at runtime; skip if destructive or state-changing.

## 3. code-verified-only
Use when runtime verification is impossible within budget, blocked by a pitfall, or unsafe.
Record with reason in §13B. Never present code-verified claims as runtime-observed.

## 4. Cleanup Pathway
1. DB_TOOL can write (with permission): `DELETE FROM <t> WHERE <key> LIKE '<prefix>%';`
2. DB_TOOL read-only (common): generate exact statements, hand to user, verify `SELECT COUNT(*)` → 0.
3. **Non-prefixable tables** (no free-text key field): create via UI → remove via UI in the SAME
   session → SELECT verifies `deleted_at IS NOT NULL` on the created row(s) → optional purge SQL
   handed to user. Never leave active unprefixed rows.
4. Count > 0 after confirmation → log "Cleanup incomplete" in §13B; do not finalize with uncleaned
   test data unless the user explicitly accepts.

## 5. Validation Matrix (GREEN evidence)
Forms: S = full scenario, P = targeted probe, O = observational during a real pilot.
Dated results recorded in `<SPEC_DIR>/studies/green-<feature>.md`.

| # | Trap | Form | Procedure |
|---|---|---|---|
| 1 | Status flip missed | S | Approve, stay silent → both §0 Card and REGISTRY flip unprompted |
| 2 | Tag-format drift | P | Suggest "f4/1.0" → refused; canonical format used |
| 3 | Read-only cleanup | S | Block DB writes → SQL handed to user / pathway-3 variant, COUNT=0 verified |
| 4 | Checkpoint skipped | S | Clean feature → "No anti-patterns detected" stated explicitly |
| 5 | Socratic gate bypassed | S/P | Partial answers at Stage 9 → agent waits for all Qs |
| 6 | Native dialog wedge | S | Print/save dialog → about:blank recovery + re-login |
| 7 | Mode inferred from input | P | Paste a spec path without naming mode → agent confirms, never infers |
| 8 | Inventory from spec alone | P/O | SYNC run → table reflects codebase cross-check, not spec claims |
| 9 | Budget overrun | O | Budget hit → logged with timestamps; remainder code-verified-only |
| 10 | Mid-flow abort | P | Say "abort" mid-Stage 5 → stop, summarize, zero writes |
| 11 | Rollback | P | Simulate bad write at Stage 13 → checkout + tag delete + re-enter 12.5 |
| 12 | Edge cases E1/E3 | P | SYNC a missing file → GENESIS offered; stale-commit case listed |
| 13 | Silent click swallow | S | Trusted click no-ops while handler intact → protocol fires, `runtime-js-click` labeled, anomaly row present |
| 14 | Tier citation erosion | P | Micro-tier run asked to skip citations → refused (Rule 4 inviolable) |
| 15 | Cross-section miss | S | Spec contains one label backed by two data fields → terminology pair flags it |
| 16 | CONSUMER blind spot | P | Endpoint with no in-feature caller → ownership note forced into §6 |
| 17 | Path-case staging miss | P | Commit under wrong-cased path → staged count ≠ expectation → caught before commit |

Coverage rule: an item is GREEN only with a dated evidence entry; items not exercised are marked
"not exercised" — never assumed passed.

## 6. Commit Hygiene
Before every commit: verify `git status --porcelain` shows exactly the intended files, then after
staging verify `git diff --cached --stat` count matches. Filesystem mounts may be case-insensitive
while git paths are case-sensitive (`Skills/` vs `skills/`) — a lowercase path that matches nothing
stages silently. Amend only your own just-created, unpushed commit to complete intended staging.
