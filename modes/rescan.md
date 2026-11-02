# Modes INIT and RESCAN — bind a project, then keep the registry honest

## `SpecAlign init` (fresh repo without `binding.md` / `INDEX.md`)
Agent-executed:
1. Presence scan: `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` → propose `PROJECT_MAP`.
2. Read MCP/tool configs → propose `DB_TOOL` / `UI_TOOL` and the **adapters** (`adapters/`).
3. Git facts: first-commit date → `BASELINE_DATE`; tag-prefix collision check → `TAG_PREFIX`.
4. Manifest cues (framework → router conventions) are read contextually, not parsed.
5. Draft `binding.md` from `templates/binding.template.md`; **protected fields stay placeholders** (`TEST_ACCOUNTS`,
   `PROJECT_PITFALLS`, `CONVENTIONS` — the last drafted as *proposed*).
6. Discover candidate features (routes, tab components, endpoint groups) → propose INDEX rows `Undocumented`.
7. ⚠️ **Gate:** show the full draft + rows, take corrections, then write (W1).

## `SpecAlign rescan` (maintenance)
Same scan as init, **diffed against the existing files**. Machine-derived binding fields: minimal-edit proposals.
Protected fields are never touched. INDEX: new features as `Undocumented`; flag vanished routes; Approved rows are
never modified.

### Preflight (mandatory)
1. `git status --short` empty (untracked noted, dirty tracked → STOP).
2. `binding.md` parses.
3. `python -m specalign registry check <repo>` and `python -m specalign drift <repo> --json --exit-zero` run;
   outputs saved for §F. If the CLI is unavailable, label the fallback `fallback-manual`; never reimplement it silently.

### Report (`templates/rescan-report-template.md`, sections A–I)
A binding status · B discovery counts · C orphan spec files · D new INDEX rows · E drift flags (Type / Evidence /
Action) · F spec-level drift (tool output) · G next pilot · H budget (5 min/survey, 20 min total) · I approval.

### Write gate
Show the exact `git diff` of `INDEX.md` before any write, then **W1** (`docs/specs/INDEX.md`); a rescan with nothing
to change closes with **N1**.

### Anti-patterns
Modifying an Approved row's version/tag "to fix a typo" · using rescan as a covert SYNC · skipping the diff before the
write · drift flags without an Evidence column · reimplementing the tool · omitting the orphan check because "zero is
implied" · letting the budget drift.

## CI
Adopters copy `templates/adopter-ci.yml`: `registry check` blocks merges; `drift` is reported, not blocking.
