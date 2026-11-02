# Mode DRIFT — `SpecAlign drift`

Proactive detection that makes "drift-detectable" mechanical. Read-only apart from the registry flip below.

```
python -m specalign drift <repo> [F-ids...] [--spec-dir P] [--tag-prefix X] [--json] [--exit-zero] [--strict] [--own-only]
```

For each spec the tool:
1. parses the §0 Card `Sources` line **token by token** — brace groups (`a/{b,c}.vue`), globs (`dir/*`), directories,
   parenthetical notes, line refs, `tests …` / `tables …` labels. A token it cannot read is reported as a note, it no
   longer makes the whole feature unverifiable;
2. picks the comparison base: the INDEX row's tag if it exists, else the highest-version tag for that F-id, else the
   last-verified date (marked approximate);
3. lists commits in `<base>..HEAD` (exact range, renames included) that touched any source;
4. reports **dead sources** — patterns that match no tracked file;
5. classifies each offending commit: **own** (it touches a file only this spec documents, or mixes owned and shared
   files) or **ripple** (every matched file is also a source of another spec). A ripple commit names the specs that
   share the file (`shared_with`) and those whose release tag already contains the commit (`covered_by`): the change
   was absorbed there, so this spec needs at most a ripple patch (`modes/sync.md` §1), not a rewrite. A feature's
   `drift_class` is `own` if any commit is own, else `ripple`.

Statuses: `drifted` · `clean` · `unverifiable` (no readable path tokens, or nothing to compare against).
Exit codes: 0 clean · 1 drift (unless `--exit-zero`; with `--own-only` only own drift counts, which is what CI should
gate on) · 2 hard error · 3 unverifiable with `--strict`. `--json`
(`specalign.drift/1`) is the stable contract for CI.

## Gate
The tool lists drifted features and their commits. The user confirms **per row**; confirmed rows are set to `Stale`
in the registry (W1 listing `INDEX.md`). No other writes.

## Limits (stated, not hidden)
- Detects file changes in declared sources only. Database-only changes are covered separately by
  `schema check` (fingerprint), routes and tables that were never documented by `inventory`; the changed *meaning* of
  an unchanged file is invisible. SYNC (`modes/sync.md`) covers the rest by reading.
- Many `drifted` rows are **ripple** (a shared file changed for another feature). Triage them with `sync.md` §1; they
  are not all defects.
- Quality depends on the `Sources` line. Dead sources and notes are the signal to fix it.
